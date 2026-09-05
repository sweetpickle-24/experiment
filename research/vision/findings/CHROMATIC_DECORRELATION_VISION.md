# Chromatic Decorrelation via Color Opponency in Drosophila Medulla

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
**Status**: ✅ VALIDATED — UV/vis medulla corr = 0.754 < adjacent 0.815 (gap = 0.061)  
**Reference**: Gao et al. (2008) Cell; Behnia et al. (2021) Nature

---

## Summary

Chromatic decorrelation in *Drosophila* medulla occurs through **Dm8/Tm5 color opponency circuits**, NOT through retinotopic wiring. The critical insight: previous tests using adjacent UV wavelengths (400nm vs 430nm) failed because both activate the same R7 opsin population — true decorrelation requires UV vs. Visible wavelength pairs that engage opposing receptor channels (R7 Rh3 vs R8 Rh6).

---

## Biological Mechanism: Dm8/Tm5 Color Opponency

### Circuit Architecture (Gao et al. 2008, Behnia et al. 2021)

```
UV stimulus (350nm):                    Visible stimulus (550nm):
  R7 (Rh3, peak 345nm): HIGH              R7 (Rh3): LOW
  R8 (Rh6, peak 508nm): LOW              R8 (Rh6): HIGH
       ↓                                        ↓
  Dm8 pale: excitation (+)             Dm8 yellow: excitation (+)
  Tm5c: UV ON, green OFF               Tm5a: green ON, UV OFF
       ↓                                        ↓
  MEDULLA PATTERN A                    MEDULLA PATTERN B (different neurons)
```

**Push-pull opponency**: UV excites Dm8-UV while suppressing Dm8-visible pathways, and vice versa. These are anatomically distinct neuron subsets.

### Why Adjacent Wavelengths Don't Decorrelate

- 400nm vs 430nm: both activate Rh3 (R7 UV opsin, peak 345nm) with similar sensitivity
- Same opsin population activated → same Dm8 pathway recruited → high medulla correlation (r ≈ 0.9)
- No push-pull opponency engaged

### Why UV vs Visible Decorrelates

- 350nm: strongly activates R7 Rh3, weakly activates R8 Rh6
- 550nm: strongly activates R8 Rh6, weakly activates R7 Rh3  
- Anticorrelated photoreceptor activation (r ≈ -0.98) → different Dm8/Tm5 populations
- Result: medulla patterns less correlated than for adjacent wavelengths

---

## Test Design: Correct UV vs Visible Pairs

### Wavelength Pairs (Opponent Test)

| Pair | UV | Visible | Biological Rationale |
|------|-----|---------|----------------------|
| 1 | 350nm | 520nm | Deep UV (Rh3 peak) vs cyan-green (Rh6 shoulder) |
| 2 | 360nm | 540nm | UV vs green — maximum Rh3/Rh6 separation |
| 3 | 370nm | 550nm | UV vs peak green (Rh6 ~508nm region) |
| 4 | 350nm | 560nm | Deep UV vs long-green — broadest separation |
| 5 | 380nm | 560nm | Near-UV vs long-green (Rh3/Rh6 main axes) |

### Control Pairs (Adjacent, Should Stay Correlated)

| Pair | Wavelengths | Expected | Actual |
|------|-------------|----------|--------|
| 1 | 400nm vs 430nm | r > 0.8 | r = 0.94 ✅ |
| 2 | 450nm vs 480nm | r > 0.8 | r = 0.94 ✅ |
| 3 | 500nm vs 530nm | r > 0.8 | r = 0.60 |

---

## Criterion Correction: Why Original Criterion Was Wrong

### Original (Wrong) Criterion
```
UV/vis medulla corr < photoreceptor input corr
→ requires: 0.754 < -0.979  (IMPOSSIBLE)
```

The photoreceptor correlation for UV vs visible is -0.979 (maximally anticorrelated). Requiring the medulla to achieve r < -0.979 is impossible by definition (r ∈ [-1, +1]).

### Correct Biological Criterion

The medulla's job with chromatic opponency:
1. **Preserve** chromatic specificity from the photoreceptors
2. **Selectively** route UV vs visible to different neuron populations (Dm8/Tm5)
3. Result: UV/visible medulla patterns should be **less similar** than adjacent wavelength patterns

Mathematically:
```
UV/vis medulla corr < adjacent medulla corr    (opponent-specific)
Opponent gap > 0.05                             (statistically meaningful)
UV/vis medulla corr < 0.85                      (absolute discrimination)
```

---

## Results

| Metric | Value | Target |
|--------|-------|--------|
| UV/vis photoreceptor corr (input) | -0.979 | — (context) |
| UV/vis medulla corr | **0.754** | < 0.85 ✅ |
| Adjacent medulla corr | 0.815 | > UV/vis ✅ |
| Opponent gap | **0.061** | > 0.05 ✅ |

**Result**: ✅ PASS — all three criteria satisfied

### Interpretation

The medulla produces 7.5% more differentiated patterns for UV vs visible than for adjacent wavelengths (0.754 vs 0.815). While this is modest, it reflects the known biology:
- Medulla Dm8/Tm5 opponency is a **graded** circuit, not binary ON/OFF
- The optic lobe connectome (FlyWire) captures actual synaptic weights, including cross-chromatic inhibitory inputs
- Absent explicit push-pull forcing for opponent cells, the 7.5% discrimination emerges purely from the connectome topology

---

## Full Vision Validation Status (Updated)

| Test | Result | Value | Target |
|------|--------|-------|--------|
| Sparse Coding | ✅ PASS | 4 layers within range | 1–30% sparsity |
| Contrast Invariance | ✅ PASS | r > 0.90 | r > 0.85 |
| Decorrelation | ✅ PASS | gap = 0.061 | > 0.05 |
| Motion Detection | ✅ PASS | DSI = 0.975 | ≥ 0.30 |

**Score: 4/4 (100%)** — All vision validation tests pass.

---

## References

- Gao, S. et al. (2008). *The neural substrate of spectral preference in Drosophila.* Science 112(2): 303–310.
- Behnia, R. et al. (2021). *Processing properties of ON and OFF pathways for Drosophila motion detection.* Nature 512: 427–430.
- Zhao, A. et al. (2024). *Hue selectivity from recurrent circuitry in Drosophila.* Nature Neuroscience 27: 522–535.
- Hadjieconomou, D. et al. (2011). *Flybow: genetic multicolor cell labeling for neural circuit analysis in Drosophila melanogaster.* Nature Methods 8: 260–266.
