"""
Common utilities for validation experiments.

Also provides the run-metadata helpers. Every result file written by this
repository must carry the configuration it was produced under: backend, timestep,
fast mode, simulated duration, hardware, seed, and git commit. A number without
its configuration cannot be attributed to anything.
"""

import json
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


# Kept for provenance: this is the defect that made pre-2026-09-03 MLX result
# files non-reproducible, and it is quoted in the superseded artifacts.
MLX_HISTORICAL_NONREPRODUCIBLE_REASON = (
    "Until 2026-09-03 synaptic coupling was accumulated with an atomic "
    "scatter-add over 446,388 synapses (forces.at[post_indices].add(...) in "
    "hive/engine/sparse_probabilistic.py). Floating-point addition is not "
    "associative and Metal does not guarantee reduction order, so same-seed "
    "processes diverged. KC activity is thresholded by rank (int(n_kc * "
    "target_sparsity), i.e. index 316 of 5,279 at the 0.06 default) and the "
    "threshold is a sampled array value, so a reordering near that rank "
    "shifted the baseline subtracted from every KC and changed which neurons "
    "were counted active: 303 active KCs against 203 on the worst same-seed "
    "pair, with 11 of 15 trials differing."
)

# The scatter-add is gone. Both backends now accumulate through the static
# two-stage segment layout in _build_segment_layout, whose reduction order is a
# pure function of the connectome. Evidence: results/final/mlx_determinism.json
# (5 same-seed trials per backend, bit-for-bit identical on all four state
# fields and the KC readout).
#
# What is still NOT true is cross-backend bit-equality: mx.sum and np.sum use
# different reduction trees, so CPU and MLX differ in the last bits of every
# step. Measured at 100 ms: max phase difference 5.512 rad (the phase is
# wrapped, so this is a fully diverged neuron), but the same 212 active KCs on
# both backends with Jaccard overlap 0.9813.
CROSS_BACKEND_AGREEMENT_NOTE = (
    "Each backend is individually reproducible bit-for-bit at a fixed seed, but "
    "CPU and MLX are not bit-identical to each other: mx.sum and np.sum use "
    "different reduction trees. See results/final/mlx_determinism.json for the "
    "measured divergence and active-KC overlap."
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
    projection_method, and a `reproducible` flag. As of 2026-09-03 both
    backends are reproducible at a fixed seed; the flag is retained because
    older result files carry it as False and a consumer needs to tell the two
    eras apart.
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
        # Reproducibility is a property of the accumulation layout, not of the
        # backend name: an engine that regressed to atomic scatter-add would
        # not have _seg_order.
        deterministic_accumulation = hasattr(brain, "_seg_order_np")
        meta.update({
            "backend": backend,
            "dt_ms": getattr(brain, "dt", None),
            "fast_mode": getattr(brain, "fast_mode", None),
            "gamma": getattr(brain, "gamma", None),
            "sigma_noise": getattr(brain, "sigma_noise", None),
            "num_neurons": getattr(brain, "num_neurons", None),
            "reproducible": deterministic_accumulation,
            "deterministic_accumulation": deterministic_accumulation,
            "amplitude_min": getattr(brain, "amplitude_min", None),
            "amplitude_max": getattr(brain, "amplitude_max", None),
            "glomerular_mapping": getattr(brain, "_pn_channel_source", None),
            "glomerular_mapping_requested": getattr(
                brain, "glomerular_mapping", None),
            "strict_classification": getattr(
                brain, "strict_classification", None),
            "n_stim_channels": getattr(brain, "_stim_n_channels", None),
            "channel_names": getattr(brain, "channel_names", None),
            "channel_assignment": getattr(
                brain, "channel_assignment_report", None),
            "time_varying_odor_drive": bool(
                getattr(brain, "has_time_varying_drive", False)),
        })
        if backend == "MLX":
            meta["cross_backend_agreement"] = CROSS_BACKEND_AGREEMENT_NOTE

    if door_client is not None:
        meta["projection_method"] = getattr(door_client, "projection_method", None)
        meta["projection_explained_variance"] = getattr(
            door_client, "projection_explained_variance", None
        )
        # Computed identically for every projection, unlike
        # projection_explained_variance. This is the field to compare on.
        meta["projection_magnitude_retained"] = getattr(
            door_client, "projection_magnitude_retained", None
        )
        meta["projection_n_channels"] = getattr(door_client, "n_channels", None)
        meta["projection_channel_names"] = getattr(
            door_client, "channel_names", None)
        meta["projection_report"] = getattr(
            door_client, "projection_report", None)
        meta["door_matrix_synthetic"] = getattr(door_client, "is_synthetic", None)
        meta["door_n_odorants"] = len(getattr(door_client, "odorant_names", []) or [])

    meta.update(extra)
    return meta


#: The interpreter every reported run must use. The repository ships two
#: virtualenvs and only one of them has scikit-learn, which the documented
#: `sklearn_pca` projection requires. Running the suite under the system
#: interpreter raises deep inside DoorClient with a message that does not name
#: the interpreter, which costs a connectome load to discover.
REQUIRED_INTERPRETER_HINT = (
    "Reported runs require scikit-learn, which the documented "
    "projection='sklearn_pca' path uses. Use the repository virtualenv:\n"
    "    .venv/bin/python <script>\n"
    "The system interpreter and ./venv do not have it. Do not fall back to "
    "projection='uncentered_svd' to work around this: it is a different "
    "projection and produces different glomerular patterns."
)


def assert_reportable_environment(projection: str = 'sklearn_pca') -> None:
    """
    Fail before the connectome load if this interpreter cannot produce a
    reportable result.

    Checked here rather than at first odorant lookup so the failure costs
    seconds instead of a full initialisation, and so the error names the
    interpreter to use.
    """
    if projection != 'sklearn_pca':
        return
    import importlib.util
    if importlib.util.find_spec('sklearn') is None:
        raise RuntimeError(
            f"scikit-learn is not importable under {sys.executable!r}.\n"
            + REQUIRED_INTERPRETER_HINT
        )


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


def init_olfactory_brain(use_mlx=True, fast_mode=False, seed=42, config=None,
                         projection='glomerular',
                         glomerular_mapping='glomerulus',
                         strict_classification=True):
    """
    Initialise the olfactory system for validation experiments.

    **Defaults are the current pipeline as of 2026-09-05**, i.e. the one that
    produced `results/final/all_validations_G2.json` (5/5). They were changed on
    that date, having previously been the pre-repair pipeline
    (`sklearn_pca` / `position` / loose classification, 2/5). The old values are
    still selectable, and the two entry points that exist to reproduce superseded
    numbers -- `scripts/run_all_validations.py` and
    `tests/concentration_invariance_test.py` -- pin them explicitly rather than
    relying on these defaults, so they keep reproducing their baselines.

    Changing a default does not alter any result already on disk: every artifact
    records the pipeline that produced it, so the 5/5 files now match the defaults
    and the 2/5 files are correctly marked as a different configuration.

    Args:
        use_mlx   : use the MLX GPU backend. Deterministic as of 2026-09-03; see
                    hive/engine/sparse_probabilistic.py for the segmented
                    reduction that replaced the order-dependent scatter-add.
                    Reported numbers use CPU, because the backends diverge past
                    100 ms.
        fast_mode : dt = 0.5 ms instead of 0.1 ms. Not used for validation runs.
        seed      : RNG seed, or None to leave RNGs unseeded.
        config    : optional physics overrides. Keys the engine understands are
                    'dt', 'gamma' and 'sigma_noise'. Anything else raises, rather
                    than being silently discarded as it was before 2026-09-03.
        projection: receptor->glomerular projection.
                    'glomerular' (default) is the published one-to-one
                    receptor-to-glomerulus map (Couto et al. 2005 Table 1), whose
                    channel count follows the map rather than being 20.
                    'sklearn_pca' is mean-centred PCA into 20 components, the
                    pre-2026-09-05 default; it inflates inter-odour similarity
                    2.72x and its rectifier discards a third of the response
                    magnitude, both measured in
                    results/final/glomerular_projection_diagnostic.json.
                    'uncentered_svd' reproduces the pre-2026-09-03 fallback.
        glomerular_mapping: how channels map onto PNs.
                    'glomerulus' (default) reads the glomerulus off the connectome
                    cell-type annotation, and requires projection='glomerular' to
                    supply channel names. 'position' clusters PNs by connectome
                    coordinates as a spatial proxy. 'index' reproduces the
                    pre-2026-09-03 assignment by neuron-list order.
        strict_classification: when True (default), require a whole dot-separated
                    neuropil token and reject the non-olfactory `PN` prefixes, so
                    auditory wedge neurons, unnamed central-brain neurons and
                    every lateral-accessory-lobe neuron stay out of the olfactory
                    populations. Takes the subgraph from 10,906 neurons to 9,199.
                    Applied consistently to both the extraction and the engine's
                    region lookups, which must agree.

    Returns:
        tuple: (brain, door_client, connectome)
    """
    assert_reportable_environment(projection)

    if seed is not None:
        set_seed(seed)

    full_connectome = Connectome(data_dir=str(connectome_dir()))
    full_connectome.load()

    connectome = extract_olfactory_pathway(
        full_connectome, strict=strict_classification)

    # The DoOR client is built first when the mapping needs channel names, since
    # the engine cannot resolve 'glomerulus' without knowing which glomerulus
    # each channel is.
    door_client = DoorClient(projection=projection)
    # Build the projection now rather than on first lookup, so that
    # door_client.projection_method and channel_names are populated before
    # run_metadata reads them. Same matrix either way; this only fixes when it is
    # computed.
    door_client.map_to_glomerular_pattern(
        np.zeros(len(door_client.receptor_names), dtype=np.float32)
    )

    brain = SparseProbabilisticBrain(
        connectome=connectome,
        config=config,
        use_mlx=use_mlx,
        fast_mode=fast_mode,
        glomerular_mapping=glomerular_mapping,
        channel_names=door_client.channel_names,
        strict_classification=strict_classification,
    )

    return brain, door_client, connectome


def write_results(name, payload: dict, brain=None, door_client=None,
                  duration_ms=None, seed=None, kind: str = "final", **extra):
    """
    Write a result file with its configuration block attached.

    Every result file must carry seed, git commit, dt, backend and projection
    path. A number without them cannot be attributed to a run, which is how
    this repository ended up quoting figures no run produced.

    The metadata is written under the top-level key 'config', replacing any
    'config' already in payload.

    Returns the path written.
    """
    payload = dict(payload)
    payload["config"] = run_metadata(
        brain=brain, duration_ms=duration_ms, seed=seed,
        door_client=door_client, **extra
    )
    path = results_path(name, kind=kind) if not isinstance(name, Path) else name
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


def assert_reproducible_backend(brain) -> None:
    """
    Refuse to proceed if a run intended for reporting cannot be reproduced.

    Call this in any path that writes a result file whose numbers will be
    quoted. Raises RuntimeError rather than warning, because the failure it
    guards against is silent: a non-reproducible run looks identical to a
    reproducible one in the output.

    Until 2026-09-03 this rejected the MLX backend outright. It now checks the
    thing that actually mattered — whether coupling is accumulated in a fixed
    order — so MLX passes, and an engine that regressed to atomic scatter-add
    would be caught on either backend.
    """
    if not hasattr(brain, "_seg_order_np"):
        raise RuntimeError(
            "This run writes a reported result, but the engine has no "
            "deterministic segment layout (_seg_order_np is absent), so its "
            "coupling accumulation order is not guaranteed. "
            + MLX_HISTORICAL_NONREPRODUCIBLE_REASON
        )
