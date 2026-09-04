#!/usr/bin/env python3
"""
Is the MBON readout a monotone function of KC->MBON synaptic weight?

Why this has to be measured
===========================
Hige et al. 2015 measures learning as a **reduction** in the MBON response
following depression of KC->MBON synapses. That measurement presupposes the
response magnitude increases with synaptic strength. If it does not, then
"depression of KC->MBON synapses" and "reduction of the MBON response" are not
the same thing in this model, the sign of the effect is not even guaranteed, and
the benchmark is ill-posed rather than failing.

There is a mechanistic reason to doubt monotonicity. This is a phase-coupled
oscillator network: the coupling force is

    w * sin(phi_pre - phi_post) * A_pre

so coupling pulls phases together rather than simply adding excitation, and the
amplitude field is driven by ``|velocity|``:

    amplitude <- amplitude * amp_decay + |velocity| * 0.1 * dt

Weaker coupling can leave a neuron oscillating more freely and therefore at
*higher* amplitude. Nothing guarantees the sign.

A first pass with one trial per scale gave a non-monotone sequence on both
backends, but a single trial is not evidence: the within-stimulus replicate
correlation in this model is about r = 0.54, so single trials are noisy. This
script averages the declared 8-trial set at each scale and sweeps finely enough
to see the shape.

Run: ``.venv/bin/python tests/diagnose_mbon_weight_monotonicity.py``
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    REFERENCE_STRENGTH, TRIAL_DURATION_MS, TRIAL_SEEDS, build, run_trial,
)
from validation_utils import write_results  # noqa: E402

SCALES = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0)
ODOR = 'pentyl_acetate'


def kc_to_mbon_current(brain, mask):
    """
    Total excitatory coupling current delivered to MBONs across KC->MBON
    synapses, using the engine's own coupling expression.

    This is the analogue of the quantity Hige et al. 2015 measured as its
    *primary* result: EPSC charge transfer at the MBON (Fig 3D, 90 +/- 3.7 %
    reduction), not spike rate. It is measured here because it is more faithful
    to the paper than the amplitude readout, and because it may be monotone in
    synaptic weight where the amplitude readout is not.

    Only the positive (depolarising) part is summed, matching an EPSC: the
    coupling term is signed and the negative half is a hyperpolarising
    contribution, which a charge-transfer measurement of *excitatory* current
    excludes.
    """
    phase = np.asarray(brain.mean_phase.tolist()
                       if hasattr(brain.mean_phase, 'tolist')
                       else brain.mean_phase, dtype=np.float64)
    amp = np.asarray(brain.mean_amplitude.tolist()
                     if hasattr(brain.mean_amplitude, 'tolist')
                     else brain.mean_amplitude, dtype=np.float64)
    w = np.asarray(brain.syn_weights.tolist()
                   if hasattr(brain.syn_weights, 'tolist')
                   else brain.syn_weights, dtype=np.float64)
    pre = np.asarray(brain.pre_indices)[mask]
    post = np.asarray(brain.post_indices)[mask]
    forces = w[mask] * np.sin(phase[pre] - phase[post]) * amp[pre]
    return float(np.sum(np.maximum(forces, 0.0)))


def main():
    from scipy.stats import spearmanr

    brain, door, connectome = build(use_mlx=True)

    from hive.substrate.olfactory_subgraph import classify_olfactory_neuron
    region_of = {}
    for nid, n in connectome.neurons.items():
        i = brain.id_to_idx.get(nid)
        if i is not None:
            region_of[i] = classify_olfactory_neuron(n)
    reg = np.array([region_of.get(i, '?') for i in range(brain.num_neurons)])
    pre, post = np.asarray(brain.pre_indices), np.asarray(brain.post_indices)
    kc_mbon = (reg[pre] == 'KC') & (reg[post] == 'MBON')

    import mlx.core as mx
    w0 = np.asarray(brain.syn_weights.tolist(), dtype=np.float32)

    print(f"KC->MBON synapses: {int(kc_mbon.sum())}")
    print(f"{len(TRIAL_SEEDS)} trials per scale, odour {ODOR}\n")
    print(f"{'scale':>6}  {'MBON mean':>12}  {'MBON sem':>10}  {'KC mean':>12}"
          f"  {'KC->MBON I':>14}")

    pattern = door.get_glomerular_pattern(ODOR)
    rows = []
    for scale in SCALES:
        w = w0.copy()
        w[kc_mbon] = w0[kc_mbon] * scale
        brain.syn_weights = mx.array(w)

        mbon, kc, current = [], [], []
        for seed in TRIAL_SEEDS:
            run_trial(brain, pattern, seed, strength=REFERENCE_STRENGTH,
                      duration_ms=TRIAL_DURATION_MS)
            mbon.append(float(np.mean(brain.get_region_activity('MBON'))))
            kc.append(float(np.mean(
                brain.get_region_activity('KC', normalize_kc=True,
                                          target_sparsity=0.06))))
            current.append(kc_to_mbon_current(brain, kc_mbon))
        m, s = float(np.mean(mbon)), float(np.std(mbon, ddof=1) / np.sqrt(len(mbon)))
        rows.append({
            'scale': scale,
            'mbon_mean': m, 'mbon_sem': s, 'mbon_trials': mbon,
            'kc_mean': float(np.mean(kc)),
            'kc_to_mbon_current_mean': float(np.mean(current)),
            'kc_to_mbon_current_sem':
                float(np.std(current, ddof=1) / np.sqrt(len(current))),
            'kc_to_mbon_current_trials': current,
        })
        print(f"{scale:>6.2f}  {m:>12.6f}  {s:>10.6f}  {np.mean(kc):>12.6f}"
              f"  {np.mean(current):>14.6f}")

    brain.syn_weights = mx.array(w0)

    scales = np.array([r['scale'] for r in rows])
    means = np.array([r['mbon_mean'] for r in rows])
    rho, p = spearmanr(scales, means)

    # Strict monotonicity of the trial means.
    monotone = bool(np.all(np.diff(means[::-1]) >= 0))

    # Is the full-strength response even distinguishable from the
    # all-KC->MBON-weights-zero response, given trial noise?
    from scipy.stats import mannwhitneyu
    u, p_extreme = mannwhitneyu(rows[0]['mbon_trials'], rows[-1]['mbon_trials'],
                                alternative='two-sided')

    # The same question for the synaptic-current readout, which is what Hige's
    # primary figure measured.
    cur = np.array([r['kc_to_mbon_current_mean'] for r in rows])
    rho_c, p_c = spearmanr(scales, cur)
    monotone_c = bool(np.all(np.diff(cur[::-1]) >= 0))
    u_c, p_extreme_c = mannwhitneyu(rows[0]['kc_to_mbon_current_trials'],
                                    rows[-1]['kc_to_mbon_current_trials'],
                                    alternative='two-sided')

    print("\n" + "-" * 70)
    print("MBON amplitude readout (analogue of spike rate):")
    print(f"  Spearman rho(scale, MBON mean) = {rho:.4f}  (p = {p:.4g})")
    print(f"  monotone non-decreasing in weight scale: {monotone}")
    print(f"  scale 1.0 vs 0.0 distinguishable: p = {p_extreme:.4g}")
    print(f"  range [{means.min():.6f}, {means.max():.6f}] "
          f"({100 * (means.max() - means.min()) / means.max():.2f} % of max)")
    print("KC->MBON coupling current (analogue of EPSC charge transfer):")
    print(f"  Spearman rho(scale, current) = {rho_c:.4f}  (p = {p_c:.4g})")
    print(f"  monotone non-decreasing in weight scale: {monotone_c}")
    print(f"  scale 1.0 vs 0.0 distinguishable: p = {p_extreme_c:.4g}")
    print(f"  range [{cur.min():.6f}, {cur.max():.6f}]")

    payload = {
        'question':
            'Is the MBON readout a monotone function of KC->MBON synaptic '
            'weight? Hige et al. 2015 measures learning as a reduction in the '
            'MBON response following synaptic depression, which presupposes '
            'that it is.',
        'mechanism_under_test':
            'coupling force is w * sin(phi_pre - phi_post) * A_pre and the '
            'amplitude field is driven by |velocity|, so coupling pulls phases '
            'together rather than simply adding excitation and weaker coupling '
            'can leave a neuron oscillating at higher amplitude',
        'protocol': {
            'odorant': ODOR,
            'n_trials_per_scale': len(TRIAL_SEEDS),
            'trial_seeds': list(TRIAL_SEEDS),
            'scales': list(SCALES),
            'backend': 'MLX',
            'note':
                'run after the compiled-kernel weight-capture fix, without '
                'which every scale would read identically on MLX',
        },
        'rows': rows,
        'summary': {
            'mbon_amplitude_readout': {
                'analogue_of': 'MBON spike rate (Hige 2015: 80 +/- 5.7 %)',
                'spearman_rho': float(rho),
                'spearman_p': float(p),
                'monotone_non_decreasing': monotone,
                'extreme_contrast_p': float(p_extreme),
                'mean_min': float(means.min()),
                'mean_max': float(means.max()),
                'dynamic_range_pct_of_max':
                    float(100 * (means.max() - means.min()) / means.max()),
            },
            'kc_to_mbon_current_readout': {
                'analogue_of':
                    'MBON EPSC charge transfer, Hige 2015 primary figure '
                    '(Fig 3D: 90 +/- 3.7 %)',
                'spearman_rho': float(rho_c),
                'spearman_p': float(p_c),
                'monotone_non_decreasing': monotone_c,
                'extreme_contrast_p': float(p_extreme_c),
                'mean_min': float(cur.min()),
                'mean_max': float(cur.max()),
            },
        },
    }
    out = write_results('mbon_weight_monotonicity.json', payload,
                        brain=brain, door_client=door,
                        duration_ms=TRIAL_DURATION_MS, seed=None,
                        suite='diagnose_mbon_weight_monotonicity')
    print(f"Written to {out}")


if __name__ == '__main__':
    main()
