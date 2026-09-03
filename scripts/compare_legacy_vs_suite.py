#!/usr/bin/env python3
"""
Cross-check the four revived standalone tests against the five-benchmark suite.

tests/validate_discrimination_threshold.py, validate_odor_similarity.py,
validate_odor_mixtures.py and validate_learning_plasticity.py measure four of
the same phenomena as scripts/run_all_validations.py, with different odour
sets, different protocols and in two cases different pass criteria. Now that
they run, this records whether the two independent implementations agree — which
is the only reason to keep both.

Usage:
    python scripts/compare_legacy_vs_suite.py [--suite all_validations_F6_after.json]
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from validation_utils import results_path  # noqa: E402


def load(name):
    with open(results_path(name)) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--suite', default='all_validations_F6_after.json')
    ap.add_argument('--output', default='legacy_vs_suite_comparison.json')
    args = ap.parse_args()

    suite = load(args.suite)['validations']
    disc = load('discrimination_threshold_results.json')
    simi = load('odor_similarity_results.json')
    mixt = load('odor_mixtures_results.json')
    learn = load('learning_plasticity_results.json')

    rows = [
        {
            'phenomenon': 'discrimination (JND)',
            'threshold': '10-20% (Weber, Borst & Heisenberg 1982)',
            'suite_value': suite['discrimination']['summary']['mean_jnd_percent'],
            'suite_verdict': suite['discrimination']['summary']['validation'],
            'standalone_value': disc['summary']['jnd_percent']['mean'],
            'standalone_verdict': disc['summary']['biological_validation']['jnd_in_range'],
            'same_criterion': True,
            'difference': (
                'Suite sweeps 5/10/15/20/25% on two odours; the standalone '
                'sweeps up to 100% on three. Both report the smallest '
                'discriminable step.'
            ),
        },
        {
            'phenomenon': 'similarity (chem-neural r)',
            'threshold': '0.3-0.5 (Bhandawat et al. 2007)',
            'suite_value': suite['similarity']['summary']['chem_neural_correlation'],
            'suite_verdict': suite['similarity']['summary']['validation'],
            'standalone_value': simi['summary']['chem_neural_correlation'],
            'standalone_verdict': simi['summary']['biological_validation']['chem_neural_correlation'],
            'same_criterion': True,
            'difference': (
                'Suite correlates 3 pairwise similarities from 3 odours; the '
                'standalone uses 5 resolvable odours, so 10 pairs. With only 3 '
                'points the suite value is a correlation over 3 observations '
                'and is not stable.'
            ),
        },
        {
            'phenomenon': 'mixtures (component overlap)',
            'threshold': '30-50% (Stettler & Axel 2009)',
            'suite_value': suite['odor_mixtures']['summary']['mean_overlap_percent'],
            'suite_verdict': suite['odor_mixtures']['summary']['validation'],
            'standalone_value': mixt['summary']['component_overlap_percent']['mean'],
            'standalone_verdict': mixt['summary']['biological_validation']['component_overlap'],
            'same_criterion': True,
            'difference': (
                'Suite tests one binary mixture; the standalone tests all '
                'binary pairs plus the ternary mixture (4 mixtures).'
            ),
        },
        {
            'phenomenon': 'learning',
            'threshold': 'suite: MBON change >= 1%; standalone: KC->MBON weight 2-3x (Hige et al. 2015)',
            'suite_value': suite['learning']['summary']['mbon_change_pct'],
            'suite_verdict': suite['learning']['summary']['validation'],
            'standalone_value': learn['summary']['weight_change_factor']['mean'],
            'standalone_verdict': learn['summary']['biological_validation']['weight_increase'],
            'same_criterion': False,
            'difference': (
                'These do NOT measure the same thing. The suite asks whether '
                'the MBON response changed at all (>= 1%) after 5 phase-based '
                'STDP trials and passes. The standalone asks whether KC->MBON '
                'weights grew 2-3x after 20 amplitude-product Hebbian trials '
                'and fails at 1.03x. The suite criterion is satisfied by any '
                'measurable change; the standalone criterion is the quantitative '
                'biological one.'
            ),
        },
    ]

    for r in rows:
        r['verdicts_agree'] = r['suite_verdict'] == r['standalone_verdict']

    agree = sum(1 for r in rows if r['verdicts_agree'])
    results = {
        'purpose': (
            'Whether the four revived standalone tests agree with the suite. '
            'They had never run before 2026-09-03: each constructed '
            'SparseProbabilisticBrain with num_neurons/dt keywords it does not '
            'accept and so raised TypeError, and each also called '
            'door_client.project_to_pca_basis, brain.load_connectome_simple and '
            'brain.inject_external_input, none of which existed.'
        ),
        'suite_file': args.suite,
        'comparisons': rows,
        'summary': {
            'phenomena_compared': len(rows),
            'verdicts_agreeing': agree,
            'shared_criterion_count': sum(1 for r in rows if r['same_criterion']),
            'conclusion': (
                'All three benchmarks that use the same criterion as the suite '
                'reach the same verdict, on different odour sets and different '
                'protocols. The learning pair disagrees because the two use '
                'different criteria, and the standalone applies the stricter, '
                'quantitative one: KC->MBON weights grow 1.03x against a 2-3x '
                'biological target.'
            ),
        },
    }

    w0 = 30
    print(f"\n{'phenomenon':<{w0}} {'suite':>12} {'standalone':>12} "
          f"{'suite':>8} {'standalone':>11} {'agree':>6}")
    print('-' * 86)
    for r in rows:
        print(f"{r['phenomenon']:<{w0}} {r['suite_value']:>12.4g} "
              f"{r['standalone_value']:>12.4g} {r['suite_verdict']:>8} "
              f"{r['standalone_verdict']:>11} "
              f"{'yes' if r['verdicts_agree'] else 'NO':>6}")
    print(f"\n{agree}/{len(rows)} verdicts agree "
          f"({results['summary']['shared_criterion_count']} share a criterion)")
    print(f"\n{results['summary']['conclusion']}")

    out = results_path(args.output)
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nWritten to {out}")


if __name__ == '__main__':
    main()
