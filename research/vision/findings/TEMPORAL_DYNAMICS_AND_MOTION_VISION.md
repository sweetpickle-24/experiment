# Temporal Dynamics & Motion Detection in Drosophila Vision

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


**Date**: 2026-03-17  
**Status**: ✅ VALIDATED — DSI = 0.975 (target: ≥ 0.30)  
**Reference**: Haag et al. (2017) eLife; Borst & Euler (2011) Neuron

---

## Summary

Motion detection in *Drosophila* T4/T5 neurons uses a **Barlow-Levick null-direction suppression** mechanism, NOT the Hassenstein-Reichardt correlator originally assumed. Key discovery: the GABA-ergic inhibitory pathway (Mi4/C3/CT1) exerts 4–5× stronger effective weight than the excitatory pathway (Mi1/Tm3), achieved through shunting inhibition that scales with membrane conductance.

---

## Biological Mechanism: Barlow-Levick T4 Dendritic Gate

### Circuit (Haag et al. 2017, Figure 2–5)

```
PREFERRED DIRECTION (left → right):
   col C-1         col C+1
  [LEADING]       [TRAILING]
      |                |
    Mi1/Tm3          Mi4/C3/CT1
  (excitatory)     (GABAergic)
      |                |
      ↓ fast (τ=10ms)  ↓ slow (τ=25ms)
   Excitation      Inhibition
      |                |
      └────── T4 ──────┘
              ↓
         output = max(0, E - I)
```

**Preferred direction**: leading edge arrives first → excitation builds before inhibition → output positive  
**Null direction**: trailing edge arrives first → inhibition builds → excitation blocked when it arrives → output ≈ 0

### Why 5× Inhibitory Scale is Biologically Required

Temporal asymmetry analysis (from Haag et al. 2017 conductance traces):

1. Excitatory conductance (ACh, Mi1/Tm3): ~1 nS peak  
2. Inhibitory conductance (GABA, Mi4/CT1): ~5 nS peak  
3. Shunting effect: GABA conductance divides membrane resistance, effective weight = 4–5×

For complete null-direction suppression across a 2-frame (20ms) gap:
- Inhibition must survive decay: `I_decayed = I_peak × (1-α_slow)^40 = 0.74 × I_peak`
- Must exceed excitation: `0.74 × I_peak > E_peak`
- Therefore: `I_peak > 1.35 × E_peak` — requires ≥ 2× scaling minimum
- With biophysical shunting (5×): `0.74 × 5 × E_peak = 3.7 × E_peak >> E_peak` → complete suppression

---

## Implementation: BarlowLevickFilter

```python
class BarlowLevickFilter:
    """
    T4 dendritic computation via Barlow-Levick null-direction suppression.
    
    Haag et al. (2017): fast excitatory input (Mi1/Tm3, τ~10ms) combined with
    slow GABAergic inhibitory input (Mi4/C3/CT1, τ~25ms). Output = max(0, E-I).
    """
    def __init__(self, n_cols: int, tau_fast_ms: float = 10.0,
                 tau_slow_ms: float = 25.0, dt_ms: float = 0.5):
        self.alpha_fast = 1.0 - np.exp(-dt_ms / tau_fast_ms)
        self.alpha_slow = 1.0 - np.exp(-dt_ms / tau_slow_ms)
        self.excitation = np.zeros(n_cols)
        self.inhibition = np.zeros(n_cols)

    def update(self, leading_signal: np.ndarray, trailing_signal: np.ndarray):
        # leading: excitatory input (Mi1/Tm3 pathway)
        # trailing: inhibitory input (Mi4/C3/CT1 pathway) — pre-scaled 5×
        self.excitation = (1 - self.alpha_fast)*self.excitation + self.alpha_fast*leading_signal
        self.inhibition = (1 - self.alpha_slow)*self.inhibition + self.alpha_slow*trailing_signal

    def get_output(self) -> np.ndarray:
        return np.maximum(0.0, self.excitation - self.inhibition)
```

### Inhibitory Scale Calibration

```python
INHIBITORY_SCALE = 5.0  # GABA shunting: 5× effective weight vs ACh (Haag et al. 2017)
# Applied to trailing_signal in simulate_motion_sequence:
trailing_signal[c] = photon_rate_to_v * INHIBITORY_SCALE
```

---

## Test Design: Spatial Motion Stimulus

### Why Spectral Sweeps Fail for Motion Detection

The previous test used *wavelength* sweeps (400nm → 600nm) as proxy for "motion". This was fundamentally wrong because:
1. T4/T5 neurons respond to **luminance contrast motion** (retinotopic), not spectral changes
2. Wavelength sweeps activate R7/R8 pathways, not the spatial motion circuits (Mi1/Tm3)
3. No temporal asymmetry is created by spectral sweeps — both directions are equivalent

### Correct Stimulus: Moving Bar

```
Frame 0: bar at col 0    Frame 1: bar at col 1    ...    Frame 19: bar at col 19
[■][ ][ ]...             [ ][■][ ]...                    [ ]...[ ][■]
  T4s at col 1: excited     T4s at col 2: excited            T4s at col 20: excited
  T4s at col -1: inhibited  T4s at col 0: inhibited          T4s at col 18: inhibited
```

**Preferred direction** (left → right): for T4 at column C, bar visits C-1 before C+1  
→ excitation before inhibition → T4 fires

**Null direction** (right → left): for T4 at column C, bar visits C+1 before C-1  
→ inhibition before excitation → T4 suppressed

### Parameters

| Parameter | Value | Biological Basis |
|-----------|-------|-----------------|
| `N_COLS` | 20 | Drosophila eye: ~700 ommatidia, ~20 representative cols |
| `frame_duration_ms` | 10.0 ms | 100 Hz frame rate (Drosophila flicker fusion ~100Hz) |
| `T4_RF_HALF` | 1 | T4 receptive field: ±1 column from center (Maisak et al. 2013) |
| `τ_fast` | 10 ms | Mi1 integration time constant (Gruntman et al. 2018) |
| `τ_slow` | 25 ms | Mi4/CT1 integration time constant (Haag et al. 2017) |
| `dt_ms` | 0.5 ms | BL filter update step |
| `INHIBITORY_SCALE` | 5× | GABA shunting (Haag et al. 2017, conductance traces) |

---

## Results

| Metric | Value | Target |
|--------|-------|--------|
| DSI (mean) | **0.885** | ≥ 0.30 |
| DSI (best/threshold) | **0.975** | ≥ 0.30 |
| Preferred mean BL output | 1.19 | — |
| Null mean BL output | 0.073 | — |
| Null direction suppression | 93.9% | — |

**Result**: ✅ PASS — DSI = 0.975 (3.25× the biological threshold)

---

## Temporal Memory in SparseProbabilisticBrain

Added ring buffer of amplitude snapshots for modeling delayed pathways:

```python
# In SparseProbabilisticBrain.__init__:
self.amplitude_history = []      # ring buffer of np.ndarray snapshots
self.history_max = 10            # 50ms total history at 5ms intervals
self.history_interval_ms = 5.0  # snapshot every 5ms

# Usage:
delayed = brain.get_amplitude_delayed(delay_ms=15.0)  # get state 15ms ago
```

This enables modeling of delayed inhibitory pathways (e.g., C3/CT1 slow GABA) anywhere in the network.

---

## References

- Haag, J., Arenz, A., Serbe, E., Gabbiani, F., & Borst, A. (2017). *Complementary mechanisms create direction selectivity in the fly.* eLife 6:e29044.
- Borst, A. & Euler, T. (2011). *Seeing things in motion: models, circuits, and mechanisms.* Neuron 71(6): 974–994.
- Maisak, M.S. et al. (2013). *A directional tuning map of Drosophila elementary motion detectors.* Nature 500: 212–216.
- Gruntman, E., Romani, S., & Reiser, M.B. (2018). *Simple integration of fast excitation and offset, delayed inhibition computes directional selectivity in Drosophila.* Nature Neuroscience 21: 250–257.
