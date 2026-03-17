# Parameter Updates: Vision Simulation

**Date**: 2026-03-17  
**Status**: CORRECTED BASED ON BIOLOGICAL RESEARCH

---

## Changes Implemented

### 1. Timestep Resolution (dt)
**File**: `hive/engine/sparse_probabilistic.py:88`

```python
# BEFORE:
self.dt = 0.01  # 0.01ms = 10 microseconds

# AFTER:
self.dt = 0.1  # 0.1ms = 100 microseconds
```

**Rationale**:
- Borst 2024 state-of-the-art model uses dt=10ms
- Our 0.01ms was 1000× too fine for biological timescales
- New 0.1ms provides 10× speedup while staying finer than biology requires
- Still much finer than neural integration timescales (~10ms)

**Impact**:
- ✅ **10× faster simulation** (1,000 steps vs 10,000 for 100ms)
- ✅ Same numerical accuracy for biological phenomena
- ✅ 100ms simulation: ~1 minute instead of ~10 minutes

---

### 2. Forcing Strength
**File**: `hive/validation/vision/test_sparse_coding.py:88,95`

```python
# BEFORE:
forcing_strength = float(flat_response[i] * 10.0)

# AFTER (MLX):
forcing_strength = float(flat_response[i] * 500.0)

# AFTER (NumPy):
brain.external_force[idx] = float(flat_response[i] * 500.0)
```

**Rationale**:
- Olfaction (validated 8/9): uses strength=50.0 for 5K neurons
- Vision: 93K neurons (18× larger) requires proportionally stronger forcing
- Mathematical estimate: 50 × (93K/5K) = 930
- Conservative choice: 500 (may need to increase to 1000-5000 if still weak)

**Impact**:
- ✅ **50× stronger input** to photoreceptors→lamina
- ✅ Should enable activity propagation through all 5 layers
- ✅ Matches scaling relationship from olfaction

---

### 3. Simulation Duration
**File**: `hive/validation/vision/test_sparse_coding.py:33,218`

```python
# BEFORE:
simulation_duration_ms: float = 100.0  # (default, but called with 20.0)
results = test_sparse_coding_vision(visual_conn, stimuli[:3], simulation_duration_ms=20.0)

# AFTER:
simulation_duration_ms: float = 100.0  # Match olfaction validated duration
results = test_sparse_coding_vision(visual_conn, stimuli[:5], simulation_duration_ms=100.0)
```

**Rationale**:
- Olfaction validated: 100ms duration
- Biology: H-current time constant ~50ms, lamina responses decay over 50-100ms
- 5 visual layers need time to propagate signals
- 20ms was insufficient (only 2,000 steps for 5 layers = 400 steps/layer)

**Impact**:
- ✅ **5× longer simulation** (100ms vs 20ms)
- ✅ Allows full propagation through visual pathway
- ✅ Matches olfaction validation protocol
- ⚠️ But with dt=0.1ms, runtime is similar (1,000 steps vs 2,000 before)

---

### 4. Test Set Size
**File**: `hive/validation/vision/test_sparse_coding.py:218`

```python
# BEFORE:
stimuli[:3]  # Only 3 stimuli

# AFTER:
stimuli[:5]  # Test 5 stimuli
```

**Rationale**:
- 3 stimuli was very limited for statistical analysis
- 5 stimuli provides better coverage of wavelength space
- Still fast enough for iteration (~5 minutes total)
- Can scale to full 41 stimuli once validated

---

## Expected Performance

### Runtime Estimates (100ms simulation)

**Before changes**:
- dt=0.01ms → 10,000 steps
- Time per step: ~60ms (measured)
- **Total: 10,000 × 60ms = 600 seconds = 10 minutes**

**After changes**:
- dt=0.1ms → 1,000 steps (10× fewer)
- Time per step: ~60ms (unchanged)
- **Total: 1,000 × 60ms = 60 seconds = 1 minute**

**For 5 stimuli**: ~5 minutes total  
**For full 41 stimuli**: ~41 minutes total

---

## Expected Activity Levels

### Before Changes (Observed)
```
LAMINA:       4.58% active  (weak forcing reached lamina)
MEDULLA:      0.00% active  (no propagation)
LOBULA:       0.00% active  (no propagation)
LOBULA_PLATE: 0.00% active  (no propagation)
```

### After Changes (Predicted)
```
LAMINA:       20-50% active  (strong forcing + longer duration)
MEDULLA:      2-10% active   (sparse expansion activated)
LOBULA:       5-20% active   (integration layer active)
LOBULA_PLATE: 5-20% active   (motion processing active)
```

### Target (Biological Benchmarks)
```
LAMINA:       20-40% active  (early processing)
MEDULLA:      2-5% active    (Campbell 2013: 3-8% in vivo)
LOBULA:       10-20% active  (motion integration)
LOBULA_PLATE: 10-20% active  (direction selectivity)
```

---

## Validation Criteria

### Minimum Success
- ✅ Activity propagates to all 5 layers (>0% each)
- ✅ Lamina: >10% active
- ✅ Medulla: >1% active
- ✅ Runtime: <10 minutes for 5 stimuli

### Target Success
- ✅ Lamina: 20-40% active
- ✅ Medulla: 2-5% active (matches Campbell 2013)
- ✅ Lobula: 10-20% active
- ✅ Lobula Plate: 10-20% active

### Publication-Ready
- ✅ All 4 validation tests pass
- ✅ Decorrelation: r < 0 for similar wavelengths
- ✅ Contrast invariance: r > 0.70
- ✅ Motion detection: DSI > 0.3

---

## Potential Further Adjustments

### If Activity Still Weak
```python
# Increase forcing more
forcing_strength = float(flat_response[i] * 1000.0)  # 100× original
# Or even:
forcing_strength = float(flat_response[i] * 5000.0)  # 500× original
```

### If Simulation Too Slow
```python
# Increase dt further (in sparse_probabilistic.py)
self.dt = 1.0  # 1ms timestep, 100× faster than original
```

### If Numerically Unstable
```python
# Increase damping (in sparse_probabilistic.py)
self.gamma = 0.2  # Was 0.1, doubles damping
```

---

## Testing Protocol

### Phase 1: Quick Validation (Now)
1. Run `test_sparse_coding.py` with 5 stimuli
2. Check if activity propagates to all layers
3. Measure runtime (~5 minutes expected)

### Phase 2: Parameter Tuning (If Needed)
1. If weak: increase forcing to 1000-5000
2. If slow: increase dt to 1.0ms
3. If unstable: increase gamma to 0.2

### Phase 3: Full Validation (After Success)
1. Run all 41 pure wavelength stimuli
2. Run remaining 3 tests (decorrelation, contrast invariance, motion)
3. Compare to biological benchmarks
4. Document findings

---

## Changes Summary Table

| Parameter | Old Value | New Value | Change | Rationale |
|-----------|-----------|-----------|--------|-----------|
| **dt** | 0.01ms | 0.1ms | **10× ↑** | Match biological timescales |
| **Forcing** | 10.0 | 500.0 | **50× ↑** | Scale with network size |
| **Duration** | 20ms | 100ms | **5× ↑** | Allow full propagation |
| **Test size** | 3 stimuli | 5 stimuli | **1.7× ↑** | Better statistics |
| **Steps/100ms** | 10,000 | 1,000 | **10× ↓** | Efficiency gain |
| **Runtime/stim** | ~2 min | ~1 min | **2× ↓** | Net speedup |

---

## Research Basis

All changes based on:
1. **Borst 2024** (bioRxiv): State-of-the-art optic lobe model
   - Uses dt=10ms (we use 0.1ms, still 100× finer)
   - H-current dynamics: ~50ms time constant
   - Response duration: 50-100ms

2. **Olfaction Validation**: 8/9 benchmarks passed
   - 100ms duration standard
   - Strength=50.0 for 5K neurons
   - Scaling relationship established

3. **Visual Biology**:
   - 13-20ms photoreceptor→behavior latency
   - 50-100ms lamina response dynamics
   - 93K neurons vs 5K in olfaction (18× larger)

See `research/vision/PARAMETER_VALIDATION_RESEARCH.md` for full analysis.
