"""
Concentration invariance, and why the target it was scored against is not real.

The 0.70 target is not in the paper it is attributed to
======================================================
Every version of this measurement in the repository is scored against
"r > 0.70 (Turner et al. 2008)". For example ``THESIS_DIGITAL_SMELL.md``:

  "**Turner, Bazhenov, Laurent (2008)**. 'Olfactory representations by
   *Drosophila* mushroom body neurons.' *J Neurophysiol* -- **Benchmark for
   concentration invariance (r > 0.70)**"

**Turner et al. 2008 contains no concentration series and no correlation
threshold.** Read in full. Its stimulus protocol is a single dilution:

  "Vials contained odor diluted 1:100 in paraffin oil, which, combined with the
   1:10 dilution in the constant air stream, resulted in a 1:1,000 effective
   odor dilution. [...] Seventy-one KCs were recorded under these stimulus
   conditions."

A second dataset of 40 KCs used one different protocol, again a single
concentration, chosen to match the conditions under which OSNs had been
characterised. The paper's measurements are KC response probability (6 % against
59 % in OSNs) and angular separation between odour pairs. Neither is a
concentration invariance.

Where the 0.70 most likely came from
====================================
Campbell et al. 2013 (J Neurosci 33:10568-10581) Fig 4C, same laboratory:

  "Across all recordings (n = 24), the correlation score of PA-BA (mean
   **r = 0.70**) is substantially and significantly greater than either PA-EL
   (mean r = 0.15) or BA-EL (mean r = 0.11)"

That is the similarity between two chemically similar *odorants*, pentyl acetate
and butyl acetate. It is not an invariance across concentrations of one odorant.
The number appears to have migrated between measurements.

What the real Drosophila concentration paper measured
=====================================================
Honegger KS, Campbell RAA, Turner GC (2011) *J Neurosci* 31:11772-11785 is the
Drosophila KC concentration study, and the quantity it found invariant is
**population sparseness**, not pattern correlation:

  "We found that response sparseness was relatively concentration-invariant.
   Within the concentration range we tested, the proportion of responding KCs
   remained < 0.2"

  "We used a mixed-effects ANOVA to evaluate the effects of stimulus
   concentration, stimulus order, and odor identity on sparseness. There was no
   effect of odor identity, so we pooled the data. We found there was a
   significant effect of stimulus concentration (p < 0.0001, F(4,73) = 32.9).
   However, this was profoundly affected by the order in which the stimuli are
   presented. In the high-to-low condition, sparseness was significantly
   modulated by concentration (p < 0.0001, F(3,25) = 22.5), but **not in the
   low-to-high situation (p = 0.71, F(3,32) = 0.47)**."

So the published invariance holds in the **ascending** order, which is the order
used here, declared in advance for that reason.

Why the published quantity cannot be tested in this model
=========================================================
The KC readout applies a rank threshold at ``int(n_kc * target_sparsity)``,
which produces exactly ``int(5279 * 0.06) = 316`` non-zero KCs for **every**
stimulus, at every concentration, always. Population sparseness is therefore
pinned to a constant by construction. Honegger et al.'s result would be
reproduced trivially and would mean nothing.

Readout sparsity is fixed for this repair, so this is reported as a limitation
rather than engineered around. Both quantities are recorded:

  (a) the pattern correlation the repository has always reported, with the note
      that no published Drosophila threshold exists for it;
  (b) the sparseness Honegger et al. actually measured, with its pinned value
      shown, so the limitation is visible in the data and not only in prose.

This measurement is reported **separately** and is not one of the five scored
benchmarks, matching how the repository has always treated it.
"""

import itertools
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    TARGET_SPARSITY,  # noqa: E402
    REFERENCE_STRENGTH, TRIAL_DURATION_MS, TRIAL_SEEDS, binarise, build,
    mean_pattern, panel_block, protocol_block, trial_set,
)
from validation_utils import write_results  # noqa: E402

# ── Declared before any result was seen ──────────────────────────────────────

#: Ascending order, matching Honegger et al. 2011's low-to-high condition,
#: which is the one in which sparseness is invariant (p = 0.71). Declared in
#: advance for that reason.
CONCENTRATIONS = (0.1, 0.5, 1.0, 5.0, 10.0)

#: The three odorants the repository's concentration test has always used, plus
#: the two Honegger et al. 2011 Fig 6 used for its concentration series
#: (isoamyl acetate is isopentyl_acetate here; ethyl acetate for breadth).
ODORANTS = ('benzaldehyde', '2-heptanone', 'isopentyl_acetate',
            'ethyl_acetate', '3-octanol')

#: Weber-Fechner receptor compression, unchanged from
#: tests/concentration_invariance_test.py so the numbers stay comparable.
def scaled_strength(conc):
    return REFERENCE_STRENGTH * np.log10(1 + 10 * conc)


HONEGGER_SPARSENESS_CEILING = 0.2


def run(use_mlx=False, output='concentration_invariance_repaired.json'):
    from scipy.stats import f_oneway

    print("=" * 70)
    print("CONCENTRATION INVARIANCE (reported separately, not one of the five)")
    print("=" * 70)

    brain, door, _ = build(use_mlx=use_mlx)

    per_odor = {}
    all_pair_r = []
    #: Kenyon cell count, taken from the readout rather than hardcoded, because
    #: strict neuron classification changes it (5,279 loose, 5,177 strict) and the
    #: rank threshold is int(n_kc * target_sparsity).
    n_kc_total = None
    for name in ODORANTS:
        pattern = door.get_glomerular_pattern(name)
        by_conc = {c: trial_set(brain, pattern, strength=scaled_strength(c))
                   for c in CONCENTRATIONS}
        if n_kc_total is None:
            n_kc_total = int(np.asarray(by_conc[CONCENTRATIONS[0]][0]).size)

        # (a) Pattern correlation between every pair of concentrations, on the
        #     mean pattern at each, binarised as the repository has always done.
        pair_r = {}
        for ca, cb in itertools.combinations(CONCENTRATIONS, 2):
            a = binarise(mean_pattern(by_conc[ca]))
            b = binarise(mean_pattern(by_conc[cb]))
            r = (float(np.corrcoef(a, b)[0, 1])
                 if np.std(a) > 0 and np.std(b) > 0 else None)
            pair_r[f'{ca}x_vs_{cb}x'] = r
            if r is not None:
                all_pair_r.append(r)

        # (b) The quantity Honegger et al. 2011 measured, per trial.
        sparseness = {
            c: [float(np.mean(t > 0)) for t in by_conc[c]]
            for c in CONCENTRATIONS
        }
        f_stat, p_sparse = f_oneway(*[sparseness[c] for c in CONCENTRATIONS])

        defined = [v for v in pair_r.values() if v is not None]
        per_odor[name] = {
            'pairwise_correlation': pair_r,
            'pairwise_correlation_mean':
                float(np.mean(defined)) if defined else None,
            'sparseness_per_concentration': sparseness,
            'sparseness_mean_per_concentration': {
                str(c): float(np.mean(sparseness[c])) for c in CONCENTRATIONS},
            'sparseness_anova': {
                'f': float(f_stat), 'p_value': float(p_sparse),
                'test': 'one-way ANOVA over concentrations',
                'caveat':
                    'meaningless here: the rank threshold pins sparseness to a '
                    'constant, so there is no variance for the test to find',
            },
        }
        print(f"  {name:<20} mean pairwise r = "
              f"{per_odor[name]['pairwise_correlation_mean']:.4f}   "
              f"sparseness = "
              f"{list(per_odor[name]['sparseness_mean_per_concentration'].values())[0]:.6f} "
              f"(constant across concentrations)")

    overall_r = float(np.mean(all_pair_r)) if all_pair_r else None

    # Is sparseness in fact pinned? Asserted from the data, not assumed.
    #
    # Tested on peak-to-peak rather than `np.std(...) == 0.0`. That earlier test
    # was a strict float equality on a *computed* standard deviation, and it gave
    # a false negative the first time the Kenyon cell count changed: under strict
    # neuron classification there are 5,177 KCs rather than 5,279, all 200
    # recorded values were identical at 310/5177 = 0.059880239521, and np.std
    # still returned 2.08e-17 instead of exactly zero. max - min is exact for
    # identical floats, so it does not have that failure mode, and the tolerance
    # is there only to absorb the last bit.
    all_sparse = [v for o in per_odor.values()
                  for vals in o['sparseness_per_concentration'].values()
                  for v in vals]
    sparseness_spread = float(np.ptp(all_sparse)) if all_sparse else 0.0
    sparseness_pinned = bool(sparseness_spread <= 1e-12)
    pinned_value = float(all_sparse[0]) if all_sparse else None
    n_kc_active = (int(round(pinned_value * n_kc_total))
                   if pinned_value and n_kc_total else None)

    print("\n" + "-" * 70)
    print(f"Pattern correlation, mean over {len(all_pair_r)} concentration "
          f"pairs across {len(ODORANTS)} odorants: r = {overall_r:.4f}")
    print(f"  no published Drosophila threshold exists for this quantity; "
          f"the 0.70 it used to be scored against is not in Turner et al. 2008")
    print(f"Sparseness (Honegger et al. 2011's quantity): "
          f"{pinned_value:.6f}, identical at every concentration: "
          f"{sparseness_pinned}  (spread {sparseness_spread:.2e})")
    print(f"  pinned by the rank threshold at "
          f"int({n_kc_total} * {TARGET_SPARSITY}) = {n_kc_active} of "
          f"{n_kc_total} KCs, so the published comparison is unavailable")

    payload = {
        'measurement': 'concentration_invariance',
        'scored': False,
        'why_not_scored':
            'reported separately, as the repository has always treated it, and '
            'because neither quantity below can be scored against a published '
            'Drosophila number: the correlation has no published threshold, '
            'and the sparseness the published paper measured is pinned to a '
            'constant by this readout.',
        'target_corrections': {
            'removed': 'r > 0.70, attributed to Turner et al. 2008',
            'why':
                'Turner et al. 2008 contains no concentration series and no '
                'correlation threshold. Read in full: all 71 KCs were recorded '
                'at a single 1:1,000 effective dilution, and a second dataset '
                'of 40 KCs used one different single-concentration protocol. '
                'The paper measures KC response probability (6 % against 59 % '
                'in OSNs) and angular separation between odour pairs.',
            'probable_origin':
                'Campbell et al. 2013 Fig 4C, same laboratory, reports mean '
                'r = 0.70 for the pentyl acetate / butyl acetate ODOUR PAIR '
                '(n = 24), significantly greater than PA-EL 0.15 and BA-EL '
                '0.11. That is similarity between two chemically similar '
                'odorants, not invariance across concentrations of one '
                'odorant. The number appears to have migrated between '
                'measurements.',
            'correct_reference':
                'Honegger KS, Campbell RAA, Turner GC (2011) J Neurosci '
                '31:11772-11785 is the Drosophila KC concentration study, and '
                'the quantity it found invariant is POPULATION SPARSENESS, not '
                'pattern correlation: "the proportion of responding KCs '
                'remained < 0.2". Its statistics: significant concentration '
                'effect overall (p < 0.0001, F(4,73) = 32.9), significant in '
                'the high-to-low order (p < 0.0001, F(3,25) = 22.5), and NOT '
                'significant in the low-to-high order (p = 0.71, '
                'F(3,32) = 0.47).',
        },
        'known_limitation': {
            'what':
                "Honegger et al. 2011's quantity cannot be tested in this "
                'model.',
            'why':
                'the KC readout applies a rank threshold at '
                'int(n_kc * target_sparsity), producing exactly '
                'int(5279 * 0.06) = 316 non-zero KCs for every stimulus at '
                'every concentration. Population sparseness is pinned to a '
                'constant by construction, so the published result would be '
                'reproduced trivially and would mean nothing.',
            'sparseness_pinned_verified_from_data': sparseness_pinned,
            'sparseness_spread_max_minus_min': sparseness_spread,
            'pinned_sparseness_value': pinned_value,
            'n_kc_total': n_kc_total,
            'n_kc_active_pinned': n_kc_active,
            'honegger_ceiling': HONEGGER_SPARSENESS_CEILING,
            'consequence':
                'readout sparsity is fixed for this repair, so this is '
                'recorded as a limitation rather than engineered around.',
        },
        'protocol': protocol_block(extra={
            'odorants': list(ODORANTS),
            'concentrations': list(CONCENTRATIONS),
            'concentration_order': 'ascending',
            'concentration_order_rationale':
                "matches Honegger et al. 2011's low-to-high condition, which "
                'is the one in which sparseness is invariant (p = 0.71, '
                'F(3,32) = 0.47); the high-to-low order is significantly '
                'modulated (p < 0.0001). Declared in advance for that reason.',
            'strength_scaling':
                'REFERENCE_STRENGTH * log10(1 + 10 * conc), the Weber-Fechner '
                'compression used by tests/concentration_invariance_test.py, '
                'unchanged so the numbers stay comparable',
        }),
        'panel': panel_block([o for o in ODORANTS]),
        'per_odorant': per_odor,
        'summary': {
            'pattern_correlation_mean': overall_r,
            'n_concentration_pairs': len(all_pair_r),
            'n_odorants': len(ODORANTS),
            'pattern_correlation_has_no_published_threshold': True,
            'sparseness_pinned_by_readout': sparseness_pinned,
            'sparseness_spread_max_minus_min': sparseness_spread,
            'pinned_sparseness_value': pinned_value,
            'n_kc_total': n_kc_total,
            'n_kc_active_pinned': n_kc_active,
            'previously_reported': {
                'F8_run': 0.2719,
                'published_claim_now_withdrawn': 0.7244,
                'withdrawn_because':
                    'the 0.7244 mean included isoamyl acetate, which is absent '
                    'from the DoOR matrix and returned a zero vector that '
                    'self-correlates at exactly 1.0000 across all ten '
                    'concentration pairs; on real odorants only the same run '
                    'gives 0.5866. See README.md.',
            },
        },
    }

    out = write_results(output, payload, brain=brain, door_client=door,
                        duration_ms=TRIAL_DURATION_MS, seed=None,
                        suite='concentration_invariance_repaired')
    print(f"Written to {out}")
    return payload


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mlx', action='store_true',
                    help='development only; reported runs use CPU')
    ap.add_argument('--output',
                    default='concentration_invariance_repaired.json')
    a = ap.parse_args()
    run(use_mlx=a.mlx, output=a.output)
