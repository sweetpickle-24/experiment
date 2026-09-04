"""
Similarity: does the KC code preserve input similarity, and does it decorrelate?

What the old benchmark measured
===============================
``scripts/run_all_validations.py::validate_similarity`` correlated three
chemical-similarity values against three neural-similarity values and required
the result to land in [0.3, 0.5].

Two problems, both fatal.

**The target has no source.** It is attributed to Bhandawat et al. 2007 and
Mathew et al. 2013. Mathew et al. 2013 (PNAS 110:E2134) is a screen of 21 larval
ORNs against ~500 odorants and reports no chemical-versus-neural similarity
correlation at all. No paper I could find reports a 0.3-0.5 band for this
quantity. An upper bound of 0.5 is also strange on its face: it fails a model
for tracking input similarity *too well*.

**Three odorants give three pairs.** A correlation computed from n = 3 has one
residual degree of freedom. The F4 and F5 runs produced r = -0.97 and -0.99 from
it, and the F8 run -0.12, from the same code. That is not a measurement at any
threshold.

What this module measures instead
=================================
Two quantities, each taken from a paper that actually reports a number for it.

**Part A -- Campbell et al. 2013 Fig 4C: similarity is graded and ordered.**

  "Across all recordings (n = 24), the correlation score of PA-BA (mean
   r = 0.70) is substantially and significantly greater than either PA-EL (mean
   r = 0.15; p < 0.05, one-way ANOVA followed by Tukey's post hoc test) or
   BA-EL (mean r = 0.11), indicating that MB response patterns evoked by PA and
   BA are more similar to each other than either are to EL."

  Pentyl acetate, butyl acetate and ethyl lactate are all in the DoOR matrix, so
  this is a direct comparison against published values rather than an analogy.
  Criterion: r(PA,BA) significantly greater than both r(PA,EL) and r(BA,EL), by
  one-way ANOVA followed by Tukey, which is the test the paper used.

**Part B -- Turner et al. 2008 Fig 5: the KC layer decorrelates its input.**

  "All pair-wise separation values [1-cos(theta), where theta is the angle
   defined by the two vectors] between odor vectors are shown in Fig 5A in OSN
   and KC spaces. Overall, distances were significantly greater between KC
   vectors than between OSN vectors (Fig 5B; t-test: P < 1e-7). Separation was
   greater in KC space for 24 of the 28 possible odor pairs (Fig 5C; Wilcoxon
   signed-rank test: P < 1e-4)."

  Computed here over all 66 pairs of the 12-odorant panel, comparing angular
  separation in the glomerular input space against the KC space, with the
  Wilcoxon signed-rank test the paper used. Criterion: KC separation greater in
  a significant majority of pairs.

  Note the layer correspondence. Turner et al. compared OSNs against KCs. This
  model's entry point is the glomerular pattern injected into projection
  neurons, so the comparison here is glomerular-input space against KC space.
  That is one stage downstream of the paper's input layer, and it is a weaker
  test than the paper's, because the antennal lobe has already transformed the
  representation. Recorded rather than glossed.

Power
=====
Part A: 3 odour pairs, 8 trials each, so 3 x 28 = 84 within-stimulus and 3 x 56
between-stimulus correlations, against the old benchmark's three single numbers.
Part B: 66 pairs against the old benchmark's three.
"""

import itertools
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    PANEL, TRIAL_DURATION_MS, TRIAL_SEEDS, binarise, build,
    between_stimulus_correlations, mean_pattern, panel_block, protocol_block,
    trial_set,
)
from validation_utils import write_results  # noqa: E402

# ── Declared before any result was seen ──────────────────────────────────────

#: Campbell et al. 2013 Fig 4C trio, with the paper's own abbreviations.
CAMPBELL_TRIO = {'PA': 'pentyl_acetate',
                 'BA': 'butyl_acetate',
                 'EL': 'ethyl_lactate'}

#: Published means from Campbell et al. 2013 Fig 4C, n = 24 recordings.
CAMPBELL_PUBLISHED_R = {'PA__BA': 0.70, 'PA__EL': 0.15, 'BA__EL': 0.11}

#: Turner et al. 2008 Fig 5C: 24 of 28 pairs more separated in KC space.
TURNER_PUBLISHED_FRACTION = 24 / 28

ALPHA = 0.05


def angular_separation(a, b):
    """
    1 - cos(theta) between two population vectors.

    Turner et al. 2008: "The angular separation between vectors representing two
    different odors was calculated as 1-cos(theta), where theta is the angle
    between the vectors." Larger means better separated.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return None
    return 1.0 - float(np.dot(a, b) / (na * nb))


def part_a_campbell(brain, door):
    """
    KC pattern correlation for the Campbell et al. 2013 Fig 4C trio.

    Correlations are taken between individual trials of different odours (the
    same-seed diagonal excluded, per the harness), so the spread reflects
    trial-to-trial variability the way the paper's n = 24 recordings did. The
    correlation of the *mean* patterns is reported too, because that is the
    quantity the published r values describe.
    """
    from scipy.stats import f_oneway, tukey_hsd

    trials = {abbr: trial_set(brain, door.get_glomerular_pattern(name))
              for abbr, name in CAMPBELL_TRIO.items()}

    pairs = {}
    groups, group_names = [], []
    for a, b in itertools.combinations(CAMPBELL_TRIO, 2):
        key = f'{a}__{b}'
        # Binary active-KC vectors, the representation the suite has always
        # used for pattern similarity.
        cross = between_stimulus_correlations(trials[a], trials[b], binary=True)
        mean_r = float(np.corrcoef(
            binarise(mean_pattern(trials[a])),
            binarise(mean_pattern(trials[b])))[0, 1])
        pairs[key] = {
            'odorants': [CAMPBELL_TRIO[a], CAMPBELL_TRIO[b]],
            'trialwise_r_mean': float(np.mean(cross)),
            'trialwise_r_std': float(np.std(cross, ddof=1)),
            'trialwise_r_n': len(cross),
            'mean_pattern_r': mean_r,
            'published_r': CAMPBELL_PUBLISHED_R[key],
        }
        groups.append(cross)
        group_names.append(key)

    f_stat, p_anova = f_oneway(*groups)

    tukey = tukey_hsd(*groups)
    tukey_rows = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            tukey_rows.append({
                'group1': group_names[i], 'group2': group_names[j],
                'meandiff': float(tukey.statistic[i, j]),
                'p_adj': float(tukey.pvalue[i, j]),
                'reject': bool(tukey.pvalue[i, j] < ALPHA),
            })

    def tukey_for(g1, g2):
        for r in tukey_rows:
            if {r['group1'], r['group2']} == {g1, g2}:
                return r
        return None

    # Criterion: PA-BA significantly greater than both PA-EL and BA-EL, which
    # is exactly the comparison Campbell et al. 2013 Fig 4C reports.
    vs_pael = tukey_for('PA__BA', 'PA__EL')
    vs_bael = tukey_for('PA__BA', 'BA__EL')
    pa_ba = pairs['PA__BA']['trialwise_r_mean']
    higher = (pa_ba > pairs['PA__EL']['trialwise_r_mean']
              and pa_ba > pairs['BA__EL']['trialwise_r_mean'])
    passed = bool(higher
                  and vs_pael and vs_pael['reject']
                  and vs_bael and vs_bael['reject'])

    return {
        'reference':
            'Campbell RAA, Honegger KS, Qin H, Li W, Demir E, Turner GC (2013) '
            'Imaging a population code for odor identity in the Drosophila '
            'mushroom body. J Neurosci 33:10568-10581, Fig 4C',
        'published':
            'PA-BA mean r = 0.70, substantially and significantly greater than '
            'PA-EL (r = 0.15) and BA-EL (r = 0.11); n = 24 recordings; '
            'one-way ANOVA followed by Tukey post hoc',
        'pairs': pairs,
        'anova': {'f': float(f_stat), 'p_value': float(p_anova),
                  'test': 'one-way ANOVA over the three pair groups'},
        'tukey': tukey_rows,
        'criterion':
            'r(PA,BA) significantly greater than both r(PA,EL) and r(BA,EL), '
            'by one-way ANOVA followed by Tukey, the test the paper used',
        'pa_ba_greater_than_both': bool(higher),
        'tukey_pa_ba_vs_pa_el': vs_pael,
        'tukey_pa_ba_vs_ba_el': vs_bael,
        'passed': passed,
    }


def part_b_turner(brain, door):
    """
    Angular separation in glomerular input space against KC space, all 66 pairs
    of the 12-odorant panel.
    """
    from scipy.stats import wilcoxon

    glom = {n: door.get_glomerular_pattern(n) for n in PANEL}
    kc = {n: mean_pattern(trial_set(brain, glom[n])) for n in PANEL}

    rows, input_sep, kc_sep = [], [], []
    for a, b in itertools.combinations(PANEL, 2):
        si = angular_separation(glom[a], glom[b])
        sk = angular_separation(kc[a], kc[b])
        if si is None or sk is None:
            continue
        rows.append({'pair': [a, b], 'input_separation': si,
                     'kc_separation': sk, 'kc_greater': bool(sk > si)})
        input_sep.append(si)
        kc_sep.append(sk)

    input_sep, kc_sep = np.array(input_sep), np.array(kc_sep)
    n_greater = int(np.sum(kc_sep > input_sep))
    n_pairs = len(rows)

    stat, p = wilcoxon(kc_sep, input_sep, alternative='greater')
    passed = bool(p < ALPHA and n_greater > n_pairs / 2)

    return {
        'reference':
            'Turner GC, Bazhenov M, Laurent G (2008) Olfactory representations '
            'by Drosophila mushroom body neurons. J Neurophysiol 99:734-746, '
            'Fig 5',
        'published':
            'separation greater in KC space for 24 of 28 odour pairs '
            '(Wilcoxon signed-rank P < 1e-4; t-test P < 1e-7), comparing 24 '
            'OSN types against 40 KCs over an 8-odour panel',
        'metric': '1 - cos(theta), per Turner et al. 2008',
        'layer_correspondence_caveat':
            "Turner et al. compared OSN space against KC space. This model's "
            'entry point is the glomerular pattern injected into projection '
            'neurons, so the comparison here is glomerular-input space against '
            'KC space: one stage downstream of the paper\'s input layer, and '
            'therefore a weaker test, because the antennal lobe has already '
            'transformed the representation.',
        'n_pairs': n_pairs,
        'n_kc_greater': n_greater,
        'fraction_kc_greater': n_greater / n_pairs if n_pairs else None,
        'published_fraction': TURNER_PUBLISHED_FRACTION,
        'input_separation_mean': float(np.mean(input_sep)),
        'kc_separation_mean': float(np.mean(kc_sep)),
        'wilcoxon': {'statistic': float(stat), 'p_value': float(p),
                     'test': 'Wilcoxon signed-rank, KC > input, one-sided'},
        'criterion':
            'KC separation greater than input separation in a significant '
            'majority of pairs (Wilcoxon signed-rank, one-sided)',
        'pairs': rows,
        'passed': passed,
    }


def run(use_mlx=False, output='similarity_repaired.json'):
    print("=" * 70)
    print("SIMILARITY: graded structure (Campbell 2013) and decorrelation "
          "(Turner 2008)")
    print("=" * 70)

    brain, door, _ = build(use_mlx=use_mlx)

    print("\nPart A -- Campbell et al. 2013 Fig 4C")
    a = part_a_campbell(brain, door)
    for key, p in a['pairs'].items():
        print(f"  {key:<8} r = {p['trialwise_r_mean']:.4f} "
              f"+/- {p['trialwise_r_std']:.4f}  "
              f"(mean-pattern r = {p['mean_pattern_r']:.4f}; "
              f"published {p['published_r']:.2f})")
    print(f"  ANOVA F = {a['anova']['f']:.3f}, p = {a['anova']['p_value']:.4g}")
    print(f"  {'PASS' if a['passed'] else 'FAIL'}  Part A")

    print("\nPart B -- Turner et al. 2008 Fig 5")
    b = part_b_turner(brain, door)
    print(f"  input separation mean {b['input_separation_mean']:.4f}, "
          f"KC separation mean {b['kc_separation_mean']:.4f}")
    print(f"  KC more separated in {b['n_kc_greater']}/{b['n_pairs']} pairs "
          f"(published 24/28)")
    print(f"  Wilcoxon p = {b['wilcoxon']['p_value']:.4g}")
    print(f"  {'PASS' if b['passed'] else 'FAIL'}  Part B")

    passed = bool(a['passed'] and b['passed'])
    print("\n" + "-" * 70)
    print(f"VERDICT: {'PASS' if passed else 'FAIL'} "
          f"(both parts required)")

    payload = {
        'benchmark': 'similarity',
        'measures':
            'whether KC pattern similarity is graded and ordered as Campbell '
            'et al. 2013 measured it, and whether the KC layer decorrelates '
            'its input as Turner et al. 2008 measured it',
        'target_corrections': {
            'removed': 'chem-neural correlation in [0.3, 0.5]',
            'why':
                'the band is attributed to Bhandawat et al. 2007 and Mathew et '
                'al. 2013 and appears in neither. Mathew et al. 2013 is a '
                'screen of 21 larval ORNs against ~500 odorants and reports no '
                'chemical-versus-neural similarity correlation. No source for '
                'a 0.3-0.5 band was found. It was also computed from three '
                'odorants, hence three pairs, leaving one residual degree of '
                'freedom: the same code produced r = -0.97, -0.99 and -0.12 '
                'across the F4, F5 and F8 runs.',
            'replaced_with':
                'two published measurements with published numbers: Campbell '
                'et al. 2013 Fig 4C (PA-BA r = 0.70 > PA-EL 0.15 and BA-EL '
                '0.11, one-way ANOVA + Tukey, n = 24) and Turner et al. 2008 '
                'Fig 5 (KC angular separation greater than input for 24/28 '
                'pairs, Wilcoxon signed-rank P < 1e-4)',
            'power':
                'Part A uses 3 pairs x 8 trials; Part B uses 66 pairs. The '
                'removed test used 3 single values.',
        },
        'protocol': protocol_block(extra={
            'part_a_odorants': CAMPBELL_TRIO,
            'part_b_odorants': list(PANEL),
        }),
        'panel': panel_block(),
        'part_a_campbell_2013': a,
        'part_b_turner_2008': b,
        'summary': {
            'part_a_passed': a['passed'],
            'part_b_passed': b['passed'],
            'part_a_pa_ba_r': a['pairs']['PA__BA']['trialwise_r_mean'],
            'part_a_pa_el_r': a['pairs']['PA__EL']['trialwise_r_mean'],
            'part_a_ba_el_r': a['pairs']['BA__EL']['trialwise_r_mean'],
            'part_b_fraction_kc_greater': b['fraction_kc_greater'],
            'validation': 'PASS' if passed else 'FAIL',
        },
    }

    out = write_results(output, payload, brain=brain, door_client=door,
                        duration_ms=TRIAL_DURATION_MS, seed=None,
                        suite='similarity_repaired')
    print(f"Written to {out}")
    return payload


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mlx', action='store_true',
                    help='development only; reported runs use CPU')
    ap.add_argument('--output', default='similarity_repaired.json')
    a = ap.parse_args()
    run(use_mlx=a.mlx, output=a.output)
