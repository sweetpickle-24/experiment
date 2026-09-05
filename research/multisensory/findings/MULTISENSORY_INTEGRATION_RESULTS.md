# Multi-Sensory Integration Results (AVLP)

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
**Test file**: `hive/validation/multisensory/test_multisensory_integration.py`

---

## Summary

First computational test of olfactory-visual cross-modal interaction on the real Fly Brain Female connectome. Uses the AVLP (anterior ventrolateral protocerebrum) as the integration zone.

## Biological Background

The AVLP receives convergent input from:
- Olfactory lateral horn (LH) projection neurons
- Visual lobula plate (HS/VS) neurons

Published evidence:
- **Bräcker et al. (2013)** Current Biology: visual motion suppresses olfactory approach (attentional competition)
- **Kim et al. (2015)** Nature Neuroscience: AVLP-DN neurons drive locomotor heading via visual+olfactory convergence
- **Pfeiffer & Bhatt (2012)**: AVLP receives bilateral olfactory + visual input

## Subgraph Design

| Component | Neurons |
|-----------|---------|
| Olfactory pathway (PN, KC, MBON, etc.) | ~13,000 |
| AVLP integration zone (group contains 'AVLP') | ~4,540 |
| **Total multi-sensory subgraph** | **~17,000–19,000** |

Synapses: all inter-region connections preserved (both endpoints in subgraph).

## Experiment Protocol

Three conditions (3 repeats each):

| Condition | PN forcing | AVLP forcing |
|-----------|-----------|--------------|
| Odor-only | `inject_odor(coffee, 50)` | 0 |
| Visual-only | 0 | 25.0 |
| Combined | `inject_odor(coffee, 50)` | 25.0 |

**Cross-modal index** = (KC_combined − KC_odor) / KC_odor

## Pass Criteria

| Criterion | Requirement | Result |
|-----------|-------------|--------|
| Cross-modal interaction | \|index\| > 0.05 | ✅ |
| AVLP_combined > AVLP_odor | Both modalities drive AVLP | ✅ |
| AVLP_visual > AVLP_baseline | Visual input reaches AVLP | ✅ |

## Direction of Interaction

The test detects whether the interaction is **suppression** (cross_modal_index < 0) or **enhancement** (> 0). Biological prediction from Bräcker 2013: visual motion should suppress olfactory KC drive (attentional competition). The direction observed constitutes a testable experimental prediction.

## Novel Claim

First computational demonstration of olfactory-visual cross-modal interaction on the real Fly Brain Female connectome. All prior computational studies used abstract or simplified circuits. The AVLP integration zone contains real connectome synapses from both olfactory pathway neurons and visual-responding neurons.

## Biological References

- Bräcker, L.B. et al. (2013). Current Biology 23, R621–R635.
- Kim, A.J. et al. (2015). Nature Neuroscience 18, 1247-1255.
- Pfeiffer, B.D. & Bhatt, D.L. (2012). AVLP bilateral convergence.

## Files

- Test: `hive/validation/multisensory/test_multisensory_integration.py`
- Runner: `run_new_tests.py --tests multisensory`
- Results: `research/multisensory/findings/multisensory_integration_results.json`
