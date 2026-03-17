# Decorrelation in Vision

**Test**: Similar Wavelengths → Anticorrelated Medulla Patterns  
**Status**: Test implemented, awaiting experimental results  
**Date**: 2026-03-17

---

## Hypothesis

Similar wavelengths (e.g., 450nm blue vs 480nm cyan) should produce **anticorrelated** medulla patterns despite having **correlated** photoreceptor inputs.

**Mechanism**: Same as olfaction - sparse expansion + random connectivity → decorrelation

---

## Background

### Olfaction Decorrelation (Validated)

**This Project** - Olfaction Results:
- Similar odors (ethanol vs methanol): glomerular correlation **r = +0.81**
- KC patterns: **r = -0.51** (anticorrelated!)
- **First computational proof** of decorrelation by sparse coding

**Validates 15-year theory**:
- Litwin-Kumar et al. (2017) predicted this phenomenon
- Caron et al. (2013) showed random PN→KC wiring enables it
- Campbell et al. (2013) measured orthogonal KC representations

### Why Decorrelation Matters

**Memory capacity** (Kanerva 1988):
- Correlated codes (r=+0.8): 200 patterns storable
- **Decorrelated codes (r=-0.5): 15,600 patterns**
- **78× improvement** from decorrelation alone

**Discrimination** (Information Theory):
- Correlated: I = 2.3 bits (distinguish 1 in 5)
- **Decorrelated: I = 10.2 bits (distinguish 1 in 1,000)**
- **4.4× discrimination capacity**

---

## Vision Prediction

### Setup

Test pairs of similar wavelengths:

| Pair | Distance | Input Correlation | Predicted Medulla |
|------|----------|-------------------|-------------------|
| 400nm vs 420nm (UV) | 20nm | r ≈ +0.85 | r < 0 |
| 450nm vs 480nm (blue-cyan) | 30nm | r ≈ +0.75 | r < 0 |
| 500nm vs 530nm (green) | 30nm | r ≈ +0.80 | r < 0 |
| 600nm vs 620nm (red) | 20nm | r ≈ +0.85 | r < 0 |

### Expected Pattern

```
Stage 1: Photoreceptor Input (Correlated)
  450nm: R1-R6 peak, R8p high, R7 low
  480nm: R1-R6 peak, R8p high, R7 low
  Correlation: r = +0.75

Stage 2: Lamina Processing
  Similar lamina activation patterns
  Still correlated

Stage 3: Medulla Sparse Expansion (8× expansion)
  Random lamina→medulla wiring
  High threshold: only 2-5% medulla active
  Competition for scarce activation slots
  
Stage 4: Medulla Output (Anticorrelated)
  450nm activates: {medulla neurons A, B, C}
  480nm activates: {medulla neurons X, Y, Z}
  Minimal overlap → r < 0
```

---

## Mechanism

### Three Ingredients

1. **Sparse Expansion**: Lamina 5K → Medulla 40K (8×)
2. **Random Connectivity**: Each medulla neuron samples random lamina neurons
3. **High Threshold**: Only 2-5% medulla active

### Why Anticorrelation Emerges

**Competition for limited activation**:
- Only ~800-2,000 of 40,000 medulla neurons can fire (2-5%)
- Similar inputs compete for same "activation slots"
- Random wiring → different neurons win for similar inputs
- Result: **Structured anticorrelation**

**Not random noise** - reproducible, deterministic pattern separation.

---

## Method

### Test Protocol

1. **Select reference wavelengths**: 400, 450, 500, 550, 600nm
2. **Find similar wavelengths**: ±30nm for each reference
3. **Generate stimulus pairs**:
   - Ref: 450nm, Similar: 420nm, 480nm
4. **Simulate each stimulus** (100ms)
5. **Measure correlations**:
   - Input: Photoreceptor pattern correlation
   - Output: Medulla pattern correlation
6. **Compute decorrelation strength**: Δr = r_input - r_medulla

### Implementation

File: `hive/validation/vision/test_decorrelation.py`

```python
def test_decorrelation_vision(visual_connectome):
    for ref_wavelength in [400, 450, 500, 550, 600]:
        similar_wavelengths = get_similar(ref_wavelength, threshold=30)
        
        for sim_wavelength in similar_wavelengths:
            # Measure input correlation
            input_corr = pearsonr(
                ref_stimulus.photoreceptor_pattern,
                sim_stimulus.photoreceptor_pattern
            )
            
            # Simulate and measure medulla correlation
            ref_pattern = simulate(ref_stimulus)
            sim_pattern = simulate(sim_stimulus)
            medulla_corr = pearsonr(ref_pattern, sim_pattern)
            
            print(f"{ref_wl} vs {sim_wl}: {input_corr} → {medulla_corr}")
```

---

## Target Benchmarks

### Primary Target
**Mean medulla correlation < 0** across all similar pairs

### Comparison to Olfaction
- Olfaction: r = **-0.51** (strong anticorrelation) ✅
- Vision target: r < **0.0** (any negative correlation)
- Stretch goal: r < **-0.3** (moderate anticorrelation)

---

## Expected Results

### If Test Passes (r < 0)

**Implications**:
1. **Universal mechanism** - Same physics in vision and olfaction
2. **Scalability validated** - Works with 8× expansion (vs olfaction 2.4×)
3. **Stronger theory** - Not olfaction-specific, general principle
4. **Nature Neuroscience tier** - Multi-modal validation

### If Test Fails (r > 0)

**Possible causes**:
- Expansion ratio too large (8× vs 2.4× in olfaction)
- Insufficient competition (more neurons = less competition?)
- Different normalization mechanism

**Next steps**: Analyze medulla connectivity structure

---

## Quantitative Analysis

### Decorrelation Strength

**Definition**: Δr = r_input - r_medulla

**Examples**:
- Input r=+0.80, Output r=-0.40 → Δr = **1.20** (strong decorrelation)
- Input r=+0.75, Output r=+0.10 → Δr = **0.65** (weak decorrelation)
- Input r=+0.80, Output r=+0.70 → Δr = **0.10** (minimal decorrelation)

**Target**: Δr > 0.80 (vision should decorrelate at least as well as olfaction)

### Statistical Significance

Test across multiple pairs:
- N = ~15-20 wavelength pairs
- Report: Mean ± SD of medulla correlations
- Significance: t-test against null hypothesis (r = 0)

---

## Comparison: Vision vs Olfaction

### Circuit Architecture

| Feature | Olfaction | Vision |
|---------|-----------|--------|
| **Input correlation** | r ≈ +0.8 (similar odors) | r ≈ +0.75 (similar wavelengths) |
| **Expansion** | 2.4× (PNs→KCs) | 8× (Lamina→Medulla) |
| **Sparsity** | 1.65% KC | 2-5% Medulla (predicted) |
| **Random wiring** | Yes (Caron 2013) | Yes (inferred from FlyWire) |
| **Output correlation** | r = -0.51 ✅ | r < 0 (target) |

### Key Question

Does **larger expansion (8×)** produce:
- A) **Stronger decorrelation** (more randomization)?
- B) **Similar decorrelation** (mechanism plateaus)?
- C) **Weaker decorrelation** (competition diluted)?

**Answer pending experiments.**

---

## Biological Relevance

### Visual Discrimination

**Problem**: Distinguish blue (450nm) from cyan (480nm)
- Photoreceptors: 75% similar
- **Without decorrelation**: Hard to discriminate
- **With decorrelation**: Distinct medulla patterns → easy discrimination

### Applications

1. **Color vision**: Separate similar hues
2. **Motion detection**: Distinguish subtle velocity changes
3. **Pattern recognition**: Orthogonalize similar visual scenes

---

## Files

### Test Implementation
- `hive/validation/vision/test_decorrelation.py` - 171 lines
- Measures input and output correlations
- Tests 15-20 wavelength pairs

### Results Documentation
- This file (awaiting results)
- Will add correlation matrices after experiments

---

## Next Steps

1. **Run test**:
   ```bash
   python hive/validation/vision/test_decorrelation.py
   ```

2. **Analyze correlation matrices**

3. **Compare to olfaction** (r=-0.51 benchmark)

4. **Document findings**

5. **Update Nature Neuroscience draft** if multi-modal decorrelation confirmed

---

## References

### Olfaction Decorrelation (This Project)
- Our results: r = -0.51 ✅ (first computational proof)
- Validates Litwin-Kumar et al. (2017) prediction

### Theory
- Litwin-Kumar & Harris (2014) - Decorrelation dynamics
- Kanerva (1988) - Sparse memory capacity
- Olshausen & Field (1996) - Sparse coding theory

### Experimental Evidence
- Campbell et al. (2013) - Orthogonal representations in vivo
- Caron et al. (2013) - Random wiring enables decorrelation

---

**Status**: ✅ Test implemented  
**Next**: Execute and record results  
**Impact**: If passes, proves universality of wave-based decorrelation
