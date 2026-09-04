#!/usr/bin/env python3
"""
Cross-backend equivalence over a full-length trajectory.

Why this exists
---------------
`results/final/mlx_determinism.json` establishes that CPU and MLX each reproduce
themselves bit-for-bit at a fixed seed, and that they select the same active KC
set as each other **over a 100 ms run**. Equivalence beyond 100 ms was never
measured, and the longest benchmark trajectory in the suite is 2000 ms — twenty
times longer. Cross-backend bit-equality is impossible in principle (`mx.sum`
and `np.sum` use different reduction trees), so the last bits differ every step
and the question is whether that divergence stays bounded or grows.

This matters because the readout is a *rank* threshold: KC activity is
thresholded at index `int(n_kc * target_sparsity)` of the descending sort, so a
reordering near that rank changes which neurons are counted active even when the
amplitudes themselves are almost identical.

Decision rule, fixed before the run
-----------------------------------
Report on MLX only if, at **every** sample point across the full 2000 ms and for
**every** seed:

    Jaccard(active KC sets) >= 0.95   AND   Pearson r(KC amplitudes) >= 0.99

Otherwise report on CPU and record the divergence as a finding. The rule is
stated here rather than chosen after seeing the numbers.

Protocol
--------
Both backends, same declared seed list, stochastic reset (random initial phase),
one odorant, sampled every 100 ms out to 2000 ms. Stochastic reset is used
deliberately: with `reset(deterministic=True)` the initial phase is all zeros and
identical on both backends, which is the easiest possible case. Random initial
phase drawn from the same seeded NumPy stream is the same initial condition on
both backends but a generic one, so it is a harder test of whether the
integrators stay together.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import (  # noqa: E402
    init_olfactory_brain, set_seed, write_results,
)

#: Declared before the run. Same list every benchmark in this repair uses.
SEEDS = [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008]

#: Sampled every 100 ms out to the longest trajectory any benchmark uses.
SAMPLE_INTERVAL_MS = 100.0
TOTAL_DURATION_MS = 2000.0

#: Odorant: benzaldehyde, the odour whose recorded PN responses drove the model
#: KC population in Turner et al. 2008 Fig 3I. Chosen by paper provenance, not
#: by outcome.
ODORANT = 'benzaldehyde'
STRENGTH = 50.0
TARGET_SPARSITY = 0.06

#: Fixed in the plan, before any number was seen.
JACCARD_MIN = 0.95
PEARSON_MIN = 0.99


def active_set(kc_normalized):
    """Active KC indices under the suite's readout: rank threshold then > 0."""
    return set(np.flatnonzero(kc_normalized > 0).tolist())


def jaccard(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def trajectory(brain, door_client, seed):
    """KC readout at every sample point of one seeded stochastic trial."""
    pattern = door_client.get_glomerular_pattern(ODORANT)

    set_seed(seed)
    brain.reset(deterministic=False)
    brain.inject_odor(pattern, strength=STRENGTH)

    n_samples = int(round(TOTAL_DURATION_MS / SAMPLE_INTERVAL_MS))
    out = []
    for _ in range(n_samples):
        brain.evolve(duration=SAMPLE_INTERVAL_MS)
        out.append(
            brain.get_region_activity('KC', normalize_kc=True,
                                      target_sparsity=TARGET_SPARSITY)
        )
    return out


def run(seeds=SEEDS):
    print("=" * 70)
    print("CROSS-BACKEND EQUIVALENCE OVER A FULL-LENGTH TRAJECTORY")
    print("=" * 70)
    print(f"Rule fixed before the run: Jaccard >= {JACCARD_MIN} AND "
          f"r >= {PEARSON_MIN} at every sample point, every seed.")

    brain_cpu, door_cpu, _ = init_olfactory_brain(use_mlx=False, seed=42)
    brain_mlx, door_mlx, _ = init_olfactory_brain(use_mlx=True, seed=42)
    if not brain_mlx.use_mlx:
        raise RuntimeError(
            "MLX backend did not initialise, so there is nothing to compare. "
            "This test is meaningless without it."
        )

    per_seed = []
    worst_jaccard, worst_r = 1.0, 1.0

    for seed in seeds:
        cpu_traj = trajectory(brain_cpu, door_cpu, seed)
        mlx_traj = trajectory(brain_mlx, door_mlx, seed)

        points = []
        for i, (kc_cpu, kc_mlx) in enumerate(zip(cpu_traj, mlx_traj)):
            t_ms = (i + 1) * SAMPLE_INTERVAL_MS
            a_cpu, a_mlx = active_set(kc_cpu), active_set(kc_mlx)
            j = jaccard(a_cpu, a_mlx)

            if np.std(kc_cpu) > 0 and np.std(kc_mlx) > 0:
                r = float(np.corrcoef(kc_cpu, kc_mlx)[0, 1])
            else:
                # Degenerate readout: recorded as None rather than silently
                # scored as 1.0, which is how a dead signal passes a
                # correlation criterion.
                r = None

            worst_jaccard = min(worst_jaccard, j)
            if r is not None:
                worst_r = min(worst_r, r)

            points.append({
                'time_ms': t_ms,
                'jaccard': j,
                'pearson_r': r,
                'n_active_cpu': len(a_cpu),
                'n_active_mlx': len(a_mlx),
                'max_abs_amplitude_diff': float(np.max(np.abs(kc_cpu - kc_mlx))),
            })

        seed_min_j = min(p['jaccard'] for p in points)
        rs = [p['pearson_r'] for p in points if p['pearson_r'] is not None]
        seed_min_r = min(rs) if rs else None
        per_seed.append({
            'seed': seed,
            'min_jaccard': seed_min_j,
            'min_pearson_r': seed_min_r,
            'n_points_with_undefined_r': sum(
                1 for p in points if p['pearson_r'] is None),
            'points': points,
        })
        print(f"  seed {seed}: min Jaccard {seed_min_j:.4f}, "
              f"min r {seed_min_r if seed_min_r is None else f'{seed_min_r:.6f}'}")

    any_undefined = any(s['n_points_with_undefined_r'] for s in per_seed)
    passed = (worst_jaccard >= JACCARD_MIN
              and worst_r >= PEARSON_MIN
              and not any_undefined)
    backend_for_reporting = 'MLX' if passed else 'NumPy'

    print("-" * 70)
    print(f"worst Jaccard over all seeds and sample points: {worst_jaccard:.4f} "
          f"(rule: >= {JACCARD_MIN})")
    print(f"worst Pearson r  over all seeds and sample points: {worst_r:.6f} "
          f"(rule: >= {PEARSON_MIN})")
    print(f"VERDICT: report on {backend_for_reporting}")

    payload = {
        'purpose': (
            'Cross-backend equivalence over the longest trajectory any '
            'benchmark uses (2000 ms), not just the 100 ms at which it was '
            'previously established.'
        ),
        'decision_rule': {
            'stated': 'before the run, in the plan',
            'jaccard_min': JACCARD_MIN,
            'pearson_min': PEARSON_MIN,
            'scope': 'every sample point, every seed',
            'on_failure': 'report on CPU and record the divergence as a finding',
        },
        'protocol': {
            'odorant': ODORANT,
            'odorant_selection_rule':
                'benzaldehyde: the odour whose recorded PN responses drove the '
                'model KC population in Turner et al. 2008 Fig 3I',
            'strength': STRENGTH,
            'reset': 'deterministic=False (random initial phase, seeded)',
            'reset_rationale':
                'deterministic reset gives all-zero initial phase, identical on '
                'both backends, which is the easiest possible case; a seeded '
                'random initial phase is the same initial condition on both '
                'backends but a generic one',
            'seeds': list(seeds),
            'sample_interval_ms': SAMPLE_INTERVAL_MS,
            'total_duration_ms': TOTAL_DURATION_MS,
            'target_sparsity': TARGET_SPARSITY,
        },
        'summary': {
            'worst_jaccard': worst_jaccard,
            'worst_pearson_r': worst_r,
            'n_seeds': len(seeds),
            'n_sample_points_per_seed': int(
                round(TOTAL_DURATION_MS / SAMPLE_INTERVAL_MS)),
            'any_undefined_correlation': any_undefined,
            'equivalent_at_full_length': passed,
            'backend_for_reporting': backend_for_reporting,
        },
        'per_seed': per_seed,
    }

    out = write_results(
        'cpu_vs_mlx_fullrun.json', payload,
        brain=brain_mlx, door_client=door_mlx,
        duration_ms=TOTAL_DURATION_MS, seed=None,
        suite='cpu_vs_mlx_fullrun',
        note=('brain metadata is the MLX instance; the CPU instance ran the '
              'same configuration with use_mlx=False'),
    )
    print(f"Written to {out}")
    return payload


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seeds', type=int, nargs='+', default=SEEDS)
    args = ap.parse_args()
    run(seeds=args.seeds)
