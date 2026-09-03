#!/usr/bin/env python3
"""
Render results/final/fix_ledger.json as a comparison table.

One column per recorded entry, so the effect of each individual fix is read off
directly rather than inferred. Every benchmark row carries the threshold it is
judged against.

Usage:
    python scripts/ledger_report.py                 # all entries
    python scripts/ledger_report.py F0_before F4_after
    python scripts/ledger_report.py --markdown      # for pasting into a report
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from validation_utils import results_path  # noqa: E402


def fmt(x, spec='%.4g'):
    if x is None:
        return '-'
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, (int, float)):
        return spec % x
    return str(x)


def suite_rows(e):
    s = e.get('suite')
    if not s:
        return [('(suite not run)', '', '-')]
    td, om, di, si, le = (s['temporal_dynamics'], s['odor_mixtures'],
                          s['discrimination'], s['similarity'], s['learning'])
    jnd = di.get('jnd_per_odor') or {}
    return [
        ('temporal: peak time (ms)', '50-150', fmt(td['peak_time_mean_ms'])),
        ('temporal: adaptation (%)', '30-70', fmt(td['adaptation_mean_percent'])),
        ('temporal: verdict', '', td['verdict']),
        ('mixtures: overlap (%)', '30-50', fmt(om['mean_overlap_percent'])),
        ('mixtures: verdict', '', om['verdict']),
        ('discrimination: JND (%)', '10-20 all', ', '.join(f'{k}={v}' for k, v in jnd.items())),
        ('discrimination: verdict', '', di['verdict']),
        ('similarity: chem-neural r', '0.3-0.5', fmt(si['chem_neural_correlation'])),
        ('similarity: verdict', '', si['verdict']),
        ('learning: MBON change (%)', '>= 1.0', fmt(le['mbon_change_pct'])),
        ('learning: verdict', '', le['verdict']),
        ('SCORE', '5/5', f"{s['score']['passed']}/{s['score']['total']}" if s.get('score') else '-'),
    ]


def invariance_rows(e):
    ci = e.get('concentration_invariance')
    if not ci:
        return [('(invariance not run)', '', '-')]
    bc, jc = ci['binary_correlation'], ci['jaccard_similarity']
    return [
        ('invariance: binary r mean', '> 0.7 strong', fmt(bc['mean'])),
        ('invariance: binary r sd', '', fmt(bc['std'])),
        ('invariance: binary r min', '', fmt(bc['min'])),
        ('invariance: binary r max', '', fmt(bc['max'])),
        ('invariance: jaccard mean', '> 0.6 strong', fmt(jc['mean'])),
        ('invariance: verdict', 'strong', ci['verdict']),
    ]


def diag_rows(e):
    d = e.get('diagnostics')
    if not d:
        return [('(diagnostics not run)', '', '-')]
    dr = d['drive']
    pn = d['regions']['PN']
    kc = d['regions']['KC']
    return [
        ('drive: time-varying', '', fmt(dr.get('time_varying'))),
        ('drive: driven neurons', '', fmt(dr['n_driven_neurons'], '%d')),
        ('drive: force peak', '', fmt(dr['force_peak'])),
        ('PN at amplitude ceiling', '0', f"{pn['n_at_amplitude_ceiling']}/{pn['n']}"),
        ('PN amplitude max', f"< {fmt(d.get('amplitude_ceiling'))}", fmt(pn['amplitude_max'])),
        ('KC at amplitude ceiling', '0', f"{kc['n_at_amplitude_ceiling']}/{kc['n']}"),
        ('peak |velocity| (rad/ms)', '', fmt(d['peak_abs_velocity'])),
        ('phase advance / step (rad)', '< pi', fmt(d['phase_advance_per_step_rad'])),
        ('KC raw max', '', fmt(d['kc_raw_max'])),
        ('KC active (> 0.01)', '', fmt(d['kc_active_above_0p01'], '%d')),
    ]


SECTIONS = [
    ('FIVE-BENCHMARK SUITE', suite_rows),
    ('CONCENTRATION INVARIANCE', invariance_rows),
    ('STIMULUS-PATH DIAGNOSTICS', diag_rows),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('labels', nargs='*', help='entries to show (default: all)')
    ap.add_argument('--markdown', action='store_true')
    args = ap.parse_args()

    with open(results_path('fix_ledger.json')) as f:
        ledger = json.load(f)
    entries = ledger['entries']
    if args.labels:
        by_label = {e['label']: e for e in entries}
        missing = [l for l in args.labels if l not in by_label]
        if missing:
            sys.exit(f"no such ledger entries: {missing}")
        entries = [by_label[l] for l in args.labels]

    labels = [e['label'] for e in entries]
    w0 = max([28] + [len(r[0]) for _, fn in SECTIONS for e in entries for r in fn(e)])
    w1 = 14
    wc = max(12, *(len(l) for l in labels))

    for title, fn in SECTIONS:
        cols = [dict(fn(e)) if False else fn(e) for e in entries]
        names = []
        for c in cols:
            for name, _, _ in c:
                if name not in names:
                    names.append(name)

        if args.markdown:
            print(f"\n**{title}**\n")
            print('| metric | threshold | ' + ' | '.join(labels) + ' |')
            print('|' + '---|' * (2 + len(labels)))
        else:
            print(f"\n{title}")
            print('-' * (w0 + w1 + (wc + 2) * len(labels) + 4))
            print(f"{'metric':<{w0}}  {'threshold':<{w1}}  " +
                  '  '.join(f'{l:<{wc}}' for l in labels))
            print('-' * (w0 + w1 + (wc + 2) * len(labels) + 4))

        for name in names:
            thr = ''
            vals = []
            for c in cols:
                m = {r[0]: (r[1], r[2]) for r in c}
                if name in m:
                    thr = thr or m[name][0]
                    vals.append(m[name][1])
                else:
                    vals.append('-')
            if args.markdown:
                print(f'| {name} | {thr} | ' + ' | '.join(vals) + ' |')
            else:
                print(f"{name:<{w0}}  {thr:<{w1}}  " +
                      '  '.join(f'{v:<{wc}}' for v in vals))

    print()
    for e in entries:
        print(f"{e['label']}: {e.get('note') or '(no note)'}")
        print(f"    commit {e.get('git_commit', '?')[:12]}  recorded {e.get('recorded_at', '?')}")


if __name__ == '__main__':
    main()
