# Updated Files Log

**Date**: 2026-09-03
**Last Updated**: 2026-09-03

Audit trail of markdown and result-artifact changes. See `OUTDATED_FILES.md` for
files known to still need updating.

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
