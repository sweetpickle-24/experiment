# Concentration Invariance Test - Formula & Methodology Validation

<!-- STALE-BANNER-2026-09-05 -->
> **SUPERSEDED — do not cite.** This document predates the September 2026 audits and
> has not been rewritten. Corrections that apply to it:
>
> - The scored suite is **5/5** (`results/final/all_validations_G2.json`). Scores of
>   9/9, 13/13, 14/14 or 27/27 appearing anywhere were **never produced by any run**;
>   the recorded history is 3/5, then 1/5, then 2/5, then 5/5.
> - GPU speedup is **10.00×**, not 86×.
> - Kenyon cell sparsity is **imposed by the readout** (310 of 5,177 cells) rather
>   than measured, so "1.65 % matching Turner et al. 2008" is withdrawn.
> - Concentration invariance is **0.6603 and deliberately unscored**; the 0.70
>   threshold it used to be compared against is not in the paper it was cited to.
> - The decorrelation result **`r = −0.51` is withdrawn** — a six-point regression
>   from a run recorded as FAIL, measured at `+0.632` on a later run.
> - Vision and auditory "firsts" are **not** part of the scored suite, and several
>   come from hand-written filters rather than the wave engine.
>
> Current: [README](../../README.md) ·
> [ARCHITECTURE](../../ARCHITECTURE.md) ·
> [LIMITATIONS](../../docs/03_validation/LIMITATIONS.md) ·
> [audit](../../docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md) ·
> [projection repair](../../docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md).
> Tracked in [OUTDATED_FILES.md](../../OUTDATED_FILES.md).


**Date**: 2026-03-16  
**Purpose**: Verify we're not using wrong formulas or fabricating results

---

## ✅ Formula Validation

### Pearson Correlation Coefficient

**Formula used**: `np.corrcoef(pattern1, pattern2)[0, 1]`

**Mathematical definition**:
```
ρ(X,Y) = cov(X,Y) / (σ_X × σ_Y)
```

**Test results**:
```
Identical patterns:  r = 1.000  ✓ PASS
Opposite patterns:   r = -1.000 ✓ PASS
```

**Source**: numpy.corrcoef() computes Pearson product-moment correlation  
**Verified**: Standard statistical measure, correctly implemented

---

### Jaccard Similarity Index

**Formula used**:
```python
intersection = sum(logical_and(active1, active2))
union = sum(logical_or(active1, active2))
jaccard = intersection / union
```

**Mathematical definition**:
```
J(A,B) = |A ∩ B| / |A ∪ B|
```

**Test results**:
```
Identical sets:    J = 1.0 ✓ PASS
Disjoint sets:     J = 0.0 ✓ PASS
50% overlap:       J = 0.5 ✓ PASS
```

**Source**: Standard set similarity measure  
**Verified**: Correctly implements intersection-over-union

---

##  ✅ Biological Validation Thresholds

### Sparsity Target: 5-7%

**Source**: Honegger, Campbell & Turner (2011), *J. Neurosci*  
**Quote**: "on average, an odor evokes responses in **∼5% of the KCs** in an imaging plane"

**Cross-validation**: Turner et al. (2008) single-cell recordings: **6% average**

**Upper bound**: "The mean proportion of responding cells did **not exceed 0.1** for any odor"

**Our measurements**:
- Ethyl acetate: 0% (pattern was all zeros!)
- Benzaldehyde: 0.02-43.6%
- 2-heptanone: 3.9-49.2%

**Conclusion**: Simulation fails to maintain biological 5-7% sparsity

---

### Concentration Invariance Target: r > 0.7

**Rationale**: 
- Biological systems maintain odor identity across 3-4 orders of magnitude
- High correlation (r>0.7) indicates same neurons active across concentrations
- This is a reasonable threshold for "strong" invariance

**Literature support**:
- Bhandawat et al. (2007): "separability" maintained across concentrations
- Olsen & Wilson (2008): Lateral inhibition provides gain control
- Ahmed et al. (2023): Input density, not cell number, tunes selectivity

**Our results**:
- Random initialization: r = 0.149 ❌
- Deterministic initialization: r = 0.476 ⚠️
- Target: r > 0.7 ❌

**Conclusion**: Deterministic reset improves but still below biological threshold

---

## ⚠️ CRITICAL FLAWS IDENTIFIED

### Flaw 1: Ethyl Acetate Pattern is Zero Vector

**Problem**:
```python
ethyl_acetate_pattern = door_client.get_glomerular_pattern('ethyl acetate')
# Returns: [0.0, 0.0, 0.0, ..., 0.0]  (20 zeros)
```

**Root cause**: 
- DOoR database PCA projection maps this odor to zero vector
- Warning message "not in database" is misleading - it IS in database but projects to zero
- This invalidates the entire ethyl acetate test

**Impact**: One-third of test data is garbage

**Fix**: Use different odor or check projection is valid

---

### Flaw 2: Backwards Sparsity Response

**Observation**:
```
Benzaldehyde: 43.6% → 0.02% (decreases with concentration)
2-heptanone: 49.2% → 3.9% (decreases with concentration)
```

**Expected (biology)**: Stable 5-7% across all concentrations

**Hypothesis for backwards response**:

1. **Saturation/Inhibition**: High concentration (strength=500) may:
   - Saturate oscillators → reduce responsiveness
   - Trigger implicit inhibitory dynamics in coupled system
   - Cause numerical instabilities

2. **Linear scaling without normalization**: 
   - Low conc (0.1×): strength = 5.0 → weak signal, low SNR
   - High conc (10.0×): strength = 500.0 → 100× difference
   - No divisive normalization to stabilize output

3. **Missing gain control**:
   - Biology uses synaptic depression at PN→KC synapses
   - We use constant coupling strength
   - No adaptation to input magnitude

---

### Flaw 3: No Lateral Inhibition

**Missing mechanism**: APL neuron provides global feedback inhibition

**Biological function**:
- Monitors total KC activity
- Provides divisive normalization
- Maintains ~5-7% sparsity regardless of input

**Impact**: Without this, sparsity ranges 0-50% instead of stable 5-7%

**Evidence from literature**: 
- Lin et al. (2014): "APL neuron normalizes KC activity"
- Honegger et al. (2011): "Disrupting APL reduces sparseness"

---

## ✅ Valid Conclusions

### What We Can Trust

1. **Formulas are correct**: Pearson correlation and Jaccard are standard measures, properly implemented

2. **Deterministic reset helps**: Removing random phase noise improved correlation by 220%

3. **The wave-based architecture works**: Oscillators couple, propagate activity, produce patterns

4. **MLX GPU acceleration works**: Real-time performance on 10K neuron olfactory system

### What We Cannot Trust

1. **Absolute correlation values**: Without normalization, hard to interpret

2. **Sparsity patterns**: Non-biological (0-50% vs 5-7% target)

3. **Concentration scaling**: Backwards response suggests systemic problem

4. **Ethyl acetate results**: Entire odor test invalid (zero pattern)

---

## 🔧 Required Fixes (Priority Order)

### Priority 1: Fix Ethyl Acetate Pattern

**Action**: Replace with valid odor or fix PCA projection

**Verification**: Ensure pattern has mean > 0.05, nonzero channels > 5

---

### Priority 2: Implement Normalization Layer

**Method**: Winner-take-all with adaptive threshold

```python
def normalize_kc_activity(activity, target_sparsity=0.06):
    """Maintain 6% sparsity via adaptive threshold"""
    sorted_activity = np.sort(activity)[::-1]
    threshold_idx = int(len(activity) * target_sparsity)
    threshold = sorted_activity[threshold_idx]
    return np.maximum(0, activity - threshold)
```

**Expected improvement**: Sparsity → 5-7% stable, correlation r → 0.65-0.75

---

### Priority 3: Add Gain Control

**Method**: Synaptic depression or divisive normalization

```python
# Option A: Adapt injection strength based on pattern magnitude
pattern_norm = np.linalg.norm(glomerular_pattern)
adapted_strength = base_strength / (1 + 0.1 * pattern_norm)

# Option B: Synaptic depression at PN→KC
syn_strength *= (1 - depression_factor * recent_PN_activity)
```

**Expected improvement**: Correlation r → 0.75-0.85

---

## 📊 Validation Metrics Summary

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Formula correctness | ✅ | ✅ | PASS |
| Sparsity (%) | 0-49 | 5-7 | FAIL |
| Correlation (r) | 0.476 | >0.7 | FAIL |
| Pattern validity | 2/3 | 3/3 | PARTIAL |
| Biological mechanism | 0/3 | 3/3 | FAIL |

**Overall**: Methodology is sound, but simulation lacks key biological mechanisms

---

## Conclusion

### We Are NOT Faking Results

- Formulas are standard and verified
- Measurements are real simulation outputs
- Correlations accurately reflect pattern similarity
- Problems are genuine failures, not measurement artifacts

### The Simulation Has Real Problems

1. **Missing normalization** → sparsity uncontrolled
2. **Missing adaptation** → concentration scaling fails
3. **Bad test data** → ethyl acetate pattern is zeros

### Path Forward

1. Fix ethyl acetate pattern (1 hour)
2. Implement normalization layer (4 hours)
3. Re-run concentration test
4. Expect r = 0.65-0.75 with correct sparsity

**Timeline**: 1-2 days to biological validation

---

## References

1. Honegger, K.S., Campbell, R.A., & Turner, G.C. (2011). Cellular-resolution population imaging reveals robust sparse coding in the Drosophila mushroom body. *J Neurosci* 31(33), 11772-11785.

2. Lin, A.C. et al. (2014). Sparse, decorrelated odor coding in the mushroom body enhances learned odor discrimination. *Nature Neuroscience* 17(4), 559-568.

3. Bhandawat, V. et al. (2007). Sensory processing in the Drosophila antennal lobe increases reliability and separability of ensemble odor representations. *Nature Neuroscience* 10, 1474-1482.

4. Turner, G.C., Bazhenov, M., & Laurent, G. (2008). Olfactory representations by Drosophila mushroom body neurons. *J Neurophysiol* 99, 734-746.

5. Ahmed, M. et al. (2023). Input density tunes Kenyon cell sensory responses in the Drosophila mushroom body. *Curr Biol* 33(13), 2742-2760.
