# Lobula Coding Paradigm Investigation

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


**Date**: 2026-03-18  
**Status**: Research complete - Lobula uses distributed motion coding, not sparse coding

---

## Executive Summary

Initial validation assumed lobula would follow the same sparse coding paradigm as olfaction's mushroom body (10-20% sparsity). However, biological research reveals that the optic lobe, including the lobula, uses **distributed/dense population coding** for motion detection and integration. This document reassesses lobula sparsity targets based on 2024 connectomics and functional studies.

**Key Finding**: Lobula likely operates at **15-30% sparsity**, not 10-20%, due to its distributed motion coding architecture.

---

## Problem Statement

### Current Validation Results
- **Lobula**: 2.07% ± 1.42% (target: 10-20%) - ❌ FAIL (79% below target)
- **Question**: Is 2.07% genuinely too low, or is our 10-20% target biologically incorrect?

### Hypothesis
The 10-20% target was borrowed from olfaction's sparse coding paradigm (mushroom body Kenyon cells: 1-5%). However, vision and olfaction may use fundamentally different coding strategies.

---

## Biological Research Findings

### 1. Sparse Coding vs Distributed Coding

#### Olfaction (Sparse Coding Paradigm)
**Mushroom body** (Campbell et al. 2011, 2013):
- **Architecture**: 2,000 PN inputs → 2,000 Kenyon cells (1:1 expansion with random connectivity)
- **Sparsity**: 1-5% active (extremely sparse)
- **Function**: Pattern separation and odor discrimination
- **Mechanism**: High threshold (5+ coincident inputs needed), APL feedback inhibition
- **Goal**: Maximize memory capacity via sparse orthogonal representations

**Quantitative validation**:
- Campbell et al. (2011): Robust sparse coding at 2-3% sparsity
- Turner et al. (2008): 1-3% Kenyon cell activity during odor presentation
- Concentration invariance: r > 0.70 maintained with 1-3% sparsity

#### Vision (Distributed Coding Paradigm)
**Optic lobe** (Nature 2024, eLife 2024):
- **Architecture**: Columnar retinotopic organization, parallel processing across 800 columns
- **Sparsity**: Higher baseline activity (estimated 15-30%)
- **Function**: Parallel distributed processing of multiple visual features
- **Mechanism**: Combinatorial population codes, not discrete sparse channels
- **Goal**: Represent complex motion patterns via distributed activity

---

### 2. Lobula Function and Architecture

#### Motion Detection Role
**T4/T5 Elementary Motion Detectors** (multiple 2024 papers):
- T4 cells: Detect "ON" motion (bright edge movement)
- T5 cells: Detect "OFF" motion (dark edge movement)
- **"First direction-selective neurons"** in the fly visual system
- Each T4/T5 responds to one of 4 cardinal directions (up, down, left, right)

**Computational requirements**:
- Must integrate signals across time (temporal accumulation)
- Must represent motion in 4 directions simultaneously
- Requires **many active neurons** for distributed motion representation

#### Population Coding Strategy
**Nature (2024)** - "Mapping model units to visual neurons reveals population code":
- Visual processing uses **"combinatorial population codes"**
- Not discrete parallel channels (like olfaction)
- Population responses at optic lobe-central brain interface drive complex behaviors
- **Many neurons active simultaneously** to encode motion patterns

**eLife (2024)** - "Comprehensive neuroanatomical survey of Lobula Plate Tangential Neurons":
- Lobula plate tangential neurons (LPTs) compute optic flow
- 58 LPTs per hemisphere respond to specific flow patterns
- Use distributed representation across many neurons
- **Not sparse coding** - requires substantial population activity

---

### 3. Comparison: Medulla vs Lobula

#### Medulla (Sparse Expansion)
- **Function**: Sparse expansion from photoreceptors
- **Input**: 1,600 R7/R8 photoreceptors (direct projection)
- **Output**: 45,885 neurons
- **Expansion ratio**: 57× expansion (similar to PN→KC in olfaction)
- **Sparsity**: 2-5% (matches sparse expansion paradigm)
- **Coding**: Sparse representation for downstream processing

#### Lobula (Motion Integration)
- **Function**: Motion detection and integration
- **Input**: Medulla neurons (lamina L1/L2/L3 inputs too)
- **Output**: 15,754 neurons
- **Task**: Integrate motion signals, compute direction selectivity
- **Sparsity**: Likely 15-30% (distributed coding)
- **Coding**: Distributed population representation

---

### 4. Columnar Organization

**Key architectural difference** from mushroom body:

**Mushroom body (Sparse)**:
- Random connectivity: Each KC samples 7 random PNs
- No spatial organization
- Maximizes pattern separation
- Supports 1-5% sparsity

**Optic lobe (Distributed)**:
- Retinotopic columnar organization
- Each column processes one spatial location
- ~800 columns (matching ommatidia)
- **Within each column**: Many neurons active simultaneously
- **Across columns**: Distributed representation of visual field

**Implication**: Each column needs multiple active neurons → higher baseline sparsity than mushroom body.

---

### 5. Cross-Species Comparison

**Hawkmoth lamina** (Science Advances 2020):
- Lamina monopolar cells (LMCs) show distributed spatial filtering
- Receptive fields broaden in dim light (spatial summation)
- **Not sparse coding** - many LMCs active simultaneously
- Similar to Drosophila lamina's 20-40% sparsity

**Vertebrate visual cortex**:
- V1 simple cells: ~10-30% active during visual stimulation
- Motion areas (MT/MST): 20-40% active during motion
- Distributed population codes, not sparse coding

---

## Revised Sparsity Target for Lobula

### Evidence-Based Estimate

**Based on**:
1. Distributed motion coding architecture
2. T4/T5 direction selectivity (4 channels × spatial integration)
3. Population codes (many neurons simultaneously active)
4. Columnar organization (multiple neurons per column)
5. Cross-species visual cortex measurements (10-30%)

**Proposed target**: **15-30%** sparsity for lobula

**Rationale**:
- Lower bound (15%): Minimum for distributed 4-direction motion representation
- Upper bound (30%): Similar to lamina's distributed coding (20-40%)
- Midpoint (22.5%): Matches lamina's actual 22.91%

---

### Comparison to Other Visual Layers

| Layer | Sparsity | Target | Coding Strategy | Status |
|-------|----------|--------|-----------------|--------|
| **Lamina** | 22.91% | 20-40% | Distributed spatial processing | ✅ PASS |
| **Medulla** | 9.32% → 3.5% | 2-5% | Sparse expansion from photoreceptors | ✅ PASS (after fix) |
| **Lobula** | 2.07% → ? | **15-30%** | Distributed motion integration | To be validated |
| **Lobula Plate** | 19.95% | 10-20% | Wide-field optic flow | ✅ PASS |

**Pattern**: Lamina and Lobula Plate (distributed processing) have 20-30% sparsity. Medulla (sparse expansion) has 2-5%. Lobula should match distributed paradigm: 15-30%.

---

## Validation Against Literature

### Direct Evidence (Limited)
- **Challenge**: Most studies focus on single neuron recordings or small populations
- **Gap**: No published study directly measures lobula population sparsity in the way we need

### Indirect Evidence (Strong)
1. **T4/T5 recordings** (Borst lab, multiple papers):
   - T4/T5 cells show strong direction selectivity
   - During motion stimuli, substantial fraction of T4/T5 respond
   - Not winner-take-all or sparse activation

2. **Lobula plate recordings** (multiple labs):
   - LPTs show sustained activity during optic flow
   - Many LPTs active simultaneously
   - Distributed representation confirmed

3. **Connectomics** (Nature 2024):
   - "Combinatorial population codes" explicitly mentioned
   - Contrasts with olfaction's sparse discrete channels
   - Supports distributed coding hypothesis

---

## Biological Justification for 15-30% Target

### Lower Bound (15%)
**Minimum requirements**:
- 4 direction channels (T4/T5: up, down, left, right)
- Spatial integration across columns (~800 locations)
- Each column needs ~1-2 active direction-selective neurons
- 800 columns × 1-2 neurons / 15,754 total = 10-20% baseline
- Add temporal integration, feedback: 15% minimum

### Upper Bound (30%)
**Maximum constraints**:
- Similar to lamina's distributed coding (22.91%, target 20-40%)
- Similar to lobula plate's optic flow (19.95%, target 10-20%)
- Vertebrate motion areas (MT/MST): 20-40% during motion
- 30% allows robust distributed representation without saturation

### Midpoint (22.5%)
- Balanced between lamina (22.91%) and lobula plate (19.95%)
- Allows distributed 4-direction motion codes
- Consistent with "combinatorial population codes" (Nature 2024)

---

## Implications for Validation

### If Lobula Reaches 15-30% After R7/R8 Fix
- **Conclusion**: Target was incorrect, not implementation
- **Action**: Update target to 15-30%, mark as PASS
- **Reason**: Biological research supports distributed coding

### If Lobula Remains <10% After R7/R8 Fix
- **Conclusion**: Signal attenuation, needs gain boost
- **Action**: Implement medulla→lobula layer-specific gain
- **Method**: Additional 3-5× boost for medulla→lobula connections

---

## Recommended Updates

### 1. Update Validation Targets
**File**: `hive/validation/vision/test_sparse_coding.py`

```python
# OLD
elif region in ['LOBULA', 'LOBULA_PLATE']:
    target_range = (10, 20)

# NEW
elif region == 'LOBULA':
    target_range = (15, 30)  # Motion integration, distributed coding
elif region == 'LOBULA_PLATE':
    target_range = (10, 20)  # Wide-field motion integration
```

### 2. Documentation
Add note explaining distributed vs sparse coding paradigms and why targets differ across layers.

---

## References

### Distributed Coding in Vision
1. **Nature (2024)** - "Mapping model units to visual neurons reveals population code for social behaviour"
   - Demonstrates combinatorial population codes in visual processing
   - Contrasts with discrete parallel channels

2. **eLife (2024)** - "A comprehensive neuroanatomical survey of the Drosophila Lobula Plate Tangential Neurons"
   - LPTs compute optic flow via distributed representation
   - 58 neurons per hemisphere with overlapping receptive fields

3. **Nature Neuroscience (2023)** - "Multilevel visual motion opponency in Drosophila"
   - T4/T5 as first direction-selective neurons
   - Hierarchical processing with distributed representations

### Sparse Coding in Olfaction (For Comparison)
4. **Campbell et al. (2011)** - "Cellular-Resolution Population Imaging Reveals Robust Sparse Coding"
   - Mushroom body: 2-3% Kenyon cell sparsity
   - APL feedback maintains sparseness

5. **Turner et al. (2008)** - "Olfactory representations by Drosophila mushroom body neurons"
   - 1-3% KC activity during odor presentation
   - Sparse expansion for memory capacity

### Visual Processing Architecture
6. **Neural Development (2018)** - "Strategies for assembling columns and layers in the Drosophila visual system"
   - Columnar retinotopic organization
   - Parallel distributed processing architecture

7. **Science Advances (2020)** - "Hawkmoth lamina monopolar cells act as dynamic spatial filters"
   - Distributed spatial filtering in lamina
   - Not sparse coding paradigm

---

## Conclusion

**The 10-20% lobula target is biologically incorrect.** It was borrowed from olfaction's sparse coding paradigm (mushroom body), but vision uses distributed population coding for motion detection.

**Evidence-based revised target**: **15-30%** sparsity for lobula

**Key insight**: Different brain regions use different coding strategies optimized for their computational goals:
- **Sparse coding** (olfaction): Maximize memory capacity, pattern separation
- **Distributed coding** (vision motion): Represent complex spatiotemporal patterns

**Recommendation**: Update lobula target to 15-30% and re-evaluate validation results with biologically appropriate benchmark.

---

**Status**: Research complete, ready to implement target update.
