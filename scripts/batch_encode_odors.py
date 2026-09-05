"""
Batch Odor Encoder
==================

Encodes every odorant in the DoOR matrix to a Kenyon cell fingerprint by running
the olfactory-pathway wave engine once per odorant and reading out the KC layer.

The output is a lookup table: molecule -> sparse KC pattern. It backs
``SmellDatabase`` cosine search and the inverse problem in
``hive/inverse/smell_optimizer.py``. It is an **encoding artifact, not a
benchmark** - nothing here is scored against a published measurement.

Why this was rewritten (2026-09-05)
-----------------------------------
The previous version produced a database that could not be reconciled with any
reported run, for three independent reasons:

1. **It used a third, undocumented projection.** Glomerular patterns came from
   ``SmellDatabase._receptors_to_glom``, which is an *uncentered SVD* of the
   response matrix - not the ``sklearn_pca`` the benchmarks used, and not the
   published one-to-one map. So the fingerprints were built on a receptor-to-
   channel mapping that appeared nowhere else in the repository.
2. **It ran under the superseded constant-drive stimulus path**, before the
   plume, carrier and receptor adaptation were wired in. The shipped artifact
   still shows the signature: its ``pn_pattern`` fields contain literal ``10.0``
   values, i.e. projection neurons pinned at the old amplitude ceiling.
3. **It ran on MLX with fast_mode** (dt = 0.5 ms), which is neither the reporting
   backend nor the reporting timestep.

This version goes through ``validation_utils.init_olfactory_brain``, so it is
built exactly as the scored suite is built, and takes its glomerular patterns
from ``DoorClient`` so the projection is the one recorded in the provenance
block. Defaults are the G2 configuration - the published one-to-one
receptor-to-glomerulus map, PN assignment from the connectome's glomerulus
annotations, and strict neuron classification - on CPU at dt = 0.1 ms.

Determinism
-----------
``reset(deterministic=True)`` is used deliberately here, which is the opposite of
what the benchmarks do. A benchmark needs trial-to-trial variability to have a
null distribution; a lookup table needs one canonical, reproducible fingerprint
per molecule. Same reason a hash function should not be salted per call.

Runtime
-------
372 odorants x 100 ms of simulated biology. About 30 minutes on CPU at
dt = 0.1 ms, or about 3 minutes with ``--mlx`` (CPU and MLX select the same
active KCs at 100 ms - Jaccard 1.0000, pattern r = 0.99988 - so ``--mlx`` is
defensible at this duration, though not beyond it).

Usage
-----
    .venv/bin/python scripts/batch_encode_odors.py
    .venv/bin/python scripts/batch_encode_odors.py --mlx --max 20
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from validation_utils import init_olfactory_brain, run_metadata  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "data" / "digital_smell_database_full.json"

#: Concentration 1.0. ``OdorStimulusDriver.REFERENCE_STRENGTH``, the same value
#: every scored benchmark uses.
#:
#: The previous version used ``50.0 * log10(1 + 10 * 1.0)`` = 52.07, a
#: Weber-Fechner scaling carried over from the concentration-invariance sweep. It
#: is dropped here because a single-concentration encoding has nothing to scale
#: relative to, and 50.0 is the value the rest of the repository means by
#: "concentration 1.0".
REFERENCE_STRENGTH = 50.0

#: KC readout sparsity, unchanged from the suite.
TARGET_SPARSITY = 0.06

#: Simulated duration per odorant, unchanged.
DURATION_MS = 100.0

#: Configuration keys that must match for a resume to be legitimate. Resuming
#: across a change in any of these would silently blend two pipelines into one
#: artifact, which is the defect this rewrite exists to undo.
RESUME_MUST_MATCH = ('projection_method', 'glomerular_mapping',
                     'strict_classification', 'backend', 'dt_ms',
                     'n_stim_channels', 'reference_strength',
                     'target_sparsity', 'duration_ms')


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--max", type=int, default=None, metavar="N",
                   help="encode only the first N odorants")
    p.add_argument("--out", type=str, default=str(DEFAULT_OUT), metavar="PATH",
                   help="output JSON path")
    p.add_argument("--mlx", action="store_true",
                   help="use the MLX GPU backend (10x faster; agrees with CPU "
                        "at this 100 ms duration but not beyond it)")
    p.add_argument("--projection", default="glomerular",
                   choices=("glomerular", "sklearn_pca", "uncentered_svd"),
                   help="receptor to channel projection (default: glomerular, "
                        "the published one-to-one map)")
    p.add_argument("--glomerular-mapping", default="glomerulus",
                   choices=("glomerulus", "position", "index"),
                   help="how channels map onto projection neurons")
    p.add_argument("--no-strict", action="store_true",
                   help="use the loose neuron classifier (the pre-2026-09-05 "
                        "behaviour, which counts auditory and central-complex "
                        "neurons as olfactory)")
    p.add_argument("--fresh", action="store_true",
                   help="ignore any existing output rather than resuming")
    return p


def main():
    args = build_parser().parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    strict = not args.no_strict

    print("=" * 70)
    print("BATCH ODOR ENCODER")
    print("=" * 70)
    print(f"  projection        : {args.projection}")
    print(f"  PN mapping        : {args.glomerular_mapping}")
    print(f"  strict classifier : {strict}")
    print(f"  backend           : {'MLX' if args.mlx else 'NumPy (CPU)'}")

    # ── Build the engine exactly as the scored suite builds it ──────────
    print("\n[1] Initialising engine...")
    t0 = time.perf_counter()
    brain, door, connectome = init_olfactory_brain(
        use_mlx=args.mlx,
        seed=42,
        projection=args.projection,
        glomerular_mapping=args.glomerular_mapping,
        strict_classification=strict,
    )
    print(f"  ready in {time.perf_counter() - t0:.1f}s")

    n_kc = int(brain.get_region_activity(
        'KC', normalize_kc=True, target_sparsity=TARGET_SPARSITY).size)

    meta = run_metadata(brain=brain, door_client=door,
                        duration_ms=DURATION_MS, seed=42,
                        reference_strength=REFERENCE_STRENGTH,
                        target_sparsity=TARGET_SPARSITY,
                        n_kc=n_kc,
                        reset='deterministic=True (canonical fingerprint per '
                              'molecule, not a benchmark trial)',
                        artifact='KC fingerprint lookup table',
                        scored=False)

    print(f"  {brain.num_neurons:,} neurons | {n_kc:,} KCs | "
          f"{brain._stim_n_channels} channels")

    # ── Odorants come from the matrix itself ────────────────────────────
    odorant_names = door.get_all_odorants()
    if args.max is not None:
        odorant_names = odorant_names[: args.max]
    print(f"\n[2] Encoding {len(odorant_names)} odorants "
          f"({DURATION_MS:.0f} ms each)")

    # ── Resume, but only across an identical configuration ─────────────
    existing: dict = {}
    if out_path.exists() and not args.fresh:
        try:
            with open(out_path) as f:
                prior = json.load(f)
            prior_cfg = prior.get('config', {}) if isinstance(prior, dict) else {}
            prior_recs = (prior.get('entries', []) if isinstance(prior, dict)
                          else prior)
            differing = [k for k in RESUME_MUST_MATCH
                         if prior_cfg.get(k) != meta.get(k)]
            if differing:
                print(f"  existing output was produced under a different "
                      f"configuration ({', '.join(differing)}); NOT resuming")
            else:
                existing = {r['odor_name']: r for r in prior_recs}
                print(f"  resuming: {len(existing)} already encoded")
        except Exception as exc:
            print(f"  could not read existing output ({exc}); starting fresh")

    # ── Encode ─────────────────────────────────────────────────────────
    print("-" * 70)
    print(f"  {'#':>5}  {'odorant':<34}  {'KC active':>9}  {'sparsity':>9}  {'ms':>6}")
    print("-" * 70)

    records, n_new = [], 0
    t_start = time.perf_counter()
    for idx, name in enumerate(odorant_names):
        if name in existing:
            records.append(existing[name])
            continue

        pattern = door.get_glomerular_pattern(name)

        t_odor = time.perf_counter()
        brain.reset(deterministic=True)
        brain.inject_odor(pattern, strength=REFERENCE_STRENGTH)
        brain.evolve(duration=DURATION_MS)
        kc = brain.get_region_activity('KC', normalize_kc=True,
                                       target_sparsity=TARGET_SPARSITY)
        pn = brain.get_region_activity('PN')
        elapsed_ms = (time.perf_counter() - t_odor) * 1000.0

        kc_active = int(np.sum(kc > 0.0))
        records.append({
            'odor_name': name,
            'family': door._classify_chemical_family(name),
            'glomerular_pattern': np.asarray(pattern, float).tolist(),
            'pn_pattern': np.asarray(pn, float).tolist(),
            'kc_pattern': np.asarray(kc, float).tolist(),
            'kc_active': kc_active,
            'kc_sparsity': float(kc_active / len(kc)),
            'simulation_ms': float(elapsed_ms),
        })
        n_new += 1

        if n_new <= 3 or (idx + 1) % 25 == 0:
            print(f"  {idx+1:>5}  {name[:34]:<34}  {kc_active:>9}  "
                  f"{kc_active/len(kc):>8.3%}  {elapsed_ms:>6.0f}")

    total_s = time.perf_counter() - t_start

    # ── Write, with the configuration attached ─────────────────────────
    # A dict rather than a bare list, so the artifact carries the pipeline it was
    # produced under. SmellDatabase.load_kc_fingerprints accepts both shapes.
    #
    # null_stimulus_odorants is filled in below, after the records exist; the
    # write happens at the end of main() so the config can carry it.
    payload = {'config': meta, 'entries': records}

    sparsities = [r['kc_sparsity'] for r in records]
    actives = [r['kc_active'] for r in records]

    # ── Null stimuli, reported rather than left in the artifact silently ──
    #
    # An odorant whose measured responses on the *mapped* receptors are all
    # negative - real inhibition below spontaneous rate - projects to an all-zero
    # glomerular pattern, because map_to_glomerular_pattern rectifies. It then
    # drives nothing and yields zero active KCs.
    #
    # This is the defect class the benchmark audit was about: a null stimulus that
    # produces plausible-looking output. Here it is not silent - kc_active is 0 -
    # but a consumer doing cosine search over the matrix would carry 26 rows that
    # can never match anything, so the list is recorded in the config block.
    null_names = [r['odor_name'] for r in records if r['kc_active'] == 0]
    if null_names:
        print(f"\n  WARNING: {len(null_names)} of {len(records)} odorants produced a "
              f"NULL stimulus (zero active KCs).")
        print(f"  Cause: on the receptors this projection maps, their measured "
              f"responses are entirely negative")
        print(f"  (inhibition below spontaneous rate), so the rectifier in "
              f"map_to_glomerular_pattern zeroes the pattern.")
        print(f"  They are usable as evidence of that, and not usable as odour "
              f"stimuli. Excluded names are in config.null_stimulus_odorants.")
        print(f"  First few: {', '.join(null_names[:6])}")

    meta['null_stimulus_odorants'] = null_names
    meta['n_null_stimulus'] = len(null_names)
    meta['n_usable'] = len(records) - len(null_names)
    meta['null_stimulus_cause'] = (
        'all measured responses on the mapped receptors are negative '
        '(inhibition below spontaneous rate), so the rectifier in '
        'map_to_glomerular_pattern produces an all-zero glomerular pattern'
    )

    with open(out_path, 'w') as f:
        json.dump(payload, f, separators=(',', ':'))
    size_mb = out_path.stat().st_size / 1024 / 1024

    print("-" * 70)
    print(f"\n  encoded  : {n_new} new, {len(records) - n_new} reused")
    print(f"  time     : {total_s:.0f}s"
          + (f" ({total_s / n_new * 1000:.0f} ms/odorant)" if n_new else ""))
    print(f"  output   : {out_path.name}  ({size_mb:.1f} MB)")
    print(f"\n  KC active per odorant: min {min(actives)}, max {max(actives)}, "
          f"of {n_kc}")
    print(f"  KC sparsity: mean {np.mean(sparsities):.4%}, "
          f"sd {np.std(sparsities):.2e}")
    if np.std(sparsities) < 1e-12:
        print(f"    constant, as expected: the rank threshold pins it at "
              f"int({n_kc} * {TARGET_SPARSITY}) = {actives[0]} KCs. This is a "
              f"property of the readout, not a measured sparsity.")
    print("=" * 70)
    print("Reload with SmellDatabase.load_kc_fingerprints(path).")


if __name__ == "__main__":
    main()
