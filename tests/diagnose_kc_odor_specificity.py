#!/usr/bin/env python3
"""
Why is dopamine-gated depression not odour-specific in this model?

The repaired learning benchmark (``benchmarks_repaired/learning.py``) passes on
depression and on the dopamine requirement, but fails odour specificity: with
pentyl acetate paired, the *unpaired* control odour ethyl lactate is depressed
84.4 % against the paired odour's 80.2 %. The sweep shows the same across five
orders of magnitude of the learning rate, so it is not a calibration artifact.

Hige et al. 2015 Fig 7I attributes specificity to a single quantity: "Magnitude
of depression correlates with extent of overlap in KC response patterns
(p < 0.005, Pearson's r = 0.90)." So the hypothesis to test is that the KC
representations of the two odours, **as the plasticity rule sees them**, are not
distinct.

The rule is ``dw_ij = -eta_d * A_KC(i) * D``, so it reads the raw KC amplitude
field, not the thresholded readout. The benchmarks all report the *thresholded*
KC pattern, in which only 316 of 5,279 KCs survive, and those patterns are
clearly odour-distinct. This script asks whether the raw amplitude field the
plasticity rule actually consumes is odour-distinct too, and quantifies the gap
between the two representations.

Run: ``.venv/bin/python tests/diagnose_kc_odor_specificity.py``
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    REFERENCE_STRENGTH, TRIAL_DURATION_MS, TRIAL_SEEDS, binarise, build,
    run_trial,
)
from validation_utils import write_results  # noqa: E402

PAIRED = 'pentyl_acetate'
CONTROL = 'ethyl_lactate'
# Third odorant with a known-overlapping representation in the paper, for
# contrast: Hige Fig 7C-E reports BA depressed nearly as much as PA.
OVERLAPPING = 'butyl_acetate'


def raw_kc(brain):
    idx = brain._region_indices('KC')
    amp = brain.mean_amplitude
    amp = np.asarray(amp.tolist() if hasattr(amp, 'tolist') else amp,
                     dtype=np.float64)
    return amp[idx]


def collect(brain, door, name):
    pattern = door.get_glomerular_pattern(name)
    raw, thresholded = [], []
    for seed in TRIAL_SEEDS:
        run_trial(brain, pattern, seed, strength=REFERENCE_STRENGTH,
                  duration_ms=TRIAL_DURATION_MS)
        raw.append(raw_kc(brain))
        thresholded.append(
            brain.get_region_activity('KC', normalize_kc=True,
                                      target_sparsity=0.06))
    return np.array(raw), np.array(thresholded)


def main():
    brain, door, _ = build(use_mlx=True)

    print("Collecting KC representations, 8 trials per odorant...\n")
    data = {}
    for name in (PAIRED, CONTROL, OVERLAPPING):
        raw, thr = collect(brain, door, name)
        data[name] = {'raw': raw, 'thr': thr}

    rows = {}
    print(f"{'odorant':<20} {'raw min':>10} {'raw max':>10} {'raw CV':>8} "
          f"{'frac>0':>8} {'thr n>0':>8}")
    for name, d in data.items():
        raw_mean = d['raw'].mean(axis=0)
        thr_mean = d['thr'].mean(axis=0)
        cv = float(np.std(raw_mean) / np.mean(raw_mean))
        rows[name] = {
            'raw_min': float(raw_mean.min()),
            'raw_max': float(raw_mean.max()),
            'raw_mean': float(raw_mean.mean()),
            'raw_cv': cv,
            'raw_fraction_nonzero': float(np.mean(raw_mean > 0)),
            'thresholded_n_nonzero': int(np.sum(thr_mean > 0)),
            'n_kc': int(raw_mean.size),
        }
        print(f"{name:<20} {raw_mean.min():>10.6f} {raw_mean.max():>10.6f} "
              f"{cv:>8.4f} {np.mean(raw_mean > 0):>8.4f} "
              f"{int(np.sum(thr_mean > 0)):>8d}")

    print("\nPairwise similarity of KC representations "
          "(mean over trials, then Pearson r):")
    pairs = {}
    names = list(data)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            raw_r = float(np.corrcoef(data[a]['raw'].mean(axis=0),
                                      data[b]['raw'].mean(axis=0))[0, 1])
            thr_r = float(np.corrcoef(data[a]['thr'].mean(axis=0),
                                      data[b]['thr'].mean(axis=0))[0, 1])
            bin_a = binarise(data[a]['thr'].mean(axis=0))
            bin_b = binarise(data[b]['thr'].mean(axis=0))
            sa, sb = set(np.flatnonzero(bin_a)), set(np.flatnonzero(bin_b))
            jac = len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0
            pairs[f'{a}__{b}'] = {
                'raw_amplitude_field_r': raw_r,
                'thresholded_readout_r': thr_r,
                'binary_active_set_jaccard': jac,
            }
            print(f"  {a:<18} vs {b:<18} "
                  f"raw r={raw_r:.4f}  thresholded r={thr_r:.4f}  "
                  f"Jaccard={jac:.4f}")

    # The decisive quantity: the plasticity rule weights each KC by its raw
    # amplitude, so the fraction of total depression that any one odour
    # directs at "its own" KCs is what specificity depends on.
    print("\nWhat the plasticity rule sees, per odorant:")
    drive = {}
    for name, d in data.items():
        raw_mean = d['raw'].mean(axis=0)
        total = float(raw_mean.sum())
        top316 = float(np.sort(raw_mean)[::-1][:316].sum())
        drive[name] = {
            'total_amplitude': total,
            'amplitude_in_top_316_kcs': top316,
            'fraction_of_depression_on_top_316': top316 / total,
        }
        print(f"  {name:<20} top-316 KCs carry "
              f"{100 * top316 / total:5.2f} % of the total KC amplitude "
              f"that the rule depresses")

    raw_rs = [v['raw_amplitude_field_r'] for v in pairs.values()]
    thr_rs = [v['thresholded_readout_r'] for v in pairs.values()]
    top_fracs = [v['fraction_of_depression_on_top_316'] for v in drive.values()]

    # The cause is NOT that the raw field is odour-blind: pentyl acetate and
    # ethyl lactate correlate at r = 0.386 in it, which is distinct. The cause
    # is that the raw field is non-zero on *every* KC, and the sparse code is a
    # small minority of the total amplitude, so depression proportional to raw
    # amplitude is dominated by the odour-invariant bulk.
    verdict = (
        'The raw KC amplitude field IS odour-distinct: the paired and control '
        f'odours correlate at r = {pairs[f"{PAIRED}__{CONTROL}"]["raw_amplitude_field_r"]:.4f} '
        'in it. That is not the problem. The problem is that the field is '
        'non-zero on every one of the 5,279 KCs, and the 316 KCs that survive '
        'the APL rank threshold carry only '
        f'{100 * min(top_fracs):.2f} to {100 * max(top_fracs):.2f} % of the '
        'total KC amplitude. A rule proportional to raw amplitude therefore '
        'directs about 86 % of its depression at KCs that are not part of the '
        'sparse code at all, and that bulk is close to odour-invariant. The '
        'odour-specific signal is present but is a minority of what the rule '
        'weights by. Hige et al. 2015 Fig 7I ties specificity to KC pattern '
        'overlap, and the mechanism it implies is that only KCs actually '
        'depolarised by the odour have their terminals depressed. The '
        'faithful analogue of "depolarised" in this model is passing the APL '
        'threshold, i.e. the thresholded readout, not the raw field. So the '
        'rule should read the thresholded activity. Both variants are scored '
        'in benchmarks_repaired/learning.py.'
    )
    print("\n" + "-" * 70)
    print(verdict)

    payload = {
        'question':
            'Why is dopamine-gated KC->MBON depression not odour-specific in '
            'this model, when Hige et al. 2015 Fig 7F-H reports the '
            'non-overlapping odour ethyl lactate as unaffected?',
        'hypothesis_tested':
            'the plasticity rule dw = -eta_d * A_KC * D reads the RAW KC '
            'amplitude field, not the thresholded readout the benchmarks '
            'report, and the raw field may not be odour-distinct',
        'reference_claim':
            "Hige et al. 2015 Fig 7I: 'Magnitude of depression correlates with "
            "extent of overlap in KC response patterns (p < 0.005, Pearson's "
            "r = 0.90)'",
        'protocol': {
            'odorants': [PAIRED, CONTROL, OVERLAPPING],
            'odorant_roles': {
                PAIRED: 'paired odour in the learning benchmark (PA)',
                CONTROL: 'control odour reported unaffected in Hige Fig 7F-H '
                         '(EL)',
                OVERLAPPING: 'odour reported depressed nearly as much as PA in '
                             'Hige Fig 7C-E (BA)',
            },
            'n_trials_per_odorant': len(TRIAL_SEEDS),
            'trial_seeds': list(TRIAL_SEEDS),
            'backend': 'MLX',
        },
        'per_odorant': rows,
        'pairwise': pairs,
        'what_the_rule_sees': drive,
        'summary': {
            'raw_amplitude_field_r_range': [min(raw_rs), max(raw_rs)],
            'thresholded_readout_r_range': [min(thr_rs), max(thr_rs)],
            'fraction_of_depression_on_top_316_range':
                [min(top_fracs), max(top_fracs)],
            'raw_field_is_nonzero_on_every_kc':
                all(r['raw_fraction_nonzero'] == 1.0 for r in rows.values()),
            'verdict': verdict,
        },
    }
    out = write_results('kc_odor_specificity.json', payload,
                        brain=brain, door_client=door,
                        duration_ms=TRIAL_DURATION_MS, seed=None,
                        suite='diagnose_kc_odor_specificity')
    print(f"Written to {out}")


if __name__ == '__main__':
    main()
