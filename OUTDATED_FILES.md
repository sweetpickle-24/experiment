# Outdated files

**Date**: 2026-09-03
**Last Updated**: 2026-09-05

Status of documentation against the current state of the code and results.

---

## Current documents

These are accurate as of 2026-09-05 and carry every claim the project makes. Nothing
else in the repository should be cited.

| Document | Scope |
|---|---|
| `README.md` | what the project is, how the pipeline works, current results |
| `ARCHITECTURE.md` | how the system is built, stage by stage |
| `QUICKSTART.md` | setup and how to run each thing |
| `docs/00_START_HERE.md` | documentation index |
| `docs/03_validation/LIMITATIONS.md` | what the numbers cannot support |
| `docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md` | every target against its cited source |
| `docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md` | the input repair and the 2/5 → 5/5 ladder |
| `docs/03_validation/DETERMINISM_AND_STIMULUS_PATH.md` | determinism fix and per-fix ledger, with a forward pointer |
| `results/README.md` | which artifact backs which claim |
| `archive/README.md` | what the archive contains and why not to cite it |

## Everything else: bannered, not rewritten

**158 markdown files** under `research/`, `publication/`, `thesis/`, `docs/` and
`archive/` now carry a single uniform banner marked
`<!-- STALE-BANNER-2026-09-05 -->`, replacing the inconsistent set of earlier
correction notices. The banner names the six corrections that apply most widely and
links to the current documents.

**This is a banner, not a rewrite.** Those files are historical drafts — status
reports, thesis chapters, publication manuscripts, per-experiment findings — and
rewriting them is a documentation project of its own. The banner exists so a reader
cannot be misled without also being told where to look. Treat any number in them as
unverified unless traced to a file under `results/`.

Re-apply after adding documents: the banner script is idempotent on the marker, so
running it again neither stacks nor duplicates.

### The corrections the banner carries

1. **The scored suite is 5/5** (`results/final/all_validations_G2.json`). Recorded
   history: 3/5 (2026-03-15) → 1/5 (2026-09-03, first seeded run) → 2/5 (2026-09-04,
   after targets were checked against sources) → 5/5 (2026-09-05, after the input
   projection was corrected). **9/9, 13/13, 14/14 and 27/27 were never produced by
   any run.**
2. **GPU speedup is 10.00×**, not 86×. The 86× came from a file now in
   `results/superseded/` that also recorded 1,283 active KCs, a null pattern
   correlation, and `validation_passed: true` against a criterion it never evaluated.
3. **Kenyon cell sparsity is imposed by the readout**, at 310 of 5,177 cells, not
   measured. "1.65 % matching Turner et al. 2008" is withdrawn and appears in no
   result file.
4. **Concentration invariance is 0.6603 and deliberately unscored.** The 0.70
   threshold is not in Turner et al. 2008, which recorded every KC at a single
   dilution.
5. **The decorrelation result `r = −0.51` is withdrawn.** It was a six-point
   regression between chemical and neural similarity from a run the harness recorded
   as FAIL; a later run measured the same quantity at `+0.632`.
6. **Vision and auditory results are not part of the scored suite**, and several — T4
   motion, HS/VS optic flow, Johnston's organ frequency tuning — come from
   hand-written filters rather than the wave engine.

---

## Open items in code, not documentation

These are real and unfixed. Tracked here because they affect how documentation should
be read.

- [ ] **The variance fields do not participate in the dynamics.**
      `var_amplitude` is never updated; `var_phase` is updated but never read, because
      the coupling uses a hardcoded constant. So `sigma_noise` provably cannot change
      any output, though it is recorded in every result file. The engine is
      deterministic despite the class name `SparseProbabilisticBrain`. See
      `LIMITATIONS.md` §3. The right fix is structural — an assertion per subsystem
      that destroying it must change the output — not a patch.
- [ ] **The coupling carries no excitation/inhibition sign.** `nt_type` and the six
      per-neuron neurotransmitter scores are loaded, stored, and unused.
      `LIMITATIONS.md` §4.
- [ ] **Kenyon cell identities do not converge under timestep refinement**, and
      refinement does not help. `LIMITATIONS.md` §2. The most consequential open
      problem.
- [ ] **`hive/inverse/smell_optimizer.py::multi_start` is broken** — it draws random
      starting logits and never uses them, so every restart runs the identical
      deterministic optimisation.
- [ ] **Neuron coordinates carry no units and are not rescaled**, which is why
      `ProbabilisticWaveBrain` allocates ~116 GB and is killed. `LIMITATIONS.md` §8.
- [ ] **`scripts/run_all_validations.py` still contains the pre-audit benchmarks**
      with their misattributed targets. Left in place deliberately so the superseded
      numbers stay reproducible; the current suite is `benchmarks_repaired/`.
- [ ] **`hive/substrate/olfactory_subgraph.py`** — `strict=True` should probably
      become the default, at which point every earlier result becomes incomparable
      and must be relabelled rather than deleted.

## Resolved since the last revision

- [x] **`ARCHITECTURE.md` rewritten** (2026-09-05). The previous version asserted a
      withdrawn `r = −0.51` result as "Discovery 1" in §14 while §6 of the same file
      withdrew it, listed eight "computational firsts", quoted 86×, described the
      engine as mean-field Fokker-Planck, and called the 5,342,446 edge count
      "synapses". §14 and §15 are gone; a "What this is not" section replaces them.
- [x] **`docs/00_START_HERE.md` rewritten** (2026-09-05). Previously said four of five
      benchmarks did not reproduce, and warned about an all-zero-stimulus defect that
      has since been fixed.
- [x] **`archive/README.md` updated** (2026-09-05) with the full score history and the
      discarded speedup.
- [x] **`QUICKSTART.md` updated** (2026-09-05) — named `sklearn_pca` as the documented
      projection, pointed at the pre-audit runner, and omitted the ladder, the
      diagnostic and the fingerprint encoder.
- [x] **The 372-odorant fingerprint database regenerated** (2026-09-05). The previous
      artifact was built with a *third* projection — `SmellDatabase`'s own uncentered
      SVD, which appeared nowhere else — under the superseded constant-drive stimulus
      path and on MLX with `fast_mode`. Its `pn_pattern` fields still contained
      literal `10.0` values, the signature of projection neurons pinned at the old
      amplitude ceiling. `scripts/batch_encode_odors.py` now builds through
      `init_olfactory_brain`, so the encoder and the scored suite share one pipeline,
      and the artifact carries its own configuration block.
- [x] **158 stale documents given one uniform, accurate banner** (2026-09-05),
      replacing 29 inconsistent "Correction notice" blocks and 54 files with no
      banner at all.
- [x] **Engine defaults flipped to the current pipeline** (2026-09-05).
      `init_olfactory_brain` and the `benchmark_harness` environment fallbacks now
      default to `glomerular` / `glomerulus` / strict, so a bare run reproduces the
      reported 5/5 rather than the superseded 2/5. Changing a default altered no
      result already on disk: every artifact records the pipeline that produced it,
      so the 5/5 files now match the defaults and the 2/5 files are correctly marked
      as a different configuration.

      Three things were deliberately **not** changed. `SparseProbabilisticBrain`
      keeps `glomerular_mapping='position'`, because 34 files construct the engine
      directly without channel names — including twelve vision tests on a connectome
      that has no glomeruli — and `'glomerulus'` raises without them. The general
      engine should not assume olfaction. `extract_olfactory_pathway` and
      `classify_olfactory_neuron` keep `strict=False`. And the two entry points that
      exist to reproduce superseded numbers, `scripts/run_all_validations.py` and
      `tests/concentration_invariance_test.py`, pin all three values explicitly
      rather than inheriting them, so they still report 10,906 neurons. Verified by
      constructing both paths.

      **Still open, deliberately deferred:** `results/final/all_validations_G2.json`
      still carries an ablation-rung label in its filename, which ages badly now that
      that rung is the default. Renaming it to something like
      `all_validations_current.json` would touch several documents and was judged not
      worth the churn today. G0/G1/G2 remain meaningful inside
      `GLOMERULAR_PROJECTION_REPAIR.md`.
