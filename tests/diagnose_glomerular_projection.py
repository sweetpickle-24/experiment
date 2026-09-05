#!/usr/bin/env python3
"""
Is the 40-to-20 PCA projection the reason the similarity benchmark fails?

The repaired similarity benchmark fails Part A on the *ordering*, not on
strength: Campbell et al. 2013 Fig 4C reports pentyl acetate vs butyl acetate
r = 0.70, above PA vs ethyl lactate 0.15 and BA vs EL 0.11. The model measures
PA-BA 0.1296, PA-EL 0.1081 and BA-EL 0.4287 - the largest correlation is on the
pair that should be smallest.

``docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md`` lists the cause as untraced:

    "Whether the wrong similarity *ordering* originates in the DoOR receptor
    data, the 40->20 PCA projection, or the network. The projection retains
    94.0 % of variance, and butyl acetate and ethyl lactate correlate at raw
    r = 0.9318 in the KC field, which points upstream of the network - but this
    was not traced."

This script traces it, and does so **without running the simulation at all**, so
it discriminates between the three candidates for the cost of a matrix multiply.
If the published ordering is present in the raw receptor responses and absent
after the projection, the projection is the culprit and the network is
exonerated. If it is absent in the raw responses too, the projection is not the
problem, the proposed one-to-one repair will not help, and that is the finding.

Three spaces are compared:

  receptor    the 33 measured DoOR columns, untouched. Ground truth: this is
              what was recorded from real flies.
  pca20       what the model currently receives: 40->20 mean-centred PCA, then
              ReLU, then L2 normalise.
  glomerular  the proposed repair: the published one-to-one receptor-to-
              glomerulus assignment (Couto et al. 2005 Table 1), then the same
              ReLU and L2, so the only difference from pca20 is the projection.

Also measured, because they are the mechanisms by which a dense projection can
damage an odour code:

  * fraction of channels non-zero per space (the code should be sparse)
  * how much response magnitude the ReLU discards in each space
  * how much of an odour's identity survives the concentration clip
    ``clip(pattern * concentration, 0, 1)`` at concentration 1, 5 and 10

Run: ``.venv/bin/python tests/diagnose_glomerular_projection.py``
"""

import csv
import gzip
import itertools
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import ODOR_PANEL  # noqa: E402
from hive.data.door_client import DoorClient  # noqa: E402
from hive.data.receptor_glomerulus_map import (  # noqa: E402
    assignment_table, build_projection, coverage_report,
)
from validation_utils import connectome_dir, write_results  # noqa: E402

#: Campbell et al. 2013 (J Neurosci 33:10568) Fig 4C, the published KC pattern
#: correlations that similarity Part A is scored against. Declared here so the
#: ordering test cannot be adjusted after seeing a result.
CAMPBELL_2013_FIG4C = {
    ('pentyl_acetate', 'butyl_acetate'): 0.70,
    ('pentyl_acetate', 'ethyl_lactate'): 0.15,
    ('butyl_acetate', 'ethyl_lactate'): 0.11,
}
CAMPBELL_TRIPLE = ('pentyl_acetate', 'butyl_acetate', 'ethyl_lactate')

#: Concentrations at which to test identity survival through the clip in
#: ``OdorReceptorArray.set_activation``.
CLIP_CONCENTRATIONS = (1.0, 5.0, 10.0)

GLOM_PN = re.compile(
    r'^(D|V|DA\d[a-z]?|DC\d|DL\d[a-z]?|DM\d|DP1[lm]|VA\d[a-z]{0,2}'
    r'|VC\d[a-z]?|VL\d[a-z]?|VM\d[a-z]?|VP\d[a-z]?\+?)_'
    r'((?:ad|l|lv|v|l2|il)?PN)', re.I)


def annotated_glomeruli() -> dict:
    """
    Glomeruli that have uniglomerular projection neurons in the connectome,
    with a PN count each, read from the cell-type annotations.

    A channel with no neuron to drive would occupy a slot in the stimulus
    vector and contribute nothing, so this is what the projection is restricted
    to.
    """
    counts: dict = {}
    path = connectome_dir() / 'consolidated_cell_types.csv.gz'
    with gzip.open(path, 'rt') as f:
        for row in csv.DictReader(f):
            m = GLOM_PN.match(row.get('primary_type') or '')
            if m:
                counts[m.group(1).upper()] = counts.get(m.group(1).upper(), 0) + 1
    return counts


def relu_l2(x: np.ndarray) -> np.ndarray:
    """The post-projection steps DoorClient.map_to_glomerular_pattern applies."""
    y = np.maximum(np.asarray(x, dtype=np.float64), 0.0)
    n = np.linalg.norm(y)
    return y / n if n > 0 else y


def corr(a: np.ndarray, b: np.ndarray):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.std(a) == 0 or np.std(b) == 0:
        # Never report 1.0 for a degenerate vector; that is how a dead signal
        # passes a correlation test.
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _pair(pairs: dict, a: str, b: str):
    """
    Look up a pair regardless of which way round the key was built.

    ``pairwise`` keys on the alphabetically sorted names, so the Campbell pairs
    are stored as ``butyl_acetate__pentyl_acetate`` rather than the order the
    paper quotes them in.
    """
    return pairs.get(f'{a}__{b}', pairs.get(f'{b}__{a}'))


def ordering_verdict(pairs: dict) -> dict:
    """
    Does this space reproduce Campbell's ordering PA-BA > PA-EL and > BA-EL?

    Scored on the ordering only, not the magnitudes, because the published
    values are KC pattern correlations and these are input-space correlations;
    only the rank order is comparable.
    """
    pa_ba = _pair(pairs, 'pentyl_acetate', 'butyl_acetate')
    pa_el = _pair(pairs, 'pentyl_acetate', 'ethyl_lactate')
    ba_el = _pair(pairs, 'butyl_acetate', 'ethyl_lactate')
    if None in (pa_ba, pa_el, ba_el):
        return {'ordering_correct': None,
                'reason': 'at least one correlation undefined'}
    return {
        'pa_ba': pa_ba, 'pa_el': pa_el, 'ba_el': ba_el,
        'pa_ba_is_largest': bool(pa_ba > pa_el and pa_ba > ba_el),
        'ba_el_is_smallest': bool(ba_el < pa_ba and ba_el < pa_el),
        'ordering_correct': bool(pa_ba > pa_el > ba_el),
        'published': {'pa_ba': 0.70, 'pa_el': 0.15, 'ba_el': 0.11},
        'published_ordering': 'pa_ba > pa_el > ba_el',
    }


def pairwise(patterns: dict) -> dict:
    out = {}
    for a, b in itertools.combinations(sorted(patterns), 2):
        out[f'{a}__{b}'] = corr(patterns[a], patterns[b])
    return out


def clip_survival(patterns: dict, concentrations=CLIP_CONCENTRATIONS) -> dict:
    """
    How much of an odour's identity survives ``clip(pattern * conc, 0, 1)``.

    This is exactly what ``OdorReceptorArray.set_activation`` does to the
    pattern before the carrier and the plume touch it, so it is on the reported
    signal path. A dense pattern drives many channels to the 1.0 ceiling at
    once, and channels pinned at the ceiling are indistinguishable, so identity
    degrades with concentration. A sparse pattern saturates fewer channels and
    should degrade less.
    """
    out = {}
    for name, p in patterns.items():
        base = np.clip(np.asarray(p, float) * concentrations[0], 0.0, 1.0)
        per_conc = {}
        for c in concentrations:
            clipped = np.clip(np.asarray(p, float) * c, 0.0, 1.0)
            n_at_ceiling = int(np.sum(clipped >= 1.0 - 1e-12))
            r = corr(base, clipped)
            per_conc[str(c)] = {
                'r_vs_conc_1': r,
                'n_channels_at_ceiling': n_at_ceiling,
                'fraction_at_ceiling': float(n_at_ceiling / clipped.size),
            }
        out[name] = per_conc
    return out


def summarise_space(name: str, patterns: dict, discarded: dict) -> dict:
    frac_nonzero = [float(np.mean(np.asarray(p) > 0)) for p in patterns.values()]
    pairs = pairwise(patterns)
    defined = [v for v in pairs.values() if v is not None]
    return {
        'space': name,
        'n_channels': int(len(next(iter(patterns.values())))),
        'fraction_nonzero_mean': float(np.mean(frac_nonzero)),
        'fraction_nonzero_range': [float(np.min(frac_nonzero)),
                                   float(np.max(frac_nonzero))],
        'pairwise_correlations': pairs,
        'mean_pairwise_r': float(np.mean(defined)) if defined else None,
        'campbell_ordering': ordering_verdict(pairs),
        'relu_discarded': discarded,
        'clip_survival': clip_survival(patterns),
    }


def main():
    panel = list(ODOR_PANEL)

    print("=" * 74)
    print("GLOMERULAR PROJECTION DIAGNOSTIC")
    print("=" * 74)

    door = DoorClient(projection='sklearn_pca')
    receptors = list(door.receptor_names)
    matrix = np.asarray(door.response_matrix, dtype=np.float64)

    # The PCA basis is built lazily on first lookup, so force it now, exactly as
    # validation_utils.init_olfactory_brain does. Without this pca_projection is
    # still None and projection_method is unset in the provenance block.
    door.map_to_glomerular_pattern(np.zeros(len(receptors), dtype=np.float32))

    live_cols = [i for i in range(matrix.shape[1])
                 if np.any(matrix[:, i] != 0)]
    print(f"\nMatrix: {matrix.shape[0]} odorants x {matrix.shape[1]} receptors")
    print(f"  columns with data : {len(live_cols)}")
    print(f"  negative entries  : {int(np.sum(matrix < 0))}")
    print(f"  fraction non-zero : {float(np.mean(matrix != 0)):.4f}")

    pn_per_glom = annotated_glomeruli()
    print(f"\nConnectome: {len(pn_per_glom)} glomeruli with annotated "
          f"uniglomerular PNs, {sum(pn_per_glom.values())} PNs total")

    glom_proj, glom_channels, proj_report = build_projection(
        receptors, restrict_to=pn_per_glom)
    print(f"Map: {proj_report['n_receptors_mapped']}/{len(receptors)} receptors "
          f"-> {len(glom_channels)} glomerular channels")
    if proj_report['multi_receptor_channels']:
        print(f"  multi-receptor channels: "
              f"{proj_report['multi_receptor_channels']}")
    if proj_report['channels_dropped_no_projection_neurons']:
        print(f"  dropped, no PNs: "
              f"{proj_report['channels_dropped_no_projection_neurons']}")

    # ── Build the three spaces ──────────────────────────────────────────
    receptor_signed, receptor_relu, pca20, glomerular = {}, {}, {}, {}
    discarded = {'receptor': {}, 'pca20': {}, 'glomerular': {}}
    missing = []

    for name in panel:
        try:
            resp = np.asarray(door.get_odorant_response(name), dtype=np.float64)
        except Exception as exc:  # OdorantNotFoundError
            missing.append(f'{name}: {exc}')
            continue

        live = resp[live_cols]
        receptor_signed[name] = live
        receptor_relu[name] = relu_l2(live)
        discarded['receptor'][name] = _discard_stats(live)

        projected_pca = resp @ door.pca_projection
        pca20[name] = relu_l2(projected_pca)
        discarded['pca20'][name] = _discard_stats(projected_pca)

        projected_glom = resp @ glom_proj
        glomerular[name] = relu_l2(projected_glom)
        discarded['glomerular'][name] = _discard_stats(projected_glom)

    if missing:
        print(f"\nOdorants not resolvable, excluded: {missing}")
    print(f"\nPanel odorants analysed: {len(receptor_signed)}")

    spaces = {
        'receptor_signed': summarise_space(
            'receptor_signed', receptor_signed, discarded['receptor']),
        'receptor_relu_l2': summarise_space(
            'receptor_relu_l2', receptor_relu, discarded['receptor']),
        'pca20': summarise_space('pca20', pca20, discarded['pca20']),
        'glomerular': summarise_space(
            'glomerular', glomerular, discarded['glomerular']),
    }

    # ── Report ──────────────────────────────────────────────────────────
    print("\n" + "-" * 74)
    print("SPARSITY AND RELU LOSS")
    print("-" * 74)
    print(f"{'space':<18} {'chans':>6} {'frac>0':>8} {'relu kept':>10} "
          f"{'mean pair r':>12}")
    for key, s in spaces.items():
        kept = np.mean([d['fraction_of_magnitude_kept']
                        for d in s['relu_discarded'].values()])
        mp = s['mean_pairwise_r']
        print(f"{key:<18} {s['n_channels']:>6} "
              f"{s['fraction_nonzero_mean']:>8.4f} {kept:>10.4f} "
              f"{(f'{mp:.4f}' if mp is not None else 'n/a'):>12}")

    print("\n" + "-" * 74)
    print("CAMPBELL 2013 FIG 4C ORDERING  (published: PA-BA 0.70 > PA-EL 0.15 "
          "> BA-EL 0.11)")
    print("-" * 74)
    print(f"{'space':<18} {'PA-BA':>9} {'PA-EL':>9} {'BA-EL':>9} "
          f"{'ordering':>10}")
    for key, s in spaces.items():
        o = s['campbell_ordering']
        if o.get('ordering_correct') is None:
            print(f"{key:<18} {'-':>9} {'-':>9} {'-':>9} {'undefined':>10}")
            continue
        print(f"{key:<18} {o['pa_ba']:>9.4f} {o['pa_el']:>9.4f} "
              f"{o['ba_el']:>9.4f} "
              f"{('CORRECT' if o['ordering_correct'] else 'wrong'):>10}")

    print("\n" + "-" * 74)
    print("IDENTITY SURVIVAL THROUGH clip(pattern * conc, 0, 1)")
    print("-" * 74)
    print(f"{'space':<18} {'conc':>6} {'mean r vs conc=1':>18} "
          f"{'mean frac at ceiling':>21}")
    clip_summary = {}
    for key, s in spaces.items():
        clip_summary[key] = {}
        for c in CLIP_CONCENTRATIONS:
            rs = [v[str(c)]['r_vs_conc_1'] for v in s['clip_survival'].values()
                  if v[str(c)]['r_vs_conc_1'] is not None]
            fr = [v[str(c)]['fraction_at_ceiling']
                  for v in s['clip_survival'].values()]
            clip_summary[key][str(c)] = {
                'mean_r_vs_conc_1': float(np.mean(rs)) if rs else None,
                'mean_fraction_at_ceiling': float(np.mean(fr)),
            }
            print(f"{key:<18} {c:>6.1f} "
                  f"{(np.mean(rs) if rs else float('nan')):>18.4f} "
                  f"{np.mean(fr):>21.4f}")

    # ── Verdict ─────────────────────────────────────────────────────────
    # Two questions, and they have different answers. Reported separately
    # rather than collapsed into one pass/fail, because collapsing them would
    # have hidden the finding.
    rmse = {k: _rmse_vs_published(s['campbell_ordering'])
            for k, s in spaces.items()}
    print("\n" + "-" * 74)
    print("DISTANCE TO THE PUBLISHED VALUES  (RMSE over the three pairs)")
    print("-" * 74)
    for k, v in sorted(rmse.items(), key=lambda kv: (kv[1] is None, kv[1])):
        print(f"  {k:<18} {('n/a' if v is None else f'{v:.4f}'):>8}")

    recep = spaces['receptor_signed']['campbell_ordering']
    pca = spaces['pca20']['campbell_ordering']
    glom = spaces['glomerular']['campbell_ordering']

    # Q1: is the ordering recoverable at all? The specific inversion is
    # BA-EL > PA-EL. If that is already in the untouched receptor responses then
    # no projection can be blamed for it and no projection can repair it.
    inversion_in_raw = bool(recep['ba_el'] > recep['pa_el'])
    ordering_recoverable = not inversion_in_raw

    # Q2: does the current projection distort the similarity structure? Measured
    # two ways that do not depend on the Campbell triple at all.
    r_recep = spaces['receptor_signed']['mean_pairwise_r']
    r_pca = spaces['pca20']['mean_pairwise_r']
    r_glom = spaces['glomerular']['mean_pairwise_r']
    inflation_pca = r_pca / r_recep if r_recep else None
    inflation_glom = r_glom / r_recep if r_recep else None
    kept_pca = float(np.mean([d['fraction_of_magnitude_kept']
                              for d in spaces['pca20']['relu_discarded'].values()]))
    kept_glom = float(np.mean([d['fraction_of_magnitude_kept']
                               for d in spaces['glomerular']['relu_discarded'].values()]))

    if not ordering_recoverable and rmse['glomerular'] < rmse['pca20']:
        gate = 'ORDERING_IS_UPSTREAM_BUT_PROJECTION_DISTORTS_STRUCTURE'
    elif ordering_recoverable and rmse['glomerular'] < rmse['pca20']:
        gate = 'PROJECTION_IS_THE_CULPRIT'
    elif not ordering_recoverable:
        gate = 'NOT_THE_PROJECTION'
    else:
        gate = 'UNEXPECTED'

    verdict = (
        "Two separate answers.\n\n"
        "(1) The ordering inversion exists in the INPUT data, not in the "
        f"projection. Campbell reports PA-EL > BA-EL, and the untouched DoOR "
        f"receptor responses have it the other way round (BA-EL "
        f"{recep['ba_el']:.4f} against PA-EL {recep['pa_el']:.4f}). So no "
        "projection can be blamed for losing it at the input stage. What IS "
        "correct in every space, including the raw data, is that PA-BA is the "
        "largest of the three pairs.\n\n"
        "    Note on scope, added after the ablation ladder was run: this is a "
        "statement about the INPUT space only, and it does not predict the "
        "benchmark. Similarity Part A scores KC-space correlations, and the "
        "PN-to-KC expansion plus the rank threshold is a nonlinear transform "
        "that can and does reorder pairs. An earlier version of this verdict "
        "predicted from the line above that Part A would keep failing. It was "
        "measured and that prediction was WRONG: under the one-to-one "
        "projection Part A passes with the published ordering (PA-BA 0.4678 > "
        "PA-EL 0.2518 > BA-EL 0.2215). See "
        "docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md. The lesson is that "
        "an input-space correlation does not bound a KC-space one, which this "
        "script already said under 'scored_on' and which the verdict then "
        "ignored.\n\n"
        "(2) The projection nevertheless distorts the similarity structure "
        "badly, and the repair fixes that. Three measurements, none of which "
        "depend on the Campbell triple:\n"
        f"  * PCA inflates mean pairwise similarity across the 12-odorant panel "
        f"from r = {r_recep:.4f} in the measured data to r = {r_pca:.4f}, a "
        f"factor of {inflation_pca:.2f}. It makes every odour look far more "
        f"like every other odour than the recordings say. The one-to-one map "
        f"gives r = {r_glom:.4f}, a factor of {inflation_glom:.2f}.\n"
        f"  * PCA plus ReLU keeps only {100 * kept_pca:.1f} % of the projected "
        f"response magnitude, discarding a third of the signal, because "
        f"principal-component signs are arbitrary and the rectifier removes "
        f"whichever half comes out negative. The one-to-one map keeps "
        f"{100 * kept_glom:.1f} %.\n"
        f"  * Against the published Campbell values, RMSE is "
        f"{rmse['pca20']:.4f} for PCA and {rmse['glomerular']:.4f} for the "
        f"one-to-one map, which is "
        f"{rmse['pca20'] / rmse['glomerular']:.1f}x closer. Two of the three "
        f"pairs land almost on the published number "
        f"(PA-BA {glom['pa_ba']:.4f} against 0.70, "
        f"PA-EL {glom['pa_el']:.4f} against 0.15).\n\n"
        "So the repair is justified, but not for the reason originally "
        "hypothesised. It should be expected to change downstream correlations "
        "substantially, because it stops compressing the odour space and stops "
        "discarding a third of the input. Measured outcome: the suite went from "
        "2/5 to 4/5, with discrimination and similarity both flipping to PASS "
        "and concentration invariance rising from r = 0.5417 to 0.6706."
    )

    print("\n" + "=" * 74)
    print(f"GATE: {gate}")
    print("=" * 74)
    print(verdict)

    payload = {
        'question':
            'Is the 40->20 PCA projection responsible for the similarity '
            'benchmark failing on the ordering of Campbell et al. 2013 '
            'Fig 4C, rather than the network?',
        'why_this_is_cheap':
            'no simulation is run. Three input spaces are compared directly, '
            'so the projection is tested in isolation from the network for the '
            'cost of a matrix multiply.',
        'audit_reference':
            'docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md lists this cause '
            'as untraced.',
        'spaces_compared': {
            'receptor_signed': 'the measured DoOR columns, untouched',
            'receptor_relu_l2': 'measured columns with the pipeline ReLU and '
                                'L2 applied, to separate the projection from '
                                'the rectification',
            'pca20': 'what the model currently receives: 40->20 mean-centred '
                     'PCA, ReLU, L2',
            'glomerular': 'proposed repair: published one-to-one receptor to '
                          'glomerulus assignment, then the same ReLU and L2',
        },
        'matrix': {
            'n_odorants': int(matrix.shape[0]),
            'n_receptor_columns': int(matrix.shape[1]),
            'n_columns_with_data': len(live_cols),
            'n_negative_entries': int(np.sum(matrix < 0)),
            'fraction_nonzero': float(np.mean(matrix != 0)),
            'all_zero_columns': [receptors[i] for i in range(matrix.shape[1])
                                 if i not in live_cols],
        },
        'connectome_coverage': coverage_report(receptors, pn_per_glom),
        'projection_report': proj_report,
        'receptor_glomerulus_map': assignment_table(),
        'panel': {
            'odorants': sorted(receptor_signed),
            'unresolvable': missing,
            'provenance': {n: ODOR_PANEL[n] for n in sorted(receptor_signed)},
        },
        'published_target': {
            'source': 'Campbell et al. 2013 J Neurosci 33:10568, Fig 4C',
            'values': {f'{a}__{b}': v
                       for (a, b), v in CAMPBELL_2013_FIG4C.items()},
            'scored_on': 'ordering only, because the published values are KC '
                         'pattern correlations and these are input-space '
                         'correlations; only the rank order is comparable',
        },
        'spaces': spaces,
        'clip_survival_summary': clip_summary,
        'rmse_vs_published': rmse,
        'findings': {
            'ordering_recoverable_by_any_projection': ordering_recoverable,
            'inversion_present_in_raw_receptor_data': inversion_in_raw,
            'inversion_described':
                'Campbell reports PA-EL 0.15 > BA-EL 0.11. The measured DoOR '
                'responses have BA-EL above PA-EL, so the inversion is in the '
                'input data, not in any projection.',
            'pa_ba_largest_in_every_space': all(
                s['campbell_ordering'].get('pa_ba_is_largest') is True
                for s in spaces.values()),
            'mean_pairwise_r': {
                'receptor': r_recep, 'pca20': r_pca, 'glomerular': r_glom,
            },
            'similarity_inflation_vs_receptor_space': {
                'pca20': inflation_pca, 'glomerular': inflation_glom,
            },
            'relu_fraction_of_magnitude_kept': {
                'pca20': kept_pca, 'glomerular': kept_glom,
            },
            'rmse_improvement_factor_glomerular_over_pca':
                (rmse['pca20'] / rmse['glomerular'])
                if rmse.get('glomerular') else None,
        },
        'prediction_before_rerun': {
            'similarity': 'expected to keep FAILING Part A; the ordering '
                          'inversion is upstream in the receptor data',
            'other_benchmarks': 'expected to move, because inter-odour '
                                'similarity falls by roughly the inflation '
                                'factor above and a third of the discarded '
                                'input magnitude is restored. Direction not '
                                'predicted.',
            'recorded': 'before the ablation ladder was run',
            'OUTCOME': 'the similarity prediction was WRONG. Part A passed under '
                       'the one-to-one projection with the published ordering '
                       '(PA-BA 0.4678 > PA-EL 0.2518 > BA-EL 0.2215). The '
                       'prediction reasoned from an input-space correlation to a '
                       'KC-space one, and the PN-to-KC expansion plus rank '
                       'threshold is a nonlinear transform that reorders pairs. '
                       'The second half of the prediction, that other benchmarks '
                       'would move without a predicted direction, held: '
                       'discrimination also flipped to PASS and the suite went '
                       '2/5 -> 4/5. Recorded rather than edited out; see '
                       'docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md.',
        },
        'gate': gate,
        'verdict': verdict,
    }
    out = write_results('glomerular_projection_diagnostic.json', payload,
                        door_client=door, seed=None,
                        suite='diagnose_glomerular_projection')
    print(f"\nWritten to {out}")
    return gate


def _rmse_vs_published(ordering: dict):
    """
    Root-mean-square distance from this space's three correlations to the
    published Campbell values.

    A single number for "how close is this input space to the measurement",
    independent of whether the strict ordering holds. Comparing input-space
    correlations to Campbell's KC-space correlations is not a like-for-like
    test, so this is a relative measure between projections, not an absolute
    score.
    """
    if ordering.get('ordering_correct') is None:
        return None
    pub = ordering['published']
    return float(np.sqrt(np.mean([
        (ordering['pa_ba'] - pub['pa_ba']) ** 2,
        (ordering['pa_el'] - pub['pa_el']) ** 2,
        (ordering['ba_el'] - pub['ba_el']) ** 2,
    ])))


def _discard_stats(projected: np.ndarray) -> dict:
    """How much the ReLU throws away from a projected pattern."""
    p = np.asarray(projected, dtype=np.float64)
    total = float(np.sum(np.abs(p)))
    kept = float(np.sum(np.maximum(p, 0.0)))
    return {
        'n_channels': int(p.size),
        'n_negative': int(np.sum(p < 0)),
        'fraction_negative': float(np.mean(p < 0)),
        'magnitude_total_abs': total,
        'magnitude_kept': kept,
        'fraction_of_magnitude_kept': (kept / total) if total > 0 else 0.0,
    }


if __name__ == '__main__':
    main()
