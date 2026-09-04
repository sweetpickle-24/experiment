# Updated Files Log

**Date**: 2026-09-03
**Last Updated**: 2026-09-04

Audit trail of markdown and result-artifact changes. See `OUTDATED_FILES.md` for
files known to still need updating.

---

## Updates on 2026-09-04

### Benchmark validity repair: every target checked against its source paper

**Reason**: the five olfactory benchmarks were scored against targets that, in
four cases, are not in the papers they cite; one citation does not exist at all.
The model also had no trial-to-trial variability under the protocol every
benchmark used, so all five were single-sample measurements with a noise floor of
exactly r = 1.0.
**Files created**: 2 markdown, 12 result artifacts, 10 code modules and tests
**Files updated**: 5 markdown

Markdown:
- [x] `docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md` - Created. Per benchmark:
      the target it was scored against, what the cited paper actually reports
      quoted verbatim with figure references, the verdict, and the measured
      result. Plus the cross-cutting defects and the "what is still broken"
      section.
- [x] `UPDATED_FILES_LOG.md` - This entry.
- [x] `OUTDATED_FILES.md` - Updated: the concentration-invariance and validation-
      score categories now point at the repaired measurements, and a new
      category lists the documents that quote the four misattributed targets.
- [x] `QUICKSTART.md` - Added the interpreter section (`.venv/bin/python`;
      the system interpreter lacks scikit-learn); replaced the 86x speedup with
      the verified 10.00x; replaced "150 seconds per 100 ms" and "0.17 seconds"
      with the measured 4.87 s (CPU) and 0.49 s (MLX); removed the claim that
      the suite is unseeded.
- [x] `README.md` - Added a pointer to the validity audit at the top of the
      validation discussion.
- [x] `.cursor/rules/Findings.mdc` - Added the 2026-09-04 findings block.

Result artifacts created under `results/final/`:
- [x] `all_validations_F9_corrected.json` - The repaired suite: 2/5, with the F8
      verdict beside each benchmark and the configuration-agreement check.
- [x] `learning_repaired.json` - Hige et al. 2015 rebuild. FAIL: depression and
      dopamine-dependence pass, specificity fails at p = 0.3227 with d = 0.038.
- [x] `similarity_repaired.json` - Campbell 2013 Fig 4C plus Turner 2008 Fig 5.
      FAIL: ordering wrong in Part A, Part B passes at p = 0.0197.
- [x] `discrimination_repaired.json` - Campbell 2013 blend series. FAIL:
      non-monotone in the middle, correct at both ends.
- [x] `temporal_repaired.json` - PASS: onset 50.0 ms on 8/8 trials, phasic at
      p = 0.0039.
- [x] `mixtures_repaired.json` - Honegger 2011 Fig 7. PASS: both published pairs
      sub-additive.
- [x] `concentration_invariance_repaired.json` - Both quantities: pattern
      correlation r = 0.5417, and the pinned sparseness 0.059860 that shows why
      Honegger's actual measurement cannot be tested here.
- [x] `cpu_vs_mlx_fullrun.json` - Backend equivalence over 2000 ms. Fails the
      pre-declared rule: worst Jaccard 0.1030, worst r 0.0650.
- [x] `mbon_weight_monotonicity.json` - The MBON amplitude field is not monotone
      in KC->MBON weight (rho = -0.0182); the coupling current is (rho = 1.0000).
- [x] `kc_odor_specificity.json` - Why depression is not odour-specific: the raw
      KC field is non-zero on all 5,279 KCs and the sparse code carries only
      12.5-14.1 % of it.
- [x] `dt_convergence_fixed_stimulus.json` - Convergence with the stimulus held
      fixed in real time. r = 0.6758, Jaccard = 0.4827, non-monotone in dt.
- [x] `temporal_dynamics_standalone.json` - First ever output from the fifth
      standalone test, revived.

Result artifacts moved to `results/superseded/`:
- [x] `concentration_invariance_results.json` - r = 0.724, inflated by a null
      odorant that self-correlates at 1.0000.
- [x] `temporal_dynamics_results.json` - superseded protocol.
- [x] `all_validations_results.json` - unseeded, NaN similarity.
- [x] `full_brain_smell_results.json` - empty `kc_response` exports.
- [x] `discrimination_300ms_results.json` - superseded protocol.

Files retired to `archive/dead_tests/`:
- [x] `tests/fix_adaptation.py`, `tests/fix_similarity_test.py` - both dead, both
      still requested `geosmin`, both superseded.

Code created:
- [x] `benchmark_harness.py` - Shared stochastic-trial harness: 8 trials per
      stimulus on declared seeds, seed-matched separability against the
      within-stimulus replicate null, and the 12-odorant panel with each entry's
      paper provenance.
- [x] `benchmarks_repaired/{learning,similarity,discrimination,temporal,
      mixtures,concentration_invariance}.py` - The rebuilt benchmarks.
- [x] `scripts/run_repaired_suite.py` - Aggregates the five result files and
      refuses to score files that disagree on configuration.
- [x] `tests/test_benchmark_harness.py` - Harness checks including null
      calibration.
- [x] `tests/test_weights_on_signal_path.py` - Regression test for the compiled-
      kernel weight capture.
- [x] `tests/test_cpu_vs_mlx_fullrun.py` - Full-length backend equivalence.
- [x] `tests/test_dt_convergence_fixed_stimulus.py` - Convergence with the
      stimulus decoupled from dt.
- [x] `tests/diagnose_mbon_weight_monotonicity.py`,
      `tests/diagnose_kc_odor_specificity.py` - Supporting diagnostics.

Code changed:
- `hive/engine/sparse_probabilistic.py` - Synaptic weights are now an argument to
  the compiled MLX step rather than captured in its closure, so plasticity
  reaches the kernel; region-index lookup cached (0.271 s -> 0.05 ms per readout,
  bit-identical output).
- `validation_utils.py` - `assert_reportable_environment` fails before the
  connectome load when scikit-learn is absent, naming the interpreter to use.
- `tests/validate_temporal_dynamics.py` - Revived onto
  `legacy_validation_support`; was still requesting `geosmin` and writing a bare
  JSON to the working directory.
- `tests/validate_learning_plasticity.py` - `'num_trials': 10-20` evaluated to
  -10 in every result file it wrote.
- `tests/test_cpu_vs_mlx.py` - The KC pattern was stored only when shorter than
  1000 values and there are 5,279 KCs, so the correlation block was unreachable
  and the run reported PASS against a threshold it never evaluated.

---

## Updates on 2026-09-03

### Deterministic MLX and a repaired odour stimulus path
**Reason**: MLX same-seed runs were not reproducible; the reported 86.34x
speedup was unusable; the odour stimulus path bypassed the plume, carrier and
receptor adaptation entirely. Seven fixes, each measured in isolation.
**Files created**: 3 markdown, 12 result artifacts, 6 tools
**Files updated**: 0 markdown (see `OUTDATED_FILES.md` - several existing
documents now contradict these measurements and are listed there rather than
edited in this session)

Markdown:
- [x] `docs/03_validation/DETERMINISM_AND_STIMULUS_PATH.md` - Created. Full
      report: what each of the seven fixes changed, the verified 10.00x
      speedup, the 1/5 -> 2/5 score, and eight things still broken.
- [x] `UPDATED_FILES_LOG.md` - Created (this file). The doc-tracking rule
      required it and it did not exist.
- [x] `OUTDATED_FILES.md` - Created. Lists the documents whose claims these
      measurements contradict.

Result artifacts created under `results/final/`:
- [x] `fix_ledger.json` - One entry per fix: every benchmark value beside the
      threshold it is judged against, the concentration-invariance block, and
      stimulus-path diagnostics. Entries F0_before through F8_final.
- [x] `mlx_determinism.json` - 5 same-seed trials per backend; both bit-for-bit
      identical on all four state fields and the KC readout.
- [x] `cpu_vs_mlx_speedup.json` - Matched-configuration timing. 10.00x median,
      range 9.96-10.03x, output agreement Jaccard 1.0000.
- [x] `dt_convergence.json` - Phase advance per step across a dt sweep, and the
      finding that the solution does not converge under dt refinement.
- [x] `legacy_vs_suite_comparison.json` - The four revived tests against the
      suite: 3/4 verdicts agree, all three that share a criterion agree.
- [x] `all_validations_F{0,1,3,4,5,6}_after.json`,
      `all_validations_F8_final.json` - Suite run per fix.
- [x] `concentration_invariance_F{0,1,3,4,5,6}_after.json`,
      `concentration_invariance_F8_final.json` - Invariance run per fix.
- [x] `discrimination_threshold_results.json`, `odor_similarity_results.json`,
      `odor_mixtures_results.json`, `learning_plasticity_results.json` - First
      ever output from the four previously dead tests, now with provenance
      blocks. Previously these scripts json.dump'd to bare filenames in the
      working directory; those root-level copies were removed.

Result artifacts moved:
- [x] `results/final/cpu_vs_mlx_validation.json` -> `results/superseded/` -
      Recorded 1,283 active KCs against a few hundred in current runs, a null
      `pattern_correlation`, an empty `kc_pattern`, and
      `validation_passed: true` against a 0.95 correlation threshold it never
      evaluated. Its 86.34x is discarded.

Tools created:
- [x] `scripts/fix_ledger.py` - Records one labelled before/after entry per fix.
- [x] `scripts/ledger_report.py` - Renders the ledger as a comparison table.
- [x] `scripts/compare_legacy_vs_suite.py` - Cross-checks the revived tests.
- [x] `tests/test_mlx_determinism.py` - Same-seed reproducibility evidence.
- [x] `tests/test_cpu_vs_mlx_speedup.py` - Replaces the discarded measurement.
- [x] `tests/test_dt_convergence.py` - Aliasing and dt-convergence check.
- [x] `tests/legacy_validation_support.py` - Adapter for the four revived tests.

Code changed (not markdown, listed for completeness):
- `hive/engine/sparse_probabilistic.py` - Deterministic segment reduction
  replacing atomic scatter-add; time-varying odour stimulus; amplitude guard
  made explicit and lifted off the signal path; glomerular mapping by position.
- `hive/interface/olfactory.py` - Carrier units fix; `OdorStimulusDriver`;
  `load_olfactory_config`.
- `hive/data/door_client.py` - Explicit projection selection, no silent
  fallback; `project_to_pca_basis` added.
- `validation_utils.py` - Reproducibility guard now checks the accumulation
  layout rather than the backend name; richer provenance.
- `scripts/run_all_validations.py`, `tests/concentration_invariance_test.py` -
  `projection` and `glomerular_mapping` parameters; corrected the stale
  "150 s per 100 ms" runtime note to the measured 4.8 s.
- `tests/validate_{discrimination_threshold,odor_similarity,odor_mixtures,
  learning_plasticity}.py` - Revived; write through `write_results`.
