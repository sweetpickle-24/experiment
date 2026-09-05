#!/usr/bin/env python3
"""
Run the glomerular-projection ablation ladder.

One rung per configuration, each rung a full pass of the five scored benchmarks
plus concentration invariance, on the same declared seeds and the **same scoring
criteria**. Only the input pipeline changes between rungs, which is what makes
the comparison controlled.

Rungs
-----
    G0  the F9 baseline. Not re-run: it is already in
        results/final/all_validations_F9_corrected.json. Mean-centred PCA into 20
        channels, PN assignment by k-means on connectome position, loose neuron
        classification.

    G1  published one-to-one receptor-to-glomerulus projection (29 channels), PN
        assignment read off the connectome's glomerulus annotations. Neuron
        classification unchanged, so the subgraph is the same 10,906 neurons as
        G0 and the only difference is how the stimulus reaches the PNs.

    G2  G1 plus strict neuron classification, which stops the substring tests
        sweeping auditory wedge PNs, unnamed central-brain neurons, and every
        lateral-accessory-lobe neuron into the olfactory populations. This
        changes the subgraph size (10,906 -> 9,199), so it is a separate rung
        rather than folded into G1.

Why the projection and the PN assignment move together in G1: a glomerular
projection whose channels are named glomeruli is pointless if those channels are
then handed to k-means spatial clusters, and glomerulus-based PN assignment is
impossible without glomerulus-named channels. They are one change.

Known confound, stated rather than hidden
-----------------------------------------
G1 changes the channel count from 20 to 29, and per-channel carrier frequencies
were only ever specified for 20 channels. There is no published per-glomerulus
carrier frequency, so at 29 channels the 20 values are resampled by
interpolation (see OdorReceptorArray). The resampling is arbitrary, and it means
G1 differs from G0 in carrier frequencies as well as in projection.
``--frequency-mode uniform`` removes carrier frequency as a variable, but only if
BOTH arms are run that way, which costs another full pass.

Usage
-----
    .venv/bin/python scripts/run_glomerular_ladder.py --rung G1
    .venv/bin/python scripts/run_glomerular_ladder.py --rung G2
    .venv/bin/python scripts/run_glomerular_ladder.py --compare

Expect 1-3 hours of CPU per rung, dominated by the learning benchmark and its
learning-rate sweep.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from validation_utils import results_path, write_results  # noqa: E402

PY = str(REPO / '.venv' / 'bin' / 'python')

#: Rung definitions. Environment is what benchmark_harness.build() reads.
RUNGS = {
    'G1': {
        'label': 'glomerular projection + glomerulus PN assignment',
        'env': {
            'FLYBRAIN_PROJECTION': 'glomerular',
            'FLYBRAIN_GLOM_MAPPING': 'glomerulus',
            'FLYBRAIN_STRICT': '0',
        },
    },
    'G2': {
        'label': 'G1 + strict neuron classification',
        'env': {
            'FLYBRAIN_PROJECTION': 'glomerular',
            'FLYBRAIN_GLOM_MAPPING': 'glomerulus',
            'FLYBRAIN_STRICT': '1',
        },
    },
}

#: module -> (result-file stem, extra args). Order matters only for readability.
BENCHMARKS = [
    ('benchmarks_repaired.temporal', 'temporal', []),
    ('benchmarks_repaired.mixtures', 'mixtures', []),
    ('benchmarks_repaired.discrimination', 'discrimination', []),
    ('benchmarks_repaired.similarity', 'similarity', []),
    # learning takes --cpu rather than defaulting to it
    ('benchmarks_repaired.learning', 'learning', ['--cpu']),
    ('benchmarks_repaired.concentration_invariance',
     'concentration_invariance', []),
]

#: The five that are scored; concentration invariance is reported separately.
SCORED_STEMS = ('temporal', 'mixtures', 'discrimination', 'similarity',
                'learning')


def run_rung(rung: str, only=None, skip_existing=False) -> dict:
    spec = RUNGS[rung]
    env = dict(os.environ)
    env.update(spec['env'])
    env['PYTHONPATH'] = str(REPO)

    print("=" * 74)
    print(f"RUNG {rung}: {spec['label']}")
    print(f"  environment: {spec['env']}")
    print("=" * 74)

    outcomes = {}
    for module, stem, extra in BENCHMARKS:
        if only and stem not in only:
            continue
        out_name = f'{stem}_{rung}.json'
        out_path = results_path(out_name)
        if skip_existing and out_path.exists():
            print(f"\n-- {stem}: already present, skipping ({out_path.name})")
            outcomes[stem] = {'status': 'skipped_existing',
                              'output': out_name}
            continue

        cmd = [PY, '-m', module, '--output', out_name] + extra
        print(f"\n-- {stem}\n   {' '.join(cmd)}")
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, cwd=str(REPO), env=env,
                              capture_output=True, text=True)
        elapsed = time.perf_counter() - t0

        tail = (proc.stdout or '').strip().splitlines()[-12:]
        for line in tail:
            print(f"   | {line}")
        if proc.returncode != 0:
            err = (proc.stderr or '').strip().splitlines()[-15:]
            print(f"   FAILED (exit {proc.returncode}) after {elapsed:.0f}s")
            for line in err:
                print(f"   ! {line}")
        else:
            print(f"   ok in {elapsed:.0f}s")

        outcomes[stem] = {
            'status': 'ok' if proc.returncode == 0 else 'failed',
            'returncode': proc.returncode,
            'elapsed_s': round(elapsed, 1),
            'output': out_name,
            'stderr_tail': (proc.stderr or '').strip().splitlines()[-15:]
                           if proc.returncode != 0 else None,
        }

    return outcomes


def aggregate(rung: str, allow_mismatch=False) -> int:
    """
    Score a rung with the existing aggregator.

    Delegated to run_repaired_suite.py --suffix rather than reimplemented, so the
    scoring, the configuration-agreement check and the output shape are literally
    the same code that produced the F9 baseline. A ladder whose rungs were scored
    by different code would not be a ladder.
    """
    cmd = [PY, str(REPO / 'scripts' / 'run_repaired_suite.py'),
           '--suffix', rung,
           '--output', f'all_validations_{rung}.json']
    if allow_mismatch:
        cmd.append('--allow-config-mismatch')
    print(f"\n-- scoring rung {rung}\n   {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    print((proc.stdout or '').rstrip())
    if proc.returncode != 0:
        print((proc.stderr or '').rstrip())
    return proc.returncode


def compare(rungs=('G1', 'G2')) -> dict:
    """Side-by-side table of every rung against the F9 baseline."""
    baseline, _ = _load('all_validations_F9_corrected.json')
    if baseline is None:
        print("F9 baseline missing; cannot compare.")
        return {}

    table = {'G0_F9_baseline': _extract_suite(baseline)}
    for rung in rungs:
        payload, path = _load(f'all_validations_{rung}.json')
        if payload is None:
            print(f"(rung {rung} not scored yet: {path.name} absent)")
            continue
        table[rung] = _extract_suite(payload)

    benches = ('temporal_dynamics', 'odor_mixtures', 'discrimination',
               'similarity', 'learning')
    print("\n" + "=" * 74)
    print("LADDER COMPARISON")
    print("=" * 74)
    header = f"{'benchmark':<22}" + ''.join(f"{k:>16}" for k in table)
    print(header)
    print("-" * len(header))
    for bench in benches:
        row = f"{bench:<22}"
        for key in table:
            row += f"{table[key]['validations'].get(bench, '-'):>16}"
        print(row)
    print("-" * len(header))
    score_row = f"{'SCORE':<22}"
    for key in table:
        s = table[key]['score']
        score_row += f"{f'{s[0]}/{s[1]}':>16}"
    print(score_row)

    inv_row = f"{'conc. invariance r':<22}"
    for key in table:
        v = table[key].get('invariance_r')
        inv_row += f"{('-' if v is None else f'{v:.4f}'):>16}"
    print(inv_row)

    n_row = f"{'neurons':<22}"
    for key in table:
        v = table[key].get('num_neurons')
        n_row += f"{('-' if v is None else str(v)):>16}"
    print(n_row)

    ch_row = f"{'stim channels':<22}"
    for key in table:
        v = table[key].get('n_channels')
        ch_row += f"{('-' if v is None else str(v)):>16}"
    print(ch_row)

    for label, field in (('projection', 'projection'),
                         ('PN mapping', 'pn_mapping')):
        row = f"{label:<22}"
        for key in table:
            v = table[key].get(field)
            row += f"{(v or '-'):>16}"
        print(row)

    return table


def _extract_suite(payload: dict) -> dict:
    validations = {k: v.get('validation')
                   for k, v in payload.get('validations', {}).items()}
    score = payload.get('score', {})
    inv = (payload.get('unscored', {})
           .get('concentration_invariance', {})
           .get('summary', {})
           .get('pattern_correlation_mean'))
    # The aggregate records only each benchmark's source filename; the
    # configuration block lives in the source file itself, which is the whole
    # point of aggregating rather than re-running. So follow the reference.
    num_neurons = n_channels = projection = mapping = None
    for entry in payload.get('validations', {}).values():
        src, _ = _load(entry.get('source_file') or '')
        cfg = (src or {}).get('config') or {}
        num_neurons = num_neurons or cfg.get('num_neurons')
        n_channels = n_channels or cfg.get('n_stim_channels')
        projection = projection or cfg.get('projection_method')
        mapping = mapping or cfg.get('glomerular_mapping')
        if num_neurons and n_channels:
            break
    return {
        'projection': projection,
        'pn_mapping': mapping,
        'validations': validations,
        'score': (score.get('passed'), score.get('total')),
        'invariance_r': inv,
        'num_neurons': num_neurons,
        'n_channels': n_channels,
    }


def _load(name):
    path = results_path(name)
    if not path.exists():
        return None, path
    with open(path) as f:
        return json.load(f), path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rung', choices=sorted(RUNGS),
                    help='run one rung of the ladder')
    ap.add_argument('--only', nargs='*',
                    help='restrict to these benchmark stems')
    ap.add_argument('--skip-existing', action='store_true',
                    help='skip benchmarks whose output file already exists')
    ap.add_argument('--compare', action='store_true',
                    help='print the side-by-side table (needs scored rungs)')
    args = ap.parse_args()

    if not args.rung and not args.compare:
        ap.error('give --rung or --compare')

    payload = {}
    if args.rung:
        t0 = time.perf_counter()
        outcomes = run_rung(args.rung, only=args.only,
                            skip_existing=args.skip_existing)
        payload['rung'] = args.rung
        payload['label'] = RUNGS[args.rung]['label']
        payload['environment'] = RUNGS[args.rung]['env']
        payload['benchmarks'] = outcomes
        payload['total_elapsed_s'] = round(time.perf_counter() - t0, 1)
        failed = [k for k, v in outcomes.items() if v['status'] == 'failed']
        payload['failed'] = failed
        print("\n" + "=" * 74)
        print(f"RUNG {args.rung} done in {payload['total_elapsed_s']:.0f}s"
              + (f", FAILED: {failed}" if failed else ", all ok"))

        if not failed and not args.only:
            payload['score_returncode'] = aggregate(args.rung)
        elif failed:
            print("Not scoring: a benchmark failed, and a partial score is not "
                  "a score.")

        out = write_results(f'ladder_{args.rung}_run.json', payload,
                            seed=None, suite='run_glomerular_ladder')
        print(f"Run log: {out}")

    if args.compare:
        table = compare()
        if table:
            write_results('glomerular_ladder_comparison.json',
                          {'table': table,
                           'rungs': {k: v['label'] for k, v in RUNGS.items()}},
                          seed=None, suite='run_glomerular_ladder_compare')

    return 0


if __name__ == '__main__':
    sys.exit(main())
