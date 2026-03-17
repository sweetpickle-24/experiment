# Vision Validation Suite

**Purpose**: Validate wave-based physics in vision system  
**Date**: 2026-03-17  
**Status**: Tests implemented, ready to run

---

## Validation Framework

Similar to olfaction validation (8/9 tests passed), vision tests check if wave physics produces biologically realistic phenomena.

### Core Hypothesis

Wave-based probabilistic dynamics on FlyWire connectome should produce:
1. Sparse coding (2-5% medulla activity)
2. Decorrelation (similar inputs → anticorrelated outputs)
3. Contrast invariance (stable across intensities)
4. Motion detection (T4/T5 direction selectivity)

---

## Test Suite Overview

| Test | Target | Benchmark | Status |
|------|--------|-----------|--------|
| **Sparse Coding** | Medulla 2-5% active | Campbell 2013: 3-8% | ✅ Implemented |
| **Decorrelation** | r < 0 for similar wavelengths | Olfaction: r=-0.51 | ✅ Implemented |
| **Contrast Invariance** | r > 0.70 across intensities | Olfaction: r=0.724 | ✅ Implemented |
| **Motion Detection** | DSI > 0.3 | Borst & Euler 2011 | ✅ Implemented |

---

## Test 1: Sparse Coding

### Objective
Measure firing sparsity in visual pathway regions.

### Prediction
- **Lamina**: 20-40% active (early processing, less sparse)
- **Medulla**: 2-5% active (sparse expansion, key target)
- **Lobula/LP**: 10-20% active (motion integration)

### Method
1. Generate 40 pure wavelength stimuli
2. Simulate each through optic lobe (100ms)
3. Measure % active neurons per region (threshold > 0.5)
4. Compare medulla to Campbell et al. (2013) benchmark

### Target Benchmark
Campbell et al. (2013) measured **3-8% medulla sparsity** in vivo calcium imaging.

### Pass Criteria
Medulla sparsity in range [2%, 5%]

### File
`hive/validation/vision/test_sparse_coding.py`

---

## Test 2: Decorrelation

### Objective
Test if similar wavelengths produce anticorrelated medulla patterns.

### Prediction
- Input: Similar wavelengths (e.g., 450nm vs 480nm)
- Photoreceptor correlation: r ≈ +0.75 (similar input)
- **Medulla correlation: r < 0** (anticorrelated output)

### Mechanism
Same as olfaction decorrelation:
- Random lamina→medulla connectivity (5K→40K expansion)
- High threshold sparse activation
- Competition for limited activation slots → anticorrelation

### Method
1. Select reference wavelengths (400, 450, 500, 550, 600nm)
2. For each, find similar wavelengths (±30nm)
3. Simulate pairs, measure input and medulla correlations
4. Compute decorrelation strength: Δr = r_input - r_medulla

### Target Benchmark
Olfaction achieved **r = -0.51** (similar odors → anticorrelated KCs).  
Vision target: **r < 0** (any negative correlation)

### Pass Criteria
Mean medulla correlation < 0 across all pairs

### File
`hive/validation/vision/test_decorrelation.py`

---

## Test 3: Contrast Invariance

### Objective
Test if wavelength representation is stable across intensity changes.

### Prediction
Same wavelength at different intensities should produce correlated medulla patterns (analog to concentration invariance in olfaction).

### Method
1. Select test wavelengths (450nm, 500nm, 600nm)
2. For each, generate 10 intensity levels (0.1-1.0, logarithmic)
3. Simulate all intensities
4. Compute pairwise correlations across intensities
5. Average correlation = contrast invariance score

### Target Benchmark
Olfaction achieved **r = 0.724** for concentration invariance.  
Vision target: **r > 0.70**

### Mechanisms Tested
- Photoreceptor adaptation (calcium feedback in TRP channels)
- Lamina gain control (L1-L3 lateral inhibition)
- Medulla normalization (APL-like global inhibition)

### Pass Criteria
Mean correlation > 0.70 across all intensity pairs

### File
`hive/validation/vision/test_contrast_invariance.py`

---

## Test 4: Motion Detection

### Objective
Test if T4/T5 neurons exhibit direction selectivity.

### Prediction
T4/T5 neurons should respond preferentially to specific temporal directions (forward vs backward wavelength sweeps).

### Method
1. Generate temporal sequences:
   - **Forward**: 400nm → 500nm (11 frames, 50ms each)
   - **Backward**: 500nm → 400nm
   - **Stationary**: 450nm (control)

2. Simulate each sequence
3. Measure T4/T5 activation per frame
4. Compute Direction Selectivity Index (DSI):
   - DSI = |forward - backward| / (forward + backward)
   - Motion enhancement = mean(forward, backward) / stationary

### Target Benchmark
Borst & Euler (2011): T4/T5 neurons show strong direction tuning (DSI > 0.5).  
Vision target: **DSI > 0.3** (moderate selectivity)

### Pass Criteria
- DSI > 0.3
- Motion enhancement > 1.2× over stationary

### File
`hive/validation/vision/test_motion_detection.py`

---

## Validation Protocol

### Setup
```bash
# 1. Extract optic lobe (one-time)
python hive/vision/optic_lobe_extractor.py

# 2. Verify extraction
ls -lh data/vision/optic_lobe/flywire_optic_lobe.json
```

### Run Tests
```bash
# Individual tests
python hive/validation/vision/test_sparse_coding.py
python hive/validation/vision/test_decorrelation.py
python hive/validation/vision/test_contrast_invariance.py
python hive/validation/vision/test_motion_detection.py
```

### Expected Runtime
- Optic lobe extraction: ~5 minutes (one-time)
- Each validation test: ~10-30 minutes (depends on GPU)
- Total validation suite: ~1-2 hours

---

## Success Criteria

### Minimum Success (3/4 tests)
Validates wave physics universality across sensory modalities

### Ideal Success (4/4 tests)
Strengthens Nature Neuroscience multi-modal submission

### Comparison to Olfaction
- Olfaction: 8/9 tests (89%)
- Vision target: ≥3/4 tests (75%)

---

## Results Documentation

After running tests, document results in:
- `SPARSE_CODING_VISION.md` - Sparsity measurements by region
- `DECORRELATION_VISION.md` - Decorrelation strength analysis
- `CONTRAST_INVARIANCE.md` - Invariance correlation scores
- `research/vision/validation/VALIDATION_RESULTS.md` - Summary

---

## Implementation Notes

### Test Infrastructure
- All tests use `SparseProbabilisticBrain` engine (same as olfaction)
- Photoreceptor input converted to lamina forcing
- Medulla patterns extracted for analysis
- Results saved to JSON for reproducibility

### Performance
- GPU acceleration via MLX (M4 Pro)
- ~53,000 neurons: expect 5-10s per 100ms simulation
- Memory: ~300 MB (still efficient vs dense alternatives)

---

## References

### Benchmarks
- Campbell et al. (2013) - Medulla sparsity: 3-8%
- Borst & Euler (2011) - T4/T5 direction selectivity
- Olfaction validation suite (this project) - Decorrelation r=-0.51

### Methods
- Hardie & Raghu (2001) - Phototransduction kinetics
- Stavenga et al. (2020) - Photoreceptor spectral sensitivity
- FlyWire Consortium (2024) - Connectome structure

---

**Status**: ✅ All tests implemented, ready to execute  
**Next**: Run experiments and document findings
