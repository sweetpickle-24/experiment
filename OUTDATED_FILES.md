# Outdated Files

**Date**: 2026-09-03
**Last Updated**: 2026-09-04

Files whose claims are contradicted by measurements in
`docs/03_validation/DETERMINISM_AND_STIMULUS_PATH.md` and
`docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md`. Listed rather than
edited, because correcting them is a documentation pass of its own and
rewriting a publication draft is not part of the fix work that produced these
numbers.

---

## Files Needing Updates

### Category: the receptor-to-channel projection and the neuron classifier (2026-09-04)

Two heuristics stood in for information that was already in the dataset, and both
now have a measured, citation-backed replacement available behind a flag. Neither
is the default yet. See
`docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md` and
`results/final/glomerular_projection_diagnostic.json`.

**The 40-to-20 PCA projection.** Measured on the 12-odorant panel: PCA inflates
mean inter-odour similarity from r = 0.1845 in the measured receptor responses to
r = 0.5026, a factor of 2.72, and its rectifier discards a third of the projected
magnitude because principal-component signs are arbitrary. The published
one-to-one map is 3.5x closer to Campbell et al. 2013 Fig 4C.

- [ ] `ARCHITECTURE.md` - section 6 describes the forward path as "SVD projection
      (40 -> 20 dimensions)" and section 12 as PCA; both should describe the
      available projections and say which produced which result
- [ ] `THESIS_DIGITAL_SMELL.md` and `thesis/` - any description of the 20-channel
      glomerular code as biological. The 20 channels and their `GLOM_LABELS`
      names (`ester_fruit`, `sulfur_mold`, ...) are not molecular classes; a
      principal component is a direction of variance over the loaded odorant panel
- [ ] `docs/02_architecture/SPARSE_CODING_THEORY.md` - check the input-stage
      description

**The neuron classifier over-matches.** `'AL' in group_str` matches 4,796 neurons
where only 2,762 are annotated `AL`, because group strings are dot-separated
neuropil lists and `LAL` contains `AL`. `'PN' in cell_types_str` sweeps in 93
auditory `WEDPN` and 161 unnamed `CB` neurons.

- [ ] Anything quoting **2,198 PNs** or **10,906 olfactory neurons** as anatomical
      figures. Under strict classification they are 866 and 9,199. The loose
      numbers are what every recorded result used, so they are correct as a
      description of the runs and wrong as a description of the fly:
      `README.md`, `ARCHITECTURE.md`, `.cursor/rules/Findings.mdc`,
      `research/REAL_CONNECTOME_POLYGLOT_BENCHMARK.md`, `thesis/`
- [ ] `hive/substrate/olfactory_subgraph.py` - `strict=True` should probably
      become the default once a full ladder rung has been scored under it, at
      which point every earlier result becomes incomparable and must be relabelled
      rather than deleted

### Category: the engine is described as probabilistic, and it is not (2026-09-04)

`var_amplitude` is set to 0.01 at initialisation and at every `reset` and is never
updated by any step function. `var_phase` *is* updated in all three step paths, but
the coupling term multiplies by a hardcoded `exp(-0.1/2)` constant
(`_var_correction_scalar`) rather than reading the live field, so `var_phase` is
write-only. Nothing downstream consumes either. Consequences:

- **`sigma_noise` provably cannot change any output.** It enters only
  `_sigma_sq_dt`, which enters only the `var_phase` recursion, which is read by
  nothing. It is nonetheless recorded as a configuration parameter in every result
  file by `validation_utils.run_metadata()`.
- The engine as written is a **deterministic** damped harmonic-oscillator network on
  a sparse graph. "Probabilistic", "mean-field" and "Fokker-Planck" overstate it.

Anything describing the engine as probabilistic or mean-field, or presenting
`Var[phi]` / `Var[A]` as state that influences the trajectory:

- [ ] `ARCHITECTURE.md` - §2 "Mean-Field Probabilistic Waves" lists `Var[phi]` and
      `Var[A]` as per-neuron state and §1 says the system uses "mean-field
      Fokker-Planck equations instead of individual spike trains"
- [ ] `docs/02_architecture/PROBABILISTIC_WAVE_IMPLEMENTATION.md`
- [ ] `docs/02_architecture/FORMULA_VALIDATION.md` - check the variance update
      against what the coupling actually reads
- [ ] `hive/engine/sparse_probabilistic.py` - the class docstring says "Still
      probabilistic (mean-field)". Either wire `var_phase` into the coupling or
      delete both fields and rename. The structural fix is an assertion per
      subsystem that destroying it must change the output, as
      `tests/test_weights_on_signal_path.py` already does for the plasticity path
- [ ] `.cursor/rules/Findings.mdc` - refers to a "phase-coupled mean-field network"
      throughout

### Category: random PN->KC wiring is no longer the published position (2026-09-04)

Zheng et al. 2022, *Structured sampling of olfactory input by the fly mushroom
body*, Current Biology 32(15):3334-3349.e6, mapped PN->KC connections at synaptic
resolution in FAFB and found that food-responsive PN types **over-converge on
individual KCs above chance** against constructed nulls. The wiring is not purely
random. Caron et al. 2013 remains the source for the ~7-PN-per-KC in-degree.

- [ ] `ARCHITECTURE.md` - §6 states "Random wiring: Each KC receives input from ~7
      random PNs (Caron et al. 2013)" and lists it as a property of the connectome
- [ ] `.cursor/rules/Findings.mdc` - "Anatomical Basis: Caron et al. (2013) proved
      random PN->KC wiring"
- [ ] `THESIS_DIGITAL_SMELL.md` - check §1.3 sparse coding theory
- [ ] `docs/02_architecture/SPARSE_CODING_THEORY.md`

### Category: the model class and substrate are already occupied (2026-09-04)

Phase oscillators on structural connectomes are standard in human whole-brain
modelling (Kuramoto in The Virtual Brain; Hopf/Stuart-Landau for phase *plus*
per-node amplitude, Deco et al. 2017, Sci. Rep. 7:3095). Ódor, Deco & Kelling have
published Kuramoto at one-oscillator-per-neuron on the Drosophila connectome: the
hemibrain in 2022 (Phys. Rev. Research 4:023057, 21,662 nodes / 3,413,160 edges) and
the **full FlyWire v630 connectome in 2025** (arXiv:2503.20708, **124,891 nodes /
3,794,615 edges**), using RK4 and adaptive Bulirsch-Stoer rather than forward Euler,
on GPU. Eight times the nodes and a better integrator.

What those papers do not do is drive the model with a sensory stimulus or compare it
against fly physiology; they are criticality studies and their own text calls it a
"brain toy model". That is the only gap this project occupies. Any claim of a novel
model class, a first-of-its-kind phase model on a fly connectome, or a scale record
is false.

- [ ] `docs/05_publication/MANUSCRIPT_PUBLICATION.md` - check novelty claims
- [ ] `docs/05_publication/EXECUTIVE_SUMMARY.md` - same
- [ ] `docs/05_publication/PUBLICATION_SUMMARY.md` - same
- [ ] `docs/04_discoveries/ALL_NOVEL_DISCOVERIES.md` - same
- [ ] `THESIS_DIGITAL_SMELL.md` and `thesis/` - same
- [ ] `ARCHITECTURE.md` - §15 "Computational Firsts"

### Category: targets that are not in the papers they cite (2026-09-04)

`docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md` records, per benchmark, the
target it was scored against and what the cited paper actually reports. Four of
six targets are not in their cited source and one citation does not exist.

Anything quoting these targets as biological benchmarks is quoting a number no
paper reports:

- **`r > 0.70` for concentration invariance, attributed to Turner et al. 2008.**
  That paper recorded all 71 KCs at a single 1:1,000 effective dilution and
  contains no concentration series and no correlation threshold. The 0.70 appears
  to be Campbell et al. 2013 Fig 4C's pentyl-acetate/butyl-acetate *odour-pair*
  correlation.
- **`10-20 %` JND, attributed to "Bodyak & Bhatt 2001".** That citation does not
  exist. The nearest real work is Bodyak & Slotnick 1999, a mouse study.
- **`30-50 %` mixture overlap, attributed to Stettler & Axel 2009 and Deisig et
  al. 2006.** Mouse piriform cortex and honeybee antennal lobe respectively;
  neither is a Drosophila mushroom-body measurement.
- **`50-150 ms` peak time (Stopfer et al. 2003, a locust study) and `30-70 %`
  adaptation (Nagel & Wilson 2011, an ORN study).** Neither band is in its cited
  paper.
- **`[0.3, 0.5]` chem-neural similarity band (Bhandawat et al. 2007; Mathew et
  al. 2013).** No source could be located for it.

- [ ] `THESIS_DIGITAL_SMELL.md` - cites Turner et al. 2008 as the "Benchmark for
      concentration invariance (r > 0.70)"
- [ ] `thesis/THESIS_MAIN.md` - same
- [ ] `thesis/CHAPTER_4_RESULTS.md` - same, plus the r = 0.724 result table
- [ ] `thesis/CHAPTER_6_CONCLUSION.md` - same
- [ ] `thesis/THESIS_STRUCTURE.txt` - same
- [ ] `publication/CPU_VS_GPU_FINAL_VALIDATION.md` - same
- [ ] `scripts/run_all_validations.py` - still contains all five original
      benchmarks with their misattributed targets. Left in place deliberately so
      the F8 numbers stay reproducible; the repaired versions are in
      `benchmarks_repaired/` and are scored by `scripts/run_repaired_suite.py`.

### Category: earlier fix work (2026-09-03)

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

The **repaired** five-benchmark suite scores **2/5** on CPU with 8 trials per
stimulus (`results/final/all_validations_F9_corrected.json`): `temporal_dynamics`
and `odor_mixtures` pass; `discrimination`, `similarity` and `learning` fail.

The earlier F8 suite also scored **2/5** at seed 42 on CPU
(`results/final/fix_ledger.json`, entry `F8_final`), up from 1/5 — but on a
different pair, and both of its passes are now withdrawn: `learning` passed on an
unsigned 99.99 % collapse caused by a renormalisation bug, and `odor_mixtures`
passed against a target band from a mouse and a honeybee paper.

- [ ] `ARCHITECTURE.md` - claims 27/27 benchmarks complete
- [ ] `docs/00_START_HERE.md` - claims 27/27
- [ ] `archive/README.md` - claims 27/27
- [ ] `.cursor/rules/Findings.mdc` - claims 27/27 with a 100% success rate
- [ ] `research/validation/FINAL_VALIDATION_COMPLETE.md`
- [ ] `research/findings/FULL_BRAIN_FINDINGS.md`
- [ ] `research/ALL_NOVEL_DISCOVERIES.md`
- [ ] `docs/03_validation/FINAL_VALIDATION.md`

### Category: concentration invariance

Two separate problems, and the second supersedes the first.

**The target is not real.** `r > 0.70` is not in Turner et al. 2008; see the
category above. There is no published Drosophila threshold for KC pattern
correlation across concentration. The real Drosophila concentration paper is
Honegger et al. 2011, whose invariant quantity is population *sparseness*, and
that quantity is pinned to a constant by this model's rank threshold
(measured 0.059860 with standard deviation exactly zero), so it cannot be tested
here at all.

**The measured value.** The repaired measurement gives pattern correlation
r = **0.5417** over 50 concentration pairs across 5 odorants, correlating 8-trial
mean patterns (`results/final/concentration_invariance_repaired.json`). The F8
single-trial figure was 0.2719. The published r = 0.7244 remains withdrawn: it
included a null odorant that self-correlates at exactly 1.0000.

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
