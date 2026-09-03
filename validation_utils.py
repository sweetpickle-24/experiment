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


def run_metadata(brain=None, duration_ms=None, seed=None, **extra) -> dict:
    """
    Configuration block to embed in every result file.

    Reads the timestep and backend off the brain object rather than off the
    config dict that was passed in, because those can differ.
    """
    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "seed": seed,
        "duration_ms": duration_ms,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
    }
    if brain is not None:
        meta.update({
            "backend": "MLX" if getattr(brain, "use_mlx", False) else "NumPy",
            "dt_ms": getattr(brain, "dt", None),
            "fast_mode": getattr(brain, "fast_mode", None),
            "gamma": getattr(brain, "gamma", None),
            "sigma_noise": getattr(brain, "sigma_noise", None),
            "num_neurons": getattr(brain, "num_neurons", None),
        })
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
        use_mlx   : use the MLX GPU backend.
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

    return brain, door_client, connectome
