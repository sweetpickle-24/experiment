# Invalid tests

**Date**: 2026-09-03

The tests in this directory are preserved for the record. **They do not produce
evidence of anything** and their results have been removed from the repository's
documentation.

Both share the same defect: the expected answer reaches the model as an input, so
the test cannot fail. A test that cannot fail cannot support a claim.

Do not run these expecting a meaningful result, and do not cite their output.

---

## `test_context_recall.py`

**Claimed:** that the same odor produces opposite mushroom body output compartment
dominance in a reward context versus an aversive context, demonstrating
context-dependent memory via PAM/PPL1 dopaminergic compartment selection.

**Why it is invalid:** the MBON population is split in half, `mbon_a_idx` and
`mbon_b_idx`. Context A training applies selective potentiation to group A only:

```python
apply_selective_stdp(brain, learning_rate=reward_rate, mbon_indices=mbon_a_idx)
```

Context B training applies it to group B only. The pass criterion then checks:

```python
ctxA_correct = ctxA_mbon_a > ctxA_mbon_b
ctxB_correct = ctxB_mbon_b > ctxB_mbon_a
```

The test potentiates group A, then verifies group A is larger. The outcome is fixed
by the training target. It would pass on any substrate, including a randomly wired
one, and tells you nothing about the connectome or the wave dynamics.

**What a valid version would need:** the compartment assignment would have to emerge
from actual PAM and PPL1 connectivity in the connectome rather than being an
arbitrary split of the MBON index array, and the potentiation target would have to be
determined by that connectivity rather than chosen to match the criterion.

---

## `test_multisensory_integration.py`

**Claimed:** olfactory-visual cross-modal interaction in AVLP on the real connectome.

**Why it is invalid:** the "visual stimulus" is external force injected directly onto
AVLP neurons. Two of the three pass criteria then check that AVLP activity rose:

```python
criterion_avlp_increase = avlp_combined > avlp_odor
criterion_visual_drive  = avlp_visual > avlp_baseline * 1.01
```

Driving a population and then confirming the population is driven is not a result.
The 1.01 factor makes the second criterion a 1% threshold on a directly forced
quantity.

The third criterion, `abs(cross_modal_index) > 0.05`, is not circular in the same
way, but 0.05 is an arbitrary bar rather than a quantitative benchmark from
Bräcker et al. (2013) or Kim et al. (2015), and the test does not predict the sign
of the interaction — either direction passes.

**What a valid version would need:** visual drive entering through the actual
visual-to-AVLP projections in the connectome rather than as direct forcing on the
readout population, and a pre-registered predicted sign and magnitude taken from the
cited experimental work.
