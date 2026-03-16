# Concentration Invariance - Final Status Report

**Date**: 2026-03-16  
**Test Iterations**: 3 (Random → Deterministic → + Normalization)

---

## Results Summary

| Configuration | Correlation | Sparsity | Status |
|---------------|-------------|----------|--------|
| Random init | r=0.149 ± 0.205 | 0-60% | ❌ FAIL |
| Deterministic | r=0.476 ± 0.420 | 0-49% | ⚠️ PARTIAL |
| + Normalization | r=0.442 ± 0.432 | 0.5-1.2% | ⚠️ PARTIAL |
| **Target** | **r>0.70** | **5-7%** | **GOAL** |

---

## Iteration 3: Normalization Results

### Sparsity Control: ✅ WORKS (but too aggressive)

**Before normalization** (deterministic only):
```
Benzaldehyde: 43.6% → 0.02%  (inverted)
2-heptanone:  49.2% → 3.9%   (inverted)
```

**After normalization** (6% target):
```
Benzaldehyde: 0.55% → 0.00%  (still decreases)
2-heptanone:  0.59% → 0.09%  (still decreases)
Isoamyl acetate: 0% all concentrations (zero pattern from DOoR)
```

**Analysis**:
- ✅ Sparsity controlled to ~0.5-1% (vs uncontrolled 0-50%)
- ❌ TOO SPARSE: getting 0.5% instead of 6% target
- ❌ Still concentration-dependent (decreases at high conc)
- ❌ Wrong threshold calculation or pattern amplitudes too low

---

## Root Causes Still Present

### 1. Odor Patterns from DOoR Database
- **Isoamyl acetate**: All zeros (like ethyl acetate)
- **Benzaldehyde**: Valid (mean=0.12, max=0.60)
- **2-heptanone**: Valid (mean=0.14, max=0.55)

**Issue**: DOoR PCA projection maps some odors to zero vectors

### 2. Concentration Scaling Still Backwards
Even with normalization, response DECREASES with concentration:
- Low (0.1×): 0.55-0.59% active
- High (10.0×): 0.00-0.09% active

**Hypothesis**: High concentration (strength=500) saturates/inhibits system

### 3. Normalization Too Aggressive
Target: 6% sparsity → Getting: 0.5% sparsity

**Possible causes**:
- Base amplitudes too low (mean ~0.001-0.01)
- Threshold cuts off too much signal
- Need multiplicative gain before threshold

---

## Why Normalization Didn't Help Correlation

**Expected**: Stable sparsity → more consistent patterns → higher correlation

**Observed**: Sparsity controlled but correlation DECREASED (0.476 → 0.442)

**Explanation**:
1. Normalization applied AFTER simulation completes
2. Doesn't fix backwards concentration response
3. At high concentration, almost all KCs are below threshold → empty pattern
4. Empty vs sparse patterns have low correlation

**What's needed**: 
- Fix concentration scaling BEFORE normalization
- Or: apply normalization during evolution (feedback loop)
- Or: adjust base injection strength

---

## Key Insights

### What Works ✅
1. **Formulas are correct**: Pearson correlation and Jaccard properly implemented
2. **Deterministic reset helps**: Removes phase noise (+220% improvement)
3. **Normalization controls sparsity**: Successfully limits to target range
4. **MLX GPU works**: Fast enough for iteration

### What Doesn't Work ❌
1. **DOoR database**: Some odors project to zero vectors
2. **Linear concentration scaling**: Causes backwards responses
3. **Post-hoc normalization**: Too late to fix dynamics
4. **Threshold positioning**: Cutting off too much signal

---

## The Real Problem: Saturation

**Hypothesis**: At high concentration, external force is SO STRONG it causes:
1. Oscillators saturate → reduced responsiveness
2. Or: numerical instabilities in coupled system
3. Or: implicit inhibitory dynamics we don't understand

**Evidence**:
- 0.1× (strength=5):    Many active KCs
- 10.0× (strength=500): Almost zero active KCs
- This is OPPOSITE of biology

**Biology does**: 
- Synaptic depression reduces effective strength at high conc
- Gain control adapts to input magnitude
- Result: stable output despite 100× input range

---

## Path Forward

### Option A: Fix Injection Scaling (Recommended)
```python
# Instead of linear scaling
scaled_strength = base_strength * conc

# Use logarithmic or saturating function
scaled_strength = base_strength * np.log10(1 + conc)
# or
scaled_strength = base_strength * conc / (1 + 0.1 * conc)  # Michaelis-Menten
```

**Expected**: Monotonic response, less saturation at high conc

---

### Option B: Add Synaptic Adaptation
```python
# Simulate synaptic depression
effective_strength = base_strength / (1 + depression_factor * mean_input_history)
```

**Expected**: Automatic gain control, concentration invariance

---

### Option C: Adjust Base Amplitudes
Current: mean_amplitude init = 0.1, typical values = 0.001-0.01  
Problem: Signal too weak relative to threshold

```python
# Increase base amplitude or reduce damping
self.mean_amplitude = np.ones(self.num_neurons) * 1.0  # instead of 0.1
# or
self.gamma = 0.05  # instead of 0.5 (less damping)
```

**Expected**: Stronger signals, normalization threshold works better

---

## Recommended Next Steps

1. **Fix DOoR patterns** (1 hour)
   - Verify all test odors have nonzero patterns
   - Use different odors or fix PCA projection

2. **Try logarithmic scaling** (1 hour)
   - Change line 104: `scaled_strength = base_strength * np.log10(1 + 10*conc)`
   - Re-run test
   - Expected: r = 0.50-0.60

3. **Tune normalization threshold** (30 min)
   - Target 6% but currently getting 0.5%
   - May need to boost signal amplitude first

4. **Add synaptic adaptation** (1 day)
   - Implement depression/facilitation
   - Expected: r > 0.70

---

## Conclusion

We've made **significant progress**:
- ✅ Identified and fixed random phase problem
- ✅ Implemented biologically-inspired normalization
- ✅ Verified formulas are correct
- ✅ Controlled sparsity (even if too aggressive)

But **concentration scaling is fundamentally broken**:
- High concentration → LOW activity (backwards!)
- This dominates everything else
- Normalization can't fix it post-hoc

**Priority 1**: Fix concentration scaling (logarithmic or adaptive)  
**Expected timeline**: 2-3 hours to biological validation  
**Confidence**: High - this is the core issue

---

## Documentation Status

Created:
1. ✅ `FORMULA_VALIDATION.md` - Proves math is correct
2. ✅ `CONCENTRATION_INVARIANCE_FINDINGS.md` - Root cause analysis
3. ✅ `CONCENTRATION_INVARIANCE_SUMMARY.md` - Executive summary
4. ✅ `CONCENTRATION_INVARIANCE_FINAL.md` - This document

All findings saved to experiment root directory.
