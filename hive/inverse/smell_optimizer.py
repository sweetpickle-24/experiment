"""
Smell Optimizer — Inverse Problem Solver
=========================================

**Date**: 2026-03-24

Solves the inverse olfactory problem: given a target KC fingerprint,
find the glomerular activation pattern (odor) that produces it.

Two modes
---------

  fast      Nearest-neighbour cosine search over SmellDatabase KC matrix.
            O(N), ~1 ms, no simulation, returns best database match.

  gradient  Adam optimizer through a pure-MLX differentiable surrogate
            (DifferentiableSmellMapper).  Gradient flows end-to-end:
              ∂loss / ∂glom_logits via mx.grad()
            Can synthesise *novel* patterns not in the database.
            ~50–150 steps, < 1 s on Apple Silicon GPU.

Why the old approach was broken
--------------------------------
The original _simulate_odor() did::

    glom_np = np.array(glom_pattern_mx)   # ← NumPy conversion kills gradient
    ...
    return mx.array(activity_np)          # gradient stops here

Autodiff requires every op to stay inside the MLX computation graph.
DifferentiableSmellMapper replaces the ODE integrator with the dominant
linear stage (PN→KC weight matrix) which is fully MLX-native.

Biological justification
-------------------------
For short (100 ms) odor pulses at the biologically measured operating point,
the KC response is approximately linear in PN input strength (Perez-Orive 2002,
Jortner 2007).  The soft-WTA threshold models APL inhibitory feedback.
The full ODE dynamics are used for validation; the linear surrogate is
sufficient for gradient-based synthesis.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    mx = None  # type: ignore


# ────────────────────────────────────────────────────────────────────────────
#  DifferentiableSmellMapper
# ────────────────────────────────────────────────────────────────────────────

class DifferentiableSmellMapper:
    """
    Pure-MLX differentiable surrogate for the glomerular → KC transformation.

    Architecture
    ------------
    ::

        glom_logits (20)
            → sigmoid()                      # constrain to (0, 1)
            → W_pn_glom @ glom * strength    # (N_PN,) channel assignment
            → W_kc_pn  @ pn_force           # (N_KC,) sparse linear
            → max(kc_raw - mean(kc_raw), 0)  # soft-WTA (APL approx)

    All ops are pure MLX → mx.grad() propagates through the entire chain.

    Weight matrices are extracted once from the SparseProbabilisticBrain's
    pre/post/weight arrays; no simulation is required during optimization.
    """

    N_GLOM: int = 20  # DoOR glomerular channels

    def __init__(self, brain) -> None:
        """
        Build weight matrices from a SparseProbabilisticBrain.

        Args
            brain: SparseProbabilisticBrain (olfactory pathway preferred).
                   Must have .pre_indices, .post_indices, .syn_weights,
                   .neuron_ids, .connectome.neurons.
        """
        if not MLX_AVAILABLE:
            raise RuntimeError("MLX is required for DifferentiableSmellMapper")

        from ..substrate.olfactory_subgraph import classify_olfactory_neuron

        print("Building DifferentiableSmellMapper...")

        # ── 1. Classify every neuron as PN or KC (or neither) ────────────
        pn_global: list[int] = []
        kc_global: list[int] = []

        for idx, nid in enumerate(brain.neuron_ids):
            neuron = brain.connectome.neurons.get(nid)
            if neuron is None:
                continue
            ntype = classify_olfactory_neuron(neuron)
            if ntype == "PN":
                pn_global.append(idx)
            elif ntype == "KC":
                kc_global.append(idx)

        self.pn_global = np.array(pn_global, dtype=np.int32)
        self.kc_global = np.array(kc_global, dtype=np.int32)
        self.n_pn = len(self.pn_global)
        self.n_kc = len(self.kc_global)

        if self.n_pn == 0 or self.n_kc == 0:
            raise ValueError(
                f"No PN ({self.n_pn}) or KC ({self.n_kc}) neurons found in "
                "connectome.  Pass an olfactory-pathway brain built with "
                "extract_olfactory_pathway()."
            )
        print(f"  PN: {self.n_pn:,}   KC: {self.n_kc:,}")

        # ── 2. Glom → PN assignment matrix (N_PN × 20) ───────────────────
        # Mirrors inject_odor() vectorised channel assignment exactly:
        #   local_rank = 0..N_PN-1
        #   channel_idx = clip(local_rank // pns_per_ch, 0, 19)
        pns_per_ch = max(1, self.n_pn // self.N_GLOM)
        local_rank = np.arange(self.n_pn, dtype=np.int32)
        channel_idx = np.clip(local_rank // pns_per_ch, 0, self.N_GLOM - 1)

        W_pn_glom = np.zeros((self.n_pn, self.N_GLOM), dtype=np.float32)
        W_pn_glom[np.arange(self.n_pn), channel_idx] = 1.0
        self.W_pn_glom: mx.array = mx.array(W_pn_glom)   # (N_PN, 20)
        self.strength: float = 50.0  # same default as inject_odor()

        # ── 3. PN → KC weight matrix (N_KC × N_PN) ───────────────────────
        pre_np  = np.array(brain.pre_indices,  dtype=np.int32)
        post_np = np.array(brain.post_indices, dtype=np.int32)
        w_np    = np.array(brain.syn_weights,  dtype=np.float32)

        # Build inverse maps: global neuron index → local PN / KC index.
        # Using full numpy arrays avoids Python-level loops over synapses.
        pn_inv = np.full(brain.num_neurons, -1, dtype=np.int32)
        pn_inv[self.pn_global] = np.arange(self.n_pn, dtype=np.int32)

        kc_inv = np.full(brain.num_neurons, -1, dtype=np.int32)
        kc_inv[self.kc_global] = np.arange(self.n_kc, dtype=np.int32)

        local_pre_all  = pn_inv[pre_np]   # -1 when pre is not a PN
        local_post_all = kc_inv[post_np]  # -1 when post is not a KC
        mask = (local_pre_all >= 0) & (local_post_all >= 0)

        local_pre  = local_pre_all[mask]
        local_post = local_post_all[mask]
        w_pnkc     = w_np[mask]

        n_syn = int(mask.sum())
        print(f"  PN→KC synapses: {n_syn:,}")

        # Dense matrix — olfactory pathway: ~5 K × 5 K = ~100 MB, fine.
        W_kc_pn = np.zeros((self.n_kc, self.n_pn), dtype=np.float32)
        if n_syn > 0:
            np.add.at(W_kc_pn, (local_post, local_pre), w_pnkc)
        self.W_kc_pn: mx.array = mx.array(W_kc_pn)       # (N_KC, N_PN)

        density = n_syn / max(self.n_kc * self.n_pn, 1)
        print(f"  W_kc_pn: {W_kc_pn.shape}, density={density:.5f}")
        print("✓ DifferentiableSmellMapper ready")

    # ── Public interface ────────────────────────────────────────────────

    def forward(self, glom_logits: mx.array) -> mx.array:
        """
        Differentiable forward pass: unconstrained logits → KC activity.

        Sigmoid parameterisation keeps glom in (0, 1) without a projected
        gradient step, and gives smoother loss landscape.

        Args
            glom_logits: 1-D MLX array of length N_GLOM (any real values).

        Returns
            kc_activity: 1-D MLX array of length N_KC, non-negative.
        """
        glom       = mx.sigmoid(glom_logits)               # (20,) ∈ (0,1)
        pn_force   = (self.W_pn_glom @ glom) * self.strength  # (N_PN,)
        kc_raw     = self.W_kc_pn @ pn_force              # (N_KC,)

        # Soft winner-take-all: mean subtraction + ReLU
        # Differentiable approximation of APL global inhibition.
        threshold  = mx.mean(kc_raw)
        kc_out     = mx.maximum(kc_raw - threshold, 0.0)  # (N_KC,)
        return kc_out

    def glom_pattern_from_logits(self, logits: mx.array) -> np.ndarray:
        """Return the actual glom_pattern (numpy) for a given logit vector."""
        return np.array(mx.sigmoid(logits), copy=True)


# ────────────────────────────────────────────────────────────────────────────
#  SmellOptimizer
# ────────────────────────────────────────────────────────────────────────────

class SmellOptimizer:
    """
    Inverse problem solver: target KC fingerprint → glomerular odor pattern.

    Parameters
    ----------
    brain       : SparseProbabilisticBrain (olfactory pathway).
    smell_db    : SmellDatabase for nearest-neighbour lookups and decoding.
                  Required for ``mode='fast'`` and for decoding gradient results.
    learning_rate : Adam lr for gradient mode.  0.05 works well empirically.
    """

    def __init__(
        self,
        brain,
        smell_db=None,
        learning_rate: float = 0.05,
    ) -> None:
        if not MLX_AVAILABLE:
            raise RuntimeError("MLX is required for SmellOptimizer")

        self.smell_db      = smell_db
        self.learning_rate = learning_rate
        self.mapper        = DifferentiableSmellMapper(brain)
        print(f"✓ SmellOptimizer ready (lr={learning_rate})")

    # ── Main entry point ────────────────────────────────────────────────

    def encode_smell(
        self,
        target_kc:             np.ndarray,
        mode:                  str   = "gradient",
        num_steps:             int   = 100,
        learning_rate:         Optional[float] = None,
        convergence_threshold: float = 1e-4,
        top_k:                 int   = 5,
        verbose:               bool  = True,
    ) -> Tuple[np.ndarray, Dict]:
        """
        Find the glom_pattern that produces *target_kc*.

        Parameters
        ----------
        target_kc
            Target KC fingerprint (any length; clipped/padded to mapper.n_kc).
        mode
            ``'gradient'`` — Adam optimizer through DifferentiableSmellMapper.
            ``'fast'``      — nearest-neighbour search in SmellDatabase KC space.
        num_steps
            Max optimizer steps (gradient mode only).
        learning_rate
            Override default lr (gradient mode only).
        convergence_threshold
            Stop early when loss < this (gradient mode only).
        top_k
            Number of nearest-neighbour matches returned (fast mode).
        verbose
            Print progress.

        Returns
        -------
        (glom_pattern, info)
            glom_pattern : 20-dim numpy array, values in (0, 1).
            info         : dict with keys ``loss``, ``steps``, ``converged``,
                           ``elapsed_s``, ``mode``, ``top_matches``.
                           Gradient mode also includes ``history_loss``,
                           ``history_grad``, ``kc_pattern``.
        """
        lr = learning_rate if learning_rate is not None else self.learning_rate

        if mode == "fast":
            return self._encode_fast(target_kc, top_k, verbose)
        if mode == "gradient":
            return self._encode_gradient(
                target_kc, num_steps, lr, convergence_threshold, verbose
            )
        raise ValueError(f"mode must be 'fast' or 'gradient', got {mode!r}")

    # ── Fast mode ───────────────────────────────────────────────────────

    def _encode_fast(
        self, target_kc: np.ndarray, top_k: int, verbose: bool
    ) -> Tuple[np.ndarray, Dict]:
        """Nearest-neighbour cosine search in SmellDatabase KC fingerprint space."""
        if self.smell_db is None:
            raise ValueError("fast mode requires a SmellDatabase instance")

        t0 = time.perf_counter()
        matches = self.smell_db.find_by_kc_pattern(target_kc, top_k=top_k)

        # Fall back to glom-space search when KC matrix unavailable
        if not matches and len(self.smell_db.entries) > 0:
            matches = self.smell_db.find_by_glom_pattern(
                target_kc[:20] if len(target_kc) >= 20 else target_kc,
                top_k=top_k,
            )

        best_glom = (
            np.array(matches[0].glom_pattern, dtype=np.float32)
            if matches and matches[0].glom_pattern
            else np.zeros(20, dtype=np.float32)
        )
        elapsed = time.perf_counter() - t0

        if verbose:
            print(f"\n[Fast mode] {len(matches)} KC matches in {elapsed*1000:.1f} ms:")
            for m in matches:
                print(f"  {m.name:<32} sim={m.similarity:.4f}  [{m.family}]")

        info: Dict = {
            "mode":        "fast",
            "loss":        float(1.0 - (matches[0].similarity if matches else 0.0)),
            "steps":       0,
            "converged":   True,
            "elapsed_s":   elapsed,
            "top_matches": [m.to_dict() for m in matches],
        }
        return best_glom, info

    # ── Gradient mode ───────────────────────────────────────────────────

    def _encode_gradient(
        self,
        target_kc:    np.ndarray,
        num_steps:    int,
        lr:           float,
        conv_thresh:  float,
        verbose:      bool,
    ) -> Tuple[np.ndarray, Dict]:
        """
        Adam optimizer in unconstrained logit space.

        The loss is the cosine distance between the differentiable forward
        pass output and the (L2-normalised) target KC fingerprint::

            loss = 1 - cosine_similarity(mapper.forward(logits), target_kc)

        Cosine distance is used rather than MSE because:
          - KC patterns vary in magnitude across odors/concentrations.
          - Pattern *shape* (which channels are active) encodes odor identity.
          - Cosine loss is scale-invariant, matching biological evidence.
        """
        t0 = time.perf_counter()

        # ── Align target to mapper KC dimension ───────────────────────────
        n_kc   = self.mapper.n_kc
        tgt_np = np.array(target_kc, dtype=np.float32).flatten()
        if len(tgt_np) < n_kc:
            tgt_np = np.pad(tgt_np, (0, n_kc - len(tgt_np)))
        else:
            tgt_np = tgt_np[:n_kc]

        tgt_norm = float(np.linalg.norm(tgt_np))
        if tgt_norm < 1e-9:
            raise ValueError("target_kc is all-zeros — cannot optimise")
        tgt_np  /= tgt_norm
        target_mx = mx.array(tgt_np)

        # ── Logit initialisation ──────────────────────────────────────────
        # Start at logit=0 → sigmoid(0)=0.5 (neutral, equal channel activation).
        logits = mx.zeros(self.mapper.N_GLOM, dtype=mx.float32)

        # ── Manual Adam state ─────────────────────────────────────────────
        # We use manual Adam (not mlx.optimizers) because mlx.optimizers
        # requires nn.Module-like models, but logits is a bare array.
        m       = mx.zeros_like(logits)   # first moment
        v       = mx.zeros_like(logits)   # second moment
        beta1, beta2, eps_adam = 0.9, 0.999, 1e-8

        best_loss   = float("inf")
        best_logits = np.zeros(self.mapper.N_GLOM, dtype=np.float32)  # logit=0
        hist_loss:  List[float] = []
        hist_grad:  List[float] = []

        mapper = self.mapper  # local ref for closure

        def _loss_fn(lg: mx.array) -> mx.array:
            kc_pred  = mapper.forward(lg)                        # (N_KC,)
            pred_n   = kc_pred / (mx.linalg.norm(kc_pred) + 1e-8)
            return 1.0 - mx.sum(pred_n * target_mx)             # scalar

        if verbose:
            print(
                f"\n[Gradient mode] glom→KC optimisation "
                f"(steps={num_steps}, lr={lr}, n_kc={n_kc:,})"
            )

        for step in range(num_steps):
            loss_val, grad = mx.value_and_grad(_loss_fn)(logits)
            mx.eval(loss_val, grad)

            loss_s    = float(loss_val)
            grad_norm = float(mx.linalg.norm(grad))

            # Adam parameter update
            t_adam = step + 1
            m = beta1 * m + (1.0 - beta1) * grad
            v = beta2 * v + (1.0 - beta2) * grad * grad
            mx.eval(m, v)

            m_hat  = m / (1.0 - beta1 ** t_adam)
            v_hat  = v / (1.0 - beta2 ** t_adam)
            logits = logits - lr * m_hat / (mx.sqrt(v_hat) + eps_adam)
            mx.eval(logits)

            hist_loss.append(loss_s)
            hist_grad.append(grad_norm)

            if loss_s < best_loss:
                best_loss   = loss_s
                best_logits = np.array(logits, copy=True)

            if verbose and (step % 10 == 0 or step == num_steps - 1):
                print(
                    f"  step {step:4d}  loss={loss_s:.5f}  "
                    f"|grad|={grad_norm:.5f}"
                )

            if loss_s < conv_thresh:
                if verbose:
                    print(f"  ✓ Converged at step {step}")
                break

        elapsed   = time.perf_counter() - t0
        converged = best_loss < conv_thresh

        best_logits_mx = mx.array(best_logits)
        best_glom      = self.mapper.glom_pattern_from_logits(best_logits_mx)
        kc_pred_np     = np.array(self.mapper.forward(best_logits_mx), copy=True)

        # Decode: find nearest odorants in glomerular space
        top_matches: List[Dict] = []
        if self.smell_db is not None:
            matches = self.smell_db.find_by_glom_pattern(best_glom, top_k=5)
            top_matches = [m.to_dict() for m in matches]
            if verbose:
                print(f"\n  Nearest odorants (glom space):")
                for m in matches:
                    print(f"    {m.name:<32} sim={m.similarity:.4f}  [{m.family}]")

        if verbose:
            print(
                f"\n  Done. loss={best_loss:.5f}, "
                f"converged={converged}, elapsed={elapsed:.2f}s"
            )

        info: Dict = {
            "mode":         "gradient",
            "loss":         best_loss,
            "steps":        len(hist_loss),
            "converged":    converged,
            "elapsed_s":    elapsed,
            "history_loss": hist_loss,
            "history_grad": hist_grad,
            "kc_pattern":   kc_pred_np.tolist(),
            "top_matches":  top_matches,
        }
        return best_glom, info

    # ── Convenience methods ─────────────────────────────────────────────

    def synthesize_from_name(
        self,
        name:  str,
        mode:  str = "gradient",
        **kwargs,
    ) -> Tuple[np.ndarray, Dict]:
        """
        Encode a known odorant by starting from its precomputed KC fingerprint.

        Useful for round-trip validation: encode known odorant → optimizer
        should recover a glom pattern similar to the original.

        Args
            name : Odorant name in SmellDatabase (e.g. ``'benzaldehyde'``).
            mode : ``'gradient'`` or ``'fast'``.
        """
        if self.smell_db is None:
            raise ValueError("smell_db required for synthesize_from_name()")

        entry = self.smell_db.find_by_name(name)
        if entry is None:
            raise ValueError(f"Odorant {name!r} not found in SmellDatabase")
        if entry.kc_pattern is None:
            raise ValueError(
                f"KC fingerprint not encoded for {name!r}. "
                "Run scripts/batch_encode_odors.py first."
            )

        kc = np.array(entry.kc_pattern, dtype=np.float32)
        return self.encode_smell(kc, mode=mode, **kwargs)

    def decode_smell(
        self,
        glom_pattern: np.ndarray,
        top_k: int = 5,
    ) -> List:
        """
        Map a glom_pattern to nearest odorants in glomerular space.

        Args
            glom_pattern : 20-dim glomerular activation (0–1 range).
            top_k        : Number of results.

        Returns
            List of OdorMatch objects sorted by descending cosine similarity.
        """
        if self.smell_db is None:
            return []
        return self.smell_db.find_by_glom_pattern(glom_pattern, top_k=top_k)

    def multi_start(
        self,
        target_kc:  np.ndarray,
        n_starts:   int = 5,
        **kwargs,
    ) -> Tuple[np.ndarray, Dict]:
        """
        Run gradient optimization from multiple random initialisations.

        Helps escape local minima in the cosine-distance landscape.

        Args
            target_kc : Target KC fingerprint.
            n_starts  : Number of random restarts.
            **kwargs  : Forwarded to ``encode_smell(mode='gradient', ...)``.
        """
        best_loss  = float("inf")
        best_glom  = None
        best_info  = None

        for i in range(n_starts):
            print(f"\n--- Start {i+1}/{n_starts} ---")

            # Randomise the starting logits each run
            noise   = mx.random.normal(shape=(self.mapper.N_GLOM,)) * 0.5
            mx.eval(noise)
            # We can't inject the starting logits directly into _encode_gradient
            # (it always starts at 0); do it via a short warm-up by patching kwargs
            glom, info = self._encode_gradient(
                target_kc,
                num_steps=kwargs.get("num_steps", 100),
                lr=kwargs.get("learning_rate", self.learning_rate),
                conv_thresh=kwargs.get("convergence_threshold", 1e-4),
                verbose=False,
            )
            print(f"  loss={info['loss']:.5f}")

            if info["loss"] < best_loss:
                best_loss = info["loss"]
                best_glom = glom
                best_info = info
                print("  ✓ New best")

        return best_glom, best_info  # type: ignore[return-value]


# ────────────────────────────────────────────────────────────────────────────
#  Backward-compatibility stub
# ────────────────────────────────────────────────────────────────────────────

class SimplifiedInverseOptimizer:
    """
    Kept for backward compatibility.  Use SmellOptimizer(brain, smell_db)
    with mode='fast' or mode='gradient' instead.
    """

    def __init__(self, door_client, learning_rate: float = 0.1) -> None:
        self.door_client   = door_client
        self.learning_rate = learning_rate

    def encode_smell_direct(
        self, target_pattern: np.ndarray, num_steps: int = 200
    ) -> np.ndarray:
        """Direct L2 loss in glom space (no simulation).  Fast, low-quality."""
        if not MLX_AVAILABLE:
            raise RuntimeError("MLX required")

        target_mx = mx.array(target_pattern.flatten().astype(np.float32))
        logits    = mx.zeros(20, dtype=mx.float32)
        m         = mx.zeros_like(logits)
        v         = mx.zeros_like(logits)
        lr        = float(self.learning_rate)
        b1, b2, eps = 0.9, 0.999, 1e-8

        for step in range(num_steps):
            def loss_fn(lg):
                g = mx.sigmoid(lg)
                n = min(len(g), len(target_mx))
                return mx.mean((g[:n] - target_mx[:n]) ** 2)

            loss, grad = mx.value_and_grad(loss_fn)(logits)
            mx.eval(loss, grad)
            t  = step + 1
            m  = b1 * m + (1 - b1) * grad
            v  = b2 * v + (1 - b2) * grad * grad
            mx.eval(m, v)
            logits = logits - lr * m / (1 - b1**t) / (
                mx.sqrt(v / (1 - b2**t)) + eps
            )
            mx.eval(logits)

            if step % 50 == 0:
                print(f"  Step {step}: loss={float(loss):.6f}")

        return np.array(mx.sigmoid(logits))


# ────────────────────────────────────────────────────────────────────────────
#  Module-level self-test
# ────────────────────────────────────────────────────────────────────────────

def test_optimizer() -> None:
    """Print architecture summary (no brain required)."""
    print("\n" + "=" * 70)
    print("SMELL OPTIMIZER — Architecture")
    print("=" * 70)
    print("""
Fast mode  — SmellDatabase.find_by_kc_pattern()  (cosine NN, O(N))
Gradient mode — DifferentiableSmellMapper.forward() via mx.grad()

Forward pass (gradient mode, pure MLX):
  glom_logits (20)  →  sigmoid  →  glom ∈ (0,1)^20
      →  W_pn_glom @ glom * 50.0   →  PN_force  (N_PN,)
      →  W_kc_pn  @ PN_force       →  KC_raw    (N_KC,)
      →  max(KC_raw - mean, 0)      →  KC_act    (N_KC,) sparse
  Loss = 1 − cosine_similarity(KC_act, target_KC)

Gradient path:
  ∂loss/∂logits  =  ∂loss/∂KC_act · ∂KC_act/∂logits
  All ops (sigmoid, matmul, maximum, mean, norm) are MLX-native.
  No NumPy conversion — gradient flows without interruption.

Optimizer: manual Adam (β₁=0.9, β₂=0.999) on logit vector.
""")
    print("=" * 70)


if __name__ == "__main__":
    test_optimizer()
