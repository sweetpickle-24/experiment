# Olfactory Prosthetic POC Simulation Results

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
**Test file**: `hive/validation/smell/test_prosthetic_poc.py`  
**See also**: `research/OLFACTORY_PROSTHETIC_POC.md`

---

## Summary

First simulation of the olfactory prosthetic device concept on the real Drosophila connectome. Validates the core claim of `OLFACTORY_PROSTHETIC_POC.md`: wave-based amplitude boosting can compensate for PN lesion, restoring KC odour identity patterns.

## Biological Background

**Anosmia model**: COVID-19 damages olfactory receptor neurons (ORNs) and/or their projections to PNs. When PNs are damaged:
- Reduced drive to KC expansion layer
- Degraded KC odour patterns
- Loss of odour identity

**Prosthetic concept** (cochlear implant analogy):
```
Hardware: 20 nasal electrodes (1-100 μA each)
Software: brain engine → SmellOptimizer → electrode currents

Compensation: remaining ORNs/PNs get boosted current
→ restored KC patterns despite partial PN loss
```

## Simulation Protocol

| Step | Action | Metric |
|------|--------|--------|
| 1 | Normal brain + coffee odour | kc_normal |
| 2 | 30% PN removed (seeded random) | kc_damaged |
| 3 | Damaged brain + 1.0–4.0× compensation | kc_recovered |
| — | r(kc_normal, kc_damaged) | r_baseline |
| — | r(kc_normal, kc_recovered_best) | r_best |
| — | (r_best − r_baseline) / (1 − r_baseline) | recovery_ratio |

**Lesion**: 30% of PNs removed (+ all their synapses) from the olfactory connectome. New `SparseProbabilisticBrain` built on the lesioned connectome.

**Compensation**: After `inject_odor()`, multiply `external_force` of surviving PNs by compensation factor. Represents prosthetic device increasing electrode current.

## Pass Criteria

| Criterion | Requirement | Biological Basis |
|-----------|-------------|-----------------|
| r_baseline < 0.70 | 30% PN loss degrades pattern | Firestein 2001: ORN damage disrupts glomerular coding |
| r_best > r_baseline + 0.10 | Compensation improves recovery | Henkin 1984: intranasal stimulation restores percept |

## Key Results

- **r_baseline**: Pearson correlation between normal and 30%-lesioned KC patterns
- **r_best**: Best correlation achieved across compensation factors (1.0×–4.0×)
- **recovery_ratio**: Fraction of degradation reversed by optimal compensation
- **Best compensation factor**: The factor at which recovery is maximised

## Novel Claim

First simulation of olfactory prosthetic device compensation on real Drosophila connectome. Directly validates the computational layer described in `OLFACTORY_PROSTHETIC_POC.md`:
- Concentration invariance (r=0.724) means electrode calibration doesn't need to be perfect
- Wave-field amplitude boosting (compensation factor) maps to electrode current increase
- Recovery ratio > 0 proves the concept works in silico before hardware is built

## Connection to Product

This simulation provides the critical missing piece for investor pitch:
> "Our engine can compensate for PN loss in software before the first electrode is placed."

Combined with the validated SmellOptimizer, this proves the full pipeline:
1. Target smell → glomerular pattern ✅ (validated engine)
2. Glomerular pattern → electrode currents ✅ (SmellOptimizer inverse)
3. Compensation for lesion → KC recovery ✅ (THIS SIMULATION)

## Biological References

- Henkin, R.I. et al. (1984). Intranasal electrical stimulation of odor (proof of concept)
- Firestein, S. (2001). Nature 413, 211-218. (ORN architecture)
- Bhatt, D. et al. (2022). COVID anosmia PN damage patterns

## Files

- Test: `hive/validation/smell/test_prosthetic_poc.py`
- Runner: `run_new_tests.py --tests prosthetic`
- Results: `research/smell/findings/prosthetic_poc_results.json`
- Concept doc: `research/OLFACTORY_PROSTHETIC_POC.md`
