# Medulla and Lobula Fine-Tuning Results

**Date**: 2026-03-18  
**Status**: Medulla improved but still needs adjustment, Lobula needs major architectural investigation

---

## Executive Summary

After reducing R7/R8 forcing gain from 0.5× to 0.15× and updating lobula target from 10-20% to biologically appropriate 15-30%:

**Results**:
- **Lamina**: 20.87% ± 4.73% (target: 20-40%) - ✅ **PASS** (was 22.91%, stable)
- **Medulla**: 7.24% ± 2.43% (target: 2-5%) - ❌ **FAIL** (was 9.32%, improved 22% but overshot)
- **Lobula**: 0.61% ± 0.42% (target: 15-30%) - ❌ **FAIL** (was 2.07%, DECREASED 71%)
- **Lobula Plate**: 17.98% ± 5.64% (target: 10-20%) - ✅ **PASS** (was 19.95%, stable)

**Score**: 2/4 passing (50%) - unchanged from before

---

## R7/R8 Gain Reduction Analysis

### Biological Rationale

**Quantum Efficiency** (Salcedo et al. 1999):
- R1-R6 outer photoreceptors: Baseline quantum efficiency 1.0
- R7/R8 inner photoreceptors: ~30% of R1-R6 efficiency

**Amplification Difference**:
- R1-R6 → Lamina: Signal amplified 5-10× via tetrad synapses (L1/L2/L3)
- R7/R8 → Medulla: Direct projection, NO amplification

**Calculation**:
```
R1-R6 effective gain: 1.0 × (5-10× lamina) = 5-10×
R7/R8 effective gain: 0.3 × (1× direct) = 0.3×
Ratio: 0.3 / 5 = 0.06× to 0.3 / 10 = 0.03×
```

**Implementation**: R7_R8_GAIN = 0.15× (compromise between 0.03× and 0.3×)

---

## Results Interpretation

### 1. Medulla: Partial Success

**Before**: 9.32% ± 6.14% (86% above target upper bound)  
**After**: 7.24% ± 2.43% (44% above target upper bound)  
**Improvement**: 22% reduction in mean sparsity

**Analysis**:
- **Variance improved**: ±6.14% → ±2.43% (60% reduction, more stable)
- **Range improved**: [4.44%, 21.27%] → [4.72%, 10.89%] (narrower distribution)
- **Still too high**: Need 7.24% → 3.5% (midpoint of 2-5%)
- **Further reduction needed**: 7.24 / 3.5 = 2.07× too strong

**Recommendation**: Reduce R7_R8_GAIN from 0.15× to 0.07× 
- Calculation: 0.15 / 2.07 = 0.072 ≈ 0.07
- Expected result: 7.24% × (0.07 / 0.15) = 3.38% ✅ **PASS**

### 2. Lobula: MAJOR CONCERN

**Before**: 2.07% ± 1.42% (90% below revised 15-30% target)  
**After**: 0.61% ± 0.42% (96% below target)  
**Change**: **DECREASED 71%** (made worse!)

**This is unexpected and concerning**:
- Reducing medulla activity should NOT decrease lobula activity
- Lobula receives inputs from medulla - cleaner signal should improve propagation
- 0.61% is extremely sparse, close to complete failure

**Possible causes**:
1. **Threshold effect**: Medulla neurons below activation threshold → no lobula input
2. **Coupling too weak**: Medulla→Lobula connections need much higher gain
3. **Temporal integration missing**: Lobula needs accumulation over time (current 100ms may be too short)
4. **Wrong neuron types**: May not be targeting correct medulla→lobula pathways

---

## Detailed Analysis

### Medulla Sparsity Distribution

| Metric | Before (0.5× gain) | After (0.15× gain) | Change |
|--------|-------------------|-------------------|--------|
| **Mean** | 9.32% | 7.24% | -22% |
| **Std Dev** | ±6.14% | ±2.43% | -60% |
| **Min** | 4.44% | 4.72% | +6% |
| **Max** | 21.27% | 10.89% | -49% |
| **Target** | 2-5% | 2-5% | - |
| **Status** | FAIL (86% high) | FAIL (44% high) | Improved |

**Conclusion**: Gain reduction worked but was insufficient (need 0.15× → 0.07×)

### Lobula Crisis

| Metric | Before (0.5× gain) | After (0.15× gain) | Change |
|--------|-------------------|-------------------|--------|
| **Mean** | 2.07% | 0.61% | **-71%** |
| **Std Dev** | ±1.42% | ±0.42% | -70% |
| **Min** | 0.42% | 0.12% | -71% |
| **Max** | 4.18% | 1.18% | -72% |
| **Target** | 15-30% | 15-30% | - |
| **Status** | FAIL (90% low) | FAIL (96% low) | **WORSE** |

**Conclusion**: Medulla gain reduction caused catastrophic lobula collapse. Requires urgent architectural investigation.

---

## Lobula Failure Root Cause Investigation

### Hypothesis 1: Threshold Effect (Most Likely)
**Theory**: Medulla neurons need >0.5 threshold to be "active". Reducing gain pushes many below threshold.

**Evidence**:
- Medulla mean: 7.24% active (down from 9.32%)
- Lobula depends on medulla inputs
- If medulla neurons at 0.3-0.5 amplitude (sub-threshold), lobula gets no input
- Lobula activity collapsed proportionally more (-71%) than medulla (-22%)

**Test**: Check medulla amplitude distribution (not just binary active/inactive)

### Hypothesis 2: Synaptic Coupling Too Weak
**Theory**: Medulla→Lobula connections use same 10× vision gain, but lobula needs more.

**Evidence**:
- Lamina (tetrad + lateral inhib): 20.87% ✅
- Medulla (direct R7/R8): 7.24% (too high)
- Lobula (from medulla): 0.61% (catastrophically low)
- Lobula Plate (from lobula + medulla): 17.98% ✅

**Question**: Why does Lobula Plate work but Lobula doesn't?
- **Answer**: Lobula Plate receives BOTH lobula AND medulla inputs (bypass pathway)
- Lobula only receives medulla → single point of failure

### Hypothesis 3: Temporal Integration Missing
**Theory**: T4/T5 motion detection requires temporal integration (accumulation over time).

**Evidence**:
- Current simulation: 100ms, threshold at t=100ms only
- Biological T4/T5: Integrate over 50-200ms windows
- May need temporal accumulation, not instantaneous threshold

**Test**: Measure lobula activity at multiple timepoints (not just final)

### Hypothesis 4: Wrong Connectivity
**Theory**: Not targeting correct medulla→lobula pathways.

**Current implementation**: Uses all medulla neurons  
**Biological reality**: Specific medulla neurons (Tm1-4, Mi1, etc.) project to lobula

**Test**: Check if we're using correct medulla neuron types for lobula input

---

## Biological Validation Against Literature

### Medulla Sparsity (7.24%)
**Our result**: 7.24% ± 2.43%  
**Literature**: Limited direct measurements, but:
- Campbell et al. (2013): Mushroom body 2-3% (olfaction reference)
- Medulla performs sparse expansion: 1,600 R7/R8 → 45,885 neurons (29× expansion)
- Expected: 2-5% (similar to PN→KC expansion which is 57× with 1-5% sparsity)

**Conclusion**: 7.24% is close but still 2× too high

### Lobula Sparsity (0.61%)
**Our result**: 0.61% ± 0.42%  
**Literature**: 
- Distributed motion coding (Nature 2024): Should be 15-30%
- T4/T5 direction selectivity: 4 channels × spatial integration = substantial activity
- Lobula Plate (downstream): 17.98% ✅

**Conclusion**: 0.61% is 25-50× too low - catastrophic failure

---

## Next Steps (Priority Order)

### URGENT: Fix Lobula (Priority 1)

**Option A**: Increase Medulla→Lobula Coupling
```python
# In sparse_probabilistic.py, _build_coupling_structure()
# After applying 10× vision gain, add layer-specific boost
if is_medulla_to_lobula_connection:
    self.syn_weights[syn_idx] *= 50.0  # Aggressive 50× boost
```

**Rationale**:
- Lobula at 0.61%, needs ~30× increase to reach 15-30% target
- Add safety margin: 50× boost
- Expected: 0.61% × 50 = 30.5% ✅

**Option B**: Reduce Threshold for Lobula
```python
# In test_sparse_coding.py, measure sparsity
if region == 'LOBULA':
    active = np.sum(amplitudes > 0.1)  # Lower threshold from 0.5 to 0.1
```

**Rationale**:
- Lobula integrates weak signals
- May be biologically active at lower amplitudes
- Test if this brings lobula into 15-30% range

**Option C**: Add Temporal Integration
- Measure activity at multiple timepoints
- Use max or average amplitude over time window
- More biologically realistic for motion detection

### Secondary: Fine-tune Medulla (Priority 2)

**After lobula fixed**, reduce R7_R8_GAIN:
- Current: 0.15×, result: 7.24%
- Target: 0.07×, expected: 3.38% ✅

---

## Updated Layer Status

| Layer | Sparsity | Target | Status | Priority |
|-------|----------|--------|--------|----------|
| **Lamina** | 20.87% | 20-40% | ✅ PASS | None (working) |
| **Medulla** | 7.24% | 2-5% | ⚠️ Close | P2 (reduce to 0.07× gain) |
| **Lobula** | 0.61% | 15-30% | 🚨 CRITICAL | **P1 (needs 50× boost)** |
| **Lobula Plate** | 17.98% | 10-20% | ✅ PASS | None (working) |

---

## Biological Justification Summary

### R7/R8 Gain Reduction (0.5× → 0.15×)

**Measurements**:
1. **Salcedo et al. (1999)**: R7/R8 quantum efficiency ~30% of R1-R6
2. **Stavenga et al. (2020)**: R7/R8 narrower spectral tuning, lower peak sensitivity
3. **No lamina amplification**: R1-R6 get 5-10× boost via L1/L2/L3 tetrad synapses

**Result**: Medulla improved from 9.32% to 7.24% (22% reduction), but still 44% above target

**Next step**: Further reduce to 0.07× for 3.38% expected result

### Lobula Distributed Coding (15-30% Target)

**Evidence**:
1. **Nature (2024)**: "Combinatorial population codes" in visual motion processing
2. **eLife (2024)**: Distributed optic flow representation in lobula plate
3. **T4/T5 function**: 4 direction channels require substantial population activity

**Result**: Our 0.61% is 25-50× too low, indicating architectural problem

**Conclusion**: Lobula needs dramatic coupling increase (50× boost) or architectural changes

---

## Performance

- **Simulation time**: 7.8 seconds for 5 stimuli × 100ms
- **Average per stimulus**: 1.56 seconds
- **GPU acceleration**: Active (MLX)
- **Improvement from before**: Slightly faster (was 8.3s)

---

## Files Modified

1. **hive/validation/vision/test_sparse_coding.py**:
   - Added `R7_R8_GAIN = 0.15` constant (line 39)
   - Updated R7/R8 forcing: `* 0.5` → `* R7_R8_GAIN` (6 locations)
   - Updated lobula target: `(10, 20)` → `(15, 30)` (line 373)

2. **research/vision/findings/LOBULA_CODING_INVESTIGATION.md** (NEW):
   - 400+ lines documenting distributed vs sparse coding
   - Biological justification for 15-30% lobula target
   - Cross-species comparisons

3. **research/vision/findings/MEDULLA_LOBULA_FINE_TUNING.md** (THIS FILE)

---

## Recommendations

### Immediate Action (Today)
1. **Implement Option A**: Add 50× medulla→lobula coupling boost
2. **Test result**: Expect lobula 0.61% → 30% ✅
3. **Verify lobula plate doesn't oversaturate** (currently 17.98%, should stay <40%)

### Follow-up Action (After lobula fixed)
1. **Fine-tune medulla**: R7_R8_GAIN 0.15× → 0.07×
2. **Expected**: Medulla 7.24% → 3.38% ✅
3. **Run full 41 stimuli** (currently only 5)

### Long-term Validation
1. **Cross-validate** with decorrelation test
2. **Cross-validate** with contrast invariance test
3. **Test motion detection** (T4/T5 direction selectivity)
4. **Compare to 2024 Nature connectomics papers**

---

## Conclusion

**Medulla**: Partial success - gain reduction worked but needs further tuning (0.15× → 0.07×)

**Lobula**: Critical failure - activity collapsed from 2.07% to 0.61% (-71%). Root cause likely threshold effect combined with weak coupling. Requires urgent architectural fix (50× coupling boost).

**Overall**: The R7/R8 gain reduction was biologically justified and improved medulla stability, but revealed a critical weakness in medulla→lobula connectivity that must be addressed before claiming full validation success.

**Status**: 2/4 layers passing. Need lobula fix to achieve 3/4, then medulla fine-tune for 4/4 (100%) validation.

---

**Next file to create**: Implementation of medulla→lobula coupling boost in `sparse_probabilistic.py`
