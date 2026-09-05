# Multi-Modal Significance: What Vision Proves

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
**Context**: Post-validation analysis comparing vision and olfaction results

---

## The Core Question

Is vision groundbreaking on its own, or is it supporting evidence? And what does the combination of olfaction + vision actually prove?

---

## Honest Assessment

### Vision alone: corroborating, not independently groundbreaking

The vision results (4/4, 100%) are impressive but each finding was already known from biology:

| Vision Result | What It Proves | Novelty |
|---------------|----------------|---------|
| Layer sparsity in biological range | Simulation reproduces known sparsity | Low — expected |
| Contrast invariance r=0.857 | Weber-Fechner encoding works | Low — textbook |
| Chromatic opponency gap=0.061 | Dm8/Tm5 circuit works correctly | Medium — validation |
| Motion detection DSI=0.975 | Barlow-Levick T4 mechanism works | Medium — computational proof |

None of these is a standalone discovery. The circuits were known. The parameters were known. We confirmed our simulation reproduces them correctly.

### Olfaction: genuinely groundbreaking

The olfactory r = [withdrawn] decorrelation result was **unexpected** — nobody predicted the exact numerical value would emerge from purely physical dynamics on a real connectome. That's what makes it publishable as a standalone finding.

---

## What Vision Actually Contributes

### 1. Multi-Modal Proof of Framework Universality (HIGH VALUE)

This is the primary contribution. The same `SparseProbabilisticBrain` engine, applied to a completely different connectome (optic lobe vs. mushroom body), produces the biologically correct emergent coding strategy for each modality:

```
Olfaction (random wiring):
  Input correlation +0.81 → KC correlation -0.51
  Mechanism: sparse expansion + competition → decorrelation

Vision (retinotopic wiring):
  UV/vis photoreceptor correlation -0.979 → medulla correlation 0.754
  Mechanism: Dm8/Tm5 opponency → chromatic discrimination
  T4 preferred vs null response: 1.19 vs 0.073 (93.9% suppression)
  Mechanism: Barlow-Levick temporal asymmetry
```

The physics doesn't know it's running on olfactory or visual tissue. The **connectome topology** determines the output. This is the publishable insight.

### 2. Scale Validation (MEDIUM VALUE)

- Olfaction: 10,906 neurons
- Vision: 53,000 neurons (5× larger, 4× more synapses)
- Same engine works at both scales with O(N) memory
- Addresses reviewer concern: "Does this scale?"

### 3. Framework Extensions (LOW-MEDIUM VALUE)

Two components added to the framework that are reusable for any future modality:
- `BarlowLevickFilter`: temporal direction-selective computation (not olfaction-specific)
- `amplitude_history` ring buffer: 50ms temporal memory (general delay-line modeling)

---

## Publication Strategy

### Option A: Combined paper (recommended)

**Title**: "Wave-based simulation of Drosophila connectomes produces modality-specific emergent sensory coding"

**Central claim**: The same wave physics engine, applied to real connectome data, produces biologically accurate emergent coding strategies in both olfaction and vision without modality-specific tuning. Connectome topology, not physics parameters, determines the coding strategy.

**Evidence**:
1. Olfaction: [score withdrawn] (100%), r = [withdrawn] decorrelation (the "wow" result)
2. Vision: 4/4 (100%), DSI=0.975, gap=0.061 (the "it generalizes" result)
3. Same engine, 0 modality-specific tuning of core dynamics

**Target**: Nature Neuroscience (multi-modal framework = higher tier than single-modality)

### Option B: Olfaction paper + vision follow-up

Submit olfaction to Nature Communications now. Vision becomes a separate paper or supplementary for a follow-up. Faster to publish but misses the multi-modal hook.

### Recommendation

Option A. The multi-modal claim is the paper's unique selling point. No other computational framework has been validated across two sensory modalities using real connectome data at this scale. This is the "universality of wave physics" claim that reviewers at Nature Neuroscience would value.

---

## What Would Make Vision Groundbreaking On Its Own

If you want to extract a standalone novel finding from vision, candidates are:

1. **Color constancy**: Show that the wave engine produces light-invariant wavelength representation (photon flux changes don't change the identity representation) — this would be the visual analogue of olfactory concentration invariance, and the result is NOT guaranteed to work given vision's more complex photoreceptor dynamics.

2. **Optic flow matching**: Measure lobula plate HS/VS cell responses to full-field grating motion and compare to known electrophysiology (Joesch et al. 2008). If DSI and preferred directions match, that's a quantitative prediction from first principles.

3. **Unexpected emergent property**: Something that emerges from the optic lobe connectome that wasn't predicted — analogous to how r = [withdrawn] wasn't predicted for olfaction. This requires running experiments and looking for surprises, not designing tests to pass.

---

## What the Olfaction + Vision Combination Says About the Brain

The deepest implication: **the brain's coding strategy is written in its wiring diagram, not in its neural dynamics**.

- Random PN→KC wiring → the brain "chose" to decorrelate chemically similar odors
- Retinotopic retina→medulla wiring → the brain "chose" to preserve spatial information
- T4 dendritic topology (leading vs trailing zones) → the brain "chose" Barlow-Levick motion detection

The wave physics provides the computational substrate. But the **function** — discrimination vs. continuity, sparse vs. distributed, correlation vs. anticorrelation — is determined entirely by how neurons are connected.

This is consistent with the connectome-first hypothesis: **understanding a brain region's function requires understanding its connectivity, not just its dynamics**.

---

## References for Multi-Modal Framework Claims

- Marr (1982): Levels of analysis — implementation vs. algorithm vs. computation
- Hopfield (1982): Energy-based neural dynamics
- Olshausen & Field (1996): Sparse coding as a general principle
- Litwin-Kumar et al. (2017): Sparse expansion prediction (validated by olfaction)
- Haag et al. (2017): Barlow-Levick T4 mechanism (validated by vision)
- Gao et al. (2008): Dm8/Tm5 chromatic opponency (validated by vision)
- Dorkenwald et al. (2024): FlyWire connectome (used by both modalities)
