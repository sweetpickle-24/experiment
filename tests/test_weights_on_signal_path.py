#!/usr/bin/env python3
"""
Regression test: synaptic weights must be on the signal path.

The compiled MLX step kernel used to capture ``self.syn_weights`` in its closure
at build time, on the documented assumption that weights "never change between
steps". Every plasticity test in this repository assigns to
``brain.syn_weights``, so on the MLX backend with compilation available those
assignments never reached the kernel and **every learning test silently trained
nothing**.

This was not visible in any result file. The failure mode is a benchmark that
reports a number without measuring anything, which is the exact class of defect
this repair exists to remove, so it gets a test.

Affected before the fix:
  scripts/run_all_validations.py::_apply_hebbian_stdp
  tests/validate_learning_plasticity.py
  hive/validation/smell/test_extinction_learning.py
  hive/validation/smell/test_sequence_learning.py
  hive/validation/auditory/test_auditory_learning.py
  hive/validation/invalid/test_context_recall.py

Run: ``.venv/bin/python tests/test_weights_on_signal_path.py``
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import build  # noqa: E402
from validation_utils import set_seed  # noqa: E402


def mbon_and_kc(brain, pattern, seed=1001):
    set_seed(seed)
    brain.reset(deterministic=False)
    brain.inject_odor(pattern, strength=50.0)
    brain.evolve(duration=100.0)
    return (float(np.mean(brain.get_region_activity('MBON'))),
            brain.get_region_activity('KC', normalize_kc=True,
                                      target_sparsity=0.06))


def weights_np(brain):
    w = brain.syn_weights
    return np.asarray(w.tolist() if hasattr(w, 'tolist') else w,
                      dtype=np.float32)


def write_w(brain, w):
    if getattr(brain, 'use_mlx', False):
        import mlx.core as mx
        brain.syn_weights = mx.array(w.astype(np.float32))
    else:
        brain.syn_weights = w.astype(np.float32)


def check_backend(use_mlx):
    label = 'MLX' if use_mlx else 'NumPy'
    print(f"\n--- {label} ---")
    failures = []

    def check(name, ok, detail=''):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   {detail}" if detail else ''))
        if not ok:
            failures.append(f"{label}: {name}")

    brain, door, connectome = build(use_mlx=use_mlx)
    if use_mlx and not brain.use_mlx:
        print("  SKIP  MLX unavailable")
        return []
    check("compiled kernel in use" if use_mlx else "interpreted path in use",
          bool(brain._compiled_step) == bool(use_mlx))

    from hive.substrate.olfactory_subgraph import classify_olfactory_neuron
    region_of = {}
    for nid, n in connectome.neurons.items():
        i = brain.id_to_idx.get(nid)
        if i is not None:
            region_of[i] = classify_olfactory_neuron(n)
    reg = np.array([region_of.get(i, '?') for i in range(brain.num_neurons)])
    pre, post = np.asarray(brain.pre_indices), np.asarray(brain.post_indices)
    kc_mbon = (reg[pre] == 'KC') & (reg[post] == 'MBON')
    print(f"  KC->MBON synapses: {int(kc_mbon.sum())}")

    pattern = door.get_glomerular_pattern('pentyl_acetate')
    w0 = weights_np(brain)

    mbon_base, kc_base = mbon_and_kc(brain, pattern)

    # 1. Zeroing every KC->MBON weight must change the MBON response. If it does
    #    not, the weights are not on the signal path and no learning test on this
    #    backend is measuring anything.
    w = w0.copy()
    w[kc_mbon] = 0.0
    write_w(brain, w)
    mbon_zero, _ = mbon_and_kc(brain, pattern)
    write_w(brain, w0)
    rel = abs(mbon_zero - mbon_base) / abs(mbon_base) if mbon_base else 0.0
    check("zeroing all KC->MBON weights changes the MBON response",
          rel > 1e-6,
          f"{mbon_base:.6g} -> {mbon_zero:.6g}  ({100 * rel:.3f} %)")

    # 2. Zeroing every weight in the network must change the KC readout too, so
    #    the check above is not specific to the MBON path.
    write_w(brain, np.zeros_like(w0))
    _, kc_zero = mbon_and_kc(brain, pattern)
    write_w(brain, w0)
    check("zeroing all synaptic weights changes the KC readout",
          not np.array_equal(kc_base, kc_zero),
          f"max |dKC| = {float(np.max(np.abs(kc_base - kc_zero))):.6g}")

    # 3. Restoring the weights must restore the response exactly, so the test
    #    above is not leaving the engine in a mutated state.
    mbon_restored, kc_restored = mbon_and_kc(brain, pattern)
    check("restoring weights restores the response bit-exactly",
          mbon_restored == mbon_base and np.array_equal(kc_restored, kc_base))

    # 4. Determinism must survive: same seed, same weights, identical output.
    #    The fix moves an array from a closure to an argument, which must not
    #    reintroduce the nondeterminism the segment layout removed.
    a = mbon_and_kc(brain, pattern, seed=1002)
    b = mbon_and_kc(brain, pattern, seed=1002)
    check("same seed still bit-identical after the fix",
          a[0] == b[0] and np.array_equal(a[1], b[1]))

    # 5. Graded weight changes must produce graded response changes, not a
    #    threshold effect.
    responses = []
    for scale in (1.0, 0.75, 0.5, 0.25, 0.0):
        w = w0.copy()
        w[kc_mbon] = w0[kc_mbon] * scale
        write_w(brain, w)
        responses.append(mbon_and_kc(brain, pattern)[0])
    write_w(brain, w0)
    monotone = all(responses[i] >= responses[i + 1] - 1e-12
                   for i in range(len(responses) - 1))
    check("MBON response decreases monotonically as KC->MBON weights scale down",
          monotone,
          ' '.join(f'{r:.5g}' for r in responses))

    return failures


def main():
    failures = []
    failures += check_backend(use_mlx=False)
    failures += check_backend(use_mlx=True)
    print("\n" + "=" * 70)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for f in failures:
            print(f"  {f}")
        return 1
    print("WEIGHTS ARE ON THE SIGNAL PATH ON BOTH BACKENDS")
    return 0


if __name__ == '__main__':
    sys.exit(main())
