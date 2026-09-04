"""
Odour mixtures: sub-additive KC recruitment (Honegger, Campbell & Turner 2011).

What the old benchmark measured
===============================
``scripts/run_all_validations.py::validate_odor_mixtures`` mixed two glomerular
patterns, counted how many of each component's active KCs the mixture also
activated, and required the mean overlap to land in [30, 50] %.

The target is attributed to Stettler & Axel 2009 and Deisig et al. 2006. Neither
is a Drosophila mushroom-body measurement: Stettler & Axel is mouse piriform
cortex, Deisig et al. is honeybee antennal lobe. No source for a 30-50 % KC
overlap band in Drosophila was found.

It also tested exactly **one** mixture, formed from the first two of the three
suite odorants, and the F8 result of 30.06 % sat 0.06 points inside the band.

What this module measures instead
=================================
Honegger KS, Campbell RAA, Turner GC (2011) "Cellular-resolution population
imaging reveals robust sparse coding in the Drosophila mushroom body",
*J Neurosci* 31:11772-11785, Fig 7 -- the Drosophila MB mixture measurement:

  "The odors 3-octanol and 4-methylcyclohexanol activate very different
   populations of KCs. Presented individually, each of these odors activates 9 %
   of KCs on average. When presented simultaneously, however, this proportion
   increases only slightly (11 %) and is smaller than the linear sum of the two
   activity patterns, 15 %. A different pair of odors, 2-heptanone and pentyl
   acetate, also did not show supra-additive responses. Individual cells
   displayed both suppressive and synergistic interactions, with most cells
   showing a weaker response to the mixture than predicted from the linear sum
   of the response to the components. [...] Overall, these results indicate that
   blending odors has only a modest effect on the sparseness of MB
   representations, due to the subadditive recruitment of KCs."

So the published quantity is **sub-additivity**: the mixture response is below
the linear sum of the components, not a fixed overlap percentage. Both published
pairs are used, and all four odorants are in the DoOR matrix.

An obstacle that has to be stated, not worked around
====================================================
Honegger et al. measured the *proportion of responding KCs*: 9 %, 9 % -> 11 %
against a 15 % linear sum. **That proportion cannot vary in this model.** The KC
readout applies a rank threshold at ``int(n_kc * target_sparsity)``, which is
exactly ``int(5279 * 0.06) = 316`` non-zero KCs for every stimulus, always.
Verified in ``tests/test_benchmark_harness.py``. The readout pins the very
quantity the paper reports.

The readout sparsity is fixed for this repair, so the published comparison is
unavailable at the binary level and that is recorded as a limitation. Instead
sub-additivity is measured on the **pre-threshold continuous KC amplitude**,
which is not pinned:

    sub-additivity index = summed mixture amplitude / summed linear-sum amplitude

where the linear-sum reference is the per-KC sum of the two component responses,
which is what "the linear sum of the two activity patterns" means. An index
below 1 is sub-additive, above 1 supra-additive.

The old 30-50 % overlap number is still computed and reported, as a secondary,
with its citation flagged as non-Drosophila.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    TRIAL_DURATION_MS, TRIAL_SEEDS, binarise, build, mean_pattern,
    panel_block, protocol_block, trial_set,
)
from validation_utils import write_results  # noqa: E402

# ── Declared before any result was seen ──────────────────────────────────────

#: Both pairs Honegger et al. 2011 Fig 7 reports. All four in the DoOR matrix.
PUBLISHED_PAIRS = (
    ('3-octanol', '4-methylcyclohexanol'),      # Fig 7A
    ('2-heptanone', 'pentyl_acetate'),          # Fig 7B
)

#: Honegger et al. 2011 Fig 7A, for reporting alongside.
PUBLISHED = {
    'component_fraction': 0.09,
    'mixture_fraction': 0.11,
    'linear_sum_fraction': 0.15,
    'subadditivity_index': 0.11 / 0.15,
}

#: The band the old benchmark used, kept only as a reported secondary.
LEGACY_OVERLAP_BAND = (30.0, 50.0)

ALPHA = 0.05


def mixture_pattern(door, a, b):
    """
    Glomerular pattern for an equal mixture of two odorants.

    Mixed in receptor space and then projected, because that is where a
    physical mixture acts. The old benchmark averaged already-projected
    glomerular patterns, which is not the same: the projection is followed by
    rectification and L2 normalisation.
    """
    ra = door.get_odorant_response(a)
    rb = door.get_odorant_response(b)
    return door.map_to_glomerular_pattern(0.5 * (ra + rb))


def analyse_pair(brain, door, a, b):
    from scipy.stats import wilcoxon

    pat_a = door.get_glomerular_pattern(a)
    pat_b = door.get_glomerular_pattern(b)
    pat_mix = mixture_pattern(door, a, b)

    ta = trial_set(brain, pat_a)
    tb = trial_set(brain, pat_b)
    tm = trial_set(brain, pat_mix)

    # Primary: sub-additivity on the pre-threshold continuous amplitude, which
    # the rank threshold does not pin.
    sub_idx = []
    for i in range(len(TRIAL_SEEDS)):
        linear_sum = float(np.sum(ta[i]) + np.sum(tb[i]))
        mix = float(np.sum(tm[i]))
        sub_idx.append(mix / linear_sum if linear_sum else None)
    sub_idx = [s for s in sub_idx if s is not None]

    # One-sided: is the index below 1, i.e. sub-additive?
    stat, p = wilcoxon(np.array(sub_idx) - 1.0, alternative='less')
    subadditive = bool(p < ALPHA and np.mean(sub_idx) < 1.0)

    # Per-KC: what fraction of KCs respond less to the mixture than the linear
    # sum predicts? Honegger: "most cells showing a weaker response to the
    # mixture than predicted from the linear sum".
    mean_a, mean_b, mean_m = (mean_pattern(ta), mean_pattern(tb),
                              mean_pattern(tm))
    predicted = mean_a + mean_b
    weaker = float(np.mean(mean_m < predicted))

    # Secondary: the legacy overlap number, on binary active sets.
    bin_a = set(np.flatnonzero(binarise(mean_a)).tolist())
    bin_b = set(np.flatnonzero(binarise(mean_b)).tolist())
    bin_m = set(np.flatnonzero(binarise(mean_m)).tolist())
    ov_a = len(bin_m & bin_a) / len(bin_a) if bin_a else 0.0
    ov_b = len(bin_m & bin_b) / len(bin_b) if bin_b else 0.0
    legacy_overlap = 100.0 * (ov_a + ov_b) / 2.0

    # The pinned quantity, recorded so the limitation is visible in the data.
    n_active = {
        'component_a': int(np.sum(mean_a > 0)),
        'component_b': int(np.sum(mean_b > 0)),
        'mixture': int(np.sum(mean_m > 0)),
        'n_kc': int(mean_a.size),
        'note':
            'the rank threshold fixes this at int(n_kc * target_sparsity) for '
            'every stimulus, so the proportion Honegger et al. 2011 reports '
            '(9 %, 9 % -> 11 % against a 15 % linear sum) cannot vary here',
    }

    print(f"  {a} + {b}")
    print(f"    sub-additivity index = {np.mean(sub_idx):.4f} "
          f"+/- {np.std(sub_idx, ddof=1):.4f}  "
          f"(published {PUBLISHED['subadditivity_index']:.4f})  "
          f"p = {p:.3g}  {'SUB-ADDITIVE' if subadditive else 'not sub-additive'}")
    print(f"    KCs responding below the linear-sum prediction: "
          f"{100 * weaker:.1f} %")
    print(f"    legacy overlap (secondary) = {legacy_overlap:.2f} %")

    return {
        'odorants': [a, b],
        'subadditivity_index_mean': float(np.mean(sub_idx)),
        'subadditivity_index_std': float(np.std(sub_idx, ddof=1)),
        'subadditivity_index_trials': sub_idx,
        'wilcoxon': {'statistic': float(stat), 'p_value': float(p),
                     'test': 'Wilcoxon signed-rank, index < 1, one-sided'},
        'subadditive': subadditive,
        'fraction_of_kcs_below_linear_sum': weaker,
        'published_subadditivity_index': PUBLISHED['subadditivity_index'],
        'active_kc_counts_pinned_by_readout': n_active,
        'legacy_overlap_percent': legacy_overlap,
        'legacy_overlap_in_band': bool(
            LEGACY_OVERLAP_BAND[0] <= legacy_overlap <= LEGACY_OVERLAP_BAND[1]),
    }


def run(use_mlx=False, output='mixtures_repaired.json'):
    print("=" * 70)
    print("MIXTURES: sub-additive KC recruitment (Honegger et al. 2011 Fig 7)")
    print("=" * 70)

    brain, door, _ = build(use_mlx=use_mlx)

    print()
    pairs = [analyse_pair(brain, door, a, b) for a, b in PUBLISHED_PAIRS]

    # Both published pairs must be sub-additive. Honegger reports neither as
    # supra-additive, so a single pair passing would not reproduce the result.
    passed = all(p['subadditive'] for p in pairs)

    print("\n" + "-" * 70)
    print(f"VERDICT: {'PASS' if passed else 'FAIL'} "
          f"({sum(p['subadditive'] for p in pairs)}/{len(pairs)} pairs "
          f"sub-additive)")

    payload = {
        'benchmark': 'odor_mixtures',
        'measures':
            'whether KC recruitment by a binary mixture is sub-additive '
            'relative to the linear sum of its components',
        'reference':
            'Honegger KS, Campbell RAA, Turner GC (2011) Cellular-resolution '
            'population imaging reveals robust sparse coding in the '
            'Drosophila mushroom body. J Neurosci 31:11772-11785, Fig 7',
        'published': PUBLISHED,
        'published_quote':
            '"Presented individually, each of these odors activates 9 % of KCs '
            'on average. When presented simultaneously, however, this '
            'proportion increases only slightly (11 %) and is smaller than the '
            'linear sum of the two activity patterns, 15 %. [...] most cells '
            'showing a weaker response to the mixture than predicted from the '
            'linear sum of the response to the components."',
        'target_corrections': {
            'removed': 'mean KC overlap in [30, 50] %',
            'why':
                'attributed to Stettler & Axel 2009 and Deisig et al. 2006, '
                'neither of which is a Drosophila mushroom-body measurement '
                '(mouse piriform cortex and honeybee antennal lobe '
                'respectively). No source for a 30-50 % KC overlap band in '
                'Drosophila was found. The old test also used exactly one '
                'mixture, formed from the first two of three suite odorants, '
                'and the F8 result of 30.06 % sat 0.06 points inside the band.',
            'replaced_with':
                'sub-additivity of mixture KC recruitment relative to the '
                'linear sum, on both odour pairs Honegger et al. 2011 Fig 7 '
                'reports',
            'retained_as_secondary':
                'the overlap percentage is still computed and reported, with '
                'its citation flagged as non-Drosophila, so the old number '
                'remains comparable',
        },
        'known_limitation': {
            'what':
                'Honegger et al. 2011 reports the PROPORTION OF RESPONDING '
                'KCs (9 %, 9 % -> 11 % against a 15 % linear sum). That '
                'proportion cannot vary in this model.',
            'why':
                'the KC readout applies a rank threshold at '
                'int(n_kc * target_sparsity), giving exactly '
                'int(5279 * 0.06) = 316 non-zero KCs for every stimulus, '
                'always. Verified in tests/test_benchmark_harness.py. The '
                'readout pins the exact quantity the paper reports.',
            'consequence':
                'the published comparison is unavailable at the binary level. '
                'Readout sparsity is fixed for this repair, so sub-additivity '
                'is measured instead on the pre-threshold continuous KC '
                'amplitude, which is not pinned. The pinned counts are '
                'recorded per pair so the limitation is visible in the data '
                'rather than only in prose.',
        },
        'protocol': protocol_block(binary=False, extra={
            'pairs': [list(p) for p in PUBLISHED_PAIRS],
            'pair_selection_rule':
                'both pairs Honegger et al. 2011 Fig 7 reports; all four '
                'odorants are in the DoOR matrix',
            'mixture_mixing':
                'mixed in receptor space and then projected, because that is '
                'where a physical mixture acts; the old benchmark averaged '
                'already-projected glomerular patterns, which differs because '
                'the projection is followed by rectification and L2 '
                'normalisation',
            'subadditivity_index':
                'summed mixture KC amplitude divided by the summed '
                'linear-sum amplitude, per trial; below 1 is sub-additive',
        }),
        'panel': panel_block(
            sorted({o for pair in PUBLISHED_PAIRS for o in pair})),
        'pairs': pairs,
        'summary': {
            'subadditivity_index_per_pair': {
                f"{p['odorants'][0]}+{p['odorants'][1]}":
                    p['subadditivity_index_mean'] for p in pairs
            },
            'subadditive_per_pair': {
                f"{p['odorants'][0]}+{p['odorants'][1]}": p['subadditive']
                for p in pairs
            },
            'published_subadditivity_index': PUBLISHED['subadditivity_index'],
            'legacy_overlap_percent_per_pair': {
                f"{p['odorants'][0]}+{p['odorants'][1]}":
                    p['legacy_overlap_percent'] for p in pairs
            },
            'n_pairs_subadditive': int(sum(p['subadditive'] for p in pairs)),
            'n_pairs': len(pairs),
            'validation': 'PASS' if passed else 'FAIL',
        },
    }

    out = write_results(output, payload, brain=brain, door_client=door,
                        duration_ms=TRIAL_DURATION_MS, seed=None,
                        suite='mixtures_repaired')
    print(f"Written to {out}")
    return payload


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mlx', action='store_true',
                    help='development only; reported runs use CPU')
    ap.add_argument('--output', default='mixtures_repaired.json')
    a = ap.parse_args()
    run(use_mlx=a.mlx, output=a.output)
