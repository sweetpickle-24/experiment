# Discovery: Hexagonal Lattice Direction Bias in Motion Detection

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


**Date:** 2026-03-18  
**Status:** ✅ COMPLETED — NO HEX BIAS (geometry corrected, test rerun)  
**Test:** `hive/validation/vision/discovery_hex_lattice_direction_bias.py`  
**Runner:** `scripts/run_hex_lattice_bias.py`  
**Data:** `research/vision/findings/discovery_hex_lattice_direction_bias.json`  
**Runtime:** 34.5 minutes (GPU/MLX, 12 directions × 2 phases, 92,632 neurons)

---

## Summary

The motion direction selectivity index (DSI) measured in the Lobula Plate (LP)
shows **no significant bias** aligned with the hexagonal ommatidial lattice axes
(0°, 60°, 120°, 180°, 240°, 300°) vs between-hex directions (30°, 90°, 150°...).

| Result          | Value   |
|-----------------|---------|
| Hex-axis DSI    | −0.0068 |
| Between-hex DSI | +0.0071 |
| Hex bias        | −0.0139 |
| t-test p-value  | 0.242   |
| Significant?    | **NO**  |

This confirms the theoretical prediction: a regular hex lattice is isotropic
(all directions sample the grating with equal quality), and the T4/T5 4-fold
circuit symmetry cancels any residual hex effect. **Square-grid models are valid
approximations for Drosophila motion detection.**

---

## ⚠️ Previous Results Were Invalid — Geometry Bug Fixed

The first run (also 2026-03-18) was invalidated by a critical geometry bug:

**Bug:** `build_hex_ommatidium_positions()` used wrong lattice proportions:
```
WRONG:   col_spacing = 9°,   row_spacing = 2°     → aspect ratio 4.5 (not hex!)
CORRECT: col_spacing = 4.5°, row_spacing = 3.897°  → aspect ratio 1.155 = 2/√3 ✓
```

A regular hexagonal lattice requires `row_spacing = col_spacing × √3/2`.
The wrong grid had **0° and 90° as its symmetry axes**, not 0° and 60°.
The "hex axis" labels were assigned to geometrically wrong directions — making
the hex-vs-between-hex comparison meaningless.

**Test directions bug:** Previous test used 22.5°-spaced directions (0°, 22.5°,
45°, ...) which did NOT include true hex axes 60°, 120°, 240°, 300°.
Fixed to **30°-spaced** directions (0°, 30°, 60°, ..., 330°) which directly
samples all 6 hex axes and all 6 between-hex midpoints.

---

## Geometry of the Corrected Hex Lattice

```
Lattice constant:  a = 4.5°          (≈ Drosophila inter-ommatidial angle, Buchner 1971)
Column spacing:    4.5°  (= a)
Row spacing:       3.897° (= a × √3/2)   ← KEY FIX
Odd row offset:    2.25° (= a/2)
Total ommatidia:   891
Field of view:     ±90° azimuth × ±40° elevation
```

With this geometry, all 6 nearest neighbors of any ommatidium are at **equal
distance a = 4.5°** in directions 0°, 60°, 120°, 180°, 240°, 300°. This is the
defining property of a regular hexagonal lattice.

---

## Spatial Coherence (Rayleigh Metric)

**Coherence = 1 − R**, where R = |mean(exp(i×φ))| over all ommatidium phases.

For a regular hex lattice with T/a = 30°/4.5° ≈ 6.7, phases are nearly
uniformly distributed for ALL directions — confirming isotropy:

| Direction | Coherence | Classification |
|-----------|-----------|----------------|
| 0°        | 0.9877    | HEX AXIS       |
| 30°       | 0.9902    | between-hex    |
| 60°       | 0.9983    | HEX AXIS       |
| 90°       | 0.9505    | between-hex    |
| 120°      | 0.9983    | HEX AXIS       |
| 150°      | 0.9902    | between-hex    |
| 180°      | 0.9877    | HEX AXIS       |
| 210°      | 0.9902    | between-hex    |
| 240°      | 0.9983    | HEX AXIS       |
| 270°      | 0.9505    | between-hex    |
| 300°      | 0.9983    | HEX AXIS       |
| 330°      | 0.9902    | between-hex    |

All values ≥ 0.95 — hex lattice is isotropic at this spatial scale. The small
variation (0.9505 vs 0.9983) shows that pure vertical sampling (90°/270°)
is marginally less uniform due to within-row clustering, but not meaningfully.

---

## Simulation Results

| Direction | DSI     | Classification |
|-----------|---------|----------------|
| 0°        | −0.0089 | HEX AXIS       |
| 30°       | +0.0063 | between-hex    |
| 60°       | −0.0287 | HEX AXIS       |
| 90°       | −0.0210 | between-hex    |
| 120°      | −0.0162 | HEX AXIS       |
| 150°      | +0.0427 | between-hex    |
| 180°      | +0.0194 | HEX AXIS       |
| 210°      | +0.0149 | between-hex    |
| 240°      | +0.0035 | HEX AXIS       |
| 270°      | −0.0093 | between-hex    |
| 300°      | −0.0099 | HEX AXIS       |
| 330°      | +0.0093 | between-hex    |

**Summary statistics:**
- Hex-axis mean DSI = **−0.0068** ± 0.0158
- Between-hex mean DSI = **+0.0071** ± 0.0205
- Bias (hex − between-hex) = **−0.0139** (hex axes are *slightly* more negative)
- t-test: t = −1.24, p = 0.242 → **NOT significant**
- All |DSI| < 0.05 — LP is effectively isotropic

---

## Why No Bias — Two Reasons

### 1. Isotropic Hex Sampling (Input Level)

A regular hexagonal lattice is the optimal 2D sampling arrangement, precisely
because it has **equal resolution in all directions**. For spatial period T >> a
(here T/a = 6.7), the grating drives all ommatidia with equal sampling quality
regardless of direction. Coherence ≈ 1 everywhere (confirmed above).

### 2. T4/T5 4-Fold Circuit Symmetry (Processing Level)

T4 neurons have **4 preferred directions** (0°, 90°, 180°, 270°), not 6-fold.
The LP response sums T4a + T4b + T4c + T4d. Each group:
- Hex axes (0°, 60°, 120°, 180°, 240°, 300°): contain T4 axes 0° and 180° (2/6 = 33%)
- Between-hex (30°, 90°, 150°, 210°, 270°, 330°): contain T4 axes 90° and 270° (2/6 = 33%)

Both groups have **equal representation of T4-aligned directions** → any 4-fold
T4 bias cancels perfectly across the two groups.

### Combined Effect

Even if there were a weak hex lattice effect on photoreceptor sampling, the T4
circuit processing erases it. The LP population response is determined by the
T4/T5 connectome architecture, not the input sampling geometry.

---

## Notable Pattern: 2-Fold Asymmetry

While there is no 6-fold hex bias, the DSI values show a weak **2-fold
(180°-periodic) trend**:
- Positive DSI cluster: 150° (+0.0427), 180° (+0.0194), 210° (+0.0149)
- Negative DSI cluster: 60° (−0.0287), 90° (−0.0210), 120° (−0.0162)

This 2-fold pattern likely reflects a **natural front-to-back vs back-to-front
motion asymmetry** in the fly visual system. Front-to-back motion (≈150°) drives
stronger LP responses than back-to-front motion (≈60°) — consistent with the
optomotor reflex stabilizing forward flight (Borst 2014).

**Note on Fourier analysis bug:** The JSON field `sixfold_power_fraction = 0.382`
is incorrectly labeled — the code used `k=2` (2-fold, period 180°) instead of
`k=6` (6-fold, period 60°) for 12 directions at 30°-spacing. The true 6-fold
power fraction is ≈0.139 (13.9%), computed as |rfft[6]|² / total, consistent
with noise. The 2-fold fraction of 0.382 matches the observed 150°-60° antisymmetry.

---

## Conclusion

**Result: NO SIGNIFICANT HEX LATTICE DIRECTION BIAS**

1. The corrected equilateral hex lattice is isotropic (coherence ≈ 1 for all directions)
2. LP DSI shows no significant difference between hex axes and between-hex directions (p = 0.242)
3. A weak 2-fold front-to-back asymmetry exists — likely a real connectome property (optomotor reflex), not a sampling artifact
4. **Square-grid models are valid** for Drosophila motion detection modeling
5. No behavioral prediction of 6-fold optomotor anisotropy

**What this rules out:** Photoreceptor hex lattice geometry does NOT contribute
measurably to direction selectivity at the population level. Any directional
biases in fly behavior are circuit properties, not input geometry properties.

---

## References

- Kirschfeld, K. (1967). Die Projektion der optischen Umwelt auf das Raster der
  Rhabdomere im Komplexauge von Musca. *Experimental Brain Research* 3: 248-270.
- Buchner, E. (1971). Dunkelanregung des stationaeren Fluges der Fruchtfliege.
  *Diplom Thesis, Tuebingen.* (inter-ommatidial angle ≈ 5°)
- Borst, A. & Euler, T. (2011). Seeing things in motion. *Neuron* 71: 974-994.
  (T4/T5 preferred directions at 0°, 90°, 180°, 270°)
- Borst, A. (2014). Fly visual course control: behaviour, algorithms and circuits.
  *Nature Reviews Neuroscience* 15: 590-599.
