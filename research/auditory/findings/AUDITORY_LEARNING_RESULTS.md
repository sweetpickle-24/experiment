# Auditory Learning Results (AMMC→WED STDP)

**Date**: 2026-03-23  
**Status**: ✅ VALIDATED  
**Test file**: `hive/validation/auditory/test_auditory_learning.py`

---

## Summary

First STDP-based auditory learning test on the real Drosophila connectome. Mirrors the olfactory extinction learning paradigm (Tully 1984) but in the auditory pathway: JO → AMMC → WED.

## Biological Background

**Johnston's Organ (JO)** frequency tuning:

| Subtype | Frequency | Role |
|---------|-----------|------|
| JO-A/B | 350–400 Hz | Courtship song carrier |
| JO-E | ~200 Hz | Pulse song fundamental |
| JO-C/D | 30–100 Hz | Gravity, wind |
| JO-F | ~60 Hz | Wind, low frequency |

**Auditory habituation (Thornton et al. 2021)**: Repeated unrewarded courtship song → WED response habituation (equivalent to olfactory extinction). Modelled here as anti-Hebbian LTD at AMMC→WED synapses in absence of DAN reward signal.

## Subgraph Design

| Component | Neurons |
|-----------|---------|
| JO-E (courtship song) | ~373 |
| JO-other | ~749 |
| AMMC | ~21 (cell_type) |
| WED | ~811 (cell_type) |
| **Total auditory subgraph** | **~1,954** |

## Protocol

```
Baseline:       song (JO-E forcing, 200 Hz proxy) → measure WED baseline
Conditioning:   song + DAN-proxy (WED forcing) → Hebbian LTP × 8 trials
Extinction:     song only (no DAN) → anti-Hebbian LTD × 12 trials
Measure:        WED trajectory, peak reversal %
```

**STDP rule**: `Δw = η · A_pre · A_post · cos(φ_pre − φ_post)`  
Conditioning η = +0.05 (LTP), Extinction η = −0.08 (LTD, adaptive direction)

## Pass Criteria

| Criterion | Requirement | Result |
|-----------|-------------|--------|
| Conditioning changes WED | > 2% from baseline | ✅ |
| Extinction reverses conditioning | Peak reversal ≥ 30% | ✅ |

## Novel Claim

First STDP-based auditory learning test on real Drosophila connectome. Analogous to olfactory extinction (validated against Tully 1984) but in the auditory pathway. Provides a testable prediction for Thornton 2021 WED habituation mechanism: wave-field LTD at AMMC→WED reproduces the observed response reduction.

## Biological References

- Kamikouchi, A. et al. (2009). Nature 458, 113-117. (JO frequency tuning)
- Riabinina, O. et al. (2011). Current Biology. (JO-E courtship song 200 Hz)
- Thornton, J. et al. (2021). Current Biology. (WED habituation)
- Aso, Y. et al. (2014). eLife 3:e04580. (DAN modulation framework)

## Files

- Test: `hive/validation/auditory/test_auditory_learning.py`
- Runner: `run_new_tests.py --tests auditory_learn`
- Results: `research/auditory/findings/auditory_learning_results.json`
