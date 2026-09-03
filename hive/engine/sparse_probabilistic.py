"""
Sparse Probabilistic Wave Engine - Memory Efficient

Instead of dense 3D grids, use sparse representation:
- Only track voxels containing neurons
- Direct neuron-to-neuron coupling (no full FFT)
- Still probabilistic (mean + variance)
- 100× less memory

This is the production version for full brain smell testing.

Performance optimisations (2026-03-24):
  1. mx.compile()  — JIT-compiles the inner step kernel; removes Python
                     graph-build overhead on every call (~2-3× speedup).
  2. Precomputed constants — omega0_sq, var_correction, decay scalars
                             computed once at construction, not per step.
  3. fast_mode     — dt=0.5 ms instead of 0.1 ms; 5× fewer integration
                     steps with no measurable physics error at biological
                     timescales (dt/period ≈ 0.5%).  Default off so all
                     validated tests remain bitwise compatible.
  4. deque ring buffer — amplitude_history uses collections.deque
                         (O(1) pop) instead of list.pop(0) (O(n)).
  5. Vectorised inject_odor — builds the external-force array with numpy
                              array indexing, avoiding a Python loop over
                              individual neurons.
  6. Lazy eval batching — mx.eval() only called every `eval_every` steps
                          (default 500 in compiled mode, 100 otherwise),
                          letting the MLX scheduler fill the GPU pipeline.
"""

import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import time

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    mx = None


@dataclass
class SparseProbabilisticState:
    """Probabilistic state for actual neurons (not grid voxels)."""
    mean_phase: np.ndarray      # E[φ] per neuron
    mean_velocity: np.ndarray   # E[v] per neuron
    mean_amplitude: np.ndarray  # E[A] per neuron
    var_phase: np.ndarray       # Var[φ] per neuron
    var_amplitude: np.ndarray   # Var[A] per neuron
    neuron_ids: list            # Neuron IDs
    time: float


class SparseProbabilisticBrain:
    """
    Memory-efficient probabilistic brain using sparse representation.

    Key difference from dense grid:
    - Tracks N neurons directly (not grid voxels)
    - Coupling uses synapse structure (not FFT on full space)
    - Still probabilistic (mean-field theory)
    - ~100× less memory than dense grid

    Memory: N neurons × 5 fields × 4 bytes
    - 15K neurons: 300 KB (vs. 30 MB for dense grid)
    - 139K neurons: 2.8 MB (vs. 300 MB for dense grid)

    Performance targets (olfactory pathway, 10,906 neurons, M4 Pro GPU):
    - Original:   0.54× RT  (dt=0.1 ms, no compile)
    - Compiled:   ~1.5× RT  (dt=0.1 ms, mx.compile)
    - Fast mode:  ~7× RT    (dt=0.5 ms, mx.compile)
    """

    _RECOGNISED_CONFIG_KEYS = {'dt', 'gamma', 'sigma_noise'}

    def __init__(self, connectome, config=None, use_mlx=True, fast_mode=False):
        """
        Initialise sparse probabilistic brain.

        Args:
            connectome : Connectome with neurons and synapses.
            config     : Optional physics overrides. Recognised keys are 'dt'
                         (ms), 'gamma' and 'sigma_noise'. An unrecognised key
                         raises ValueError.

                         Before 2026-09-03 this argument was accepted and then
                         silently discarded, so callers passing dt=0.01 were in
                         fact running at dt=0.1 and recording the wrong value in
                         their result files.
            use_mlx    : Use MLX GPU acceleration (recommended).
            fast_mode  : If True, use dt=0.5 ms (5× speedup) instead of
                         dt=0.1 ms.  Suitable for real-time demos; not used
                         during biological validation runs. An explicit 'dt' in
                         config takes precedence over fast_mode.
        """
        print("\n" + "="*70)
        print("SPARSE PROBABILISTIC BRAIN (Memory Efficient)")
        print("="*70)

        self.connectome = connectome
        self.config = dict(config or {})
        self.use_mlx = use_mlx and MLX_AVAILABLE
        self.fast_mode = fast_mode

        unknown = set(self.config) - self._RECOGNISED_CONFIG_KEYS
        if unknown:
            raise ValueError(
                f"Unrecognised config key(s): {sorted(unknown)}. "
                f"Recognised keys are {sorted(self._RECOGNISED_CONFIG_KEYS)}. "
                "Unknown keys are rejected rather than ignored so that a result "
                "file cannot record a parameter the engine never applied."
            )

        if self.use_mlx:
            print("✓ MLX GPU acceleration enabled")
        if self.fast_mode:
            print("⚡ fast_mode=True: dt=0.5 ms (5× speedup)")

        # Build neuron index
        self.neuron_ids = list(connectome.neurons.keys())
        self.num_neurons = len(self.neuron_ids)
        self.id_to_idx = {nid: idx for idx, nid in enumerate(self.neuron_ids)}

        print(f"Neurons: {self.num_neurons:,}")
        print(f"Synapses: {len(connectome.synapses):,}")

        # Initialise probability fields
        self._initialize_fields()

        # Build coupling structure
        self._build_coupling_structure()

        # ── Physics parameters ──────────────────────────────────────────
        # fast_mode: 5× larger step, still 10× finer than 5 ms KC timescale.
        # An explicit config['dt'] overrides fast_mode.
        self.dt = float(self.config.get('dt', 0.5 if fast_mode else 0.1))   # ms
        self.gamma = float(self.config.get('gamma', 0.1))
        self.sigma_noise = float(self.config.get('sigma_noise', 0.1))
        self.time = 0.0

        if self.dt > 2.0:
            print(f"⚠ dt={self.dt} ms exceeds the 2 ms stability ceiling for the "
                  f"APL feedback loop under forward Euler; results may be invalid.")
        print(f"Physics: dt={self.dt} ms, gamma={self.gamma}, "
              f"sigma_noise={self.sigma_noise}")

        # ── Precomputed constants (avoid recomputation every step) ───────
        self._precompute_step_constants()

        # ── Temporal memory: deque ring buffer ───────────────────────────
        # Biological basis: lamina L1/L2 H-current ~10-50 ms temporal memory.
        # T4/T5 direction selectivity requires ~20 ms past state (Haag 2017).
        self.history_max = 10
        self.history_interval_ms = 5.0
        self.amplitude_history: deque = deque(maxlen=self.history_max)
        self._last_history_time = -999.0

        # ── Build compiled step (JIT) if MLX available ───────────────────
        self._compiled_step = None
        if self.use_mlx:
            self._build_compiled_step()

        memory_mb = self.num_neurons * 5 * 4 / 1024 / 1024
        mode_tag = f"dt={self.dt}ms, {'compiled' if self._compiled_step else 'interpreted'}"
        print(f"✓ Initialised: {self.num_neurons:,} neurons, {memory_mb:.1f} MB ({mode_tag})")
        print("="*70)

    # ────────────────────────────────────────────────────────────────────
    #  Initialisation helpers
    # ────────────────────────────────────────────────────────────────────

    def _initialize_fields(self):
        """Initialise probabilistic fields for all neurons."""
        self.mean_phase = np.random.uniform(-np.pi, np.pi, self.num_neurons).astype(np.float32)
        self.mean_velocity = np.zeros(self.num_neurons, dtype=np.float32)
        self.mean_amplitude = np.ones(self.num_neurons, dtype=np.float32) * 0.1

        self.var_phase = np.ones(self.num_neurons, dtype=np.float32) * 0.1
        self.var_amplitude = np.ones(self.num_neurons, dtype=np.float32) * 0.01

        self.external_force = np.zeros(self.num_neurons, dtype=np.float32)

        # Natural frequencies (default: 10 Hz alpha)
        self.omega0 = np.ones(self.num_neurons, dtype=np.float32) * (2 * np.pi * 10.0 / 1000.0)

        self.amplitude_history = deque(maxlen=getattr(self, 'history_max', 10))
        self._last_history_time = -999.0
        self.time = 0.0

        if self.use_mlx:
            self.mean_phase     = mx.array(self.mean_phase)
            self.mean_velocity  = mx.array(self.mean_velocity)
            self.mean_amplitude = mx.array(self.mean_amplitude)
            self.var_phase      = mx.array(self.var_phase)
            self.var_amplitude  = mx.array(self.var_amplitude)
            self.external_force = mx.array(self.external_force)
            self.omega0         = mx.array(self.omega0)

    def _build_coupling_structure(self):
        """Build sparse coupling matrix from synapses with layer-specific gains."""
        print("Building coupling structure...")

        synapses = self.connectome.synapses

        is_vision = self.num_neurons > 50000
        neuron_regions: dict = {}

        if is_vision:
            print("  Analysing visual pathway structure...")
            from ..substrate.visual_pathway import VISUAL_NEURON_TYPES
            for nid, neuron in self.connectome.neurons.items():
                cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
                for region, types in VISUAL_NEURON_TYPES.items():
                    if any(keyword in cell_types_str for keyword in types):
                        neuron_regions[nid] = region
                        break

        pre_indices  = []
        post_indices = []
        weights      = []

        for syn in synapses:
            if syn.pre_id in self.id_to_idx and syn.post_id in self.id_to_idx:
                pre_indices.append(self.id_to_idx[syn.pre_id])
                post_indices.append(self.id_to_idx[syn.post_id])
                weights.append(float(syn.weight))

        self.pre_indices  = np.array(pre_indices,  dtype=np.int32)
        self.post_indices = np.array(post_indices, dtype=np.int32)
        self.syn_weights  = np.array(weights,      dtype=np.float32)

        if len(self.syn_weights) > 0:
            max_weight = np.max(self.syn_weights)
            if max_weight > 0:
                self.syn_weights = self.syn_weights / max_weight
                if self.num_neurons > 50000:
                    vision_gain = 10.0
                    self.syn_weights = self.syn_weights * vision_gain
                    print(f"  Vision network detected: {vision_gain}× coupling gain applied")
                else:
                    print("  Olfaction network: baseline coupling")

        print(f"✓ Coupling: {len(self.syn_weights):,} synapses")

        if self.use_mlx:
            self.pre_indices  = mx.array(self.pre_indices)
            self.post_indices = mx.array(self.post_indices)
            self.syn_weights  = mx.array(self.syn_weights)

    def _precompute_step_constants(self):
        """
        Precompute all per-step scalar/array constants so the hot path
        contains no recomputation.  Called after dt and gamma are set.
        """
        dt   = self.dt
        g    = self.gamma
        sig  = self.sigma_noise

        # Scalar constants (stored as Python floats for max speed)
        self._two_gamma          = float(2.0 * g)
        self._sigma_sq_dt        = float(sig * sig * dt)
        self._var_decay          = float(1.0 - 2.0 * g * dt)
        self._amp_decay          = float(1.0 - g * dt)
        self._amp_drive_dt_scale = float(0.1 * dt)   # |v| * 0.1 * dt

        # Analytical variance correction: exp(-Var[Δφ]/2) ≈ exp(-0.05)
        # Computed once; constant because we use simplified Var[Δφ]=0.1
        self._var_correction_scalar = float(np.exp(-0.1 / 2.0))

        # Per-neuron array (precomputed; never changes)
        if self.use_mlx:
            self._omega0_sq      = self.omega0 ** 2
            self._var_correction = mx.array(self._var_correction_scalar)
        else:
            self._omega0_sq_np   = np.array(self.omega0) ** 2

    def _build_compiled_step(self):
        """
        Build and JIT-compile the inner MLX step kernel with mx.compile.

        The compiled closure captures all static tensors (indices, weights,
        precomputed constants) so the hot-loop arguments are only the
        mutable state arrays and the (rarely changing) external force.

        On the first evolve() call the kernel is traced once; every
        subsequent call dispatches the pre-compiled Metal kernel without
        any Python graph-building overhead.
        """
        # Capture static tensors in closure (never change between steps)
        pre_idx      = self.pre_indices
        post_idx     = self.post_indices
        syn_w        = self.syn_weights
        omega0_sq    = self._omega0_sq
        n            = self.num_neurons

        # Scalar constants as Python floats (MLX treats them as literals
        # in the compiled graph, enabling constant folding)
        two_gamma          = self._two_gamma
        dt                 = float(self.dt)
        sigma_sq_dt        = self._sigma_sq_dt
        var_decay          = self._var_decay
        amp_decay          = self._amp_decay
        amp_drive_dt_scale = self._amp_drive_dt_scale
        var_correction     = self._var_correction_scalar

        @mx.compile
        def _step(phase, velocity, amplitude, var_phase, ext_force):
            # ── Coupling force (sparse scatter-add) ─────────────────────
            phase_pre  = phase[pre_idx]
            phase_post = phase[post_idx]
            amp_pre    = amplitude[pre_idx]

            delta_phi  = phase_pre - phase_post
            syn_forces = syn_w * mx.sin(delta_phi) * amp_pre * var_correction

            forces = mx.zeros(n, dtype=mx.float32)
            forces = forces.at[post_idx].add(syn_forces)

            # ── Damped harmonic oscillator ───────────────────────────────
            accel    = -two_gamma * velocity - omega0_sq * phase + forces + ext_force
            velocity = velocity + accel * dt
            phase    = phase + velocity * dt
            phase    = mx.arctan2(mx.sin(phase), mx.cos(phase))

            # ── Variance update ──────────────────────────────────────────
            var_phase = var_phase * var_decay + sigma_sq_dt
            var_phase = mx.clip(var_phase, 0.01, 10.0)

            # ── Amplitude update ─────────────────────────────────────────
            amp_drive = mx.abs(velocity) * amp_drive_dt_scale
            amplitude = amplitude * amp_decay + amp_drive
            amplitude = mx.clip(amplitude, 0.001, 10.0)

            return phase, velocity, amplitude, var_phase

        self._compiled_step = _step
        print("✓ mx.compile step kernel ready")

    # ────────────────────────────────────────────────────────────────────
    #  Main simulation loop
    # ────────────────────────────────────────────────────────────────────

    def evolve(self, duration: float = 100.0):
        """
        Evolve brain for *duration* ms of biological time.

        Uses the compiled MLX kernel when available, falling back to the
        interpreted step for CPU or when compilation failed.

        Eval strategy:
        - Compiled mode : flush every 500 steps (GPU pipeline stays full)
        - Interpreted   : flush every 100 steps (avoids graph blowup)
        History snapshots force an eval at the history-interval boundary,
        which naturally limits graph accumulation anyway.
        """
        num_steps = int(duration / self.dt)
        history_interval_steps = max(1, int(self.history_interval_ms / self.dt))

        use_compiled = self.use_mlx and self._compiled_step is not None
        # Fewer forced evals in compiled mode; graph is bounded by history snapshots
        eval_every = 500 if use_compiled else 100

        for step in range(num_steps):
            if use_compiled:
                (self.mean_phase,
                 self.mean_velocity,
                 self.mean_amplitude,
                 self.var_phase) = self._compiled_step(
                    self.mean_phase, self.mean_velocity,
                    self.mean_amplitude, self.var_phase,
                    self.external_force
                )
            else:
                self._step()

            self.time += self.dt

            # Periodic forced eval (non-history steps)
            if self.use_mlx and not use_compiled and step % eval_every == 0:
                mx.eval(self.mean_phase, self.mean_velocity, self.var_phase)

            # Amplitude history snapshot
            if step % history_interval_steps == 0:
                if self.use_mlx:
                    mx.eval(self.mean_amplitude)
                    snap = np.array(self.mean_amplitude, copy=True)
                else:
                    snap = self.mean_amplitude.copy()
                self.amplitude_history.append(snap)

        # Final sync
        if self.use_mlx:
            mx.eval(self.mean_phase, self.mean_velocity,
                    self.mean_amplitude, self.var_phase)

    # ────────────────────────────────────────────────────────────────────
    #  Fallback (non-compiled) step
    # ────────────────────────────────────────────────────────────────────

    def _step(self):
        """Single integration step (interpreted fallback)."""
        if self.use_mlx:
            self._step_mlx()
        else:
            self._step_numpy()
        self.time += self.dt

    def _step_mlx(self):
        """MLX interpreted step (used when compilation not yet triggered)."""
        coupling_force = self._compute_coupling_mlx()

        accel = (-self._two_gamma * self.mean_velocity
                 - self._omega0_sq * self.mean_phase
                 + coupling_force
                 + self.external_force)

        self.mean_velocity  = self.mean_velocity  + accel * self.dt
        self.mean_phase     = self.mean_phase     + self.mean_velocity * self.dt
        self.mean_phase     = mx.arctan2(mx.sin(self.mean_phase), mx.cos(self.mean_phase))

        self.var_phase      = self.var_phase * self._var_decay + self._sigma_sq_dt
        self.var_phase      = mx.clip(self.var_phase, 0.01, 10.0)

        amp_drive           = mx.abs(self.mean_velocity) * self._amp_drive_dt_scale
        self.mean_amplitude = self.mean_amplitude * self._amp_decay + amp_drive
        self.mean_amplitude = mx.clip(self.mean_amplitude, 0.001, 10.0)

    def _step_numpy(self):
        """NumPy CPU step."""
        coupling_force = self._compute_coupling_numpy()

        accel = (-self._two_gamma * self.mean_velocity
                 - self._omega0_sq_np * self.mean_phase
                 + coupling_force
                 + self.external_force)

        self.mean_velocity  += accel * self.dt
        self.mean_phase     += self.mean_velocity * self.dt
        self.mean_phase      = np.arctan2(np.sin(self.mean_phase), np.cos(self.mean_phase))

        self.var_phase       = self.var_phase * self._var_decay + self._sigma_sq_dt
        self.var_phase       = np.clip(self.var_phase, 0.01, 10.0)

        amp_drive            = np.abs(self.mean_velocity) * self._amp_drive_dt_scale
        self.mean_amplitude  = self.mean_amplitude * self._amp_decay + amp_drive
        self.mean_amplitude  = np.clip(self.mean_amplitude, 0.001, 10.0)

    def _compute_coupling_mlx(self):
        """Sparse scatter-add coupling (MLX, interpreted)."""
        phase_pre  = self.mean_phase[self.pre_indices]
        phase_post = self.mean_phase[self.post_indices]
        amp_pre    = self.mean_amplitude[self.pre_indices]

        delta_phi  = phase_pre - phase_post
        syn_forces = self.syn_weights * mx.sin(delta_phi) * amp_pre * self._var_correction

        forces = mx.zeros(self.num_neurons, dtype=mx.float32)
        forces = forces.at[self.post_indices].add(syn_forces)
        return forces

    def _compute_coupling_numpy(self):
        """Sparse scatter-add coupling (NumPy)."""
        phase_pre  = self.mean_phase[self.pre_indices]
        phase_post = self.mean_phase[self.post_indices]
        amp_pre    = self.mean_amplitude[self.pre_indices]

        delta_phi  = phase_pre - phase_post
        syn_forces = self.syn_weights * np.sin(delta_phi) * amp_pre * self._var_correction_scalar

        forces = np.zeros(self.num_neurons, dtype=np.float32)
        np.add.at(forces, self.post_indices, syn_forces)
        return forces

    # ────────────────────────────────────────────────────────────────────
    #  Temporal memory
    # ────────────────────────────────────────────────────────────────────

    def get_amplitude_delayed(self, delay_ms: float) -> np.ndarray:
        """
        Return amplitude snapshot from *delay_ms* ago.

        Biological basis: T4 receives slow inhibitory inputs (~20 ms delay)
        from trailing-side Mi4/C3/CT1 neurons (Haag et al. 2017).
        """
        if not self.amplitude_history:
            if self.use_mlx:
                return np.array(self.mean_amplitude)
            return self.mean_amplitude.copy()

        steps_back = int(delay_ms / self.history_interval_ms)
        # deque: index 0 = oldest, -1 = newest
        idx = max(0, len(self.amplitude_history) - 1 - steps_back)
        history_list = list(self.amplitude_history)
        return history_list[idx]

    # ────────────────────────────────────────────────────────────────────
    #  Odor injection
    # ────────────────────────────────────────────────────────────────────

    def inject_odor(self, glom_pattern, strength: float = 50.0):
        """
        Inject odor as external force to PN neurons.

        Fully vectorised: builds the force array with numpy indexing
        (no Python loop over individual neurons) then assigns once.

        Args:
            glom_pattern : 20-dim glomerular activation pattern.
            strength     : Injection strength multiplier.
        """
        from ..substrate.olfactory_subgraph import classify_olfactory_neuron

        # Collect PN indices (one-time classification; fast set lookup)
        pn_id_set = set()
        if hasattr(self.connectome, 'neurons'):
            for nid, neuron in self.connectome.neurons.items():
                if classify_olfactory_neuron(neuron) == 'PN':
                    pn_id_set.add(nid)

        pn_indices = np.array(
            [i for i, nid in enumerate(self.neuron_ids) if nid in pn_id_set],
            dtype=np.int32
        )

        if len(pn_indices) == 0:
            # Fallback: first 20 % of neurons
            pn_indices = np.arange(int(self.num_neurons * 0.2), dtype=np.int32)

        n_pns      = len(pn_indices)
        n_channels = len(glom_pattern)
        pns_per_ch = max(1, n_pns // n_channels)

        # ── Vectorised channel assignment ─────────────────────────────
        # Each PN gets the channel index = floor(local_rank / pns_per_ch),
        # clipped so the last channel absorbs any remainder.
        local_rank       = np.arange(n_pns, dtype=np.int32)
        channel_idx      = np.clip(local_rank // pns_per_ch, 0, n_channels - 1)
        channel_strength = np.array(glom_pattern, dtype=np.float32)[channel_idx]

        force_np = np.zeros(self.num_neurons, dtype=np.float32)
        force_np[pn_indices] = channel_strength * strength

        if self.use_mlx:
            self.external_force = mx.array(force_np)
        else:
            self.external_force = force_np

    # ────────────────────────────────────────────────────────────────────
    #  Reset
    # ────────────────────────────────────────────────────────────────────

    def reset(self, deterministic: bool = False):
        """
        Reset to initial state.

        Args:
            deterministic : If True, fixed initial conditions (for
                            reproducible validation runs).
        """
        if deterministic:
            self.mean_phase     = np.zeros(self.num_neurons, dtype=np.float32)
            self.mean_velocity  = np.zeros(self.num_neurons, dtype=np.float32)
            self.mean_amplitude = np.ones(self.num_neurons,  dtype=np.float32) * 0.1
        else:
            self.mean_phase     = np.random.uniform(-np.pi, np.pi, self.num_neurons).astype(np.float32)
            self.mean_velocity  = np.zeros(self.num_neurons, dtype=np.float32)
            self.mean_amplitude = np.ones(self.num_neurons,  dtype=np.float32) * 0.1

        self.var_phase      = np.ones(self.num_neurons, dtype=np.float32) * 0.1
        self.var_amplitude  = np.ones(self.num_neurons, dtype=np.float32) * 0.01
        self.external_force = np.zeros(self.num_neurons, dtype=np.float32)

        self.amplitude_history    = deque(maxlen=self.history_max)
        self._last_history_time   = 0.0

        if self.use_mlx:
            self.mean_phase     = mx.array(self.mean_phase)
            self.mean_velocity  = mx.array(self.mean_velocity)
            self.mean_amplitude = mx.array(self.mean_amplitude)
            self.var_phase      = mx.array(self.var_phase)
            self.var_amplitude  = mx.array(self.var_amplitude)
            self.external_force = mx.array(self.external_force)

        self.time = 0.0

    # ────────────────────────────────────────────────────────────────────
    #  State extraction
    # ────────────────────────────────────────────────────────────────────

    def get_region_activity(self, region: str = 'PN', normalize_kc: bool = False,
                            target_sparsity: float = 0.06) -> np.ndarray:
        """
        Extract activity for a named region.

        Args:
            region           : 'PN', 'KC', 'LN', or 'MBON'.
            normalize_kc     : Apply APL-like WTA normalisation (KC only).
            target_sparsity  : Target active fraction for normalisation.
        """
        from ..substrate.olfactory_subgraph import classify_olfactory_neuron

        if hasattr(self.connectome, 'neurons'):
            region_ids = [
                nid for nid, neuron in self.connectome.neurons.items()
                if classify_olfactory_neuron(neuron) == region
            ]

            if not region_ids:
                if self.use_mlx:
                    return np.array(self.mean_amplitude)
                return self.mean_amplitude.copy()

            indices = [i for i, nid in enumerate(self.neuron_ids) if nid in region_ids]

            if not indices:
                return np.zeros(20)

            if self.use_mlx:
                activity = np.array(self.mean_amplitude)[indices]
            else:
                activity = self.mean_amplitude[indices]

            if region == 'PN' and len(activity) > 20:
                n_bins   = 20
                bin_size = len(activity) // n_bins
                activity = np.array([
                    activity[i * bin_size: (i + 1) * bin_size if i < n_bins - 1 else len(activity)].mean()
                    for i in range(n_bins)
                ])

            if normalize_kc and region == 'KC':
                activity = self._apply_kc_normalization(activity, target_sparsity)

            return activity

        if self.use_mlx:
            return np.array(self.mean_amplitude)
        return self.mean_amplitude.copy()

    def _apply_kc_normalization(self, kc_activity: np.ndarray,
                                target_sparsity: float = 0.06) -> np.ndarray:
        """
        Winner-take-all normalisation mimicking APL feedback inhibition.

        Reference: Lin et al. (2014) Nature Neuroscience.
        """
        if len(kc_activity) == 0:
            return kc_activity

        sorted_activity = np.sort(kc_activity)[::-1]
        threshold_idx   = int(len(kc_activity) * target_sparsity)
        threshold       = sorted_activity[threshold_idx] if threshold_idx < len(sorted_activity) else 0.0
        return np.maximum(0.0, kc_activity - threshold)

    def get_state(self) -> SparseProbabilisticState:
        """Return current full state (copies arrays to numpy)."""
        if self.use_mlx:
            return SparseProbabilisticState(
                mean_phase     = np.array(self.mean_phase),
                mean_velocity  = np.array(self.mean_velocity),
                mean_amplitude = np.array(self.mean_amplitude),
                var_phase      = np.array(self.var_phase),
                var_amplitude  = np.array(self.var_amplitude),
                neuron_ids     = self.neuron_ids,
                time           = self.time,
            )
        return SparseProbabilisticState(
            mean_phase     = self.mean_phase.copy(),
            mean_velocity  = self.mean_velocity.copy(),
            mean_amplitude = self.mean_amplitude.copy(),
            var_phase      = self.var_phase.copy(),
            var_amplitude  = self.var_amplitude.copy(),
            neuron_ids     = self.neuron_ids,
            time           = self.time,
        )

    # ────────────────────────────────────────────────────────────────────
    #  Benchmark
    # ────────────────────────────────────────────────────────────────────

    def benchmark(self, bio_duration_ms: float = 100.0) -> dict:
        """
        Measure wall-clock time for *bio_duration_ms* of simulation and
        compute the real-time (RT) factor.

        Returns a dict with keys:
            wall_s       – wall-clock seconds elapsed
            bio_ms       – biological milliseconds simulated
            rt_factor    – bio_ms / (wall_s * 1000)  [>1 = faster than RT]
            steps        – number of integration steps
            dt_ms        – integration step size
            mode         – 'compiled_mlx' | 'interpreted_mlx' | 'numpy'
        """
        self.reset(deterministic=True)

        t0 = time.perf_counter()
        self.evolve(duration=bio_duration_ms)
        if self.use_mlx:
            mx.eval(self.mean_amplitude)
        wall_s = time.perf_counter() - t0

        steps     = int(bio_duration_ms / self.dt)
        rt_factor = (bio_duration_ms / 1000.0) / wall_s  # >1 = faster than RT

        if not self.use_mlx:
            mode = 'numpy'
        elif self._compiled_step is not None:
            mode = 'compiled_mlx'
        else:
            mode = 'interpreted_mlx'

        result = dict(
            wall_s    = round(wall_s, 4),
            bio_ms    = bio_duration_ms,
            rt_factor = round(rt_factor, 3),
            steps     = steps,
            dt_ms     = self.dt,
            mode      = mode,
        )

        label = "✓ REAL-TIME" if rt_factor >= 1.0 else f"{1/rt_factor:.2f}× slower than RT"
        print(f"\nBenchmark [{mode}, dt={self.dt}ms]:")
        print(f"  {bio_duration_ms:.0f} ms bio → {wall_s*1000:.1f} ms wall")
        print(f"  RT factor: {rt_factor:.3f}×  ({label})")
        return result


if __name__ == "__main__":
    print("\nSparse Probabilistic Brain - Memory Efficient")
    print("Tracks neurons directly, not grid voxels")
    print("100× less memory than dense grid approach")
