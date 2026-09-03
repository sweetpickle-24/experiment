# Documentation index

**Last Updated**: 2026-09-03

This is a navigation guide for the documentation in this repository. Start with the
[README](../README.md), which states what the project is, what the results are, and
what they do and do not establish.

---

## Read the README first

The README carries three things you need before reading anything else here:

1. **The KC readout imposes sparsity.** Every olfactory measurement passes through a
   rank threshold that keeps exactly 316 of 5,279 Kenyon cells active regardless of
   stimulus. Numbers in the older documents below were often written without that
   caveat.
2. **Three odorants used throughout produce all-zero stimuli** — geosmin, isoamyl
   acetate and ethyl acetate are absent from the DoOR database and the client returns
   zeros with only a printed warning. One of the core suite's three test odors is one
   of them.
3. **Four of the five olfactory benchmarks did not reproduce their targets** in the
   most recent run (2026-09-03, the first seeded one).
4. **Several widely quoted figures come from analytic filter models, not the wave
   simulation** — specifically T4 motion detection, HS/VS optic flow, and Johnston's
   Organ frequency tuning.

---

## Warning about the documents in this folder

Most files under `docs/`, `research/`, `thesis/`, and `publication/` were written
between March 11 and April 2, 2026, before the claim audit. They contain numbers
that are superseded, unsupported by any result file, or derived from runs the test
harness itself recorded as failing.

A documentation audit in September 2026 corrected the README, `QUICKSTART.md`, and
this file. **The remaining documents have been marked but not rewritten.** Treat any
number in them as unverified unless you have traced it to a file under `results/`.

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
