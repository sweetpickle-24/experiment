# Updated Files Log

**Date**: 2026-09-03
**Last Updated**: 2026-09-05

Audit trail of markdown and result-artifact changes. See `OUTDATED_FILES.md` for
files known to still need updating.

---

## Updates on 2026-09-05 (later the same day)

### Engine defaults flipped to the current pipeline

**Reason**: the defaults still selected the pre-repair input pipeline, so a bare
`python -m benchmarks_repaired.temporal` reproduced the superseded 2/5 while the
README reported 5/5. Anyone cloning the repository and running it without reading the
environment-variable section would have got the worse number and concluded the
reported one was inflated. The better configuration was reachable but not
discoverable, which is a defect in its own right.

**Files changed**: 3 python, 3 markdown. **No result artifact altered.**

- [x] `validation_utils.py` - `init_olfactory_brain` now defaults to
      `projection='glomerular'`, `glomerular_mapping='glomerulus'`,
      `strict_classification=True`. Docstring rewritten to state what the defaults are
      as of this date, what they were before, and where the measured cost of the old
      projection is recorded.
- [x] `benchmark_harness.py` - The three environment fallbacks flipped to match. The
      hardcoded comparison dictionary that the printout used to detect a non-default
      configuration had been written as a literal and would have silently drifted out
      of step with the fallbacks, so it is now the named constant `_CURRENT_PIPELINE`.
      The printout now says whether the path differs from current, rather than
      "F9 defaults".
- [x] `scripts/run_all_validations.py` - **Pinned, not flipped.** This is the
      pre-audit suite, kept only so the superseded F8/F9 numbers stay reproducible; its
      targets are the misattributed ones. It gained an explicit
      `strict_classification=False` parameter, passed through to the constructor, plus
      a `--strict-classification` flag for symmetry. Without the pin it would have
      inherited the new defaults and silently stopped reproducing the baselines it
      exists to preserve.
- [x] `README.md`, `QUICKSTART.md` - Run instructions inverted: the bare command now
      gives 5/5, and the three variables shown are the ones that return to 2/5.
- [x] `OUTDATED_FILES.md` - The pending decision moved to resolved, recording what was
      deliberately left alone and why.

**Deliberately not changed.** `SparseProbabilisticBrain` keeps
`glomerular_mapping='position'`: 34 files construct the engine directly without
channel names, including twelve vision tests on a connectome that has no glomeruli,
and `'glomerulus'` raises without them. The general engine should not assume
olfaction. `extract_olfactory_pathway` and `classify_olfactory_neuron` keep
`strict=False`. `tests/concentration_invariance_test.py` needed nothing: it builds
the engine directly with its own pinned defaults rather than through
`init_olfactory_brain`, so it was already insulated.

**Verified by construction, without simulating.** A bare `build()` reports
`glomerular` into 29 channels, `glomerulus` PN assignment, strict on, 9,199 neurons.
The pinned legacy call reports `sklearn_pca` into 20 channels, `position`, 10,906
neurons. The engine, extraction and classifier defaults are unchanged.

**No result on disk changed meaning.** Every artifact records the pipeline that
produced it, so flipping a default cannot retroactively alter an old file: the 5/5
files now agree with the defaults and the 2/5 files remain correctly marked as a
different configuration.

---

## Updates on 2026-09-05

### Documentation brought current, and the odorant fingerprint database regenerated

**Reason**: the 5/5 result made several documents wrong rather than merely dated,
and the 372-odorant fingerprint database had been generated with a third,
undocumented projection under the superseded stimulus path.

**Files rewritten**: 5 markdown. **Files bannered**: 158. **Artifacts regenerated**: 1.

- [x] `ARCHITECTURE.md` - **Rewritten.** The previous version asserted a withdrawn
      `r = -0.51` decorrelation result as "Discovery 1" in §14 while §6 of the same
      file withdrew it, listed eight "computational firsts", quoted the discarded
      86x speedup, described the engine as "mean-field Fokker-Planck" when the
      variance fields do not participate in the dynamics, called the 5,342,446 edge
      count "synapses", and reported "SVD projection (40 -> 20)". §14 and §15 are
      replaced by a "What this is not" section that states plainly that the model
      class is not novel, that Ódor/Deco/Kelling published Kuramoto on the full
      FlyWire connectome at 124,891 nodes, and that Lazar's group already models fly
      olfaction on the hemibrain.
- [x] `docs/00_START_HERE.md` - **Rewritten.** Said four of five benchmarks did not
      reproduce, and warned about an all-zero-stimulus defect that has since been
      fixed. Now lists the five current documents and four things to know first.
- [x] `QUICKSTART.md` - **Updated.** Named `sklearn_pca` as the documented
      projection, pointed at the pre-audit runner as the way to run the suite, and
      omitted the ladder, the diagnostic and the fingerprint encoder. Then updated
      again the same day, once the defaults were flipped, to say that a bare run now
      reproduces the reported 5/5 and to show the three environment variables that
      select the superseded baseline instead.
- [x] `README.md` - Same correction to the run instructions.
- [x] `archive/README.md` - Full score history and the discarded speedup.
- [x] `docs/03_validation/DETERMINISM_AND_STIMULUS_PATH.md` - Forward pointer added;
      the report itself stands. Also notes that its "no stochasticity in the step"
      finding goes further than stated: the variance fields are read by nothing.
- [x] **158 stale markdown files** under `research/`, `publication/`, `thesis/`,
      `docs/` and `archive/` given one uniform banner marked
      `<!-- STALE-BANNER-2026-09-05 -->`, replacing 29 inconsistent "Correction
      notice" blocks and adding one to 129 files that had none. The banner names the
      six corrections that apply most widely and links to the current documents. This
      is a banner, not a rewrite; those files are historical drafts and
      `OUTDATED_FILES.md` says so.
- [x] `scripts/batch_encode_odors.py` - **Rewritten**, and the 372-odorant database
      regenerated. The previous artifact could not be reconciled with any reported
      run for three independent reasons: it took glomerular patterns from
      `SmellDatabase._receptors_to_glom`, an **uncentered SVD that appeared nowhere
      else in the repository** and matched neither the benchmarks' PCA nor the
      published map; it ran under the superseded constant-drive stimulus path, whose
      signature was still visible as literal `10.0` values in its `pn_pattern` fields
      (projection neurons pinned at the old amplitude ceiling); and it ran on MLX with
      `fast_mode`, which is neither the reporting backend nor the reporting timestep.
      It now builds through `init_olfactory_brain`, so the encoder and the scored
      suite share one pipeline, and the artifact carries its own configuration block.
      New: 372 x 5,177, `pn_pattern` max 1.47 with nothing at the old ceiling,
      295 distinct active sets.
- [x] **New finding recorded**: 26 of the 372 odorants produce a **null stimulus** -
      zero active Kenyon cells - because on the 29 mapped receptors their measured
      responses are entirely *negative*, and the projection rectifies. Most are a
      single -1.0 on `Or71a`. The encoder now warns, and the artifact records the
      list in `config.null_stimulus_odorants`. 346 of 372 are usable. Added as
      `LIMITATIONS.md` §11. The root cause is that the model cannot represent
      inhibition at all (`LIMITATIONS.md` §4).
- [x] `hive/data/smell_database.py` - `load_kc_fingerprints` accepts both the new
      `{"config", "entries"}` shape and the old bare list, and exposes
      `kc_source_config` so a consumer can see which pipeline produced the
      fingerprints.
- [x] `OUTDATED_FILES.md` - Restructured as a status document: what is current, what
      is bannered, and the open items in code.
- [x] `UPDATED_FILES_LOG.md` - This entry.

---

## Updates on 2026-09-04

### Glomerular projection repair, and the README rewritten as a project description

**Reason**: the receptor-to-glomerular-channel step compressed 33 measured
receptor responses into 20 principal components. In the animal the relationship is
one-to-one and published, and both halves of it were already present in the data:
the DoOR matrix names its receptors, and the FlyWire cell-type annotations name 60
glomeruli across 304 uniglomerular projection neurons. Measured before changing
anything, the PCA step inflated mean inter-odour similarity by 2.72x and discarded
a third of the projected magnitude through its rectifier.

**Outcome**: ablation ladder **2/5 -> 4/5 -> 5/5**, same scoring code, criteria,
seeds and odorant panel throughout. G1 (glomerular projection) flipped
discrimination and similarity to PASS; G2 (+ strict neuron classification) flipped
learning, whose specificity effect size went from Cohen's d = 0.038 to 2.305. No
benchmark regressed from PASS to FAIL. Concentration invariance 0.5417 -> 0.6603.
This is a correction to the experiment rather than new evidence about the physics,
and it changes none of the standing limitations.

**Files created**: 4 code/test modules, 2 markdown, result artifacts per rung

- [x] `hive/data/receptor_glomerulus_map.py` - Created. The published one-to-one
      receptor-to-glomerulus assignment, 29 of the 33 measured receptors, each
      entry carrying its own citation (Couto, Alenius & Dickson 2005 Curr Biol
      15:1535 Table 1, cross-checked against Fishilevich & Vosshall 2005 and DoOR
      2.0 Table 1). Four receptors with real data are **excluded rather than
      guessed** because no glomerular assignment could be sourced (Or45a, Or45b,
      Or59a, Or85c), and Or83b is excluded because it is Orco, a co-receptor with
      no glomerulus. Non-injective cases documented with a stated combination
      rule (DL4 receives Or49a and Or85f). VM7 fans out to VM7d/VM7v because
      Couto predates that subdivision. Also holds `annotated_glomeruli()`, which
      reads the glomeruli that actually have projection neurons.
- [x] `tests/diagnose_glomerular_projection.py` - Created. Compares the
      12-odorant panel in three input spaces without running the simulation, so
      the projection is tested in isolation from the network for the cost of a
      matrix multiply. Answers the question
      `docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md` listed as untraced.
- [x] `scripts/run_glomerular_ladder.py` - Created. Runs the ablation ladder,
      one rung per configuration, and scores each rung with the existing
      aggregator rather than reimplementing the scoring.
- [x] `docs/03_validation/LIMITATIONS.md` - Created. Twelve sections covering
      what the model does not do and what its numbers cannot support, gathered so
      the README can describe the project without either being diluted. Includes
      a newly recorded defect: the variance fields are computed every step and
      read by nothing, so `sigma_noise` provably cannot change any output.
- [x] `docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md` - Created. The
      diagnostic, the cited map, the ladder, and a plain verdict.
- [x] `hive/data/door_client.py` - Added `projection='glomerular'` as a third
      option; `_compute_pca_projection` became a dispatcher. Channel count is now
      a consequence of the map rather than a parameter. Added
      `projection_magnitude_retained`, computed identically for all three
      projections, because `projection_explained_variance` means
      `explained_variance_ratio_` for PCA and has no counterpart for a lookup.
      Defaults unchanged.
- [x] `hive/interface/olfactory.py` - Channel count parameterised throughout;
      `NUM_GLOM_CHANNELS` is now a default rather than a fixed property.
      `OdorStimulusDriver` no longer rejects a pattern whose length is not 20.
      `OdorReceptorArray` takes `num_channels` and a `frequency_mode`
      (`literature_spread` or `uniform`); at 20 channels the historical
      frequencies and phases are reproduced bit-for-bit, verified.
- [x] `hive/engine/sparse_probabilistic.py` - Added `'glomerulus'` to
      `GLOMERULAR_MAPPINGS`, which reads each PN's glomerulus off the connectome
      cell-type annotation instead of clustering positions. PNs naming no channel
      glomerulus are dropped from the drive and counted rather than defaulted to
      channel 0. Added `channel_assignment_report` for all three mappings.
- [x] `hive/substrate/olfactory_subgraph.py` - Added opt-in `strict` mode to
      `classify_olfactory_neuron`. It fixes two over-matches: the cell-type test
      `'PN' in cell_types_str` sweeps in 93 auditory `WEDPN` and 161 unnamed `CB`
      neurons, and the region test `'AL' in group_str` matches **4,796** neurons
      where only **2,762** are annotated `AL`, because group strings are
      dot-separated neuropil lists and `LAL` contains `AL`. That second one is how
      `PFL3` (central complex) and `LC33` (visual) were classified as olfactory
      projection neurons. Strict mode takes the subgraph from 10,906 to 9,199
      neurons and PN from 2,198 to 866. Off by default.
- [x] `benchmark_harness.py` - `build()` now reads the stimulus-path
      configuration from the environment, so an ablation ladder can vary it across
      subprocesses without editing six argument parsers. Unrecognised values
      raise rather than falling back.
- [x] `validation_utils.py` - Threaded `strict_classification` through
      `init_olfactory_brain`; the DoOR client is now built before the brain so
      channel names are available to the engine. Provenance block gained the
      channel count, channel names, the PN assignment report, the requested
      mapping, and the projection report.
- [x] `scripts/run_repaired_suite.py` - Added `--suffix` so a ladder rung can be
      scored by the same code that produced the F9 baseline.
- [x] `benchmarks_repaired/concentration_invariance.py` - Fixed the
      sparseness-pinned check, which was `bool(np.std(all_sparse) == 0.0)`, a
      strict float equality on a computed standard deviation. It gave a **false
      negative** the first time the Kenyon cell count changed: under strict
      classification all 200 values were identical at 310/5177 and `np.std`
      returned 2.08e-17 rather than zero, so the result file briefly claimed the
      readout no longer pinned sparseness. Now `max - min <= 1e-12`, which is
      exact for identical floats, with the spread and both KC counts recorded.
      The KC total is read from the readout instead of hardcoded as 5,279. Both
      rungs re-run.
- [x] `README.md` - Rewritten as a project description rather than a record of
      corrections. Removed the validity-audit banner, the superseded-number
      tables, the historical-defect narrative and the limitations section; added a
      "How the smell input works" section distinguishing measured data from
      modelled components from computational choices, which did not previously
      exist anywhere. Honest material moved to
      `docs/03_validation/LIMITATIONS.md` and linked from a "Validation
      methodology" section.
- [x] `OUTDATED_FILES.md` - Added the receptor-projection category.
- [x] `UPDATED_FILES_LOG.md` - This entry.

### README brought in line with the post-audit measurements

**Reason**: the README header correctly pointed at the validity audit, but four
sections below it still carried claims the audit and the 2026-09-03 fix work had
superseded. A reader following the header and a reader following the body got
different answers.
**Files updated**: 3 markdown, 1 config

- [x] `README.md` - Corrected:
      - **Performance**: the discarded 86.34x speedup was quoted in three places
        (the practical-consequence line, the performance table, and the table's
        source column, all pointing at `cpu_vs_mlx_validation.json`, which is now
        in `results/superseded/`). Replaced with the verified **10.00x median**
        from `results/final/cpu_vs_mlx_speedup.json`, plus the cross-backend
        agreement measurement and the pre-registered rule it failed
        (`cpu_vs_mlx_fullrun.json`).
      - **Known limitations**: "the DoOR 40-receptor to 20-glomerulus mapping is a
        random projection" is fixed and was also mislabelled — the fallback was
        uncentered SVD, not a random projection. "Missing odorants fail silently"
        is fixed; lookups raise `OdorantNotFoundError`.
      - **"The GPU path is not reproducible, and seeding does not fix it"**:
        retitled to record that both defects are fixed, with the segment-reduction
        mechanism and the `mlx_determinism.json` evidence, and kept as history
        because it is why pre-2026-09-03 artifacts should be read with suspicion.
      - **Benchmark outcomes**: led with the 1/5 pre-audit run as "most recent".
        Now leads with the repaired suite (**2/5**,
        `all_validations_F9_corrected.json`) and demotes the old table to a
        clearly-labelled superseded section with its target column marked invalid.
        "Why there is no summary score" rewritten as "why a score is quoted now",
        addressing each of the four original reasons, and stating what 2/5 still
        does not mean.
      - **Connectome counts**: `5,342,446` was labelled "synapses". It is the
        **edge** count. Verified directly from `connections_princeton.csv.gz`:
        summing `syn_count` over all 5,342,446 rows gives **50,666,648** synapses,
        which is **93 %** of the 54.5 M published by Dorkenwald et al. 2024. Also
        fixed a citation to `results/final/full_brain_smell_results.json`, which
        lives in `results/superseded/`, and named the FlyWire release (v783).
      - **New disclosures**: the variance fields do not participate in the
        dynamics (`var_amplitude` never updated, `var_phase` write-only), so
        `sigma_noise` cannot change any output; the coupling carries no
        excitation/inhibition sign despite `nt_type` being loaded; the MBON
        amplitude readout is non-monotone in synaptic weight; the model class and
        substrate are both already occupied in the literature (Ódor, Deco &
        Kelling, Kuramoto on the full FlyWire connectome at 124,891 nodes); the
        dt non-convergence promoted from the header banner to its own section; the
        stale 372-odorant fingerprint database; the unrescaled coordinate units.
      - **What was built**: expanded to name the deterministic segment reduction,
        the receptor front-end and its seeded plume, the measurement harness, and
        the provenance block, which were previously undescribed.
      - **Running it**: pointed at `scripts/run_repaired_suite.py` and documented
        that `.venv/bin/python` is required.
- [x] `UPDATED_FILES_LOG.md` - This entry.
- [x] `OUTDATED_FILES.md` - Two new categories: documents describing the engine as
      probabilistic/mean-field, and documents citing Caron 2013 as proof of random
      PN->KC wiring.

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
