#!/usr/bin/env python3
"""
CPU against MLX: wall-clock ratio, on matched configurations.

Replaces results/final/cpu_vs_mlx_validation.json, which is not usable as
evidence and has been moved to results/superseded/. That file recorded 1,283
active KCs where current runs give a few hundred, its pattern_correlation was
null and its kc_pattern was an empty list, and it recorded
validation_passed: true against a stated correlation threshold of 0.95 that it
never evaluated. Its 86.34x is discarded.

What this measures instead
--------------------------
Same engine class (SparseProbabilisticBrain), same connectome (the olfactory
pathway), same neuron and synapse counts, same dt, same simulated duration,
same odour and injection strength, on both backends. Warm-up runs are excluded
so the MLX figure is not dominated by mx.compile tracing. The reported ratio is
the median of per-repeat wall times, and the spread is reported so a reader can
see whether the ratio is stable.

Output agreement is reported alongside the ratio, because a speedup on a
different answer is not a speedup. Both backends are individually reproducible
bit-for-bit (see tests/test_mlx_determinism.py); they are not bit-identical to
each other, so agreement is reported as active-KC overlap and correlation.

Usage:
    python tests/test_cpu_vs_mlx_speedup.py [--repeats 5] [--duration 100]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import init_olfactory_brain, set_seed, write_results  # noqa: E402

DEFAULT_SEED = 42
DIAG_ODOR = 'benzaldehyde'
STRENGTH = 50.0
WARMUP = 1


def timed_runs(use_mlx, seed, duration_ms, repeats, warmup=WARMUP):
    """
    Time `repeats` evolutions of `duration_ms`, after `warmup` untimed ones.

    The brain and the glomerular pattern are built once; only the reset,
    injection and evolution are inside the timed region, so the ratio reflects
    the integration loop rather than connectome loading.
    """
    brain, door, _ = init_olfactory_brain(use_mlx=use_mlx, seed=seed)
    pattern = door.get_glomerular_pattern(DIAG_ODOR)

    def one():
        brain.reset(deterministic=True)
        brain.inject_odor(pattern, strength=STRENGTH)
        t0 = time.perf_counter()
        brain.evolve(duration=duration_ms)
        if use_mlx:
            import mlx.core as mx
            mx.eval(brain.mean_phase, brain.mean_velocity,
                    brain.mean_amplitude, brain.var_phase)
        return time.perf_counter() - t0

    for _ in range(warmup):
        one()

    times = [one() for _ in range(repeats)]
    kc = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)

    return {
        'backend': 'MLX' if brain.use_mlx else 'NumPy',
        'num_neurons': int(brain.num_neurons),
        'num_synapses': int(len(np.asarray(brain.post_indices))),
        'dt_ms': float(brain.dt),
        'duration_ms': duration_ms,
        'steps': int(duration_ms / brain.dt),
        'mode': 'compiled_mlx' if getattr(brain, '_compiled_step', None)
                else ('interpreted_mlx' if brain.use_mlx else 'numpy'),
        'warmup_runs': warmup,
        'repeats': repeats,
        'wall_s_per_run': [round(t, 6) for t in times],
        'wall_s_median': float(np.median(times)),
        'wall_s_mean': float(np.mean(times)),
        'wall_s_std': float(np.std(times)),
        'wall_s_min': float(np.min(times)),
        'wall_s_max': float(np.max(times)),
        'rt_factor_median': float((duration_ms / 1000.0) / np.median(times)),
    }, np.asarray(kc, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repeats', type=int, default=5)
    ap.add_argument('--duration', type=float, default=100.0)
    ap.add_argument('--seed', type=int, default=DEFAULT_SEED)
    ap.add_argument('--output', default='cpu_vs_mlx_speedup.json')
    args = ap.parse_args()

    set_seed(args.seed)

    print(f"\n{'='*70}\nCPU vs MLX wall-clock ratio\n{'='*70}")
    print(f"repeats={args.repeats} (+{WARMUP} warm-up)  "
          f"duration={args.duration} ms  seed={args.seed}\n")

    mlx_stats, mlx_kc = timed_runs(True, args.seed, args.duration, args.repeats)
    cpu_stats, cpu_kc = timed_runs(False, args.seed, args.duration, args.repeats)

    # Matched-configuration check: a ratio between unmatched runs is meaningless,
    # so assert the match rather than trusting that the two calls agree.
    mismatches = {
        k: (cpu_stats[k], mlx_stats[k])
        for k in ('num_neurons', 'num_synapses', 'dt_ms', 'duration_ms', 'steps')
        if cpu_stats[k] != mlx_stats[k]
    }

    speedup_median = cpu_stats['wall_s_median'] / mlx_stats['wall_s_median']
    # Worst and best case over the observed spread, so the headline number is
    # bounded rather than a single lucky pair.
    speedup_worst = cpu_stats['wall_s_min'] / mlx_stats['wall_s_max']
    speedup_best = cpu_stats['wall_s_max'] / mlx_stats['wall_s_min']

    mlx_active = set(np.where(mlx_kc > 0.01)[0].tolist())
    cpu_active = set(np.where(cpu_kc > 0.01)[0].tolist())
    union = len(mlx_active | cpu_active)
    corr = (float(np.corrcoef(mlx_kc, cpu_kc)[0, 1])
            if np.std(mlx_kc) > 0 and np.std(cpu_kc) > 0 else None)

    agreement = {
        'active_kc_mlx': len(mlx_active),
        'active_kc_cpu': len(cpu_active),
        'active_kc_jaccard': (len(mlx_active & cpu_active) / union) if union else 1.0,
        'kc_pattern_pearson_r': corr,
        'kc_pattern_max_abs_diff': float(np.abs(mlx_kc - cpu_kc).max()),
        'bitwise_identical': bool(np.array_equal(mlx_kc, cpu_kc)),
        'note': (
            'Each backend is bit-for-bit reproducible against itself at a fixed '
            'seed. They are not bit-identical to each other because mx.sum and '
            'np.sum use different reduction trees; agreement is therefore '
            'reported as active-set overlap and pattern correlation.'
        ),
    }

    results = {
        'supersedes': 'results/superseded/cpu_vs_mlx_validation.json',
        'supersede_reason': (
            'That file recorded 1,283 active KCs against a few hundred in '
            'current runs, a null pattern_correlation, an empty kc_pattern, and '
            'validation_passed: true against a 0.95 correlation threshold it '
            'never evaluated. Its 86.34x is discarded.'
        ),
        'mlx': mlx_stats,
        'cpu': cpu_stats,
        'configuration_matched': not mismatches,
        'configuration_mismatches': mismatches,
        'speedup_cpu_over_mlx': {
            'median': speedup_median,
            'worst_case': speedup_worst,
            'best_case': speedup_best,
            'definition': 'cpu wall_s / mlx wall_s, both median of per-repeat times',
        },
        'output_agreement': agreement,
    }

    print(f"MLX : {mlx_stats['wall_s_median']*1000:8.1f} ms median "
          f"(sd {mlx_stats['wall_s_std']*1000:.1f}) "
          f"[{mlx_stats['mode']}]  RT {mlx_stats['rt_factor_median']:.3f}x")
    print(f"CPU : {cpu_stats['wall_s_median']*1000:8.1f} ms median "
          f"(sd {cpu_stats['wall_s_std']*1000:.1f}) "
          f"[{cpu_stats['mode']}]  RT {cpu_stats['rt_factor_median']:.4f}x")
    print(f"\nmatched configuration: {results['configuration_matched']} "
          f"({mlx_stats['num_neurons']:,} neurons, "
          f"{mlx_stats['num_synapses']:,} synapses, dt={mlx_stats['dt_ms']} ms, "
          f"{mlx_stats['steps']:,} steps)")
    print(f"speedup (CPU/MLX): median {speedup_median:.2f}x  "
          f"range {speedup_worst:.2f}x - {speedup_best:.2f}x")
    print(f"output agreement: {agreement['active_kc_cpu']} vs "
          f"{agreement['active_kc_mlx']} active KCs, "
          f"Jaccard {agreement['active_kc_jaccard']:.4f}, "
          f"r = {agreement['kc_pattern_pearson_r']:.4f}")

    brain, door, _ = init_olfactory_brain(use_mlx=True, seed=args.seed)
    out = write_results(args.output, results, brain=brain, door_client=door,
                        duration_ms=args.duration, seed=args.seed,
                        test='cpu_vs_mlx_speedup')
    print(f"\nWritten to {out}")


if __name__ == '__main__':
    main()
