#!/usr/bin/env python3
"""
Checks on the shared benchmark harness.

Three things must hold before any repaired benchmark can be believed:

1. **The harness is exactly reproducible.** A declared seed list must give the
   same numbers every time, or none of the repaired results can be re-derived.
2. **It changes nothing about the model.** dt, gamma, sigma_noise, the synaptic
   weights and the readout sparsity must be identical before and after a trial
   set runs.
3. **It actually produces variance**, which is the whole point: the old protocol
   produced none.

Run: ``.venv/bin/python tests/test_benchmark_harness.py``
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    ODOR_PANEL, PANEL, TRIAL_SEEDS, between_stimulus_correlations, binarise,
    build, separability, trial_set, within_stimulus_correlations,
)


def main():
    failures = []

    def check(name, ok, detail=''):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              + (f"   {detail}" if detail else ''))
        if not ok:
            failures.append(name)

    print("Building engine (MLX)...")
    brain, door, _ = build(use_mlx=True)

    print("\n1. Panel availability")
    missing = []
    for name in PANEL:
        try:
            door.get_glomerular_pattern(name)
        except Exception as exc:                     # noqa: BLE001
            missing.append(f"{name}: {exc}")
    check(f"all {len(PANEL)} panel odorants resolve in the DoOR matrix",
          not missing, '; '.join(missing))
    check("every panel odorant carries a paper provenance string",
          all(ODOR_PANEL.get(n) for n in PANEL))

    pattern = door.get_glomerular_pattern('benzaldehyde')

    print("\n2. Physics untouched by running trials")
    before = {
        'dt': brain.dt, 'gamma': brain.gamma,
        'sigma_noise': brain.sigma_noise,
        'w_sum': float(np.sum(np.asarray(
            brain.syn_weights.tolist() if hasattr(brain.syn_weights, 'tolist')
            else brain.syn_weights, dtype=np.float64))),
    }
    trials = trial_set(brain, pattern)
    after = {
        'dt': brain.dt, 'gamma': brain.gamma,
        'sigma_noise': brain.sigma_noise,
        'w_sum': float(np.sum(np.asarray(
            brain.syn_weights.tolist() if hasattr(brain.syn_weights, 'tolist')
            else brain.syn_weights, dtype=np.float64))),
    }
    for k in before:
        check(f"{k} unchanged", before[k] == after[k],
              f"{before[k]} -> {after[k]}")

    print("\n3. Readout sparsity unchanged (rank threshold still 6 %)")
    n_active = [int(np.sum(binarise(t))) for t in trials]
    n_nonzero = [int(np.sum(t > 0)) for t in trials]
    check("rank threshold gives int(5279 * 0.06) = 316 non-zero KCs every trial",
          all(n == 316 for n in n_nonzero), f"{sorted(set(n_nonzero))}")
    check("binarised active count constant across trials",
          len(set(n_active)) == 1, f"{sorted(set(n_active))}")

    print("\n4. Exact reproducibility of the declared seed list")
    repeat = trial_set(brain, pattern)
    check("same seeds give bit-identical trials",
          np.array_equal(trials, repeat))

    print("\n5. The harness produces variance (the old protocol did not)")
    distinct = len({t.tobytes() for t in trials})
    check(f"all {len(TRIAL_SEEDS)} trials distinct", distinct == len(TRIAL_SEEDS),
          f"{distinct} distinct")
    within = within_stimulus_correlations(trials, binary=True)
    check("within-stimulus null is defined and below 1.0",
          len(within) == 28 and max(within) < 1.0,
          f"n={len(within)}, mean r={np.mean(within):.4f}, "
          f"range [{min(within):.4f}, {max(within):.4f}]")

    print("\n6. Contrast: deterministic reset carries no randomness at all")
    det = []
    for seed in (42, 7, 1234):
        from validation_utils import set_seed
        set_seed(seed)
        brain.reset(deterministic=True)
        brain.inject_odor(pattern, strength=50.0)
        brain.evolve(duration=100.0)
        det.append(brain.get_region_activity('KC', normalize_kc=True,
                                             target_sparsity=0.06))
    check("deterministic reset: seeds 42/7/1234 bit-identical "
          "(so repeats cannot be averaged)",
          np.array_equal(det[0], det[1]) and np.array_equal(det[0], det[2]))

    print("\n7. Null calibration: a stimulus is NOT separable from itself")
    self_sep = separability(trials, repeat, binary=True)
    check("identical stimulus, seed-matched -> not separable",
          self_sep['separable'] is False,
          f"p={self_sep['p_value']:.4f}, within={self_sep['within_mean']:.4f}, "
          f"between={self_sep['between_mean']:.4f}, "
          f"auc={self_sep['effect_size_auc']:.3f}")

    print("\n7b. Why the design is seed-matched (documented finding)")
    # An unmatched design compares the same odorant across two disjoint,
    # consecutive seed blocks. It reports the stimulus separable from itself,
    # because consecutive-seed blocks carry enough structure to shift the mean
    # correlation and the sample sizes are large enough for that to be
    # significant. Asserted here so a future change back to an unmatched design
    # fails loudly instead of quietly producing significance from nothing.
    from scipy.stats import mannwhitneyu
    block_b = trial_set(brain, pattern,
                        seeds=(2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008))
    unmatched_within = (within_stimulus_correlations(trials, True)
                        + within_stimulus_correlations(block_b, True))
    unmatched_between = between_stimulus_correlations(
        trials, block_b, binary=True, exclude_same_seed=False)
    _, p_unmatched = mannwhitneyu(unmatched_between, unmatched_within,
                                  alternative='less')
    check("unmatched seed blocks DO manufacture significance "
          "(this is why the design is matched)",
          p_unmatched < 0.05,
          f"p={p_unmatched:.4f}, within={np.mean(unmatched_within):.4f}, "
          f"between={np.mean(unmatched_between):.4f}")

    print("\n8. A clearly different odorant IS separable")
    el = door.get_glomerular_pattern('ethyl_lactate')
    el_trials = trial_set(brain, el)
    diff_sep = separability(trials, el_trials, binary=True)
    check("benzaldehyde vs ethyl_lactate -> separable",
          diff_sep['separable'] is True,
          f"p={diff_sep['p_value']:.2e}, within={diff_sep['within_mean']:.4f}, "
          f"between={diff_sep['between_mean']:.4f}, "
          f"auc={diff_sep['effect_size_auc']:.3f}")

    print("\n" + "=" * 70)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED: {failures}")
        return 1
    print("ALL HARNESS CHECKS PASSED")
    return 0


if __name__ == '__main__':
    sys.exit(main())
