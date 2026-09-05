# Limitations

**Date**: 2026-09-04
**Last Updated**: 2026-09-04

What this model does not do, what its numbers cannot support, and what is known
to be broken. Kept as a single document so the README can describe the project
and this can carry the caveats without either one being diluted.

Read this before quoting any olfactory number from
[`results/`](../../results/README.md).

---

## 1. The readout imposes sparsity rather than producing it

Every olfactory measurement reads Kenyon cell activity through
`get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)`, which
applies a rank threshold:

```1098:1111:hive/engine/sparse_probabilistic.py
    def _apply_kc_normalization(self, kc_activity: np.ndarray,
                                target_sparsity: float = 0.06) -> np.ndarray:
        # ... docstring ...
        sorted_activity = np.sort(kc_activity)[::-1]
        threshold_idx   = int(len(kc_activity) * target_sparsity)
        threshold       = sorted_activity[threshold_idx] if threshold_idx < len(sorted_activity) else 0.0
        return np.maximum(0.0, kc_activity - threshold)
```

With 5,279 Kenyon cells and `target_sparsity = 0.06` this keeps exactly
`int(5279 * 0.06) = 316` neurons above zero for every stimulus, every odorant and
every concentration. Population sparseness is therefore pinned at
`316 / 5279 = 0.059860` with standard deviation exactly zero.

It is intended as a model of APL feedback inhibition (Lin et al. 2014) and as a
modelling choice it is defensible. The consequences are not negotiable:

- **Sparsity itself is a parameter, not a result.** Any claim that this model
  reproduces biological sparse coding would be circular, and none is made.
- **Honegger et al. 2011 cannot be compared against.** That paper reports
  population sparseness for both its mixture and its concentration results, which
  is exactly the pinned quantity, so both published comparisons are unavailable
  at the binary level.
- **Set identity is still an output.** The threshold fixes *how many* KCs are
  active, not *which*. Odour-pair similarity, mixture overlap and concentration
  discrimination depend on identity, so they are reported - with the conditioning
  stated, and against a chance baseline where one is meaningful. Two random
  316-of-5,279 sets overlap at 5.99 % by intersection-over-size and 3.09 % by
  Jaccard index.

Replacing the rank threshold with a genuine dynamical loop through the two APL
neurons that are already in the extracted subgraph would make sparsity an output.
It has not been done, and it is the most valuable open change: Lazar et al. obtain
concentration-invariant KC representations *from* APL feedback, which makes the
static approximation here a live suspect for why this model's concentration
invariance is weak.

## 2. Kenyon cell identities do not converge under timestep refinement

This is the most consequential unresolved problem.

Measured with the stimulus held fixed as a function of real time, so that only
integrator error varies (`results/final/dt_convergence_fixed_stimulus.json`,
three seeds). Production `dt = 0.1 ms` against `dt = 0.01 ms`:

| | mean | range |
|---|---|---|
| KC pattern correlation | **0.6758** | [0.6260, 0.7287] |
| active-set Jaccard | **0.4827** | [0.4529, 0.5012] |

**Refinement does not help.** Agreement is non-monotone in `dt` for all three
seeds; for seed 1001 it gets worse as `dt` falls from 0.1 to 0.02 (Jaccard
0.5012 -> 0.4202 -> 0.4013).

So roughly half the active set at the production timestep is discretisation
artifact, and the absolute identity of the 316 active Kenyon cells is not a
property of the model's equations. Benchmarks can still be valid *comparisons*,
because both arms of every contrast share a timestep, but no claim should rest on
which particular neurons are active.

Whether this is a defect or genuine chaos is not determined. A phase-coupled
network near a synchronisation transition can be legitimately chaotic, in which
case individual trajectories are the wrong observable and only distributions over
them are meaningful. Distinguishing the two is the first thing to do; moving from
forward Euler to RK4 or an adaptive stepper is the second.

## 3. The variance fields do not participate in the dynamics

The engine is described in several places as probabilistic or mean-field. As
written it is not.

- `var_amplitude` is set to 0.01 at initialisation and at every `reset`, is
  carried in the state dataclass, and is **never updated by any step function**.
- `var_phase` *is* updated in all three step paths and clipped to [0.01, 10.0],
  but the coupling term multiplies by a hardcoded `exp(-0.1/2)` constant
  (`_var_correction_scalar`) rather than reading the live field. `var_phase` is
  therefore write-only; nothing downstream consumes it.
- Consequently **`sigma_noise` provably cannot change any output.** It enters
  only `_sigma_sq_dt`, which enters only the `var_phase` recursion, which is read
  by nothing. It is nonetheless recorded as a configuration parameter in every
  result file.

The engine as written is a **deterministic** damped harmonic-oscillator network on
a sparse graph. Not fixed. The right fix is structural rather than a patch: an
assertion per subsystem that destroying it must change the output, which
`tests/test_weights_on_signal_path.py` already does for the plasticity path and
nothing does for this one.

## 4. The coupling has no excitation or inhibition

Synaptic coupling is `w · sin(φ_pre − φ_post) · A_pre`, which treats a GABAergic
and a cholinergic synapse identically. `nt_type` and the six per-neuron
neurotransmitter scores are loaded and stored in
[`hive/substrate/connectome.py`](../../hive/substrate/connectome.py) and never
used in the coupling.

This is the largest biological gap in the model. Shiu et al. (2024) build their
whole-brain leaky integrate-and-fire model from connectivity **plus** predicted
neurotransmitter identity, and argue that those two ingredients suffice. This
model has the first and discards the second.

## 5. The MBON readout is not monotone in synaptic weight

Measured across 11 weight scales x 8 trials
(`results/final/mbon_weight_monotonicity.json`):

| readout | Spearman rho | p | monotone |
|---|---|---|---|
| MBON amplitude | **-0.0182** | 0.958 | no |
| KC->MBON coupling current | **1.0000** | 0.0 | yes |

Coupling is a phase-pulling term and amplitude is driven by `|velocity|`, so
tighter phase locking *lowers* amplitude. The response peaks at half strength and
the dynamic range is 14.6 % of maximum.

Hige et al. 2015 measures learning as a reduction in MBON response following
synaptic depression, which presupposes monotonicity. That measurement therefore
cannot be scored in its primary form, and the learning benchmark scores the
coupling current instead - the analogue of the paper's Fig 3D charge-transfer
measurement. The substitution is declared in the result file.

A related limitation: depression can be the right size or aimed at the right
synapses, but not both. Restricting depression to the 316 threshold-passing KCs
gives a 29.93 % ceiling against Hige's 80-90 %, because those KCs carry about
14 % of the KC->MBON amplitude. The raw-amplitude variant reaches 79.96 % but has
*negative* specificity (control 81.73 %).

## 6. Neuron classification is heuristic, and the loose default is wrong

`classify_olfactory_neuron` matches substrings against cell-type strings with a
neuropil-region fallback. Both tests over-match, measurably:

- **Cell types.** The test is `'PN' in cell_types_str`, so `WEDPN6B` (an auditory
  wedge projection neuron) and `CB1078` (an unnamed central-brain neuron) are
  classified as olfactory projection neurons. Of the 854 neurons whose type
  string contains `PN`, 289 are uniglomerular olfactory PNs, 264 are
  multiglomerular `M_` PNs, and **254 - about 30 % - are neither**.
- **Neuropil regions.** The test is `'AL' in group_str`, and group strings are
  dot-separated neuropil lists. That matches every `LAL` neuron - the lateral
  accessory lobe, a central-complex output region with no olfactory role.
  Measured: the substring test matches **4,796** neurons where only **2,762** are
  annotated `AL`. This is how `PFL3` (central complex) and `LC33` (lobula
  columnar, visual) end up in the olfactory subgraph.

`strict=True` fixes both - requiring a whole dot-separated region token and
rejecting the non-olfactory `PN` prefixes - and takes the subgraph from 10,906
neurons to 9,199, with PN falling from 2,198 to 866. It is **off by default**,
because turning it on changes the subgraph size and therefore makes every
previously recorded result incomparable. See the ablation ladder in
[GLOMERULAR_PROJECTION_REPAIR.md](GLOMERULAR_PROJECTION_REPAIR.md).

## 7. The 40-to-20 PCA projection distorts the odour code

Measured without running the simulation
(`results/final/glomerular_projection_diagnostic.json`), comparing the
12-odorant panel in the measured receptor space against the projection the model
receives:

| | measured receptors | PCA into 20 | one-to-one glomerular |
|---|---|---|---|
| mean pairwise similarity | 0.1845 | **0.5026** | 0.2134 |
| fraction of magnitude kept through the ReLU | 0.998 | **0.670** | 0.998 |
| RMSE against Campbell 2013 Fig 4C | 0.1722 | **0.4702** | **0.1354** |

PCA inflates inter-odour similarity by a factor of 2.72 - it makes every odorant
look far more like every other odorant than the recordings say - and its
rectification discards a third of the projected magnitude, because
principal-component signs are arbitrary and the ReLU removes whichever half comes
out negative. The DoOR matrix contains 478 negative entries, which are real
inhibitory responses.

The one-to-one map is available as `projection='glomerular'` and is the subject of
[GLOMERULAR_PROJECTION_REPAIR.md](GLOMERULAR_PROJECTION_REPAIR.md). It is not yet
the default.

Note also what the diagnostic ruled *out*: the specific ordering failure in the
similarity benchmark is upstream of any projection. Campbell reports
`PA-EL 0.15 > BA-EL 0.11`, and the untouched receptor responses have BA-EL
(0.3656) above PA-EL (0.0331). No projection can be blamed for losing an ordering
the input data does not have.

## 8. Neuron coordinates carry no unit and are not rescaled

Positions are stored exactly as exported, in FAFB voxel/nanometre scale, so the
loaded cloud spans roughly 445,000 x 303,000 x 231,000
([`_load_coordinates`](../../hive/substrate/connectome.py)).

Harmless for `SparseProbabilisticBrain`, which uses positions only for clustering
and distance-based delays. **Fatal** for `ProbabilisticWaveBrain`, which derives a
dense voxel grid from the bounding box: at its documented 100 um spacing the shape
comes out (4457, 3032, 2313), about 31.3 billion voxels, roughly 116 GB per
float32 field, and the process is killed with exit code 137. That engine carries a
"do not use with real connectome data" banner and its claimed advantages have
never been measured on real data.

Not fixed, because rescaling changes the coupling distances every recorded run
used.

## 9. Numerical and scale limits

- **Forward Euler.** Timesteps above roughly 2 ms are unstable for the APL
  feedback loop, and the solution does not converge even below that (see §2).
- **Every reported result comes from the 10,906-neuron olfactory subgraph**, not
  the full 139,255-neuron brain. The full-brain path exists; no reported number
  uses it.
- **Reported numbers are CPU.** CPU and MLX agree at 100 ms (Jaccard 0.9627,
  r 0.9932) and diverge past it, worst case Jaccard 0.1030 and r 0.0650 over a
  2,000 ms trajectory, against a rule of Jaccard >= 0.95 and r >= 0.99 fixed
  before the run (`results/final/cpu_vs_mlx_fullrun.json`). The 10x faster
  backend is therefore unusable for reporting. Whether the divergence is bounded
  chaos or a bug in one backend has not been determined.
- **Throughput is unremarkable.** Per edge per second of simulated biology, the
  MLX path is about 1.8x slower than Shiu et al.'s reported figure and about 37x
  slower than the Brian 2 reference in Sandia's Loihi 2 port. This is not a
  performance result.

## 10. Statistical power

Both passing benchmarks pass at `p = 0.0039`, which is the **floor** for a
one-sided Wilcoxon test at n = 8. The tests are saturated rather than comfortably
significant, and whether n = 8 is adequate is recorded as uncertain in the
[audit](BENCHMARK_VALIDITY_AUDIT.md). Read them as "consistent with the published
direction", not as "validated".

For the learning benchmark the power analysis is the informative part: paired
depression of 34.70 % against a control of 12.98 % looks like a large effect, but
per-trial Cohen's d is 0.038, requiring n = 8,576 for 80 % power. It is not
underpowered - the specificity is genuinely swamped by variance.

## 11. Provenance gaps in older material

- **Everything before 2026-09-03 was unseeded**, and the MLX backend was not
  reproducible, so run-to-run variation in that era was large and is not
  recoverable.
- **Many validation scripts print rather than write.** Of the 19 scripts under
  `hive/validation/` containing a `json.dump`, 14 expected output files do not
  exist, and four core vision tests write no file at all. Where a documented
  number had no artifact it was removed rather than kept.
- **`data/digital_smell_database_full.json` is stale.** The 372-odorant KC
  fingerprint database was generated under the superseded constant drive and the
  old amplitude ceiling; its `pn_pattern` fields contain literal `10.0` values,
  i.e. projection neurons pinned at that ceiling. It needs regenerating.
- **Documents under `docs/`, `research/`, `thesis/` and `publication/` predate
  the 2026-09 audit.** They carry a correction banner but have not been
  rewritten. `OUTDATED_FILES.md` tracks which and why.

## 12. Three components that were computed and never used

A recurring defect class worth naming, because the symptom in each case was a
plausible result rather than an error:

| Component | Symptom | Status |
|---|---|---|
| Compiled MLX kernel captured `syn_weights` by value | Zeroing all 49,599 KC->MBON weights changed the MBON response by exactly **0.000 %**; every learning test on that path trained nothing | Fixed, regression-tested |
| `inject_odor` wrote one constant force vector, bypassing plume, carrier and adaptation | All 981 driven PNs saturated within 50 ms and the temporal benchmark measured a constant to four decimal places | Fixed |
| Variance fields computed every step, read by nothing | `sigma_noise` cannot affect any output (§3) | **Not fixed** |

---

## Related documents

- [BENCHMARK_VALIDITY_AUDIT.md](BENCHMARK_VALIDITY_AUDIT.md) - every benchmark
  target checked against the full text of the paper it cites. Four of six were
  not in their cited source and one citation does not exist.
- [DETERMINISM_AND_STIMULUS_PATH.md](DETERMINISM_AND_STIMULUS_PATH.md) - the
  deterministic accumulation fix and the stimulus-path repair, with a per-fix
  ledger.
- [GLOMERULAR_PROJECTION_REPAIR.md](GLOMERULAR_PROJECTION_REPAIR.md) - the
  one-to-one receptor-to-glomerulus map and the ablation ladder.
- [`results/README.md`](../../results/README.md) - which artifact backs which
  claim, including the claims that have no artifact.
