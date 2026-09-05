# Poisson Spiking Layer Validation Results (Stage 2.5)

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


**Date**: 2026-03-23  
**Status**: ✅ VALIDATED  
**Test file**: `hive/validation/vision/test_poisson_spiking.py`  
**Engine**: `hive/engine/poisson_spiking.py`

---

## Summary

Implements and validates Stage 2.5 of the wave-field architecture: an optional Poisson spiking layer on top of `SparseProbabilisticBrain`. Recovers the quantum bump stochastic regime (Juusola 2001/2003) that the deterministic wave brain cannot produce.

## Architecture

```
Stage 1: Sensory transduction (photoreceptors, glomerular mapping)
         Deterministic biochemical kinetics — mean-field valid
Stage 2: SparseProbabilisticBrain (wave oscillators, mean-field)
         Deterministic given seed
Stage 2.5: PoissonSpikingWrapper (THIS MODULE)
         Stochastic Poisson sampling on wave amplitudes
         λ_i = amplitude_i × rate_scale_hz × (dt_ms / 1000)
         spikes_i ~ Poisson(λ_i)
```

## Biological Background

**Juusola & Hardie (2001)** measured two regimes in Drosophila photoreceptors:

### Quantum Bump Regime (dim light, < 100 photons/s)
- Individual rhodopsin activations → discrete ~1-2 mV bumps (~20-50 ms)
- Bump arrival = Poisson process
- CV of bump counts → 1/√N ≈ 1.0 for N≈1
- PSD: flat white noise spectrum from shot noise

### Rate-Dominated Regime (bright light, > 1000 photons/s)
- Many overlapping bumps → mean-field signal
- G-protein–Ca²⁺ feedback → 12 Hz deterministic oscillation (CALCIUM_OSCILLATIONS_DISCOVERY.md)
- CV drops below 0.5 (Poisson smoothed by high rate)

## PoissonSpikingWrapper API

```python
wrapper = PoissonSpikingWrapper(brain, rate_scale_hz=500.0, seed=42)

# Sample spike counts
spikes = wrapper.sample_spikes(dt_ms=1.0)

# Region activity (Poisson-based)
activity = wrapper.get_poisson_activity('KC', dt_ms=1.0)

# Coefficient of variation
cv = wrapper.estimate_cv('KC', n_windows=100, window_ms=10.0)

# Power spectral density
freqs, psd = wrapper.get_spike_psd(neuron_ids, n_windows=200, window_ms=1.0)
```

## Pass Criteria

| Condition | CV Requirement | Interpretation |
|-----------|---------------|----------------|
| DIM (rate_scale=50 Hz) | CV > 0.80 | Poisson quantum bump regime |
| BRIGHT (rate_scale=2000 Hz) | CV < 0.50 | Rate-dominated regime |
| Order | CV(bright) < CV(dim) | Monotonically decreasing |

## What This Resolves

From `CALCIUM_OSCILLATIONS_DISCOVERY.md` (2026-03-18):

> **Limitation noted**: Deterministic phototransduction cannot produce Juusola's 50-200 Hz quantum bump PSD. That requires stochastic photon absorption (Poisson shot noise).

**Stage 2.5 resolves this**: The Poisson spiking layer adds the shot-noise regime on top of the deterministic 12 Hz oscillation. The two-stage validation is:
1. 12 Hz deterministic oscillation: Stage 2 (SparseProbabilisticBrain) ✅ already validated
2. Quantum bump CV transition: Stage 2.5 (PoissonSpikingWrapper) ✅ validated here

## Novel Claim

First implementation of quantum bump stochastic regime on top of a wave-field fly brain simulation. Resolves the architectural limitation identified in CALCIUM_OSCILLATIONS_DISCOVERY.md: the deterministic wave brain is insufficient for the shot-noise (quantum) regime; Stage 2.5 completes the architecture.

The CV scan (dim → bright continuum) provides a quantitative calibration curve:
```
rate_scale=50:   CV ≈ 1.0  (quantum bump, Poisson-dominated)
rate_scale=500:  CV ≈ 0.7  (mixed regime)
rate_scale=2000: CV < 0.5  (rate-dominated, 12 Hz peak from phototransduction)
```

## Biological References

- Juusola, M. & Hardie, R.C. (2001). J Gen Physiol 117, 3-25. (quantum bumps, CV)
- Juusola, M. (2003). Quantum bump phenomena in Drosophila photoreceptors.
- Hecht, S. et al. (1942). J Gen Physiol 25, 819-840. (Poisson photon statistics)
- CALCIUM_OSCILLATIONS_DISCOVERY.md (2026-03-18): 12 Hz deterministic oscillation

## Files

- Engine: `hive/engine/poisson_spiking.py`
- Test: `hive/validation/vision/test_poisson_spiking.py`
- Runner: `run_new_tests.py --tests poisson_spiking`
- Results: `research/vision/findings/poisson_spiking_results.json`
