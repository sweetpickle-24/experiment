# Outdated Files

**Date**: 2026-09-03
**Last Updated**: 2026-09-03

Files whose claims are contradicted by measurements in
`docs/03_validation/DETERMINISM_AND_STIMULUS_PATH.md`. Listed rather than
edited, because correcting them is a documentation pass of its own and
rewriting a publication draft is not part of the fix work that produced these
numbers.

---

## Files Needing Updates

### Category: the discarded 86.34x speedup

`results/final/cpu_vs_mlx_validation.json` has been moved to
`results/superseded/`. It recorded 1,283 active KCs against a few hundred in
current runs, a null `pattern_correlation`, an empty `kc_pattern`, and
`validation_passed: true` against a 0.95 correlation threshold it never
evaluated.

The verified replacement is **10.00x** (median, range 9.96-10.03x), measured at
matched configuration in `results/final/cpu_vs_mlx_speedup.json`.

- [ ] `publication/CPU_VS_GPU_FINAL_VALIDATION.md` - built entirely on the
      discarded measurement, including the 1,283 vs 1,282 active-KC comparison
      and the 0.019% sparsity difference
- [ ] `publication/CPU_GPU_VALIDATION_COMPLETE.md` - same
- [ ] `publication/CPU_GPU_DOCUMENTATION_UPDATE.md` - same
- [ ] `publication/EXECUTIVE_SUMMARY.md` - quotes the 86x figure
- [ ] `publication/MANUSCRIPT_PUBLICATION.md` - quotes the 86x figure
- [ ] `publication/MANUSCRIPT_FORMATTED.docx.md` - quotes the 86x figure
- [ ] `publication/FIGURES_SUMMARY.md` - figure captions cite 86x
- [ ] `publication/FIGURES_COMPLETE_REPORT.md` - same
- [ ] `ARCHITECTURE.md` - quotes the 86x figure
- [ ] `QUICKSTART.md` - quotes the 86x figure
- [ ] `research/POC_STATUS.md` - quotes the 86x figure
- [ ] `research/MONETIZATION_IDEAS.md` - quotes the 86x figure
- [ ] `.cursor/rules/Findings.mdc` - "CPU vs GPU Hardware Independence" section
      records 86x, 1,283 vs 1,282 active KCs, and 0.019% sparsity difference,
      all from the superseded file

### Category: MLX reproducibility

MLX was non-reproducible; it is now bit-for-bit identical across same-seed
runs, evidence in `results/final/mlx_determinism.json`. Anything asserting
CPU-GPU *equivalence* on the basis of the old 0.019% sparsity difference is
citing a run that cannot be reproduced. The correct current statement is that
each backend is individually reproducible and the two agree on the active-KC
set exactly (Jaccard 1.0000) while not being bit-identical to each other.

- [ ] `publication/CPU_VS_GPU_FINAL_VALIDATION.md`
- [ ] `.cursor/rules/Findings.mdc`

### Category: validation score

The five-benchmark suite scores **2/5** at seed 42 on CPU
(`results/final/fix_ledger.json`, entry `F8_final`), up from 1/5.

- [ ] `ARCHITECTURE.md` - claims 27/27 benchmarks complete
- [ ] `docs/00_START_HERE.md` - claims 27/27
- [ ] `archive/README.md` - claims 27/27
- [ ] `.cursor/rules/Findings.mdc` - claims 27/27 with a 100% success rate
- [ ] `research/validation/FINAL_VALIDATION_COMPLETE.md`
- [ ] `research/findings/FULL_BRAIN_FINDINGS.md`
- [ ] `research/ALL_NOVEL_DISCOVERIES.md`
- [ ] `docs/03_validation/FINAL_VALIDATION.md`

### Category: concentration invariance

Every recorded run of this repository's concentration-invariance test at seed
42 returns a *weak* verdict. Best measured value after all fixes is binary
r = **0.2719** (`results/final/fix_ledger.json`, entry `F8_final`), against
0.5 for moderate and 0.7 for strong.

- [ ] `.cursor/rules/Findings.mdc` - records r = 0.724 as a passing biological
      validation; no current run reproduces it
- [ ] `research/findings/FULL_BRAIN_FINDINGS.md`
- [ ] `docs/03_validation/FINAL_VALIDATION.md`

### Category: results derived from the uncentered-SVD projection

Every result recorded before 2026-09-03 was produced with the uncentered-SVD
fallback while the documentation said PCA. scikit-learn is now installed and
mean-centred PCA is the explicit path. Measured effect on the benchmarks is in
`docs/03_validation/DETERMINISM_AND_STIMULUS_PATH.md` section 3, and the
projection difference itself in
`results/final/projection_path_comparison.json` (mean r 0.50 between the two
paths, minimum 0.13, pairwise odour-similarity shift up to 0.58).

- [ ] any document quoting a smell result dated before 2026-09-03, which is
      most of `research/` and `publication/`

### Category: results derived from the constant-DC stimulus path

Every smell result recorded before 2026-09-03 was produced by a constant force
vector that bypassed the plume, the sinusoidal carrier and receptor adaptation,
and that pinned 981 of 2,198 projection neurons at the amplitude clip ceiling.
Temporal-dynamics and adaptation figures from that era describe a saturated
fixed point.

- [ ] `research/TEMPORAL_ADAPTATION_FINAL_RESULTS.md` - 53.1% adaptation
- [ ] `.cursor/rules/Findings.mdc` - the temporal-adaptation entry
- [ ] `research/POLYGLOT_SMELL_BENCHMARK.md`

---

## Not outdated

Vision and auditory results are untouched by this work. The engine changes
affect them only through the coupling accumulation order (F1) and the amplitude
guard (F5); neither has been re-measured for those pathways.

- [ ] `research/vision/findings/*` - not re-measured after F1 and F5; the
      vision pathway uses `external_force` directly rather than `inject_odor`,
      so the stimulus-path fixes do not apply, but the guard change may.
