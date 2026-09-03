"""
Common utilities for validation experiments.

Also provides the run-metadata helpers. Every result file written by this
repository must carry the configuration it was produced under: backend, timestep,
fast mode, simulated duration, hardware, seed, and git commit. A number without
its configuration cannot be attributed to anything.
"""

import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.data.door_client import DoorClient


# ── Paths ────────────────────────────────────────────────────────────────────

def repo_root() -> Path:
    """Repository root, independent of the current working directory."""
    return Path(__file__).resolve().parent


def results_path(name: str, kind: str = "final") -> Path:
    """
    Path for a result artifact.

    kind: 'final' for the current best run, 'superseded' for runs kept as
    evidence but no longer authoritative.
    """
    d = repo_root() / "results" / kind
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def log_path(name: str) -> Path:
    """Path for a run log."""
    d = repo_root() / "results" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def connectome_dir() -> Path:
    """Location of the raw connectome CSVs."""
    return repo_root() / "Fly Brain Female"


# ── Run metadata ─────────────────────────────────────────────────────────────

def git_commit() -> str:
    """Current commit, with a -dirty suffix if the tree has uncommitted changes."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root(),
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo_root(),
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        return f"{sha}-dirty" if dirty else sha
    except Exception:
        return "unknown"


# Why an MLX run cannot be reproduced bit-for-bit, recorded verbatim in any
# result file produced on the GPU backend.
MLX_NONREPRODUCIBLE_REASON = (
    "Synaptic coupling is accumulated with a scatter-add over 446,388 synapses "
    "(forces.at[post_indices].add(...) in hive/engine/sparse_probabilistic.py). "
    "Floating-point addition is not associative and Metal does not guarantee "
    "reduction order, so same-seed processes diverge at around 1 part in 1e5. "
    "KC activity is then thresholded by rank (int(n_kc * target_sparsity), i.e. "
    "index 316 of 5,279 at the 0.06 default), and the threshold is a sampled "
    "array value, so a reordering near that rank shifts the baseline subtracted "
    "from every KC and changes which neurons are counted active. Re-run on "
    "use_mlx=False to obtain a reproducible number."
)


def run_metadata(brain=None, duration_ms=None, seed=None, door_client=None, **extra) -> dict:
    """
    Configuration block to embed in every result file.

    Reads the timestep and backend off the brain object rather than off the
    config dict that was passed in, because those can differ.

    Args:
        brain       : brain instance; backend, dt and physics are read off it.
        duration_ms : simulated duration the result covers.
        seed        : RNG seed passed to set_seed, or None if unseeded.
        door_client : DoorClient whose projection path should be recorded.
                      Two different projections can run (mean-centred sklearn
                      PCA, or uncentred SVD when scikit-learn is absent) and
                      they give different glomerular patterns, so a result is
                      not interpretable without knowing which one ran.

    Always carries: timestamp, git_commit, seed, backend, dt_ms,
    projection_method, and a `reproducible` flag. `reproducible` is False on
    MLX, with the reason in `nonreproducible_reason`.
    """
    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "seed": seed,
        "duration_ms": duration_ms,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        # Filled below when a brain / door_client is supplied. Present even when
        # unknown so a consumer can tell "not recorded" from "not applicable".
        "backend": None,
        "dt_ms": None,
        "projection_method": None,
        "reproducible": None,
    }
    if brain is not None:
        backend = "MLX" if getattr(brain, "use_mlx", False) else "NumPy"
        meta.update({
            "backend": backend,
            "dt_ms": getattr(brain, "dt", None),
            "fast_mode": getattr(brain, "fast_mode", None),
            "gamma": getattr(brain, "gamma", None),
            "sigma_noise": getattr(brain, "sigma_noise", None),
            "num_neurons": getattr(brain, "num_neurons", None),
            "reproducible": backend != "MLX",
        })
        if backend == "MLX":
            meta["nonreproducible_reason"] = MLX_NONREPRODUCIBLE_REASON

    if door_client is not None:
        meta["projection_method"] = getattr(door_client, "projection_method", None)
        meta["projection_explained_variance"] = getattr(
            door_client, "projection_explained_variance", None
        )
        meta["door_matrix_synthetic"] = getattr(door_client, "is_synthetic", None)
        meta["door_n_odorants"] = len(getattr(door_client, "odorant_names", []) or [])

    meta.update(extra)
    return meta


def set_seed(seed: int = 42) -> int:
    """
    Seed every RNG the validation path can reach.

    The suite was historically unseeded, which made consecutive runs of identical
    code produce different results. Call this at the start of any run whose output
    you intend to quote.
    """
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import mlx.core as mx
        mx.random.seed(seed)
    except Exception:
        pass
    return seed


# ── Brain construction ───────────────────────────────────────────────────────

DEFAULT_BRAIN_CONFIG = {
    "gamma": 0.1,
    "sigma_noise": 0.1,
}


def init_olfactory_brain(use_mlx=True, fast_mode=False, seed=42, config=None):
    """
    Initialise the olfactory system for validation experiments.

    Args:
        use_mlx   : use the MLX GPU backend. Pass False for any run whose number
                    will be reported: the MLX scatter-add is order-dependent, so
                    same-seed runs diverge (see MLX_NONREPRODUCIBLE_REASON).
        fast_mode : dt = 0.5 ms instead of 0.1 ms. Not used for validation runs.
        seed      : RNG seed, or None to leave RNGs unseeded.
        config    : optional physics overrides. Keys the engine understands are
                    'dt', 'gamma' and 'sigma_noise'. Anything else raises, rather
                    than being silently discarded as it was before 2026-09-03.

    Returns:
        tuple: (brain, door_client, connectome)
    """
    if seed is not None:
        set_seed(seed)

    full_connectome = Connectome(data_dir=str(connectome_dir()))
    full_connectome.load()

    connectome = extract_olfactory_pathway(full_connectome)

    brain = SparseProbabilisticBrain(
        connectome=connectome,
        config=config,
        use_mlx=use_mlx,
        fast_mode=fast_mode,
    )

    door_client = DoorClient()
    # Build the projection now rather than on first lookup, so that
    # door_client.projection_method is populated before run_metadata reads it.
    # Same matrix either way; this only fixes when it is computed.
    door_client.map_to_glomerular_pattern(
        np.zeros(len(door_client.receptor_names), dtype=np.float32)
    )

    return brain, door_client, connectome


def assert_reproducible_backend(brain) -> None:
    """
    Refuse to proceed if a run intended for reporting is on the MLX backend.

    Call this in any path that writes a result file whose numbers will be
    quoted. Raises RuntimeError rather than warning, because the failure it
    guards against is silent: an MLX run looks identical to a CPU run in the
    output, it just cannot be reproduced.
    """
    if getattr(brain, "use_mlx", False):
        raise RuntimeError(
            "This run writes a reported result but is on the MLX backend. "
            + MLX_NONREPRODUCIBLE_REASON
        )
