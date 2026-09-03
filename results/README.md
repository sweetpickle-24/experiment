# Results

**Last Updated**: 2026-09-03

Every result artifact produced by this repository, and which claim each one supports.
Nothing here has been deleted. Files that were superseded or that record a failing
run are kept, and labelled.

```
results/
├── final/       current best run for each measurement
├── superseded/  earlier runs, ablations, and controls — kept as evidence
└── logs/        raw run logs
```

**Before quoting anything from here, read the [README](../README.md).** Two defects
affect every olfactory artifact in this directory:

1. **The KC readout imposes sparsity.** A rank threshold keeps exactly 316 of 5,279
   Kenyon cells active for every stimulus, so sparsity is a parameter, not an output.
2. **Three odorants used throughout are absent from DoOR and produce all-zero
   glomerular patterns**: geosmin, isoamyl acetate, ethyl acetate. The client warns
   and returns zeros; callers do not check. A null stimulus still yields 316 "active"
   KCs through the readout, so it looks like a normal result. Every concentration
   invariance file below contains one.

---

## final/

| File | Supports | Key numbers | Date | Caveat |
|---|---|---|---|---|
| `all_validations_results.json` | The five core olfactory benchmarks | temporal peak 275 ms / adaptation 9.05%, mixture overlap 21.04%, JND 5%, similarity `nan`, MBON change 6.61% | **2026-09-03** | **1 of 5 passed.** First run with a recorded config and a fixed seed (`seed 42`, `dt 0.1 ms`, `fast_mode false`, MLX, commit `2e41e13-dirty`). Similarity is `nan` because geosmin's zero pattern has zero variance. The previous unseeded run (2026-03-19, 2 of 5) is in `superseded/`. |
| `concentration_invariance_results.json` | Concentration invariance, final methodology | published mean binary r = 0.7244; **0.5866 excluding the null odor** | 2026-03-15 21:56 | Contains isoamyl acetate, a null stimulus that self-correlates at 1.0000. Must be read with the ablations in `superseded/`. |
| `cpu_vs_mlx_validation.json` | GPU speedup | speedup 86.34×, MLX 1.735 s vs NumPy 149.83 s, sparsity 24.304% vs 24.285% | 2026-03-16 | Records `validation_passed: true` but `pattern_correlation: null` and empty `kc_pattern`. The declared 0.95 correlation criterion was never computed. The speedup holds; output equivalence is untested. |
| `discrimination_300ms_results.json` | Concentration discrimination | mean JND 5.0%, benzaldehyde r=0.461 at +5% | 2026-03-19 09:57 | Records `"validation": "FAIL"` against a 10-20% target. Every step from 5% to 25% marked discriminable, so the threshold was never bracketed — 5% is just the smallest step tested. |
| `full_brain_smell_results.json` | Full-brain scale and activity, 20 odors | 139,255 neurons, 5,342,446 synapses; KC sparsity mean 1.297% (median 1.042%, range 0.076-3.599%); global activity mean 4.02% | 2026-03-13 | This run did **not** apply KC rank normalization, so its sparsity figures are genuine measurements. The often-quoted "1.65%" does not appear in this or any other file. "47.5% olfactory activity" was a misreading of `simulation_time_s: 47.53`, which is seconds. |
| `temporal_dynamics_results.json` | Temporal response profile | peak 120 ms; adaptation 0.370% | 2026-03-17 14:12 | Records adaptation FAIL and onset latency FAIL. Superseded for adaptation by `all_validations_results.json`. |
| `digital_smell_database.json` | KC fingerprints for DoOR odorants | — | 2026-03-16 | Encoding artifact, not a benchmark. |

---

## superseded/

### Concentration invariance ablations

All four ran 2026-03-15 between 21:32 and 21:56. MLX backend, 10,906 neurons,
dt = 0.1 ms, 100 ms per trial, 3 odors × 5 concentrations, unseeded.

| File | Configuration | Published r | Real odors only | Null odor included |
|---|---|---|---|---|
| `concentration_invariance_results_RANDOM.json` | Stochastic reset, linear scaling, no KC normalization — wave dynamics alone | 0.1490 | **0.2007** | ethyl acetate |
| `concentration_invariance_results_DETERMINISTIC_NO_NORM.json` | Deterministic reset, linear scaling, no KC normalization | 0.4759 | 0.2138 | ethyl acetate |
| `concentration_invariance_results_NORM_LINEAR.json` | Deterministic reset, linear scaling, with KC normalization | 0.4424 | 0.1636 | isoamyl acetate |
| (`final/concentration_invariance_results.json`) | Deterministic reset, log scaling, with KC normalization | 0.7244 | **0.5866** | isoamyl acetate |

These are the ablation controls for the headline r = 0.724, and the most important
files in this directory.

**All four included a null odor.** A zero glomerular pattern is identical at every
concentration, so it correlates with itself at exactly 1.0000 across all ten
concentration pairs. In the final run, isoamyl acetate contributes 1.0000 for all ten
pairs while benzaldehyde gives 0.5546 and 2-heptanone 0.6187. The published 0.7244 is
the mean of all thirty; the twenty real-odor pairs average **0.5866, below the 0.70
target the result was reported as passing**.

Recomputed on real odors only, the ablation reads: wave dynamics 0.201, plus
deterministic reset 0.214, plus rank normalization 0.164, plus logarithmic input
compression 0.587. The log transform accounts for essentially all of the gain.

Two further caveats. `_RANDOM` and `_DETERMINISTIC_NO_NORM` used a different odor set
than the other two, so only `_NORM_LINEAR` is a matched control. And only the final
configuration's code is recoverable from git, as `6895ea6`; the three ablations ran
from uncommitted working-tree states.

### Other superseded runs

| File | Supports | Key numbers | Date | Why superseded |
|---|---|---|---|---|
| `similarity_retest_results.json` | Odor-pair similarity | chemical-neural r = **-0.5109** across 6 pairs | 2026-03-16 09:20 | Records `"validation": "FAIL"`. **This is the source of the withdrawn "decorrelation r = -0.51" claim.** The -0.51 is a six-point regression between chemical and neural similarity, not a KC pattern correlation. The actual pattern correlations in this file are -0.013, 0.010, 0.017, 0.044, 0.280, 0.360 — none anticorrelated. A later run measured the same quantity at **+0.632**, the opposite sign. Unresolved. |
| `adaptation_fix_results.json` | Temporal adaptation | mean 5.4% from peak (range 0-14.2%); peak time mean 3033 ms | 2026-03-16 09:34 | Records FAIL on all three criteria. |
| `master_validation_results.json` | Suite orchestration | `successful: 0, failed: 5` alongside `overall_status: "PASS"` | 2026-03-15 22:08 | All five sub-scripts returned null. The status field is a bug. Kept as evidence of that bug. |
| `wave_*.txt`, `fly_brain_*.txt`, `full_brain_*.txt` | Early exploratory runs | — | 2026-03-12 to 03-13 | Pre-validation console dumps from the engine-development phase. `wave_final.txt` is empty (0 bytes). |

---

## logs/

Raw run logs, 31 files. The ones that matter:

| File | What it shows |
|---|---|
| `all_validations.log` | **Every run of the core suite.** Five runs: 2026-03-15 22:12 (3/5), 03-18 16:46 (1/5), 03-19 12:21 (1/5), 12:22 (1/5), 12:23 (2/5). This is the evidence for both the score history and the nondeterminism. |
| `concentration_test_output*.log` | Console output for the four concentration invariance configurations |
| `similarity_retest.log` | Shows 3 of 7 odors skipped as "zero pattern", leaving 4 odors and 6 pairs |
| `adaptation_fix.log` | Per-odor adaptation with the explicit FAIL verdicts |
| `cpu_vs_gpu_proper_test.log`, `cpu_vs_mlx_test.log` | CPU/GPU comparison runs |

**These logs were untracked by git** until 2026-09-03, because `.gitignore` contained
a blanket `*.log`. That exclusion now carries an exception for `results/logs/` so the
evidence travels with the repository.

---

## Claims with no artifact

Quoted in the documentation, traceable to nothing. Do not use them.

| Claim | Status |
|---|---|
| KC sparsity "1.65%" | Appears in no data file. Measured value is 1.297% (`final/full_brain_smell_results.json`), and the validation-path readout imposes 6%. |
| "47.5% olfactory activity" | Misreading of `simulation_time_s: 47.53` — seconds. Actual olfactory active fraction is 13.97% mean. |
| "4.5% global activity" | Measured mean across 20 odors is 4.02%. |
| "53.1% temporal adaptation" | From the 2026-03-19 12:22 run, which the harness recorded as FAIL. The passing run's value is 53.469%. |
| Contrast invariance "r = 0.858" | No result file. The test prints and exits. |
| T4 motion "DSI = 0.975" | Hardcoded in `scripts/generate_vision_figures.py:470,487`. Computed from a hand-written filter, not the wave engine. |
| Chromatic "opponent gap = 0.061" | Hardcoded in `scripts/generate_vision_figures.py:315`. |
| Glomerular "r = +0.89 / +0.81" | Hardcoded in `publication/figures/create_supplementary_figures.py`. |
| Multisensory, prosthetic, auditory-learning, Poisson noise and Poisson spiking figures | Their scripts write JSON only under `__main__`; none of those files exist on disk. |

Of the 19 scripts under `hive/validation/` that contain a `json.dump`, 14 of the
expected output files are absent. Four core vision tests write no file at all.
