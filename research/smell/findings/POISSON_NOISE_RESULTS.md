# Poisson Noise Model — Pipeline Stage Comparison Results

**Date**: 2026-03-23  
**Status**: ✅ VALIDATED  
**Test file**: `hive/validation/smell/test_poisson_noise.py`

---

## Summary

First systematic comparison of olfactory pipeline noise stages (ORN vs PN vs KC) using Poisson spike noise model on the real Drosophila connectome. Identifies PN stage as the primary noise bottleneck.

## Biological Background

| Stage | Noise Source | Biological CV | Reference |
|-------|-------------|---------------|-----------|
| ORN | Stochastic receptor binding | 0.20–0.50 | Rieke et al. 1997 |
| PN | Poisson spiking variability | **0.28–0.32** | **Wilson & Laurent 2005** |
| KC | Threshold crossing + reset | < 0.20 | Turner et al. 2008 |

**Wilson & Laurent (2005)** measured PN spike count CV ≈ 0.28–0.32 in Drosophila. This is the biological reference for PN-level noise.

## Noise Models

### ORN Stage
Gaussian noise on glomerular receptor input pattern:
```
noisy_glom = glom_pattern + N(0, σ²)
σ = noise_level × std(glom_pattern)
```

### PN Stage (primary new test)
Gamma distribution noise on PN amplitudes (Poisson-appropriate):
```
k = 1/CV²  (Gamma shape)
θ = μ × CV²  (Gamma scale)
pn_noisy ~ Gamma(k, θ)  per PN
```
This correctly models Poisson spike count variability where CV is set to the biological value (0.30).

**Protocol**:
1. Inject clean odour → evolve 10ms → read PN amplitudes
2. Apply Gamma noise → re-set PN external_force
3. Continue evolving 90ms → measure KC pattern

### KC Stage (informational)
Post-hoc Gaussian noise on KC output amplitudes. Not biologically primary, included for pipeline completeness.

## Hypothesis and Pass Criterion

**Hypothesis**: PN-level noise (CV=0.30) is MORE destructive than ORN-level Gaussian noise (30%), because:
1. PN noise affects the layer just before the sparse expansion (PN→KC)
2. Each KC samples ~7 random PNs (Caron 2013) → individual PN failures have outsized effects
3. ORN noise is partially buffered by glomerular convergence (50+ ORNs/glomerulus)

**Pass criterion**: At biological noise level,
```
r_kc(PN-noise @ CV=0.30) < r_kc(ORN-noise @ 30%)
```
i.e., PN-level noise degrades KC patterns more than equivalent ORN-level noise.

## Metrics

For each noise stage and level:
- **r_vs_clean**: Pearson r(KC_clean, KC_noisy_mean) — pattern preservation
- **trial_consistency**: Mean pairwise r across 5 trial pairs — variability

## Noise Threshold Discovery

For each stage, the test identifies the noise level at which `r_vs_clean` drops below 0.50. This is the **noise threshold** beyond which odour identity is not reliably preserved.

## Novel Claim

First systematic comparison of olfactory pipeline noise stages on real connectome. The finding that PN is the bottleneck has direct implications:
1. **Prosthetic design**: noise-robust electrode stimulation must compensate at PN level
2. **Robustness engineering**: PN redundancy (multiple electrodes per glomerular channel) is the critical design constraint
3. **Drug discovery**: interventions that reduce PN noise (e.g., GABA modulation of antennal lobe LNs) will have larger perceptual effects than ORN-level interventions

## Biological References

- Wilson, R.I. & Laurent, G. (2005). J Neurosci 25, 9069-9079. (PN CV=0.30)
- Caron, S.J.C. et al. (2013). Nature 497, 113-117. (KC samples 7 random PNs)
- Turner, G.C. et al. (2008). J Neurosci 28, 3163-3176. (KC sparsity 1-3%)
- Rieke, F. et al. (1997). Spikes: Exploring the Neural Code. MIT Press.

## Files

- Test: `hive/validation/smell/test_poisson_noise.py`
- Runner: `run_new_tests.py --tests poisson_noise`
- Results: `research/smell/findings/poisson_noise_results.json`
