#!/usr/bin/env python3
"""
Same-seed reproducibility of the MLX backend, and CPU/MLX agreement.

Before 2026-09-03 the MLX coupling force was accumulated with an atomic
scatter-add over 446,388 synapses. Metal gives no guarantee about reduction
order, floating-point addition is not associative, and the KC readout
thresholds by rank, so same-seed MLX runs disagreed about which neurons were
active. This test is the evidence that the replacement segmented reduction
(hive/engine/sparse_probabilistic.py::_build_segment_layout) fixed it.

Three things are checked and recorded:

  1. same-seed MLX runs are bit-for-bit identical across all four state fields
     and the KC readout;
  2. same-seed CPU runs are bit-for-bit identical (they always were);
  3. how far CPU and MLX drift apart. They cannot be bit-identical: mx.sum and
     np.sum use different reduction trees, so they differ in the last bits of
     every step and the rank threshold amplifies that. The number is measured
     and reported rather than asserted away.

Usage:
    python tests/test_mlx_determinism.py [--trials 5] [--duration 100]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import init_olfactory_brain, set_seed, write_results  # noqa: E402

STATE_FIELDS = ('mean_phase', 'mean_velocity', 'mean_amplitude', 'var_phase')
DEFAULT_SEED = 42
DIAG_ODOR = 'benzaldehyde'


def run_once(use_mlx, seed, duration_ms, odor=DIAG_ODOR, strength=50.0):
    """One full same-seed trial, returning state arrays plus the KC readout."""
    brain, door, _ = init_olfactory_brain(use_mlx=use_mlx, seed=seed)
    pattern = door.get_glomerular_pattern(odor)
    brain.reset(deterministic=True)
    brain.inject_odor(pattern, strength=strength)
    brain.evolve(duration=duration_ms)

    state = {f: np.array(getattr(brain, f), copy=True) for f in STATE_FIELDS}
    kc = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    state['kc_normalized'] = np.asarray(kc, dtype=np.float32)
    state['kc_active'] = np.asarray(kc > 0.01, dtype=np.float32)
    return state


def compare(a, b):
    """Per-field bitwise equality and max absolute difference."""
    out = {}
    for k in a:
        x, y = a[k], b[k]
        out[k] = {
            'bitwise_identical': bool(np.array_equal(x, y)),
            'max_abs_diff': float(np.abs(x.astype(np.float64) - y.astype(np.float64)).max()),
        }
    out['active_kc_counts'] = [int(a['kc_active'].sum()), int(b['kc_active'].sum())]
    return out


def all_identical(runs):
    """True when every run matches run 0 bit-for-bit on every field."""
    return all(
        np.array_equal(runs[0][k], r[k])
        for r in runs[1:] for k in runs[0]
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--trials', type=int, default=5,
                    help='same-seed repeats per backend')
    ap.add_argument('--duration', type=float, default=100.0,
                    help='simulated milliseconds per trial')
    ap.add_argument('--seed', type=int, default=DEFAULT_SEED)
    ap.add_argument('--output', default='mlx_determinism.json')
    args = ap.parse_args()

    set_seed(args.seed)
    results = {'trials': args.trials, 'duration_ms': args.duration,
               'seed': args.seed, 'state_fields': list(STATE_FIELDS)}

    print(f"\n{'='*70}\nMLX / CPU same-seed reproducibility\n{'='*70}")
    print(f"trials={args.trials}  duration={args.duration} ms  seed={args.seed}\n")

    backends = {}
    for name, use_mlx in (('mlx', True), ('cpu', False)):
        runs = [run_once(use_mlx, args.seed, args.duration)
                for _ in range(args.trials)]
        backends[name] = runs

        identical = all_identical(runs)
        pairwise = [compare(runs[0], r) for r in runs[1:]]
        worst = max((c[k]['max_abs_diff'] for c in pairwise for k in STATE_FIELDS),
                    default=0.0)
        counts = sorted({int(r['kc_active'].sum()) for r in runs})

        results[name] = {
            'all_runs_bitwise_identical': identical,
            'worst_state_max_abs_diff_between_runs': worst,
            'distinct_active_kc_counts': counts,
            'pairwise_vs_run0': pairwise,
        }
        verdict = 'REPRODUCIBLE' if identical else 'NOT REPRODUCIBLE'
        print(f"{name.upper():4s}: {verdict}  "
              f"worst state diff between same-seed runs = {worst:.3g}  "
              f"active KC counts observed = {counts}")

    # Cross-backend agreement. Not expected to be bitwise; measured, not assumed.
    cross = compare(backends['mlx'][0], backends['cpu'][0])
    mlx_set = set(np.where(backends['mlx'][0]['kc_active'] > 0)[0].tolist())
    cpu_set = set(np.where(backends['cpu'][0]['kc_active'] > 0)[0].tolist())
    union = len(mlx_set | cpu_set)
    cross['active_kc_jaccard'] = (len(mlx_set & cpu_set) / union) if union else 1.0
    results['cross_backend'] = cross
    results['cross_backend_note'] = (
        "mx.sum and np.sum use different reduction trees, so the two backends "
        "differ in the last bits of every step even though both are internally "
        "reproducible. The KC readout thresholds by rank, which amplifies that "
        "difference over the run; the Jaccard overlap of the active sets is the "
        "honest measure of agreement."
    )
    print(f"\nCPU vs MLX: max state diff = "
          f"{max(cross[k]['max_abs_diff'] for k in STATE_FIELDS):.3g}, "
          f"active-KC Jaccard = {cross['active_kc_jaccard']:.4f}, "
          f"counts {cross['active_kc_counts']}")

    both_ok = results['mlx']['all_runs_bitwise_identical'] and \
        results['cpu']['all_runs_bitwise_identical']
    results['verdict'] = 'PASS' if both_ok else 'FAIL'
    print(f"\nVerdict: {results['verdict']}")

    brain, door, _ = init_olfactory_brain(use_mlx=True, seed=args.seed)
    out = write_results(args.output, results, brain=brain, door_client=door,
                        duration_ms=args.duration, seed=args.seed,
                        test='mlx_determinism')
    print(f"Written to {out}")
    return 0 if both_ok else 1


if __name__ == '__main__':
    sys.exit(main())
