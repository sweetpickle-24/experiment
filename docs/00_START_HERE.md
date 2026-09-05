# Documentation index

**Last Updated**: 2026-09-05

This is a navigation guide for the documentation in this repository. Start with the
[README](../README.md), which states what the project is, what the results are, and
what they do and do not establish.

---

## The five current documents

Everything below this list is either historical or specialised. These five are
current as of 2026-09-05, and between them they carry every claim the project makes:

| Document | What it is for |
|---|---|
| [README](../README.md) | what the project is, how the pipeline works, current results |
| [03_validation/LIMITATIONS.md](03_validation/LIMITATIONS.md) | twelve constraints on what the numbers can support |
| [03_validation/BENCHMARK_VALIDITY_AUDIT.md](03_validation/BENCHMARK_VALIDITY_AUDIT.md) | every benchmark target checked against the paper it cites |
| [03_validation/GLOMERULAR_PROJECTION_REPAIR.md](03_validation/GLOMERULAR_PROJECTION_REPAIR.md) | the input-pipeline repair and the 2/5 → 5/5 ablation ladder |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | how the system is built, stage by stage |

Plus [results/README.md](../results/README.md), which records which artifact backs
which claim — including the claims that have no artifact.

## Four things to know before reading anything else

1. **The scored suite is 5/5**, on the current input pipeline
   (`results/final/all_validations_G2.json`). It was 2/5 before the input projection
   was corrected, and the ladder between those two numbers is documented. Any other
   score you find in this repository — 1/5, 3/5, 9/9, 13/13, 27/27 — is either
   historical or was never produced by a run.
2. **Kenyon cell sparsity is imposed by the readout, not produced by the
   simulation.** A rank threshold keeps exactly 310 of 5,177 cells active regardless
   of stimulus. Numbers in the older documents below were generally written without
   that caveat.
3. **Kenyon cell identities do not converge under timestep refinement.** Active-set
   overlap against a ten-times finer step is a Jaccard index of 0.4827, and refining
   further does not help. Benchmarks remain valid as *comparisons*; absolute
   identities are not properties of the equations.
4. **Several widely quoted vision and auditory figures come from analytic filter
   models, not the wave simulation** — T4 motion detection, HS/VS optic flow, and
   Johnston's Organ frequency tuning. They are filter implementations, not tests of
   the connectome, and they are not part of the scored suite.

One thing that is **no longer** true and appears in older documents: missing odorants
used to return an all-zero stimulus silently. `DoorClient` now raises
`OdorantNotFoundError`, so a null stimulus cannot enter a run undetected.

---

## Warning about the documents in this folder

Most files under `docs/`, `research/`, `thesis/`, and `publication/` were written
between March 11 and April 2, 2026, before the claim audit. They contain numbers
that are superseded, unsupported by any result file, or derived from runs the test
harness itself recorded as failing.

Documentation audits in September 2026 rewrote the five documents listed above.
**The remaining documents carry a correction banner but have not been rewritten.**
Treat any number in them as unverified unless you have traced it to a file under
`results/`. [OUTDATED_FILES.md](../OUTDATED_FILES.md) lists which and why.

Specifically, do not rely on these figures if you encounter them:

| Figure | Problem |
|---|---|
| "1.65% KC sparsity" | Appears in no result file. Sparsity is imposed by the readout. |
| "53.1% temporal adaptation" | Comes from a run the harness recorded as FAIL. |
| "47.5% olfactory activity" | Misreading of `simulation_time_s: 47.53` — seconds, not percent. |
| "4.5% global activity" | Measured mean across 20 odors is 4.02%. |
| "r = -0.51 anticorrelated neural codes" | The -0.51 is a 6-point regression between chemical and neural similarity, not a code correlation. No anticorrelated code exists in the data. |
| "9/9", "13/13", "14/14", "27/27" | No run ever produced these. The best recorded was 3/5; the most recent, and first seeded, run gave 1/5. |
| "Concentration invariance r = 0.724" | Includes a null-stimulus odor that self-correlates at 1.0. On real odors the value is 0.587, below the 0.70 target. |

---

## Documents that exist

### Setup
- [`01_setup/HOW_TO_RUN.md`](01_setup/HOW_TO_RUN.md)
- [`01_setup/TESTING_GUIDE.md`](01_setup/TESTING_GUIDE.md)

### Architecture
- [`02_architecture/PROBABILISTIC_WAVE_IMPLEMENTATION.md`](02_architecture/PROBABILISTIC_WAVE_IMPLEMENTATION.md) — the oscillator model
- [`02_architecture/MLX_GPU_IMPLEMENTATION.md`](02_architecture/MLX_GPU_IMPLEMENTATION.md) — GPU backend
- [`02_architecture/WAVE_NATIVE_IMPLEMENTATION.md`](02_architecture/WAVE_NATIVE_IMPLEMENTATION.md)
- [`02_architecture/WAVE_ENHANCED_COMPLETE.md`](02_architecture/WAVE_ENHANCED_COMPLETE.md)
- [`02_architecture/FORMULA_VALIDATION.md`](02_architecture/FORMULA_VALIDATION.md)
- [`02_architecture/SPARSE_CODING_THEORY.md`](02_architecture/SPARSE_CODING_THEORY.md) — background theory; note its sparsity figures are imposed by the readout, not measured

The engine source is the most reliable description of what actually runs:
`hive/engine/sparse_probabilistic.py`.

### Validation
The authoritative record is the README plus the raw artifacts under `results/`. The
files below predate the audit and overstate their outcomes.

- [`03_validation/FINAL_VALIDATION.md`](03_validation/FINAL_VALIDATION.md)
- [`03_validation/FINAL_VALIDATION_COMPLETE.md`](03_validation/FINAL_VALIDATION_COMPLETE.md)
- [`03_validation/FINAL_VALIDATION_STATUS.md`](03_validation/FINAL_VALIDATION_STATUS.md)
- [`03_validation/VALIDATION_RESULTS_SUMMARY.md`](03_validation/VALIDATION_RESULTS_SUMMARY.md)

### Findings
- [`04_discoveries/FULL_BRAIN_FINDINGS.md`](04_discoveries/FULL_BRAIN_FINDINGS.md)
- [`04_discoveries/ALL_NOVEL_DISCOVERIES.md`](04_discoveries/ALL_NOVEL_DISCOVERIES.md)
- [`04_discoveries/FULL_IMPLEMENTATION_COMPLETE.md`](04_discoveries/FULL_IMPLEMENTATION_COMPLETE.md)

These are framed as discoveries. No priority claim in them has been checked against
a literature review, and the two headline items rest on runs recorded as failures.

### Write-ups
- [`05_publication/MANUSCRIPT_PUBLICATION.md`](05_publication/MANUSCRIPT_PUBLICATION.md)
- [`05_publication/EXECUTIVE_SUMMARY.md`](05_publication/EXECUTIVE_SUMMARY.md)
- [`05_publication/PUBLICATION_SUMMARY.md`](05_publication/PUBLICATION_SUMMARY.md)

Drafts only. Nothing has been submitted anywhere.

### Status
- [`06_status/POC_STATUS.md`](06_status/POC_STATUS.md)
- [`06_status/NEXT_STEPS.md`](06_status/NEXT_STEPS.md)
- [`06_status/WHY_NO_PARALLEL.md`](06_status/WHY_NO_PARALLEL.md)
- [`06_status/AUTHOR_INFO.md`](06_status/AUTHOR_INFO.md)

---

## Where the actual evidence is

| Question | File |
|---|---|
| Most recent full validation run | `results/final/all_validations_results.json`, `results/final/all_validations.log` |
| Concentration invariance, final configuration | `results/final/concentration_invariance_results.json` |
| Concentration invariance ablations | `results/superseded/concentration_invariance_results_*.json` |
| CPU vs GPU timing | `results/final/cpu_vs_mlx_validation.json` |
| Full-brain run, 20 odors | `results/final/full_brain_smell_results.json` |
| Cross-language timing | `benchmarks/real_connectome/`, `benchmarks/smell_test/` |

`results/README.md` maps each file to the claim it supports.
