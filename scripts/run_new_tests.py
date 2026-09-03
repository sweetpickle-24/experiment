#!/usr/bin/env python3
"""
New Test Suite Runner
=====================

**Date**: 2026-03-23
**Last Updated**: 2026-09-03

Supplementary tests beyond the core olfactory suite in `run_all_validations.py`.

Caveats that apply to everything here (see README):
  - Pass criteria in this suite are mostly relative or trivially low ("change > 2%",
    "|index| > 0.05", "within 3x of clean") rather than quantitative biological
    benchmarks. Passing does not mean a published result was reproduced.
  - JO frequency tuning does not run the wave engine. Each subtype's resonant
    frequency is supplied as an input parameter, so recovering it is not a test of
    the connectome.
  - Two tests were withdrawn as invalid on 2026-09-03 because the expected answer
    was supplied to the model as an input. See `hive/validation/invalid/README.md`.

Batch 1:
  1. JO Frequency Tuning   — analytic oscillator model, not a connectome test
  2. Extinction Learning   — MBON decay after unreinforced odor presentation
  3. Sequence Learning     — A→B temporal prediction
  4. Noise Robustness      — sparsity, invariance, discrimination under noise

Batch 2:
  5. Auditory Learning          — AMMC→WED STDP conditioning/extinction
  6. Olfactory Prosthetic POC   — PN lesion + wave compensation recovery
  7. Poisson Noise Model        — ORN vs PN vs KC noise stage comparison
  8. Poisson Spiking Layer      — Stage 2.5 CV transition: quantum bump vs rate regime

Run as:
    python run_new_tests.py
    python run_new_tests.py --tests auditory extinction          (subset)
    python run_new_tests.py --tests auditory_learn prosthetic    (batch 2 subset)
"""

import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ─── Batch 1 runners ──────────────────────────────────────────────────────────

def run_auditory_test() -> dict:
    from hive.substrate.connectome import Connectome
    from hive.validation.auditory.test_jo_frequency_tuning import run_jo_frequency_tuning_test
    print("\n[1/10] Johnston's Organ Frequency Tuning...")
    c = Connectome(data_dir='Fly Brain Female')
    c.load()
    return run_jo_frequency_tuning_test(c)


def run_extinction_test() -> dict:
    from hive.validation.smell.test_extinction_learning import run_extinction_learning_test
    print("\n[2/10] Extinction Learning...")
    return run_extinction_learning_test()


def run_sequence_test() -> dict:
    from hive.validation.smell.test_sequence_learning import run_sequence_learning_test
    print("\n[4/10] Sequence Learning...")
    return run_sequence_learning_test()


def run_noise_test() -> dict:
    from hive.validation.smell.test_noise_robustness import run_noise_robustness_tests
    print("\n[5/10] Noise Robustness...")
    return run_noise_robustness_tests()


# ─── Batch 2 runners ──────────────────────────────────────────────────────────

def run_auditory_learning_test() -> dict:
    from hive.validation.auditory.test_auditory_learning import run_auditory_learning_test
    print("\n[7/10] Auditory Learning (AMMC→WED STDP)...")
    return run_auditory_learning_test()


def run_prosthetic_poc_test() -> dict:
    from hive.validation.smell.test_prosthetic_poc import run_prosthetic_poc_test
    print("\n[8/10] Olfactory Prosthetic POC...")
    return run_prosthetic_poc_test()


def run_poisson_noise_test() -> dict:
    from hive.validation.smell.test_poisson_noise import run_poisson_noise_tests
    print("\n[9/10] Poisson Noise Model (pipeline stages)...")
    return run_poisson_noise_tests()


def run_poisson_spiking_test() -> dict:
    from hive.validation.vision.test_poisson_spiking import run_poisson_spiking_test
    print("\n[10/10] Poisson Spiking Layer (Stage 2.5)...")
    return run_poisson_spiking_test()


# ─── Test registry ────────────────────────────────────────────────────────────

TESTS = {
    # Batch 1
    'auditory':        run_auditory_test,
    'extinction':      run_extinction_test,
    'sequence':        run_sequence_test,
    'noise':           run_noise_test,
    # Batch 2
    'auditory_learn':  run_auditory_learning_test,
    'prosthetic':      run_prosthetic_poc_test,
    'poisson_noise':   run_poisson_noise_test,
    'poisson_spiking': run_poisson_spiking_test,
}

TEST_LABELS = {
    # Batch 1
    'auditory':        'JO Frequency Tuning (Auditory)',
    'extinction':      'Extinction Learning',
    'sequence':        'Sequence Learning (DAN/MBON)',
    'noise':           'Noise Robustness',
    # Batch 2
    'auditory_learn':  'Auditory Learning (AMMC→WED)',
    'prosthetic':      'Olfactory Prosthetic POC',
    'poisson_noise':   'Poisson Noise Model (ORN/PN/KC)',
    'poisson_spiking': 'Poisson Spiking Layer (Stage 2.5)',
}

BATCH_1 = ['auditory', 'extinction', 'sequence', 'noise']
BATCH_2 = ['auditory_learn', 'prosthetic', 'poisson_noise', 'poisson_spiking']


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Run new validation tests')
    parser.add_argument(
        '--tests', nargs='+',
        choices=list(TESTS.keys()),
        default=list(TESTS.keys()),
        help='Which tests to run (default: all)',
    )
    parser.add_argument(
        '--batch', choices=['1', '2', 'all'], default='all',
        help='Run a specific batch (1=original 5, 2=extended 5, all=all 10)',
    )
    args = parser.parse_args()

    # Resolve which tests to run
    if args.batch == '1':
        tests_to_run = BATCH_1
    elif args.batch == '2':
        tests_to_run = BATCH_2
    else:
        tests_to_run = args.tests

    print("=" * 70)
    print("NEW VALIDATION TEST SUITE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Tests: {', '.join(tests_to_run)}")
    print("=" * 70)

    results = {}
    timings = {}

    for test_key in tests_to_run:
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
    for key in tests_to_run:
        res = results.get(key, {})
        ok  = res.get('passed', False)
        t   = timings.get(key, 0.0)
        sym = '✅' if ok else '❌'
        print(f"{sym} {TEST_LABELS[key]:<40} {'PASS' if ok else 'FAIL'}  ({t:.1f}s)")
        if ok:
            passed += 1

    print(f"\nOverall: {passed}/{len(tests_to_run)} passed")

    # Save results
    out_dir = Path('research')
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / 'new_tests_results.json'
    combined = {
        'timestamp': datetime.now().isoformat(),
        'tests_run': tests_to_run,
        'batch': args.batch,
        'summary': {k: results[k].get('passed', False) for k in tests_to_run},
        'passed_count': passed,
        'total_count': len(tests_to_run),
        'results': results,
        'wall_times_sec': timings,
    }
    with open(out_path, 'w') as f:
        json.dump(combined, f, indent=2)
    print(f"\nFull results saved to {out_path}")


if __name__ == '__main__':
    main()
