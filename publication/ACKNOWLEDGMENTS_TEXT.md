# Acknowledgments Text for Manuscript

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


**To be added to the manuscript before submission**

---

## Acknowledgments Section

We thank Udi Shkolnik (Ehud Sagi Shkolnik) for inspiring discussions on wave physics, quantum mechanics, and the theoretical foundations of wave-based neural computation. His pioneering work on multi-frequency brain dynamics and hive intelligence provided valuable conceptual framework for this research.

We acknowledge the FlyWire Consortium for making the complete fly brain connectome publicly available (Dorkenwald et al., 2024). We thank the DOoR database maintainers (Münch & Galizia, 2016) for olfactory receptor response data.

This work was conducted using consumer hardware (Apple M4 Pro) with the MLX framework, demonstrating that large-scale connectome simulation is accessible without institutional supercomputing resources.

---

## Funding

This work was self-funded with no external grant support. Research was conducted independently without institutional affiliation.

---

## Competing Interests

The author declares that provisional patent applications have been filed for the methods described in this work (USPTO, pending):
1. Memory-Efficient Probabilistic Oscillator Network for Large-Scale Neural Simulation
2. Method and System for Inverse Optimization of Sensory Inputs via Gradient Descent Through Neural Dynamics
3. System and Method for Real-Time Large-Scale Neural Network Simulation Using GPU-Accelerated Sparse Probabilistic Dynamics

No other competing financial or non-financial interests exist. All code will be released under MIT License and all data will be publicly available under CC BY 4.0.

---

## Author Contributions

V.B. conceived the project, developed the methodology, wrote all software, performed all experiments and analyses, and wrote the manuscript. This work was inspired by theoretical discussions on wave physics with Udi Shkolnik.

---

## Data Availability

All data generated in this study are available at [Zenodo DOI to be added]. This includes:
- Full brain olfactory responses (20 odors, 139,255 neurons)
- Digital smell database (glomerular + PN + KC + MBON patterns)
- Concentration invariance test results
- Performance benchmarking data

Source data: FlyWire connectome v783 (https://flywire.ai/), DOoR database (http://neuro.uni.wroc.pl/door).

---

## Code Availability

All software developed for this study is publicly available at [GitHub URL to be added] under MIT License. Archived version with DOI available at [Zenodo DOI to be added].

The repository includes:
- Sparse Probabilistic Wave Brain engine
- Full brain simulation scripts
- Validation test suite
- Figure generation code
- Complete documentation

System requirements: Python 3.9+, 16GB RAM, GPU recommended (Apple MLX, CUDA, or ROCm).

---

**Status:** Ready to copy into manuscript  
**Location:** Add to end of manuscript before references  
**Format:** Adjust formatting to match journal style (Word/LaTeX)
