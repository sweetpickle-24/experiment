# Chapter 3: Methods

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
> Current: [README](../README.md) ·
> [ARCHITECTURE](../ARCHITECTURE.md) ·
> [LIMITATIONS](../docs/03_validation/LIMITATIONS.md) ·
> [audit](../docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md) ·
> [projection repair](../docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md).
> Tracked in [OUTDATED_FILES.md](../OUTDATED_FILES.md).


---

## 3.1 Connectome Extraction

**Source**: FlyWire female adult brain connectome (139,255 neurons, 5.3M synapses)

**Olfactory Pathway Extraction**:
```
Full brain → Filter by cell type → Olfactory neurons

Criteria:
- ORN: Olfactory receptor markers
- PN: Projection neuron types (uPN, mPN, adPN, lPN, vPN)
- LN: Local neurons (inhibitory processing)
- KC: Kenyon cells (KCab, KCg, KC')
- APL: Anterior paired lateral (global inhibition)
- MBON: Mushroom body output
- DAN: Dopaminergic (learning/reward)

Result: 10,906 neurons, 446,388 synapses (7.8% of full brain)
```

## 3.2 Sparse Probabilistic Wave Brain

**Architecture**: Each neuron is a probabilistic oscillator with wave dynamics.

**State Variables** (per neuron):
- `mean_phase` (E[φ]): Expected phase angle
- `mean_velocity` (E[v]): Expected angular velocity  
- `mean_amplitude` (E[A]): Expected oscillation strength
- `var_phase` (Var[φ]): Phase uncertainty
- `var_amplitude` (Var[A]): Amplitude uncertainty

**Wave Equations** (mean-field approximation):
```
∂E[φ]/∂t = E[v]
∂E[v]/∂t = -2γ·E[v] - ω₀²·E[φ] + K·⟨sin(Δφ)⟩ + F_ext
∂E[A]/∂t = -γ·E[A] + |E[v]|·α

Variance evolution (Fokker-Planck):
∂Var[φ]/∂t = 2Var[v] - 2γ·Var[φ] + σ²

Coupling (analytical expectation):
⟨sin(Δφ)⟩ = sin(⟨Δφ⟩)·exp(-Var[Δφ]/2)
```

**Key Innovation**: Tracking distributions (mean, variance) instead of individual neuron states → massive memory savings.

**Parameters**:
- γ = 0.1 (damping)
- ω₀ = 2π·10 Hz (alpha band natural frequency)
- K = connectome synaptic weights
- dt = 0.01 ms

**Memory Efficiency**:
- Full brain (139K neurons): 2.8 MB
- Olfactory (10.9K neurons): 0.2 MB
- Compare to: Dense 3D grid FFT approach → 80 TB (infeasible)

## 3.3 Odor Injection Protocol

**Input**: Glomerular pattern (20 channels, normalized [0-1])

**Injection**:
1. Classify all neurons by type using cell markers
2. Identify 2,198 PN neurons
3. Distribute 20 glomerular channels across PNs (~110 PNs per channel)
4. Inject as external force: `F_ext = glom_pattern[i] × 50.0`

**Source Data**: DOoR database (Database of Odorant Responses)
- 47 odorants × 40 receptor responses
- PCA projection to 20 glomerular channels
- Synthetic data generated for missing entries

## 3.4 Activity Metrics

**Sparsity Threshold**: Neuron is "active" if amplitude > 0.01

**Measurements**:
- PN response: Mean, std, max, active count
- KC sparsity: % active, active count (threshold 0.01)
- MBON output: Mean, max (behavioral drive)

## 3.5 Validation Against Published Data

**Target Metrics** (from literature):
- Turner et al. 2008: 1-3% KC sparsity
- Honegger et al. 2011: ~5% KCs active
- Campbell et al. 2013: 5-10% KCs respond
- Lin et al. 2014: ~200 KCs per odor

## 3.6 GPU Implementation

**Hardware**: Apple M4 Pro with MLX framework
- 20-core GPU, 16 GB unified memory
- Metal Performance Shaders backend

**Optimization Techniques**:
- Sparse connectivity storage (CSR format)
- Vectorized operations on GPU
- Memory-efficient state representation (5 floats per neuron)
- Periodic memory cleanup every 100 steps
