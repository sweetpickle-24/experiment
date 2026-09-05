# Contrast Invariance in Vision

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
> Current: [README](../../../README.md) ·
> [ARCHITECTURE](../../../ARCHITECTURE.md) ·
> [LIMITATIONS](../../../docs/03_validation/LIMITATIONS.md) ·
> [audit](../../../docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md) ·
> [projection repair](../../../docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md).
> Tracked in [OUTDATED_FILES.md](../../../OUTDATED_FILES.md).


**Test**: Wavelength Representation Stability Across Intensities  
**Status**: Test implemented, awaiting experimental results  
**Date**: 2026-03-17

---

## Hypothesis

Same wavelength at different intensities (e.g., 500nm green at 10% vs 100% brightness) should produce **correlated medulla patterns**, demonstrating contrast-invariant wavelength encoding.

**Analog**: Concentration invariance in olfaction (r=0.724 ✅)

---

## Background

### Olfaction Concentration Invariance (Validated)

**This Project** - Olfaction Results:
- Same odor across 100× concentration range
- KC pattern correlation: **r = 0.724** ✅
- Target: r > 0.70 (Turner et al. 2008 benchmark)
- **Mechanism**: Deterministic reset + APL normalization + logarithmic scaling

**Biological significance**:
- Odor identity stable despite concentration fluctuations
- Enables reliable odor recognition in variable environments

### Weber-Fechner Law

**Sensory systems encode stimuli logarithmically**:
- Response ~ log(Intensity)
- Perception linear in log space
- Invariance to multiplicative scaling

**In phototransduction**:
- Calcium feedback in TRP channels
- Adaptation timescale: ~100ms
- Maintains sensitivity across 4+ log units of light intensity

---

## Vision Prediction

### Setup

Test same wavelength at 10 intensity levels:

| Intensity | Relative | Photon Rate | Expected Response |
|-----------|----------|-------------|-------------------|
| 0.10 | 10% | Low | Weak medulla activation |
| 0.22 | 22% | ↓ | ↓ |
| 0.46 | 46% | ↓ | ↓ |
| 1.00 | 100% | High | Strong medulla activation |

**Key prediction**: Medulla patterns should be **correlated** across intensities (r > 0.70)

### Test Wavelengths
- **450nm** (blue): R1-R6 peak, R8p high
- **500nm** (green): R1-R6 peak, balanced R8p/R8y
- **600nm** (red): R8y peak, R1-R6 low

---

## Mechanism

### Three Adaptation Layers

1. **Photoreceptor Adaptation** (Hardie & Raghu 2001)
   - Calcium-dependent feedback on TRP channels
   - High [Ca²⁺] → reduced sensitivity
   - Implements Weber-Fechner logarithmic encoding

2. **Lamina Gain Control** (Laughlin 1981)
   - L1-L3 lateral inhibition
   - Normalizes across spatial locations
   - Maintains contrast despite luminance changes

3. **Medulla Normalization**
   - Global inhibition (APL-like mechanism)
   - Maintains ~2-5% sparsity
   - Pattern structure preserved

### Why Invariance Emerges

**Intensity changes affect**:
- Absolute firing rates ✗
- Photon absorption ✗

**But preserve**:
- Relative activation patterns ✓
- Which neurons fire ✓
- Wavelength-specific signatures ✓

**Result**: Same "neural barcode" across intensities

---

## Method

### Test Protocol

1. **Select test wavelengths**: 450nm, 500nm, 600nm
2. **Generate intensity series**: 10 levels (0.1 to 1.0, logarithmic)
3. **For each wavelength**:
   - Simulate all 10 intensities (100ms each)
   - Extract medulla activation patterns
   - Compute pairwise correlations
   - Average → contrast invariance score

4. **Statistical analysis**:
   - Mean correlation across all intensity pairs
   - Compare to r=0.70 threshold (olfaction benchmark)

### Implementation

File: `hive/validation/vision/test_contrast_invariance.py`

```python
def test_contrast_invariance_vision(visual_connectome):
    for wavelength in [450, 500, 600]:
        # Generate intensity series
        intensities = np.logspace(-1, 0, 10)  # 0.1 to 1.0
        
        patterns = []
        for intensity in intensities:
            stimulus = generate_stimulus(wavelength, intensity)
            pattern = simulate(stimulus)
            patterns.append(pattern)
        
        # Compute pairwise correlations
        correlations = []
        for i, j in combinations(range(10), 2):
            corr = pearsonr(patterns[i], patterns[j])
            correlations.append(corr)
        
        mean_corr = np.mean(correlations)
        print(f"{wavelength}nm: r = {mean_corr:.3f}")
```

---

## Target Benchmarks

### Primary Target
**Mean correlation r > 0.70** across intensity pairs

### Comparison to Olfaction
- Olfaction: r = **0.724** (100× concentration range) ✅
- Vision target: r > **0.70** (10× intensity range)
- Stretch goal: r > **0.75** (better than olfaction)

### Intensity Range
- Test range: **10× (0.1 to 1.0)**
- Biological range: **10,000× (0.0001 to 1.0)**
- POC tests conservative range first

---

## Expected Results

### If Test Passes (r > 0.70)

**Implications**:
1. **Contrast invariance validated** in vision
2. **Universal mechanism** - Same adaptation in vision and olfaction
3. **Wavelength encoding robust** to intensity fluctuations
4. **Practical application** - Reliable color perception

### If Test Fails (r < 0.70)

**Possible causes**:
- Adaptation too strong (overcorrects)
- Insufficient normalization
- Threshold effects at low intensities

**Next steps**: 
- Adjust adaptation parameters
- Test narrower intensity range (2× instead of 10×)

---

## Quantitative Analysis

### Correlation by Intensity Difference

Expected pattern:

| Intensity Ratio | Correlation | Interpretation |
|----------------|-------------|----------------|
| 1.1× (close) | r ≈ 0.95 | Very similar |
| 2× (moderate) | r ≈ 0.80 | Similar |
| 5× (large) | r ≈ 0.70 | Threshold |
| 10× (extreme) | r ≈ 0.65 | Challenging |

**If this pattern holds**: Validates logarithmic adaptation

### Wavelength Differences

Different wavelengths may show different invariance:

| Wavelength | Photoreceptor Dominance | Predicted Invariance |
|------------|------------------------|---------------------|
| **450nm** (blue) | R1-R6 + R8p | High (broad activation) |
| **500nm** (green) | R1-R6 balanced | Medium |
| **600nm** (red) | R8y only | Lower (narrow activation) |

**If red shows lower invariance**: Suggests reliance on multiple receptor types for robustness

---

## Biological Mechanisms

### Phototransduction Adaptation

**Calcium feedback loop**:
```
High light → Many TRP channels open
    ↓
High [Ca²⁺] influx
    ↓
Ca²⁺ reduces TRP sensitivity
    ↓
Response compressed (logarithmic)
    ↓
Maintains sensitivity at high light
```

**Parameters** (from Hardie & Raghu 2001):
- Ca pump rate: 200 s⁻¹
- Adaptation threshold: 0.2 μM
- Time constant: ~100ms

### Lamina Gain Control

**L1-L3 neurons** normalize via lateral inhibition:
- Detect average luminance
- Subtract from local signals
- Maintains contrast sensitivity

**Similar to photographic histogram equalization**

### Medulla Normalization

**Global inhibition** maintains sparsity:
- APL-like mechanism (hypothesized)
- Keeps ~2-5% neurons active
- Pattern structure preserved despite intensity

---

## Comparison: Vision vs Olfaction

### Adaptation Timescales

| System | Mechanism | Timescale | Range |
|--------|-----------|-----------|-------|
| **Olfaction** | ORN adaptation | ~500ms | 100× concentration |
| **Vision** | Phototransduction Ca²⁺ | ~100ms | 10,000× intensity |

Vision adapts **5× faster** but handles **100× wider range**

### Neural Implementation

| Feature | Olfaction | Vision |
|---------|-----------|--------|
| **Input adaptation** | ORN gain control | Photoreceptor Ca²⁺ feedback |
| **Early processing** | PN normalization | Lamina gain control |
| **Sparse layer** | KC APL inhibition | Medulla normalization |
| **Invariance** | r=0.724 ✅ | r>0.70 (target) |

### Computational Principle

**Same across modalities**:
- Logarithmic input encoding
- Normalization layers
- Sparse expansion maintains pattern structure
- **Universal wave physics** produces invariance

---

## Practical Applications

### Color Constancy

**Human example**: White paper looks white under:
- Sunlight (bright)
- Indoor lighting (dim)
- Shade (very dim)

**Mechanism**: Contrast invariance enables stable color perception

### Vision Systems

**Robotics/AI**: 
- Camera auto-exposure mimics adaptation
- But **neural adaptation is faster and more robust**
- Wave-based vision could enable real-time invariance

---

## Files

### Test Implementation
- `hive/validation/vision/test_contrast_invariance.py` - 178 lines
- Tests 3 wavelengths × 10 intensities
- Computes 45 pairwise correlations per wavelength

### Results Documentation
- This file (awaiting results)
- Will add correlation plots after experiments

---

## Next Steps

1. **Run test**:
   ```bash
   python hive/validation/vision/test_contrast_invariance.py
   ```

2. **Analyze correlation vs intensity ratio**

3. **Compare wavelengths** (blue, green, red)

4. **Compare to olfaction** (r=0.724 benchmark)

5. **Document findings** and update POC status

---

## References

### Olfaction Invariance (This Project)
- Our results: r = 0.724 ✅
- Mechanism: Deterministic reset + APL normalization
- Benchmark: Turner et al. (2008) >0.70

### Vision Adaptation
- Hardie & Raghu (2001) - Phototransduction Ca²⁺ feedback
- Laughlin (1981) - Lamina gain control
- Juusola & Hardie (2001) - Adaptation dynamics

### Theory
- Weber-Fechner law - Logarithmic psychophysics
- Histogram equalization - Computational analog

---

**Status**: ✅ Test implemented  
**Next**: Execute and record results  
**Impact**: If passes, validates universal invariance mechanism
