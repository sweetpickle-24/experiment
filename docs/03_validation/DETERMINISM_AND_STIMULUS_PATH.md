# Deterministic MLX and a Repaired Odour Stimulus Path

**Date**: 2026-09-03
**Last Updated**: 2026-09-05 (forward pointer added; the report itself stands)
**Status**: Complete. Score 2/5 (was 1/5). MLX bit-for-bit reproducible. Verified speedup 10.00x.

> **Still accurate for what it covers, but no longer the current score.** This report
> documents the determinism fix and the stimulus-path repair, and every measurement in
> it stands. The 2/5 it ends on was superseded twice after it was written: the
> benchmark targets were checked against their cited papers
> ([BENCHMARK_VALIDITY_AUDIT.md](BENCHMARK_VALIDITY_AUDIT.md)), and then the input
> projection was corrected, taking the suite to **5/5**
> ([GLOMERULAR_PROJECTION_REPAIR.md](GLOMERULAR_PROJECTION_REPAIR.md)).
>
> One finding here has since been extended: this report establishes that the engine
> has no stochasticity in its step. It goes further than stated — the variance fields
> are computed every step and read by nothing, so `sigma_noise` cannot affect any
> output at all. See [LIMITATIONS.md](LIMITATIONS.md) §3.

Every number below cites the result file that produced it. Nothing here is
quoted from prose.

---

## 1. Summary

| Outcome | Before | After | Evidence |
|---|---|---|---|
| MLX same-seed reproducibility | 11 of 15 trials differed, 303 vs 203 active KCs | bit-for-bit identical, 5/5 trials, all state fields | `results/final/mlx_determinism.json` |
| CPU vs MLX speedup | 86.34x (unusable) | **10.00x** (range 9.96-10.03x) | `results/final/cpu_vs_mlx_speedup.json` |
| CPU vs MLX output agreement | pattern_correlation null, kc_pattern empty | 62 vs 62 active KCs, Jaccard 1.0000, r = 0.9999 | `results/final/cpu_vs_mlx_speedup.json` |
| Five-benchmark score | 1/5 | **2/5** | `results/final/fix_ledger.json` |
| Concentration invariance (binary r) | 0.1031 | **0.2719** | `results/final/fix_ledger.json` |
| Driven PNs pinned at amplitude ceiling | 981 / 2198 | **0 / 2198** | `results/final/fix_ledger.json` |
| Phase advance per integration step | 18.09 rad (5.8x the pi aliasing limit) | **1.294 rad** | `results/final/dt_convergence.json` |
| Dead tests in `tests/` | 4 had never executed | all 4 run; 3/4 verdicts agree with the suite | `results/final/legacy_vs_suite_comparison.json` |

---

## 2. Correction to the premise

**The units defect in `OdorReceptorArray.compute_forces` was not the cause of
the flat benzaldehyde trace.** It is a real defect and it is fixed, but it is
not on the path that produced any reported result.

`scripts/run_all_validations.py` and `tests/concentration_invariance_test.py`
drove the brain only through `brain.inject_odor(...)`, which wrote a single
constant force vector. `compute_forces` is reachable only from `hive/main.py`
-> `OlfactorySystem` -> `hive/interface/sensory.py`, and from two demo scripts.

Proof rather than assertion: after the units fix, the suite's entire
`validations` block is **identical** to the run before it, the
concentration-invariance `summary` is identical, and the only field that
differs anywhere in the invariance results is `simulation_time_sec`. Compare
ledger entries `F1_after` and `F3_after`, or diff
`results/final/all_validations_F1_after.json` against
`all_validations_F3_after.json`.

The actual cause was measured directly: under the constant drive all 999 driven
PNs reached the amplitude clip ceiling within 50 ms and the system sat at a
fixed point, so KC activity was flat at 0.000484 / 0.000489 / 0.000491 /
0.000483 at t = 50 / 100 / 500 / 2000 ms. That reproduces the reported trace in
`results/final/all_validations_cpu_seed42.json` (0.0004857, 0.0004860,
0.0004917, 0.0004724, 0.0004837). `OdorReceptorArray.update_adaptation`, whose
time constant is the quantity the temporal benchmark scores, was never called.

**A second premise did not hold either.** The rank-threshold tie hypothesis is
not the mechanism: all 981 ceiling-pinned neurons were PNs, while the top-316
cutoff ranks the 5,279 KCs, of which **0** were at the ceiling and whose raw
amplitudes peaked at 0.20. The saturation destroyed concentration information
one stage upstream instead, by making PN amplitude identical at every
concentration so that concentration reached the KCs through phase alone.

---

## 3. What each fix changed

One ledger entry per fix, in `results/final/fix_ledger.json`. Reported runs are
CPU, seed 42, dt = 0.1 ms, 100 ms per trial.

### Five-benchmark suite

| metric | threshold | F0 before | F0 PCA | F1 determinism | F3 units | F4 front-end | F5 guard | F6 mapping |
|---|---|---|---|---|---|---|---|---|
| temporal: peak time (ms) | 50-150 | 850 | 383.3 | 216.7 | 216.7 | 366.7 | **50** | 200 |
| temporal: adaptation (%) | 30-70 | 5.92 | 21.47 | 21.78 | 21.78 | **49.74** | 74.07 | **34.21** |
| temporal: verdict | | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| mixtures: overlap (%) | 30-50 | 11.23 | 24.84 | 24.84 | 24.84 | **35.60** | **34.34** | **30.06** |
| mixtures: verdict | | FAIL | FAIL | FAIL | FAIL | **PASS** | **PASS** | **PASS** |
| discrimination: JND (%) | 10-20 | 5, 5 | 5, 5 | 5, 5 | 5, 5 | 5, 5 | 5, 5 | 5, 5 |
| discrimination: verdict | | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| similarity: chem-neural r | 0.3-0.5 | 0.6229 | 0.9937 | 0.9688 | 0.9688 | -0.9665 | -0.9988 | -0.1204 |
| similarity: verdict | | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| learning: MBON change (%) | >= 1.0 | 28.74 | 331.3 | 5.75 | 5.75 | 96.5 | 99.98 | 99.99 |
| learning: verdict | | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| **SCORE** | 5/5 | **1/5** | 1/5 | 1/5 | 1/5 | **2/5** | 2/5 | **2/5** |

### Concentration invariance

| metric | threshold | F0 before | F0 PCA | F1 | F3 | F4 | F5 | F6 |
|---|---|---|---|---|---|---|---|---|
| binary r mean | > 0.7 strong | 0.1031 | 0.1157 | 0.1185 | 0.1185 | 0.1962 | 0.2109 | **0.2719** |
| binary r sd | | 0.1030 | 0.1341 | 0.1367 | 0.1367 | 0.0709 | **0.0584** | 0.1232 |
| binary r min | | -0.0175 | -0.0185 | -0.0302 | -0.0302 | 0.0885 | **0.1203** | 0.0812 |
| binary r max | | 0.3672 | 0.4657 | 0.4817 | 0.4817 | 0.3338 | 0.3465 | **0.5244** |
| Jaccard mean | > 0.6 strong | 0.0590 | 0.0694 | 0.0711 | 0.0711 | 0.1114 | 0.1195 | **0.1620** |
| verdict | strong | weak | weak | weak | weak | weak | weak | weak |

### Stimulus path

| metric | want | F0 PCA | F4 front-end | F5 guard | F6 mapping |
|---|---|---|---|---|---|
| drive time-varying | yes | no | **yes** | yes | yes |
| drive peak force | | 36.14 | **6.058** | 6.058 | 6.058 |
| PNs at amplitude ceiling | 0 | 981/2198 | 109/2198 | **0/2198** | **0/2198** |
| PN amplitude max | below guard | 10.0 (clipped) | 10.0 (clipped) | **13.66** | 13.67 |
| KCs at amplitude ceiling | 0 | 0/5279 | 0/5279 | 0/5279 | 0/5279 |
| peak abs velocity (rad/ms) | | 180.9 | **12.28** | 12.27 | 12.94 |
| phase advance / step (rad) | < pi | 18.09 | **1.228** | 1.227 | 1.294 |

### Fix by fix

**F0 - real PCA replaces a silent fallback.** `DoorClient` degraded to
uncentered SVD whenever scikit-learn was absent, which it was, while every
docstring and result file said PCA. scikit-learn 1.9.0 installed; the
projection is now selected explicitly and a missing dependency raises.
`uncentered_svd` stays selectable to reproduce old numbers.

Effect: no threshold crossed, but several metrics moved substantially. Temporal
peak 850 -> 383.3 ms, adaptation 5.92 -> 21.47%, mixture overlap 11.23 ->
24.84%, similarity r 0.6229 -> 0.9937 (further outside its band), invariance
0.1031 -> 0.1157. Score 1/5 -> 1/5.

**F1 - deterministic coupling accumulation.** `forces.at[post_idx].add(...)`
lowers to unordered atomic scatter-add on Metal. Sorting the indices does not
help: still 7.45e-9 run-to-run drift after a stable sort. Replaced with a
static two-stage segment reduction (synapses sorted by postsynaptic index once,
padded into 64-wide blocks so no block straddles two neurons, then two
fixed-shape axis reductions). Cost 0.251 ms/call against 0.248 ms for the
scatter it replaces. The NumPy path shares the layout.

Effect: MLX became reproducible. Because the summation order changed on CPU
too, CPU numbers moved: temporal peak 383.3 -> 216.7 ms, similarity r 0.9937 ->
0.9688, learning 331.3 -> 5.75%, invariance 0.1157 -> 0.1185. Score 1/5.

**F3 - carrier units.** `omega = 2*pi*f` with f in Hz multiplied by t in
milliseconds, so the carrier advanced f cycles per millisecond, 1000x too fast.
Every channel frequency is a whole number of Hz, so the aliased phase landed on
a multiple of 2*pi at every sample: measured 1 distinct value across 10 samples
on a 1 ms grid and 0 sign changes across 2 ms at dt = 0.1 ms, for a channel
whose period is 50 ms. After the fix channel 0 measures 20.00 Hz against its
stated 20 Hz with 500 distinct values over 60 ms.

Effect: **none, as predicted.** Every reported value is bit-identical to
F1_after. Score 1/5.

**F4 - receptor front-end wired in.** `inject_odor` now attaches a stimulus
that `evolve` re-evaluates every step: turbulent plume, per-channel sinusoidal
carrier, 200 ms adaptation recursion. `strength` maps to concentration as
`strength/50.0`; `amplitude_scale = 10.0` from `hive/config.yaml` is the only
force constant. No plume, carrier or adaptation constant was changed.

Drive verified time-varying (714 sign changes over 2000 ms) and adapting (peak
force envelope 6.058 -> 1.068 across 2000 ms, adaptation reaching its 0.2
floor).

Effect: **score 1/5 -> 2/5.** Mixtures 24.84 -> 35.60% (PASS). Temporal
adaptation 21.78 -> 49.74%, inside its band, though peak time 216.7 -> 366.7 ms
keeps the benchmark failing. Invariance 0.1185 -> 0.1962 with the spread
tightening sharply (sd 0.1367 -> 0.0709, min -0.0302 -> +0.0885, so no odour
pair is anticorrelated across concentration any more). Temporal traces became
genuinely transient: benzaldehyde went from flat at 0% adaptation to peaking at
50 ms with 77.34%.

**F5 - amplitude guard lifted off the signal path.** `clip(amplitude, 0.001,
10.0)` was hardcoded in three places, and 10.0 sat inside the physical
operating range. The bound is now derived: the amplitude recursion has unit
steady-state gain to `|v|` (`A* = |v| * 0.1 / gamma`, gamma = 0.1), and a damped
oscillator under bounded forcing satisfies `|v| <= F_max / (2*gamma)` = 30.3 for
the measured `F_max` of 6.06. The guard sits three orders above that, and
`count_at_amplitude_ceiling()` makes the claim testable: it returns 0 for all
eight runs of the dt sweep.

This is a numerical guard change, not a physics change.

Effect: PNs at ceiling 109 -> 0, PN amplitude max 10.0 -> 13.66. Temporal peak
time 366.7 -> **50 ms**, inside its band, but adaptation 49.74 -> 74.07%
overshoots by 4.07 points, so the benchmark still fails - now for the opposite
reason. Invariance 0.1962 -> 0.2109. Score 2/5.

**F6 - glomerular mapping by position.** `inject_odor` assigned
`channel = floor(local_rank / pns_per_ch)` where `local_rank` is the neuron's
index in `self.neuron_ids`, i.e. connectome iteration order. Each channel drove
an arbitrary block of 109 PNs that were neither a glomerulus nor near each
other. `GlomerularMapper`, which clusters PNs by connectome coordinates,
already existed and was unused.

Measured spatial coherence (mean within-channel positional spread relative to
the spread of all PNs): index **0.993**, position **0.300**. Cluster sizes go
from a uniform 109/109/127 to 28/94/255.

Effect: largest invariance gain of any fix, 0.2109 -> **0.2719** (max 0.3465 ->
0.5244, Jaccard 0.1195 -> 0.1620). Temporal adaptation 74.07 -> 34.21%, back
inside its band, but peak time 50 -> 200 ms moves outside. Similarity r
-0.9988 -> -0.1204, much closer to its band. Score 2/5.

**F7 - the four dead tests.** See section 6.

---

## 4. Goal A: MLX

### Determinism

`results/final/mlx_determinism.json`, 5 same-seed trials per backend, 100 ms,
seed 42:

| backend | all runs bit-identical | worst state diff between runs | distinct active-KC counts |
|---|---|---|---|
| MLX | **true** | 0 | [62] |
| CPU | **true** | 0 | [62] |

Bit-for-bit on `mean_phase`, `mean_velocity`, `mean_amplitude`, `var_phase`,
the normalised KC pattern and the binary active-KC mask.

Cross-backend equality is **not** achieved and cannot be: `mx.sum` and `np.sum`
use different reduction trees, so the two differ in the last bits of every
step. Measured max phase difference 6.2 rad (the phase is wrapped to
[-pi, pi], so this is a fully diverged neuron), yet both backends select the
**same 62 active KCs**, Jaccard **1.0000**.

### Speedup

`results/final/cpu_vs_mlx_speedup.json`. Same `SparseProbabilisticBrain`,
10,906 neurons, 446,388 synapses, dt = 0.1 ms, 1,000 steps, 5 timed repeats
after a warm-up so `mx.compile` tracing is excluded. `configuration_matched`
is asserted, not assumed.

| backend | median wall | sd | mode | RT factor |
|---|---|---|---|---|
| MLX | 486.7 ms | 0.5 ms | compiled_mlx | 0.205x |
| CPU | 4867.3 ms | 8.0 ms | numpy | 0.0205x |

**Speedup 10.00x median, range 9.96x - 10.03x.** Output agreement: 62 vs 62
active KCs, Jaccard 1.0000, KC pattern r = 0.9999.

The previous **86.34x is discarded** and the file moved to
`results/superseded/cpu_vs_mlx_validation.json`. It recorded 1,283 active KCs
against a few hundred in current runs, a null `pattern_correlation`, an empty
`kc_pattern`, and `validation_passed: true` against a 0.95 correlation
threshold it never evaluated. Neither backend runs faster than real time.

---

## 5. Goal B: does the model respond to odours sensibly?

Better, and no longer obviously broken at the stimulus path, but not fixed.

Working now: the drive is time-varying and adapting; no neuron sits at a clip
boundary; the integrator is inside its aliasing limit; responses are transient
rather than constant; concentration invariance is 2.6x its baseline and no
longer contains anticorrelated pairs.

`results/final/dt_convergence.json`, production dt = 0.1 ms:

| drive | peak abs velocity | rad/step | aliasing |
|---|---|---|---|
| constant (old path) | 190.6 | 19.06 | **YES**, ~2.9 cycles discarded per step |
| front-end (current) | 20.6 | **2.06** | no |

---

## 6. The four dead tests

`project_to_pca_basis` was not their only breakage and not even their first.
Each of the four constructed
`SparseProbabilisticBrain(num_neurons=..., dt=0.01, use_mlx=True)`, which
raises TypeError because the constructor takes a `connectome` and has no
`num_neurons` or `dt` keyword. Behind that sat
`brain.load_connectome_simple`, `door_client.project_to_pca_basis` and
`brain.inject_external_input('ORN', ...)`, none of which existed, plus odorant
names absent from the DoOR matrix (`geosmin`, `E2-hexenal`).

`validate_learning_plasticity.py` additionally identified KC->MBON synapses by
hardcoded index ranges ("KCs: 5198-10476, MBONs: 10477-10572"). Neurons are
stored in connectome iteration order, not grouped by cell type, so those ranges
selected an arbitrary neuron set.

What they were meant to test: discrimination JND against Weber's law, chemical
vs neural similarity structure, mixture component overlap, and KC->MBON weight
growth under conditioning. All four now run.

`results/final/legacy_vs_suite_comparison.json`:

| phenomenon | threshold | suite | standalone | agree |
|---|---|---|---|---|
| discrimination JND | 10-20% | 5% FAIL | 5% FAIL | yes |
| similarity chem-neural r | 0.3-0.5 | -0.120 FAIL | -0.358 FAIL | yes |
| mixture overlap | 30-50% | 30.06% PASS | 32.14% PASS | yes |
| learning | differs | 99.99% PASS | 1.03x FAIL | **no** |

Three of four agree, and **all three that share a criterion agree**, on
different odour sets and different protocols. The learning pair disagrees
because the criteria differ, and this is the important finding: the suite asks
only whether the MBON response changed by at least 1%, which any measurable
change satisfies, while the standalone applies the quantitative Hige et al.
(2015) target of 2-3x KC->MBON weight growth and **fails at 1.03x**. The
suite's one baseline PASS rests on the weaker criterion.

---

## 7. Still broken

1. **The integration does not converge under dt refinement.** With the stimulus
   held fixed, KC pattern r between dt = 0.1 ms and dt = 0.01 ms is **0.3081**
   and active-set Jaccard is 0.0743
   (`results/final/dt_convergence.json`). Being under the pi aliasing limit is
   necessary, not sufficient. The KC identities at production dt are not the
   solution of the underlying equations. Not addressed: dt is a parameter and
   refining it is not a fix.

2. **temporal_dynamics fails on both halves, alternately.** The criterion needs
   peak time in 50-150 ms *and* adaptation in 30-70%. F5 delivers peak 50 ms
   with adaptation 74.07%; F6 delivers adaptation 34.21% with peak 200 ms.
   Neither satisfies both. Not tuned.

3. **discrimination JND is 5% at every fix, against a 10-20% target.** Unmoved
   by all seven changes. The model discriminates finer than the biological
   benchmark; whether that is a defect or a real property is unresolved.

4. **similarity chem-neural r is outside 0.3-0.5 throughout**, and its sign
   flipped from +0.9688 to -0.1204. The suite computes it from 3 odours, so it
   is a correlation over 3 observations and is not stable; the standalone gets
   -0.358 from 10 pairs. Both fail.

5. **Concentration invariance is still weak.** 0.2719 against 0.5 for moderate
   and 0.7 for strong, despite 2.6x improvement.

6. **The plume is resampled when dt changes**, because it is sampled on the
   integrator's timestep. Any dt comparison on the reported path mixes
   integrator error with a different turbulence realisation. Documented in
   `test_dt_convergence.py`; the constant-drive sweep exists to avoid it.

7. **`hive/config.yaml` still stores `oscillator.dt: 0.0005` annotated
   "(0.5ms)"** - a seconds value that every consumer in `olfactory.py` reads as
   milliseconds. Worked around by `load_olfactory_config`, which samples the
   plume on the engine's dt, rather than by reinterpreting the file, because
   other consumers read that key.

8. **`inject_odor` drives projection neurons, not ORNs.** The four standalone
   tests asked for the receptor stage. The engine injects one stage
   downstream, so the ORN population is never directly stimulated.

---

## Files

Code:
`hive/engine/sparse_probabilistic.py`, `hive/interface/olfactory.py`,
`hive/data/door_client.py`, `validation_utils.py`,
`scripts/run_all_validations.py`, `tests/concentration_invariance_test.py`,
`tests/legacy_validation_support.py`, the four `tests/validate_*.py`.

New tools:
`scripts/fix_ledger.py`, `scripts/ledger_report.py`,
`scripts/compare_legacy_vs_suite.py`, `tests/test_mlx_determinism.py`,
`tests/test_cpu_vs_mlx_speedup.py`, `tests/test_dt_convergence.py`.

Results:
`results/final/fix_ledger.json`, `mlx_determinism.json`,
`cpu_vs_mlx_speedup.json`, `dt_convergence.json`,
`legacy_vs_suite_comparison.json`, `all_validations_F{0,1,3,4,5,6}_after.json`,
`concentration_invariance_F{0,1,3,4,5,6}_after.json`,
`all_validations_F8_final.json`, `concentration_invariance_F8_final.json`.

Superseded: `results/superseded/cpu_vs_mlx_validation.json`.
