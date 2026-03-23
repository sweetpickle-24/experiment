#!/usr/bin/env python3
"""
New Test Suite Runner
=====================

**Date**: 2026-03-23

Runs all new tests created after the initial 14/14 validation suite:

  1. JO Frequency Tuning   — Auditory pathway, Johnston's Organ (NEW MODALITY)
  2. Extinction Learning   — MBON decay after unreinforced odor presentation
  3. Context Recall        — Same odor, different MBON response per DAN context
  4. Sequence Learning     — A→B temporal prediction (NOVEL — no prior connectome test)
  5. Noise Robustness      — Sparse coding, invariance, discrimination under noise

Run as:
    python run_new_tests.py
    python run_new_tests.py --tests auditory extinction   (subset)
    python run_new_tests.py --no-auditory                 (skip connectome reload)
"""

import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))


def run_auditory_test() -> dict:
    from hive.substrate.connectome import Connectome
    from hive.validation.auditory.test_jo_frequency_tuning import run_jo_frequency_tuning_test
    print("\n[1/5] Johnston's Organ Frequency Tuning...")
    c = Connectome(data_dir='Fly Brain Female')
    c.load()
    return run_jo_frequency_tuning_test(c)


def run_extinction_test() -> dict:
    from hive.validation.smell.test_extinction_learning import run_extinction_learning_test
    print("\n[2/5] Extinction Learning...")
    return run_extinction_learning_test()


def run_context_test() -> dict:
    from hive.validation.smell.test_context_recall import run_context_recall_test
    print("\n[3/5] Context-Dependent Recall...")
    return run_context_recall_test()


def run_sequence_test() -> dict:
    from hive.validation.smell.test_sequence_learning import run_sequence_learning_test
    print("\n[4/5] Sequence Learning...")
    return run_sequence_learning_test()


def run_noise_test() -> dict:
    from hive.validation.smell.test_noise_robustness import run_noise_robustness_tests
    print("\n[5/5] Noise Robustness...")
    return run_noise_robustness_tests()


TESTS = {
    'auditory':   run_auditory_test,
    'extinction': run_extinction_test,
    'context':    run_context_test,
    'sequence':   run_sequence_test,
    'noise':      run_noise_test,
}

TEST_LABELS = {
    'auditory':   'JO Frequency Tuning (Auditory)',
    'extinction': 'Extinction Learning',
    'context':    'Context-Dependent Recall',
    'sequence':   'Sequence Learning (DAN/MBON)',
    'noise':      'Noise Robustness',
}


def main():
    parser = argparse.ArgumentParser(description='Run new validation tests')
    parser.add_argument('--tests', nargs='+', choices=list(TESTS.keys()),
                        default=list(TESTS.keys()),
                        help='Which tests to run (default: all)')
    args = parser.parse_args()

    print("=" * 70)
    print("NEW VALIDATION TEST SUITE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Tests: {', '.join(args.tests)}")
    print("=" * 70)

    results = {}
    timings = {}

    for test_key in args.tests:
        start = time.time()
        try:
            res = TESTS[test_key]()
            results[test_key] = res
        except Exception as e:
            print(f"\n❌ {test_key} FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results[test_key] = {'passed': False, 'error': str(e)}
        timings[test_key] = time.time() - start

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    passed = 0
    for key in args.tests:
        res = results.get(key, {})
        ok  = res.get('passed', False)
        t   = timings.get(key, 0.0)
        sym = '✅' if ok else '❌'
        print(f"{sym} {TEST_LABELS[key]:<35} {'PASS' if ok else 'FAIL'}  ({t:.1f}s)")
        if ok:
            passed += 1

    print(f"\nOverall: {passed}/{len(args.tests)} passed")

    # Save
    out_dir = Path('research')
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / 'new_tests_results.json'
    combined = {
        'timestamp': datetime.now().isoformat(),
        'tests_run': args.tests,
        'summary': {k: results[k].get('passed', False) for k in args.tests},
        'results': results,
        'wall_times_sec': timings,
    }
    with open(out_path, 'w') as f:
        json.dump(combined, f, indent=2)
    print(f"\nFull results saved to {out_path}")


if __name__ == '__main__':
    main()
