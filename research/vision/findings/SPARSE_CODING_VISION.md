# Sparse Coding in Vision

**Test**: Medulla Sparsity Measurement  
**Status**: Test implemented, awaiting experimental results  
**Date**: 2026-03-17

---

## Hypothesis

Visual system should produce sparse firing patterns similar to olfaction (1.65% KC sparsity), with medulla neurons exhibiting 2-5% sparsity.

---

## Background

### Biological Evidence

**Campbell et al. (2013)** - "Imaging a Population Code for Odor Identity in the Drosophila Mushroom Body"
- Measured **3-8% medulla sparsity** in vivo using calcium imaging
- Similar sparse expansion mechanism as olfactory system
- Supports pattern separation for visual discrimination

### Circuit Architecture

```
Photoreceptors (R1-R8) → Lamina (~5,000 neurons)
        ↓
    Sparse Expansion (8× expansion)
        ↓
    Medulla (~40,000 neurons)
        ↓ (sparse codes)
    Lobula / Lobula Plate
```

**Key features**:
- **8× expansion**: Lamina 5K → Medulla 40K (vs olfaction 2.4×)
- **Random connectivity**: Similar to PN→KC wiring
- **High threshold**: Requires coincident inputs
- **Global inhibition**: APL-like normalization

---

## Predictions

### By Region

| Region | Predicted Sparsity | Reasoning |
|--------|-------------------|-----------|
| **Lamina** | 20-40% | Early processing, less sparse |
| **Medulla** | 2-5% | Sparse expansion, target benchmark |
| **Lobula** | 10-20% | Motion integration |
| **Lobula Plate** | 10-20% | Wide-field motion |

### Comparison to Olfaction

| System | Input | Expansion | Sparsity |
|--------|-------|-----------|----------|
| **Olfaction** | 2,198 PNs | → 5,279 KCs (2.4×) | 1.65% |
| **Vision** | ~5K lamina | → 40K medulla (8×) | 2-5% (predicted) |

Larger expansion → potentially lower sparsity (more neurons to distribute across)

---

## Method

### Test Protocol

1. **Load visual connectome** (~53,000 neurons from FlyWire)
2. **Generate stimuli**: 40 pure wavelengths (300-700nm)
3. **Simulate each stimulus** (100ms, wave-based physics)
4. **Measure sparsity** per region:
   - Count active neurons (amplitude > 0.5 threshold)
   - Compute % = (active / total) × 100

### Implementation

File: `hive/validation/vision/test_sparse_coding.py`

```python
def test_sparse_coding_vision(visual_connectome, stimuli):
    brain = SparseProbabilisticBrain(visual_connectome)
    
    for region in ['LAMINA', 'MEDULLA', 'LOBULA', 'LOBULA_PLATE']:
        neurons = get_visual_region_neurons(connectome, region)
        
        for stimulus in stimuli:
            # Simulate
            brain.step(forcing)
            
            # Measure sparsity
            active = sum(amplitudes > 0.5)
            sparsity = 100.0 * active / len(neurons)
```

---

## Target Benchmarks

### Primary Target: Medulla
- **Campbell et al. (2013)**: 3-8% in vivo
- **Our target**: 2-5% (conservative estimate)
- **Pass criteria**: Mean sparsity in [2%, 5%] range

### Secondary Targets
- Lamina: 20-40% (early processing)
- Lobula/LP: 10-20% (motion integration)

---

## Expected Results

### If Test Passes (2-5% medulla sparsity)

**Implications**:
1. Wave physics produces sparse codes in vision
2. Same mechanism as olfaction (expansion + threshold)
3. Validates scalability (53K neurons vs 10K olfactory)

### If Test Fails

**Possible causes**:
- Forcing magnitude calibration needed
- Threshold adjustment required
- Different normalization mechanism in vision vs olfaction

**Next steps**: Systematic parameter sweep

---

## Mechanistic Understanding

### Why Sparse Coding Emerges

**Three key factors** (same as olfaction):

1. **Expansion ratio**: 8× lamina→medulla
   - More neurons than inputs
   - Competition for activation

2. **Random connectivity**: 
   - Each medulla neuron samples ~N lamina neurons
   - Requires coincident inputs to fire
   - Combinatorial explosion of possible patterns

3. **High firing threshold**:
   - Wave amplitude must exceed threshold
   - Only strong, coherent inputs activate neurons
   - Weak/noisy inputs suppressed

### Information Theory

**Sparse codes provide**:
- **Higher capacity**: More distinguishable patterns
- **Energy efficiency**: Fewer spikes = less ATP
- **Noise robustness**: Clear signal/noise separation

**Kanerva (1988)** - Sparse Distributed Memory:
- 2% sparsity → ~7,000 stored patterns
- vs 50% dense → ~200 patterns
- **35× capacity improvement**

---

## Comparison to Olfaction

### Olfaction Results (Validated)
- KC sparsity: **1.65%** ✅
- Target: 1-3% (Turner et al. 2008)
- Mechanism: PN→KC expansion (2.4×) + APL inhibition

### Vision Predictions
- Medulla sparsity: **2-5%** (target)
- Expansion: Lamina→Medulla (8×, larger than olfaction)
- Mechanism: Similar random connectivity + normalization

### Key Question
Does **larger expansion (8× vs 2.4×)** produce:
- A) Lower sparsity (more neurons available)?
- B) Similar sparsity (threshold scales with expansion)?

**Answer pending experimental validation.**

---

## Files

### Test Implementation
- `hive/validation/vision/test_sparse_coding.py` - 206 lines
- Uses `SparseProbabilisticBrain` engine (same as olfaction)
- Measures sparsity across 4 visual regions

### Results Documentation
- This file (awaiting results)
- Will add quantitative measurements after experiments

---

## Next Steps

1. **Run test**:
   ```bash
   python hive/validation/vision/test_sparse_coding.py
   ```

2. **Analyze results** by region

3. **Compare to benchmarks** (Campbell 2013)

4. **Document findings** in this file

5. **Update POC status** based on pass/fail

---

## References

- Campbell et al. (2013) - Visual sparsity benchmark: 3-8%
- Turner et al. (2008) - Olfactory KC sparsity: 1-3%
- Kanerva (1988) - Sparse distributed memory theory
- Olshausen & Field (1996) - Sparse coding principle
- This project - Olfaction validation: 1.65% ✅

---

**Status**: ✅ Test implemented  
**Next**: Execute and record results
