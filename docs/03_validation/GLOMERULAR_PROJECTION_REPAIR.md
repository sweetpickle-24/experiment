# Glomerular projection repair

**Date**: 2026-09-05
**Last Updated**: 2026-09-05
**Status**: Complete. G1 scored 4/5 and G2 scored 5/5, from a 2/5 baseline.

Replacing two approximations in the stimulus path - a learned projection and a
spatial-clustering proxy - with the published one-to-one receptor-to-glomerulus
map and the connectome's own glomerulus labels, and what that did to the five
scored benchmarks.

Every number below cites the result file that produced it.

---

## 1. Summary

| Outcome | G0 (F9) | G1 | G2 |
|---|---|---|---|
| **Suite score** | **2/5** | **4/5** | **5/5** |
| temporal_dynamics | PASS | PASS | PASS |
| odor_mixtures | PASS | PASS | PASS |
| discrimination | FAIL, series non-monotone | **PASS**, monotone | **PASS** |
| similarity | FAIL, ordering wrong | **PASS**, published ordering | **PASS** |
| learning | FAIL, 2/3 criteria | FAIL, 2/3, specificity worse | **PASS**, 3/3 |
| concentration invariance (unscored) | r = 0.5417 | **r = 0.6706** | r = 0.6603 |
| KC decorrelation, Turner Fig 5 | 39/66 pairs | 56/66 | **59/66** |
| learning specificity effect size | d = 0.038, needs n = 8,576 | d = 0.857, needs n = 17 | **d = 2.305, needs n = 3** |
| neurons / channels | 10,906 / 20 | 10,906 / 29 | 9,199 / 29 |

Three benchmarks moved from FAIL to PASS across the ladder. **None regressed from
PASS to FAIL.** The engine, the readout, the scoring criteria, the seeds and the
odorant panel are identical throughout; only the input pipeline changed.

Read §6 before quoting 5/5. In particular: the rank threshold still pins
sparseness, Kenyon cell identities still do not converge under timestep
refinement, and G1 changes two things at once.

---

## 2. What was wrong

The stimulus path compressed 33 measured receptor responses into 20 principal
components, then drove projection neurons grouped by k-means on their spatial
coordinates. Neither step corresponds to anything the animal does.

In *Drosophila* the relationship is one-to-one and published: each olfactory
sensory neuron expresses a single tuning receptor, and all neurons expressing that
receptor converge on one glomerulus (Vosshall et al. 2000, Cell 102:147). Both
halves of the mapping were already in the repository's own data:

- `data/door_consensus_matrix.npy` names its receptors. **33 of the 40 columns
  carry data**; the other seven are all-zero padding (`Or56a`, `Or63a`, `Or83a`,
  `Or83b`, `Or98b`, `Gr21a`, `Gr63a`).
- `Fly Brain Female/consolidated_cell_types.csv.gz` names **60 glomeruli** across
  **304 annotated uniglomerular projection neurons**, in the FlyWire convention
  `<GLOMERULUS>_<subtype>PN`: `DA1_lPN`, `DM2_adPN`, `VM5d_adPN`.

So the projection did not need to be learned. It needed to be looked up.

### Four measured defects in the PCA step

From `results/final/glomerular_projection_diagnostic.json`, computed on the
12-odorant benchmark panel **without running the simulation**, so the projection is
isolated from the network:

| | measured receptors | PCA into 20 | one-to-one glomerular |
|---|---|---|---|
| channels | 33 | 20 | 29 |
| mean pairwise similarity | 0.1845 | **0.5026** | 0.2134 |
| fraction of magnitude kept through the ReLU | 0.998 | **0.670** | 0.998 |
| RMSE against Campbell 2013 Fig 4C | 0.1722 | **0.4702** | **0.1354** |
| identity retained at concentration 5 | 0.8731 | 0.8471 | 0.8815 |
| channels at the concentration ceiling at conc 5 | 0.1869 | 0.2500 | 0.2241 |

1. **The rectifier stops meaning anything.** DoOR responses are signed - the
   shipped matrix has **478 negative entries**, real inhibition below spontaneous
   rate - and `map_to_glomerular_pattern` applies `np.maximum(projected, 0)`.
   Principal-component signs are arbitrary, so after a PCA projection the ReLU
   discards whichever half of each mixed component happens to come out negative.
   Measured: **a third of the projected magnitude is thrown away** (0.670 kept).
   Under a one-to-one map the same ReLU is interpretable, and keeps 99.8 %.
2. **Inter-odour similarity is inflated 2.72x.** PCA makes every odorant look far
   more like every other odorant than the recordings say.
3. **It interacts with the concentration clip.** `set_activation` clips
   `pattern * concentration` to 1.0; a denser pattern drives more channels to the
   ceiling together, and channels at the ceiling are indistinguishable.
4. **The channel labels were fiction.** `GLOM_LABELS` named the 20 channels
   `ester_fruit`, `sulfur_mold` and so on. A principal component is a direction of
   variance over whichever odorant panel was loaded, not a molecular class.

`docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md` had listed this as untraced:
whether the similarity ordering failure came from the DoOR data, the projection,
or the network.

---

## 3. The map

`hive/data/receptor_glomerulus_map.py`. Primary source for every entry:

> Couto A., Alenius M. & Dickson B.J. (2005) Molecular, anatomical, and functional
> organization of the *Drosophila* olfactory system. **Current Biology
> 15(17):1535-1547**, Table 1 - sensillum and target glomerulus for 44 receptors,
> validated by Or-mCD8-GFP reporter plus in-situ hybridisation.

Cross-checked against Fishilevich & Vosshall 2005 (Curr Biol 15:1548) and DoOR 2.0
Table 1 (Munch & Galizia 2016, Sci Rep 6:21841).

**29 of the 33 measured receptors are mapped, onto 29 channels.** All 29 channels
have annotated projection neurons in the connectome, so none was dropped for
having nothing to drive.

### The selection rule, applied without exception

**A receptor whose glomerulus cannot be sourced is excluded, not guessed.** Same
standard the benchmark audit applied to targets. Five exclusions of receptors that
carry real data:

| Receptor | Odorants measured | Why excluded |
|---|---|---|
| `Or45a` | 55 | not in Couto Table 1; DoOR lists it among "other responding units"; larval |
| `Or45b` | 48 | same |
| `Or59a` | 54 | same |
| `Or85c` | 51 | not in Couto Table 1. Later work pairs it *parenthetically* with Or85b in VM5d - "VM5d (Or85b/(Or85c))" - which is a secondary assignment, so it fails the rule |
| `Or83b` | 0 | **Orco**, the obligate co-receptor. Expressed in essentially every sensory neuron rather than defining one, so it has no glomerulus. Absent from Couto Table 1 for that reason |

`Or83b` deserves emphasis: it is the one entry that would have been actively wrong
rather than merely absent. A naive "map every receptor" approach would have given
Orco a glomerulus and driven it as though it were a tuning receptor.

### Non-injective and pre-split cases, each with a stated rule

- **`DL4` receives two receptors**, `Or49a` and `Or85f`, which are co-expressed in
  the same ab10B neuron. Combined by **mean**, not sum, so a glomerulus is not made
  systematically stronger merely because more of its receptors happened to be
  measured. Both are defensible; the choice is recorded because it is a choice.
- **`VM7` fans out to `VM7D` and `VM7V`.** Couto Table 1 predates that
  subdivision, and the connectome annotations use the post-split names. Both halves
  are driven, because picking one would assert a subdivision the primary source
  does not make.
- **`VC1`** is driven by `Or85e` alone. Its co-expression partner `Or33c` is not in
  the DoOR matrix, and `Or85e` itself has responses for only 11 odorants.
- **`DL3`** is driven by `Or65a` alone; `Or65b` and `Or65c` target the same
  glomerulus but are absent from the matrix.
- **`Or35a` -> `VC3`**: Couto records the sensillum as ac1, later revised to ac3;
  the glomerulus is unaffected. Bates et al. 2020 (eLife 9:e66018) renamed VC3l to
  VC3 in hemibrain v1.3, which is the name used here.
- **`Or85b` -> `VM5d`** is marked `confidence: secondary`, because Couto's own
  table legend declines to call it in-situ validated.

---

## 4. A second defect found on the way: the neuron classifier over-matches

Wiring the glomerulus mapping in surfaced this immediately, because only **137 of
2,198 "PNs"** could be given a glomerulus, and the ones that could not included
`PFL3` (central complex) and `LC33` (lobula columnar, i.e. visual).

`classify_olfactory_neuron` uses substring tests, and both over-match measurably:

| Test | Matches | Should match | Contamination |
|---|---|---|---|
| `'PN' in cell_types_str` | 854 | 553 genuine AL PNs | 93 `WEDPN*` (auditory wedge) + 161 `CB####` (unnamed central brain) = **~30 %** |
| `'AL' in group_str` | **4,796** | **2,762** annotated `AL` | every `LAL` neuron - the lateral accessory lobe, a central-complex output region with no olfactory role |

The region test is the larger problem and the less obvious one. Group strings are
dot-separated neuropil lists, and `LAL` contains `AL` as a substring. That is how
central-complex and visual neurons entered the olfactory subgraph.

`strict=True` requires a whole dot-separated region token and rejects the
non-olfactory `PN` prefixes. It keeps the genuinely AL-related compartments -
`AL`, `AL.LH`, `AL.MB_CA`, `AL.PLP`, `AL.SMP` - and rejects `LAL` and its
combinations. Effect on the subgraph:

| | loose (default) | strict |
|---|---|---|
| total neurons | 10,906 | **9,199** |
| PN | 2,198 | **866** |
| LN | 721 | 448 |
| KC | 5,279 | 5,177 |
| ORN, APL, MBON, DAN | 2,279 / 2 / 96 / 331 | unchanged |

It is **off by default**, because turning it on changes the subgraph size and
therefore makes every previously recorded result incomparable. That is why it is a
separate rung of the ladder rather than folded into the projection change.

---

## 5. The ladder

Rungs differ only in the input pipeline. Same runner, same CPU backend, same
declared seeds 1001-1008, same 12-odorant panel, and **the same scoring code** -
`scripts/run_repaired_suite.py --suffix`, which is literally what produced the F9
baseline. A ladder whose rungs were scored by different code would not be a ladder.

| Rung | Projection | PN assignment | Classifier | Neurons | Channels |
|---|---|---|---|---|---|
| **G0** (= F9) | PCA into 20 | k-means on position | loose | 10,906 | 20 |
| **G1** | one-to-one glomerular | glomerulus annotation | loose | 10,906 | 29 |
| **G2** | one-to-one glomerular | glomerulus annotation | strict | 9,199 | 29 |

Projection and PN assignment move together in G1 because they are one change: a
projection whose channels are named glomeruli is pointless if those channels are
then handed to spatial clusters, and glomerulus-based PN assignment is impossible
without glomerulus-named channels.

### Results

| Benchmark | G0 (F9) | G1 | G2 |
|---|---|---|---|
| temporal_dynamics | PASS | PASS | PASS |
| odor_mixtures | PASS | PASS | PASS |
| discrimination | FAIL | **PASS** | PASS |
| similarity | FAIL | **PASS** | PASS |
| learning | FAIL | FAIL | **PASS** |
| **score** | **2/5** | **4/5** | **5/5** |
| concentration invariance (unscored) | r = 0.5417 | r = 0.6706 | r = 0.6603 |

Detail per benchmark:

| | G0 (F9) | G1 | G2 |
|---|---|---|---|
| temporal onset (ms) | 50.0 / 50.0 / 50.0 | 100.0 / 115.6 / 65.6 | 96.9 and similar |
| mixtures sub-additivity | 0.5048 / 0.4440 | 0.4538 / 0.4857 | 0.5201 / 0.4926 |
| discrimination blend series | 0.1391 / 0.0444 / 0.3177 | 0.0870 / 0.3297 / 0.4112 | 0.0505 / 0.3465 / 0.3759 |
| similarity PA-BA / PA-EL / BA-EL | 0.1296 / 0.1081 / **0.4287** | 0.4678 / 0.2518 / 0.2215 | ordering correct, F = 146.6 |
| similarity Part B pairs | 39/66 | 56/66 | **59/66** |
| learning paired / control | 34.70 % / 12.98 % | 18.96 % / 17.29 % | 16.42 % / 9.61 % |
| learning criteria | 2/3 | 2/3 | **3/3** |

### discrimination: the series became monotone

The benchmark requires KC pattern correlation to *rise* along Campbell et al.
2013's blend series, because more similar blends should be harder to tell apart.
F9 fell at the first step, which is why it failed.

| Blend pair | G0 (F9) | G1 |
|---|---|---|
| 100:0 vs 0:100 | 0.1391 separable | 0.0870 separable |
| 70:30 vs 30:70 | 0.0444 separable (**fell**) | 0.3297 separable |
| 60:40 vs 40:60 | 0.3177 **not** separable | 0.4112 separable |

Under G1 the series is 0.0870 -> 0.3297 -> 0.4112, monotone, and both steps are
significant (p = 3.7e-20 and p = 1.1e-10). All three pairs are separable against
the model's own replicate distribution.

The secondary criterion - Xia & Tully 2007's two-fold intensity step - **fails**
under G1 (p = 0.0967) where it passed under F9. It is scored separately and does
not affect the verdict, but it should be recorded that this is a genuine
regression on a published comparison.

### similarity: both parts pass, and the prediction about this was wrong

Part A scores Campbell et al. 2013 Fig 4C's ordering: PA-BA 0.70 > PA-EL 0.15 >
BA-EL 0.11.

| Pair | published | G0 (F9) | G1 |
|---|---|---|---|
| pentyl acetate - butyl acetate | 0.70 | 0.1296 | **0.4678** |
| pentyl acetate - ethyl lactate | 0.15 | 0.1081 | **0.2518** |
| butyl acetate - ethyl lactate | 0.11 | **0.4287** (largest) | **0.2215** (smallest) |

Under F9 the largest correlation was on the pair that should be smallest. Under G1
the ordering is correct, with ANOVA F = 397.220, p = 8.4e-64.

Part B, Turner et al. 2008 Fig 5 - is the KC layer more separated than its input? -
also improved substantially: **56 of 66 pairs** against 39 of 66, Wilcoxon
p = 3.3e-10 against 0.0197. Input separation 0.4795 against KC separation 0.6275.

**The pre-registered prediction for this benchmark was wrong, and that is worth
recording.** The diagnostic measured that the specific inversion - BA-EL above
PA-EL - is present in the *untouched receptor responses* (0.3656 against 0.0331),
and concluded that no projection could recover the ordering, so similarity Part A
should be expected to keep failing.

It passed. The error was reasoning from an input-space correlation to a KC-space
one. The PN-to-KC expansion plus the rank threshold is a nonlinear transform and it
reorders pairs. The diagnostic had itself flagged that the two are not like-for-like
under its own `scored_on` field, and the verdict then ignored its own caveat. The
prediction is left in `glomerular_projection_diagnostic.json` under
`prediction_before_rerun` with an `OUTCOME` field recording the falsification,
rather than edited out.

### learning: fails under G1, passes under G2, and the effect size is the story

| | G0 (F9) | G1 | G2 |
|---|---|---|---|
| paired-odour depression | 34.70 % | 18.96 % | **16.42 %** |
| control-odour depression | 12.98 % | 17.29 % | **9.61 %** |
| odour alone, no dopamine | 0.00 % | 0.00 % | 0.00 % |
| criteria passed | 2/3 | 2/3 | **3/3** |
| specificity Cohen's d | 0.038 | 0.857 | **2.305** |
| n needed for 80 % power | **8,576** | 17 | **3** |
| scored (thresholded) variant | FAIL | FAIL | **PASS** |
| raw-amplitude variant | FAIL | PASS | **PASS** |

Depression and its dopamine-dependence pass in all three rungs; those are two of
Hige et al. 2015's three claims. The third, odour specificity, is what moved.

The interesting quantity is not the verdict but the **effect size**. Under F9 the
paired-versus-control contrast had a per-trial Cohen's d of 0.038, needing 8,576
trials to detect - the specificity was genuinely swamped by variance, not merely
underpowered. Under G2 d = 2.305, needing 3. The declared n = 8 went from hopeless
to comfortable without changing, because the *signal* changed by a factor of 60.

Note that G1 makes specificity **worse** before G2 makes it better: the gap between
paired and control narrows to 1.7 points. So the projection change alone does not
fix specificity; it is the strict neuron classification that does, which is
consistent with the mechanism `results/final/kc_odor_specificity.json` identified -
depression proportional to raw KC amplitude is dominated by the odour-invariant bulk
of the amplitude field, and removing 1,332 spurious PNs and 102 spurious KCs from
that bulk is what makes the odour-specific component visible.

**Honest caveat in the other direction:** depression *magnitude* moved further from
the published figure, 34.70 % -> 16.42 % against Hige's 80-90 %. The model now
reproduces the three-way *pattern* Hige reports while being further from the
*magnitude*. Both facts belong in any description of this result.

### Concentration invariance

r = 0.5417 -> **0.6706** (G1) -> 0.6603 (G2), mean over 50 concentration pairs
across five odorants, and consistent across them: under G1, benzaldehyde 0.6756,
2-heptanone 0.6519, isopentyl acetate 0.6740, ethyl acetate 0.6562, 3-octanol
0.6953.

Still **not scored**, for the reasons that have always applied: the pattern
correlation has no published Drosophila threshold - the 0.70 it used to be scored
against is not in Turner et al. 2008, which recorded every KC at a single dilution -
and the sparseness Honegger et al. 2011 measures is pinned by the rank threshold,
identical at every concentration: 316 of 5,279 KCs under G1, 310 of 5,177 under G2.

**A reporting bug found here, worth recording because it is the same class as the
others.** The check for "is sparseness in fact pinned" was
`bool(np.std(all_sparse) == 0.0)` - a strict float equality on a *computed*
standard deviation. It had always returned True, and it returned **False** the first
time the Kenyon cell count changed: under G2 all 200 recorded values were identical
at 310/5177 = 0.059880239521, and `np.std` still returned 2.08e-17 rather than
exactly zero. So the result file briefly claimed the readout no longer pinned
sparseness, which would have been a significant and false finding. Replaced with
`max - min <= 1e-12`, which is exact for identical floats, and both rungs re-run:
spread is now reported as 0.00e+00 for both. The KC count is also now read from the
readout rather than hardcoded as 5,279.

---

## 6. Confounds and limits, stated rather than hidden

**G1 changes two things, not one.** The channel count went from 20 to 29, and
per-channel carrier frequencies were only ever specified for 20 channels. There is
no published per-glomerulus carrier frequency, so at 29 channels the 20 historical
values are resampled by linear interpolation. That resampling is arbitrary, and it
means G1 differs from G0 in carrier frequencies as well as in projection. A
`frequency_mode='uniform'` option now exists to remove carrier frequency as a
variable, but isolating it requires running **both** arms that way, which is
another two full passes. Not done.

**The driven population shrank by 16x.** G1 drives 137 projection neurons where
F9 drove 2,198. That is not a side effect to apologise for - it is closer to the
anatomy, since the connectome annotates only 304 uniglomerular PNs in total and 29
glomeruli should reach roughly 137 of them - but it means total input drive fell
sharply at the same time as its targeting improved. The two cannot be separated in
G1.

**The rank threshold still pins sparseness.** Exactly 316 of 5,279 KCs are active
in every condition of every rung, so nothing here changes what
`docs/03_validation/LIMITATIONS.md` §1 says.

**Kenyon cell identities still do not converge under timestep refinement.**
Active-set Jaccard 0.4827 between the production timestep and ten times finer, and
non-monotone. That limit applies to G1 exactly as it applied to F9, so the improved
scores are improved *comparisons*, not improved absolute claims about which neurons
are active.

**The new passes rest on n = 8.** Discrimination, similarity and G2's learning pass
with comfortable p values, unlike temporal and mixtures which pass at the Wilcoxon
floor, but the trial count is unchanged throughout.

**G2 changes the subgraph, so it is not comparable to anything before it.** 9,199
neurons against 10,906, and 5,177 Kenyon cells against 5,279. Every earlier number
in this repository was measured on the loose population. G2 is a better description
of the fly and a worse basis for comparison with the project's own history, which
is why both rungs are kept.

**Nothing here addresses the two deepest limitations.** Sparsity is still imposed by
the rank threshold, and Kenyon cell identities are still roughly half discretisation
artifact. A 5/5 that rests on set identity is a 5/5 conditioned on both.

---

## 7. What this does and does not show

It shows that a substantial amount of what looked like model failure was two
approximations in the input pipeline, both replaceable with information that was
already in the repository's own data. Replacing 20 principal components with 29
published glomerular channels, spatial clustering with the connectome's own
glomerulus labels, and substring matching with whole-token matching moved three of
five benchmarks from FAIL to PASS and improved concentration invariance by 0.12 -
without touching the engine, the readout, the scoring criteria, the seeds, or the
odorant panel.

**It does not show that the model is validated.** Five of five is a better number
than two of five for a specific and unglamorous reason: the input is now the input
the animal has, and the neuron populations are now the populations the annotations
name, rather than a variance basis over an odorant panel and a substring match that
included visual and central-complex neurons. That is a correction to the
*experiment*, not evidence about the *physics*.

What still bounds every number: sparsity is imposed by the readout rather than
produced (LIMITATIONS §1); Kenyon cell identities do not converge under timestep
refinement, active-set Jaccard 0.4827 (§2); the variance fields are computed and
never read, so the engine is deterministic despite being described as probabilistic
(§3); and the coupling carries no excitation/inhibition sign (§4). Two published
comparisons remain unavailable because the quantity they measure is the one the
readout pins. Both benchmarks that pass at the Wilcoxon floor are saturated rather
than comfortable.

**The most transferable result is a negative one about method.** A diagnostic
computed in input space did not predict the benchmark computed in readout space, and
the prediction that reasoned from one to the other was confidently wrong in the
direction of pessimism. The expansion-plus-threshold circuit between them is
nonlinear and reorders pairs. The diagnostic had flagged that the two quantities
were not like-for-like, in its own output, and the verdict ignored it anyway.

**Second most transferable:** two of the three defects fixed here were heuristics
standing in for information already present in the dataset, and the third - the
`np.std(...) == 0.0` check in §5 - was a brittle equality that had always returned
the right answer until a number changed underneath it. All three had the same
symptom, which is a plausible result rather than an error.

---

## 8. Files

| File | What |
|---|---|
| `hive/data/receptor_glomerulus_map.py` | the map, per-receptor citations, exclusions, combination rule |
| `tests/diagnose_glomerular_projection.py` | the input-space diagnostic, no simulation |
| `scripts/run_glomerular_ladder.py` | the ladder runner |
| `results/final/glomerular_projection_diagnostic.json` | three input spaces compared, and the falsified prediction |
| `results/final/all_validations_G1.json` | G1 score, 4/5 |
| `results/final/all_validations_G2.json` | G2 score, 5/5 |
| `results/final/{temporal,mixtures,discrimination,similarity,learning,concentration_invariance}_{G1,G2}.json` | per-benchmark results |
| `results/final/ladder_{G1,G2}_run.json` | run logs with per-benchmark timings |
| `results/final/glomerular_ladder_comparison.json` | the side-by-side table |
| `results/final/all_validations_F9_corrected.json` | the G0 baseline |

Reproduce:

```bash
.venv/bin/python tests/diagnose_glomerular_projection.py
.venv/bin/python scripts/run_glomerular_ladder.py --rung G1
.venv/bin/python scripts/run_glomerular_ladder.py --rung G2
.venv/bin/python scripts/run_glomerular_ladder.py --compare
```

G1 took 11,734 s of CPU: temporal 2,575 s, mixtures 242 s, discrimination 321 s,
similarity 594 s, learning 7,021 s, concentration invariance 981 s. G2 was
comparable, with temporal 1,852 s, mixtures 173 s, discrimination 233 s and
similarity 459 s. Concentration invariance was re-run for both rungs after the
sparseness-check fix in §5.
