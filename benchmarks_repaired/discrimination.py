"""
Discrimination: fine odour discrimination along a blend series (Campbell 2013).

The citation the old benchmark scored against does not exist
=============================================================
``scripts/run_all_validations.py::validate_discrimination`` recorded its target
as::

    'biological_target': '10-20% (Weber\\'s law, Bodyak & Bhatt 2001)'

**There is no Bodyak & Bhatt 2001.** Searching the literature returns nothing by
those two authors in that year on this subject. The nearest real paper is
Bodyak N & Slotnick B (1999) "Performance of mice in an automated olfactometer:
odor detection, discrimination and odor memory", *Chem Senses* 24:637-645 --
a **mouse** study. This repository's own `.cursor/rules/Findings.mdc` already
records that the 10-20 % figure "was rodent data, not validated in flies".

No published Drosophila concentration JND at 5-25 % resolution exists. So the
old benchmark scored the model against a number that no paper reports, for a
species it was not measured in, via a citation that cannot be located.

The measurement was also unfalsifiable as built
===============================================
It swept concentration deltas of 5, 10, 15, 20 and 25 %, called a delta
discriminable when the KC correlation fell below a fixed 0.9, and reported the
smallest discriminable delta as the JND. Every delta scored discriminable at
every odour, so the reported JND was always 5 %: the smallest delta in the
sweep. The JND was set by where the sweep started, not measured.

The fixed 0.9 threshold is the deeper problem. The same-stimulus replicate
correlation in this model is about r = 0.54
(``tests/test_benchmark_harness.py``), far below 0.9, so the old test would have
called a stimulus discriminable from *itself*. Several of the correlations it
scored as discriminable (0.36, 0.45, 0.37, 0.20) sit below that noise floor.

What this module measures instead
=================================
Campbell et al. 2013 is the published Drosophila fine-discrimination benchmark,
and it uses **blend ratio**, not concentration:

  "Increasingly similar odors were constructed by blending OCT and MCH over
   three pairs of increasingly similar blend ratios. [...] Flies accurately
   discriminated pure OCT from pure MCH (100:0), but do progressively worse with
   blends of the two odors (70:30 and 60:40). Training on the more similar blend
   (60:40) produces performance just above chance." (Fig 2A-B)

  "even though MB representations are sparse, KC patterns become increasingly
   overlapping and correlated when approaching the discrimination limit.
   Second, the variability of KC responses is an important limiting factor."

Both odorants are in the DoOR matrix. The published result is a **psychometric
ordering**, so that is what gets scored: KC pattern correlation between the two
members of a blend pair must rise as the blends converge, and separability must
weaken in the same order. Every separability judgement is made against this
model's own replicate distribution rather than a fixed constant, which is also
what Campbell et al. identify as the limiting factor.

Blends are mixed at the **receptor** level and then projected, because that is
where a physical mixture acts. The projection is linear but is followed by a
rectification and an L2 normalisation, so mixing before it is not the same as
mixing after it; the old mixture benchmark averaged already-projected glomerular
patterns.

Secondary, scored separately: Xia & Tully 2007
==============================================
The one published Drosophila intensity-discrimination result:

  "To saturate MCH as the background odor, naive flies were allowed to choose
   in the T-maze between 2 x [MCH] versus 1 x [MCH]. As the concentration of
   MCH was increased, a threshold (i.e. about 10 %) was reached at which flies
   would fail to recognize the intensity difference, thereby yielding a PI of
   zero."

  Xia S, Tully T (2007) "Segregation of odor identity and intensity during odor
  discrimination in Drosophila mushroom body", *PLoS Biol* 5:e264.

So the published quantity is a **two-fold** step, discriminable below
saturation. Reported here as a secondary measurement, separately scored, and not
folded into the primary verdict.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    REFERENCE_STRENGTH, TRIAL_DURATION_MS, TRIAL_SEEDS,
    between_stimulus_correlations, build, panel_block, protocol_block,
    separability, trial_set, within_stimulus_correlations,
)
from validation_utils import write_results  # noqa: E402

# ── Declared before any result was seen ──────────────────────────────────────

ODOR_A = '3-octanol'                # Campbell et al. 2013: OCT
ODOR_B = '4-methylcyclohexanol'     # Campbell et al. 2013: MCH

#: Campbell et al. 2013 Fig 2A, in the paper's order: pure, then progressively
#: more similar. Each entry is the OCT fraction of the two blend members.
BLEND_PAIRS = (
    ('100:0 vs 0:100', 1.00, 0.00),
    ('70:30 vs 30:70', 0.70, 0.30),
    ('60:40 vs 40:60', 0.60, 0.40),
)

#: Xia & Tully 2007: 2 x [MCH] against 1 x [MCH].
INTENSITY_FACTOR = 2.0

ALPHA = 0.05


def blend_pattern(door, frac_a):
    """
    Glomerular pattern for a blend of ODOR_A and ODOR_B.

    Mixed in **receptor** space and then projected, because that is where a
    physical mixture acts. ``map_to_glomerular_pattern`` applies a linear
    projection followed by rectification and L2 normalisation, so mixing before
    it differs from mixing after it.
    """
    ra = door.get_odorant_response(ODOR_A)
    rb = door.get_odorant_response(ODOR_B)
    return door.map_to_glomerular_pattern(frac_a * ra + (1.0 - frac_a) * rb)


def primary_campbell(brain, door):
    """The blend series: does discriminability weaken as blends converge?"""
    from scipy.stats import mannwhitneyu

    rows = []
    for label, fa, fb in BLEND_PAIRS:
        ta = trial_set(brain, blend_pattern(door, fa))
        tb = trial_set(brain, blend_pattern(door, fb))
        cross = between_stimulus_correlations(ta, tb, binary=True)
        within = (within_stimulus_correlations(ta, True)
                  + within_stimulus_correlations(tb, True))
        sep = separability(ta, tb, binary=True, alpha=ALPHA)
        rows.append({
            'blend_pair': label,
            'oct_fractions': [fa, fb],
            'between_r_mean': float(np.mean(cross)),
            'between_r_std': float(np.std(cross, ddof=1)),
            'between_r': cross,
            'within_r_mean': float(np.mean(within)),
            'separability': sep,
        })
        print(f"  {label:<16} between r = {np.mean(cross):.4f}  "
              f"within r = {np.mean(within):.4f}  "
              f"separable = {sep['separable']}  "
              f"p = {sep['p_value']:.3g}  auc = {sep['effect_size_auc']:.3f}")

    # Ordered contrasts. Campbell et al. 2013's published result is that
    # discrimination gets harder along this series, so each step must be
    # significantly more correlated than the one before it.
    contrasts = []
    for i in range(len(rows) - 1):
        u, p = mannwhitneyu(rows[i]['between_r'], rows[i + 1]['between_r'],
                            alternative='less')
        contrasts.append({
            'step': f"{rows[i]['blend_pair']} -> {rows[i + 1]['blend_pair']}",
            'r_before': rows[i]['between_r_mean'],
            'r_after': rows[i + 1]['between_r_mean'],
            'u': float(u), 'p_value': float(p),
            'increased': bool(p < ALPHA),
            'test': 'one-sided Mann-Whitney U, earlier pair less correlated',
        })

    means = [r['between_r_mean'] for r in rows]
    monotone = all(means[i] < means[i + 1] for i in range(len(means) - 1))
    all_steps_significant = all(c['increased'] for c in contrasts)

    # The pure pair must be separable at all, or there is no discrimination to
    # degrade and the ordering would be vacuous.
    pure_separable = bool(rows[0]['separability']['separable'])

    # Separability effect size must weaken along the series, which is the
    # neural counterpart of the psychometric curve in Fig 2B.
    aucs = [r['separability']['effect_size_auc'] for r in rows]
    auc_weakens = all(aucs[i] >= aucs[i + 1] for i in range(len(aucs) - 1))

    passed = bool(pure_separable and monotone and all_steps_significant
                  and auc_weakens)

    return {
        'reference':
            'Campbell RAA, Honegger KS, Qin H, Li W, Demir E, Turner GC (2013) '
            'J Neurosci 33:10568-10581, Fig 2A-B and Fig 3',
        'published':
            'flies discriminate pure OCT from pure MCH accurately, do '
            'progressively worse at 70:30 and 60:40, and perform just above '
            'chance when trained on 60:40; KC patterns become increasingly '
            'overlapping and correlated when approaching the discrimination '
            'limit, and KC response variability is an important limiting '
            'factor',
        'blend_series': rows,
        'ordered_contrasts': contrasts,
        'criteria': {
            'pure_pair_separable': pure_separable,
            'correlation_increases_monotonically': monotone,
            'every_step_significant': all_steps_significant,
            'separability_effect_size_weakens': auc_weakens,
        },
        'criterion':
            'KC correlation between blend-pair members must rise monotonically '
            'and significantly as the blends converge, the pure pair must be '
            "separable, and separability's effect size must weaken along the "
            'series. Judged against this model\'s own replicate distribution, '
            'never a fixed constant.',
        'passed': passed,
    }


def secondary_xia_tully(brain, door):
    """Xia & Tully 2007: is a two-fold intensity step discriminable?"""
    pattern = door.get_glomerular_pattern(ODOR_B)   # MCH, the paper's odour
    t1 = trial_set(brain, pattern, strength=REFERENCE_STRENGTH)
    t2 = trial_set(brain, pattern,
                   strength=REFERENCE_STRENGTH * INTENSITY_FACTOR)
    sep = separability(t1, t2, binary=True, alpha=ALPHA)
    print(f"  1x vs {INTENSITY_FACTOR:g}x [MCH]: separable = {sep['separable']}, "
          f"p = {sep['p_value']:.3g}, auc = {sep['effect_size_auc']:.3f}")
    return {
        'reference':
            'Xia S, Tully T (2007) Segregation of odor identity and intensity '
            'during odor discrimination in Drosophila mushroom body. '
            'PLoS Biol 5:e264, Fig S2A',
        'published':
            'naive flies discriminate 2 x [MCH] from 1 x [MCH] in a T-maze '
            'until MCH saturates at about 10 % v/v, where the preference index '
            'falls to zero',
        'odorant': ODOR_B,
        'intensity_factor': INTENSITY_FACTOR,
        'reference_strength': REFERENCE_STRENGTH,
        'separability': sep,
        'criterion': 'the two-fold intensity step is separable from the '
                     'replicate distribution',
        'passed': bool(sep['separable']),
        'scored_separately':
            'reported as a secondary measurement and not folded into the '
            'primary verdict, because it tests intensity rather than the fine '
            'blend discrimination the primary criterion is taken from',
    }


def run(use_mlx=False, output='discrimination_repaired.json'):
    print("=" * 70)
    print("DISCRIMINATION: blend series (Campbell 2013)")
    print("=" * 70)

    brain, door, _ = build(use_mlx=use_mlx)

    print("\nPrimary -- Campbell et al. 2013 blend series")
    primary = primary_campbell(brain, door)
    for c in primary['ordered_contrasts']:
        print(f"  step {c['step']}: r {c['r_before']:.4f} -> {c['r_after']:.4f}"
              f"  p = {c['p_value']:.4g}  "
              f"{'significant' if c['increased'] else 'NOT significant'}")
    print(f"  {'PASS' if primary['passed'] else 'FAIL'}  primary")

    print("\nSecondary -- Xia & Tully 2007 two-fold intensity step")
    secondary = secondary_xia_tully(brain, door)
    print(f"  {'PASS' if secondary['passed'] else 'FAIL'}  secondary "
          f"(scored separately)")

    passed = primary['passed']
    print("\n" + "-" * 70)
    print(f"VERDICT: {'PASS' if passed else 'FAIL'} (primary criterion only)")

    payload = {
        'benchmark': 'discrimination',
        'measures':
            'whether KC pattern discriminability weakens along a blend series '
            'in the published psychometric order, judged against the model\'s '
            'own trial-to-trial replicate distribution',
        'target_corrections': {
            'removed': "JND in 10-20 %, cited as \"Weber's law, Bodyak & "
                       'Bhatt 2001\"',
            'why': [
                'THE CITATION DOES NOT EXIST. No paper by Bodyak and Bhatt in '
                '2001 on this subject could be located. The nearest real work '
                'is Bodyak N & Slotnick B (1999) Chem Senses 24:637-645, a '
                'MOUSE olfactometer study. This repository\'s own '
                'Findings.mdc already records that the 10-20 % figure "was '
                'rodent data, not validated in flies".',
                'No published Drosophila concentration JND at 5-25 % '
                'resolution exists.',
                'The measurement was unfalsifiable as built: every delta in '
                'the 5-25 % sweep scored discriminable for every odour, so the '
                'reported JND was always 5 %, the smallest delta swept. The '
                'JND was set by where the sweep started.',
                'The fixed 0.9 discriminability threshold sits far above this '
                "model's same-stimulus replicate correlation of about "
                'r = 0.54, so the old test would call a stimulus '
                'discriminable from itself. Correlations of 0.36, 0.45, 0.37 '
                'and 0.20 were scored as discriminable while lying below the '
                'noise floor.',
            ],
            'replaced_with':
                'Campbell et al. 2013 Fig 2A-B blend-ratio series (100:0, '
                '70:30, 60:40), the published Drosophila fine-discrimination '
                'benchmark, scored on the psychometric ordering against the '
                "model's own replicate distribution",
            'secondary_added':
                'Xia & Tully 2007 two-fold intensity step, the one published '
                'Drosophila intensity-discrimination result, scored separately',
        },
        'protocol': protocol_block(extra={
            'odorants': [ODOR_A, ODOR_B],
            'odorant_selection_rule':
                'Campbell et al. 2013 Fig 2A used OCT and MCH; both are in the '
                'DoOR matrix',
            'blend_pairs': [b[0] for b in BLEND_PAIRS],
            'blend_mixing':
                'mixed in receptor space and then projected, because that is '
                'where a physical mixture acts; map_to_glomerular_pattern '
                'applies a linear projection followed by rectification and L2 '
                'normalisation, so mixing before it differs from mixing after',
        }),
        'panel': panel_block([ODOR_A, ODOR_B]),
        'primary_campbell_2013': primary,
        'secondary_xia_tully_2007': secondary,
        'summary': {
            'blend_correlations': {
                r['blend_pair']: r['between_r_mean']
                for r in primary['blend_series']
            },
            'blend_separable': {
                r['blend_pair']: r['separability']['separable']
                for r in primary['blend_series']
            },
            'primary_passed': primary['passed'],
            'secondary_passed': secondary['passed'],
            'validation': 'PASS' if passed else 'FAIL',
        },
    }

    out = write_results(output, payload, brain=brain, door_client=door,
                        duration_ms=TRIAL_DURATION_MS, seed=None,
                        suite='discrimination_repaired')
    print(f"Written to {out}")
    return payload


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mlx', action='store_true',
                    help='development only; reported runs use CPU')
    ap.add_argument('--output', default='discrimination_repaired.json')
    a = ap.parse_args()
    run(use_mlx=a.mlx, output=a.output)
