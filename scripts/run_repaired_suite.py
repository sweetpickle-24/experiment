#!/usr/bin/env python3
"""
Score the five repaired olfactory benchmarks.

This aggregates the five per-benchmark result files rather than re-running them
in one process. That is deliberate: each benchmark writes its own file carrying
its own configuration block, so every number in the combined score stays
traceable to the run that produced it. Re-running them here would save four
connectome loads and cost that traceability.

It also refuses to combine files that do not share a backend or a protocol,
because a score assembled from runs under different conditions is not a score.

Usage
-----
Produce the five inputs first (each on the reporting backend, which is CPU --
see ``results/final/cpu_vs_mlx_fullrun.json``)::

    .venv/bin/python -m benchmarks_repaired.learning       --cpu
    .venv/bin/python -m benchmarks_repaired.similarity
    .venv/bin/python -m benchmarks_repaired.discrimination
    .venv/bin/python -m benchmarks_repaired.temporal
    .venv/bin/python -m benchmarks_repaired.mixtures

then::

    .venv/bin/python scripts/run_repaired_suite.py
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import results_path, write_results  # noqa: E402

#: The five scored benchmarks, with the file each writes.
BENCHMARKS = {
    'temporal_dynamics': 'temporal_repaired.json',
    'odor_mixtures': 'mixtures_repaired.json',
    'discrimination': 'discrimination_repaired.json',
    'similarity': 'similarity_repaired.json',
    'learning': 'learning_repaired.json',
}

#: Reported alongside but not scored, as the repository has always treated it.
UNSCORED = {
    'concentration_invariance': 'concentration_invariance_repaired.json',
}

#: The F8 baseline this replaces, for a before/after column.
F8_BASELINE = {
    'temporal_dynamics': ('FAIL', 'adaptation 34.21 %, peak 200 ms'),
    'odor_mixtures': ('PASS', '30.06 % overlap'),
    'discrimination': ('FAIL', 'JND 5.0 %, target 10-20 %'),
    'similarity': ('FAIL', 'chem-neural correlation -0.1204'),
    'learning': ('PASS', 'MBON 0.03327 -> 0.0000044 (99.99 %), KC 316 -> 315'),
}

#: Configuration keys that must agree across all five files. A score assembled
#: from runs on different backends or timesteps is not a score.
MUST_AGREE = ('backend', 'dt_ms', 'projection_method', 'glomerular_mapping',
              'gamma', 'sigma_noise', 'num_neurons',
              'projection_explained_variance', 'door_matrix_synthetic')


def load(name):
    path = results_path(name)
    if not path.exists():
        return None, path
    with open(path) as f:
        return json.load(f), path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', default='all_validations_F9_corrected.json')
    ap.add_argument('--allow-config-mismatch', action='store_true',
                    help='score anyway when the five files disagree on '
                         'configuration (records the mismatch)')
    args = ap.parse_args()

    print("=" * 74)
    print("REPAIRED OLFACTORY VALIDATION SUITE")
    print("=" * 74)

    loaded, missing = {}, []
    for bench, fname in BENCHMARKS.items():
        payload, path = load(fname)
        if payload is None:
            missing.append((bench, path))
        else:
            loaded[bench] = payload

    if missing:
        print("\nMissing result files. Produce them first:")
        for bench, path in missing:
            print(f"  {bench:<20} {path}")
        return 1

    # ── Configuration agreement ──────────────────────────────────────────────
    configs = {b: p.get('config', {}) for b, p in loaded.items()}
    mismatches = {}
    for key in MUST_AGREE:
        values = {b: c.get(key) for b, c in configs.items()}
        if len({json.dumps(v, sort_keys=True) for v in values.values()}) > 1:
            mismatches[key] = values

    if mismatches:
        print("\nCONFIGURATION MISMATCH across the five result files:")
        for key, values in mismatches.items():
            print(f"  {key}:")
            for b, v in values.items():
                print(f"    {b:<20} {v}")
        if not args.allow_config_mismatch:
            print("\nRefusing to score. A score assembled from runs under "
                  "different conditions is not a score.")
            print("Re-run the mismatched benchmarks on one configuration, or "
                  "pass --allow-config-mismatch to record the mismatch and "
                  "score anyway.")
            return 2
        print("\n--allow-config-mismatch given; the mismatch is recorded in "
              "the output.")

    commits = {b: c.get('git_commit') for b, c in configs.items()}
    backend = next(iter(configs.values())).get('backend')

    # ── Score ────────────────────────────────────────────────────────────────
    print(f"\nBackend: {backend}")
    print(f"{'benchmark':<20} {'F8':<6} {'now':<6}  what it now measures")
    print("-" * 74)

    rows = {}
    for bench, payload in loaded.items():
        verdict = payload['summary']['validation']
        f8_verdict, f8_detail = F8_BASELINE[bench]
        rows[bench] = {
            'validation': verdict,
            'f8_validation': f8_verdict,
            'f8_detail': f8_detail,
            'changed': verdict != f8_verdict,
            'measures': payload.get('measures'),
            'target_corrections': payload.get('target_corrections'),
            'summary': payload['summary'],
            'source_file': BENCHMARKS[bench],
            'git_commit': commits[bench],
        }
        arrow = '' if verdict == f8_verdict else '  <-- changed'
        print(f"{bench:<20} {f8_verdict:<6} {verdict:<6}{arrow}")
        measures = payload.get('measures', '')
        for line in _wrap(measures, 68):
            print(f"{'':<21}{line}")

    passed = sum(1 for r in rows.values() if r['validation'] == 'PASS')
    total = len(rows)

    print("-" * 74)
    print(f"SCORE: {passed}/{total}")
    f8_passed = sum(1 for v, _ in F8_BASELINE.values() if v == 'PASS')
    print(f"F8 baseline was {f8_passed}/{total}")

    # ── Unscored ─────────────────────────────────────────────────────────────
    unscored = {}
    for name, fname in UNSCORED.items():
        payload, path = load(fname)
        if payload is None:
            print(f"\n(unscored) {name}: not produced ({path})")
            continue
        unscored[name] = {
            'summary': payload['summary'],
            'why_not_scored': payload.get('why_not_scored'),
            'source_file': fname,
        }
        print(f"\n(unscored) {name}:")
        for k, v in payload['summary'].items():
            if not isinstance(v, (dict, list)):
                print(f"  {k}: {v}")

    out_payload = {
        'suite': 'repaired olfactory validation suite',
        'note':
            'aggregated from the five per-benchmark result files so every '
            'number stays traceable to the run that produced it; each source '
            'file carries its own configuration block',
        'backend_for_reporting': backend,
        'backend_rationale':
            'CPU, per the rule fixed before the run in '
            'results/final/cpu_vs_mlx_fullrun.json: CPU and MLX agree at '
            '100 ms (Jaccard 0.9446, r 0.9901) but not beyond, with worst '
            'Jaccard 0.1030 and worst r 0.0650 over a 2000 ms trajectory',
        'validations': rows,
        'unscored': unscored,
        'config_agreement': {
            'keys_checked': list(MUST_AGREE),
            'mismatches': mismatches or None,
            'git_commit_per_benchmark': commits,
        },
        'score': {'passed': passed, 'total': total},
        'f8_baseline_score': {'passed': f8_passed, 'total': total},
    }

    out = write_results(args.output, out_payload,
                        brain=None, door_client=None,
                        duration_ms=None, seed=None,
                        suite='run_repaired_suite', n_benchmarks=total,
                        backend=backend)
    print(f"\nWritten to {out}")
    return 0


def _wrap(text, width):
    if not text:
        return []
    words, lines, cur = text.split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f'{cur} {w}'.strip()
    if cur:
        lines.append(cur)
    return lines


if __name__ == '__main__':
    sys.exit(main())
