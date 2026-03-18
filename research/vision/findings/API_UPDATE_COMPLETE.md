# Vision Tests API Update — Complete

**Date:** 2026-03-18  
**Status:** ✅ ALL FILES UPDATED (8 files)

---

## Summary

Updated all vision validation and discovery tests from the old `brain.step(dt, forcing)` API to the new `brain.evolve(duration)` + `brain.external_force` API.

---

## API Changes Applied

### Old API (deprecated)
```python
brain._reset_state()

forcing = {}
for nid in neurons:
    forcing[nid] = value

brain.step(dt_ms / 1000.0, forcing)
```

### New API (current)
```python
brain._initialize_fields()
if brain.use_mlx:
    import mlx.core as mx
    brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
else:
    brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)

for nid in neurons:
    idx = brain.id_to_idx[nid]
    brain.external_force[idx] = value

brain.evolve(duration=dt_ms)
```

---

## Files Updated

### Vision Goal Tests (3 files)

1. **test_color_constancy.py** ✅
   - Property: Color constancy via phototransduction adaptation
   - Changes: 1 location (simulation loop with constant forcing)
   - Special case: Forcing dict built once, then copied to external_force array

2. **test_hs_vs_optic_flow.py** ✅
   - Property: HS/VS optic flow matching electrophysiology
   - Changes: 1 location (direction × temporal frequency sweep)
   - Pattern: Reset + BL filter + external forcing per step

3. **test_emergent_properties.py** ✅
   - Property 1: Orientation selectivity
   - Property 3: Chromatic motion blindness
   - Changes: 2 locations (one per property test)
   - Pattern: Loop over orientations/stimulus types, reset brain per condition

### Discovery Tests (5 files)

4. **discovery_hex_lattice_direction_bias.py** ✅
   - Discovery: 6-fold hex lattice bias in DSI
   - Changes: 1 location (16 direction sweep)
   - Pattern: Initialize once per direction, evolve per step

5. **discovery_velocity_memory.py** ✅
   - Discovery: LP velocity persistence after stimulus cessation
   - Changes: 2 locations (ON phase with forcing, OFF phase with zero forcing)
   - Pattern: BarlowLevick filter drives forcing during ON, zero external_force during OFF

6. **discovery_predictive_suppression.py** ✅
   - Discovery: LP suppression via Dm feedback to lamina
   - Changes: 2 locations (ON/OFF periods within repetition loop)
   - Pattern: Initialize once, then ON/OFF cycles with forcing toggle

7. **discovery_velocity_tuning_cascade.py** ✅
   - Discovery: Which stage sets HS/VS velocity optimum
   - Changes: 1 location (temporal frequency sweep)
   - Pattern: Initialize per TF, BL filter drives forcing

8. **discovery_t4_dsi_heterogeneity.py** ✅
   - Discovery: Individual T4 DSI distribution vs anatomy
   - Changes: 1 location (preferred/null direction loop)
   - Pattern: Initialize per direction, simple ON-signal forcing

---

## Key Patterns Identified

### Pattern A: Simple Forcing Loop
Most common pattern for gratings/motion stimuli:

```python
brain._initialize_fields()
brain.external_force = mx.zeros(...) or np.zeros(...)

for step in range(num_steps):
    # Compute stimulus (luminance, grating, etc.)
    # Update brain.external_force array directly
    for nid in neurons:
        idx = brain.id_to_idx[nid]
        brain.external_force[idx] = computed_value
    
    brain.evolve(duration=dt_ms)
    
    # Read state if needed
    state = brain.get_state()
```

### Pattern B: Constant Forcing (test_color_constancy)
For stimuli that don't change over time:

```python
# Build forcing dict once
forcing = {nid1: val1, nid2: val2, ...}

# Copy to external_force
for nid, val in forcing.items():
    idx = brain.id_to_idx[nid]
    brain.external_force[idx] = val

# Evolve multiple steps with same forcing
for step in range(num_steps):
    brain.evolve(duration=dt_ms)
```

### Pattern C: Zero Forcing (decay/OFF periods)
For blank screen or post-stimulus decay:

```python
# Zero out external forcing
if brain.use_mlx:
    brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
else:
    brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)

brain.evolve(duration=dt_ms)
```

---

## Testing Status

**API updates complete, NOT yet tested.**

To test these scripts:
1. Run each test individually to verify no runtime errors
2. Check that results are quantitatively similar to previous runs (if available)
3. Expected runtime for full suite: ~30-60 minutes (92K neuron visual connectome, 16-direction sweeps)

---

## Common Issues Fixed

### Issue 1: `brain._reset_state()` → `brain._initialize_fields()`
The old `_reset_state()` method no longer exists. Replaced with `_initialize_fields()` which properly initializes the wave oscillator states.

### Issue 2: Forcing dict → `external_force` array
The old API accepted a `forcing` dict mapping neuron IDs to values. New API requires direct manipulation of the `brain.external_force` array indexed by `brain.id_to_idx[neuron_id]`.

### Issue 3: `brain.step(dt, forcing)` → `brain.evolve(duration)`
The `step` method no longer exists. Use `evolve(duration=dt_ms)` which internally calls `_step_mlx()` or `_step_numpy()` depending on `use_mlx` flag.

### Issue 4: MLX vs NumPy external_force initialization
Must check `brain.use_mlx` and initialize `external_force` as either `mlx.core.mx.zeros()` or `numpy.zeros()` accordingly.

---

## Validation Checklist

Before running tests, verify:

- [ ] All `brain.step(` occurrences replaced ✅ (verified via grep)
- [ ] All `brain._reset_state(` occurrences replaced ✅ (verified via grep)
- [ ] External forcing uses `brain.external_force[idx]` not `forcing[nid]` ✅
- [ ] MLX/NumPy conditional initialization present ✅
- [ ] No orphaned `forcing = {}` dict creation ✅ (except test_color_constancy which reuses it)
- [ ] `brain.evolve(duration=dt_ms)` not `brain.evolve(dt_ms / 1000.0)` ✅ (duration is in ms, not seconds)

---

## Performance Notes

**Expected behavior after update:**

1. **Initialization**: `brain._initialize_fields()` should complete in <1s (same as before)
2. **Per-step forcing update**: Setting `external_force` array is O(N) where N = number of forced neurons (typically 800-2000 for vision tests)
3. **Evolve duration**: Same as before — ~1-2ms per step on MLX GPU, ~20-50ms per step on CPU
4. **Memory**: No change — external_force array pre-allocated, just updating values

**Total runtime estimates (M4 Pro MLX):**
- Single direction test (200ms sim): ~2-3 seconds
- 16-direction sweep: ~30-50 seconds
- Full discovery suite (5 tests): ~5-10 minutes

---

## Files Ready to Run

All 8 files are now API-compatible and ready for testing:

```
hive/validation/vision/
├── test_color_constancy.py              ✅ UPDATED
├── test_hs_vs_optic_flow.py             ✅ UPDATED
├── test_emergent_properties.py          ✅ UPDATED
├── discovery_hex_lattice_direction_bias.py    ✅ UPDATED
├── discovery_velocity_memory.py         ✅ UPDATED
├── discovery_predictive_suppression.py  ✅ UPDATED
├── discovery_velocity_tuning_cascade.py ✅ UPDATED
└── discovery_t4_dsi_heterogeneity.py    ✅ UPDATED
```

---

## Next Steps (Not Performed)

To complete the vision validation:

1. **Run tests individually** to verify API updates work
2. **Document results** in MD files (following calcium oscillations / T4_T5 pattern)
3. **Update Findings.mdc** with new discoveries
4. **Generate figures** for publication (following vision validation figure pattern)

**Estimated time**: 1-2 hours for running + documentation
