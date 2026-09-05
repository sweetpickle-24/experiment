# Wave-based simulation of the Drosophila connectome

**Last Updated**: 2026-09-04 (stale performance, projection and reproducibility
claims corrected; edge-vs-synapse counts reconciled against the published FlyWire
figures; benchmark section moved to the repaired suite)

This project simulates a fruit fly's brain by treating each neuron as a damped
oscillator and letting activity spread as waves across the real wiring diagram of
the fly brain (the FAFB/FlyWire connectome). Instead of modelling individual
spikes, it tracks the phase and amplitude of every neuron and evolves them forward
in time, which makes it cheap enough to load a 139,255-neuron brain on a laptop.
Every reported result comes from a 10,906-neuron olfactory subgraph, not the full
brain.

This is independent, unreviewed work. Nothing here has been peer reviewed,
replicated by anyone else, or published. Several results below did not reproduce
their biological targets, and they are reported as such.

> ## Read the validity audit before any benchmark number
>
> **[docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md](docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md)**
>
> Every one of the five olfactory benchmarks was checked against the full text of
> the paper it cites. **Four of six targets are not in their cited source, and
> one citation does not exist.** Turner et al. 2008 — the source for
> `r > 0.70` on concentration invariance — recorded every KC at a single
> dilution and contains no concentration series at all. "Bodyak & Bhatt 2001",
> the source for the 10-20 % discrimination JND, cannot be located; the nearest
> real paper is a mouse study.
>
> The audit rebuilds each benchmark on what its paper actually measured. The
> repaired suite scores **2/5**
> (`results/final/all_validations_F9_corrected.json`): `temporal_dynamics` and
> `odor_mixtures` pass, `discrimination`, `similarity` and `learning` fail.
>
> Two further findings there affect everything: the model had **no
> trial-to-trial variability** under the protocol every benchmark used, and the
> **KC active set does not converge under timestep refinement** (active-set
> Jaccard 0.4827 between the production timestep and ten times finer, and
> refining further does not help).
>
> Reported numbers now come from the **CPU** backend, because CPU and MLX agree
> at 100 ms and diverge past it (`results/final/cpu_vs_mlx_fullrun.json`).

> ### And one finding made after that audit
>
> **The variance fields do not participate in the dynamics.** `var_amplitude` is
> never updated by any step function, and `var_phase` is updated but never read —
> the coupling uses a hardcoded constant instead of the live field. So
> `sigma_noise` provably cannot change any output, despite being recorded as a
> configuration parameter in every result file. The engine as written is a
> *deterministic* damped harmonic-oscillator network on a sparse graph. Documents
> that describe it as "probabilistic", "mean-field" or "Fokker-Planck" overstate
> what the code does. Details under Known limitations; not yet fixed.

---

## What was built

- **Connectome ingestion** — loads the FlyWire female brain (FAFB v783 Princeton
  export): 139,255 neurons and **5,342,446 weighted edges**
  (`results/superseded/full_brain_smell_results.json`).

  **These are edges, not synapses.** Each row of `connections_princeton.csv.gz` is
  keyed on `(pre_root_id, post_root_id, neuropil)` and carries a `syn_count`.
  Summing `syn_count` over all 5,342,446 rows gives **50,666,648** synapses, mean
  9.48 per edge. The published FlyWire figure is 139,255 neurons and 54.5 M
  synapses (Dorkenwald et al. 2024, Nature 634:124-138), so this export accounts
  for **93 %** of the published synapse total — consistent with its cleft-score and
  proofreading thresholds. The neuron count matches exactly. Earlier versions of
  this README called the 5,342,446 figure "synapses"; it is the edge count.
- **Subgraph extraction** — pulls the olfactory pathway out of the full graph:
  10,906 neurons and 446,388 edges, comprising 2,279 ORNs, 2,198 PNs, 721 LNs,
  5,279 KCs, 331 DANs, 96 MBONs and 2 APL neurons
  (`benchmarks/real_connectome/network_meta.json`). A visual pathway extractor
  exists for the optic lobe.

  The fan-in distribution is what makes this substrate awkward: mean 40.9 edges per
  neuron, **maximum 14,662 onto a single neuron**
  (`network_meta.json`, `max_row_nnz`), minimum 1-5 on peripheral ORNs.
- **Wave engine** (`hive/engine/sparse_probabilistic.py`) — sparse coupled-oscillator
  integrator with an MLX (Apple GPU) backend and a NumPy CPU fallback. Forward
  Euler, `dt = 0.1 ms`, or `dt = 0.5 ms` when `fast_mode=True`. Coupling is
  accumulated through a **static two-stage segment reduction** whose order is a pure
  function of the connectome, which is what makes both backends bit-for-bit
  reproducible at a fixed seed.
- **Receptor front-end** (`hive/interface/olfactory.py`) — DoOR 2.0 receptor
  responses projected 40 → 20 glomerular channels by mean-centred PCA, then a
  turbulent plume (exponential whiff train plus Ornstein-Uhlenbeck noise), a
  per-channel sinusoidal carrier, and a 200 ms receptor-adaptation recursion. The
  plume is drawn from a seeded stream in fixed 500 ms chunks with the global RNG
  state saved and restored, so it is a pure function of absolute time and identical
  across odorants — which makes odour-to-odour comparisons controlled rather than
  confounded by which turbulence realisation each one drew.
- **Measurement harness** (`benchmark_harness.py`, `benchmarks_repaired/`) — shared
  stochastic-trial protocol: 8 trials per stimulus on seeds declared in source, a
  12-odorant panel selected by paper provenance with the published figure recorded
  per entry, and every separability claim judged against the model's own
  within-stimulus replicate distribution rather than a fixed constant.
- **Provenance** (`validation_utils.py`) — every result file carries backend, `dt`,
  `fast_mode`, gamma, sigma_noise, neuron count, seed, git commit with a `-dirty`
  suffix, Python version, platform, projection method and its explained variance,
  whether the DoOR matrix is synthetic, the glomerular mapping used, and whether the
  odour drive was time-varying. Unrecognised config keys **raise**, so a result file
  cannot record a parameter the engine never applied.
- **Cross-language benchmark** — the same olfactory step loop reimplemented in
  Python/MLX, Rust/Metal and Julia/Metal against the same exported connectome
  binaries (`benchmarks/`). See Performance for what it established.

---

## Read this before any result below: the KC readout imposes sparsity

Every olfactory measurement in this repository reads Kenyon cell activity through
`get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)`. That path
calls a rank threshold:

```643:656:hive/engine/sparse_probabilistic.py
    def _apply_kc_normalization(self, kc_activity: np.ndarray,
                                target_sparsity: float = 0.06) -> np.ndarray:
        # ... docstring ...
        sorted_activity = np.sort(kc_activity)[::-1]
        threshold_idx   = int(len(kc_activity) * target_sparsity)
        threshold       = sorted_activity[threshold_idx] if threshold_idx < len(sorted_activity) else 0.0
        return np.maximum(0.0, kc_activity - threshold)
```

With 5,279 KCs and `target_sparsity = 0.06`, this keeps exactly
`int(5279 * 0.06) = 316` neurons above zero, for every stimulus, every odor, and
every concentration. The value 316 appears unchanged throughout the logs and
result files for that reason.

This is intended as a model of APL feedback inhibition (Lin et al. 2014), and as a
modelling choice it is reasonable. But it means **KC sparsity is set by the readout,
not produced by the simulation**. Any claim that this model reproduces biological
sparse coding would be circular, so no such claim is made here.

### What the readout invalidates, and what it only constrains

The threshold fixes *how many* KCs are active. It does not fix *which* ones.

- **Determined by the threshold — not evidence of anything.** The KC sparsity
  percentage itself. Earlier versions of this README reported "1.65% sparsity
  matching Turner et al. 2008". That figure appeared in no result file, and the
  quantity it described is imposed by the readout. It has been removed.
- **Not determined by the threshold, but conditioned on it.** Odor-pair similarity,
  binary mixture overlap, and concentration discrimination all depend on set
  identity rather than set size. These are reported below, with the conditioning
  stated, and with chance-level baselines where a baseline is meaningful.
- **Cannot be cleanly placed — flagged.** Two results:
  - *Concentration invariance.* Fixing the active count removes the amplitude
    scaling that changing concentration produces, and amplitude scaling is part of
    what the test measures. See the ablation table below.
  - *The learning result.* MBON amplitude is measured downstream of the KC readout,
    so the threshold does not directly set it. But active KCs collapse from 316 to 1
    after training, which is degenerate readout behaviour I have not explained.

---

## Two defects that affected every olfactory number before 2026-09-03

Both are fixed. They are kept here because they are the reason every result file
dated before 2026-09-03 should be read with suspicion, and because the mechanism of
the second one is the most useful thing in this repository.

### 1. A missing odorant returned a zero vector — FIXED

`DoorClient.get_receptor_response` used to return a zero vector for any odorant
absent from the DoOR matrix, print a warning, and continue. Callers did not check.
Three odorants used throughout this repository were affected:

| Odorant | Glomerular pattern |
|---|---|
| benzaldehyde | 9 of 20 channels active |
| 2-heptanone | 12 of 20 channels active |
| 1-hexanol | 10 of 20 channels active |
| **geosmin** | **all zeros** |
| **isoamyl acetate** | **all zeros** |
| **ethyl acetate** | **all zeros** |

The old core suite used `['benzaldehyde', '2-heptanone', 'geosmin']`, so one of its
three odors delivered no stimulus. The brain still evolved and the readout still
selected 316 "active" KCs, so a null odor produced plausible-looking output rather
than an obvious failure. A zero pattern also correlates with itself at exactly
1.0000 at every concentration, which is how it inflated the headline concentration
invariance figure from 0.5866 to 0.7244 — across the 0.70 threshold the result was
reported as passing. Quantified below.

**Fix:** lookups now raise `OdorantNotFoundError`, carrying the closest names in the
matrix so a caller can tell a spelling variant from a genuine absence
(`hive/data/door_client.py`). Names are normalised for case, spacing and
hyphen/underscore differences, and a synonym table resolves `isoamyl_acetate` →
`isopentyl_acetate`. Synthetic DoOR data is refused by default and, when explicitly
requested, is held in memory and never written to the canonical filename.

### 2. The MLX GPU path was not reproducible, and seeding did not fix it — FIXED

Two runs of identical code on 2026-03-19, at 12:22 and 12:23, gave different
numbers: 2-heptanone adaptation 91.0% then 92.7%, chemical-neural correlation 0.634
then 0.632, MBON change 30.10% then 22.99%, and post-training active KCs 7 then 1.
Seeding was added and did **not** fix it: two seeded runs still diverged, temporal
peak time 75 ms then 275 ms, mixture overlap 21.68% then 14.87%.

The cause was not the RNG — the step function contains none. It was the synaptic
coupling accumulation. `forces.at[post_indices].add(...)` lowers to an *unordered*
atomic scatter-add over 446,388 edges on Metal. Floating-point addition is not
associative and the hardware guarantees no reduction order, so two same-seed
processes diverged by about 1e-8 per step. **Sorting the indices does not fix it**
either — measured, still 7.45e-9 drift after a stable sort, because the atomics
remain unordered.

That would be negligible on its own. The amplifier is the KC readout, which
thresholds by *rank*: it sorts, takes the value at index `int(5279 × 0.06) = 316`,
and subtracts that sampled array value from all 5,279 KCs. A reordering near rank
316 shifts the baseline subtracted from every neuron in the population, so a 1e-8
analog perturbation becomes a different *set* of active neurons — 303 active KCs
against 203 on the worst same-seed pair, with 11 of 15 trials differing. Every
downstream metric is computed on that set.

**Fix:** a static two-stage segment reduction
(`hive/engine/sparse_probabilistic.py`, `_build_segment_layout`). Edges are sorted
by postsynaptic index once at construction and padded into 64-wide blocks so no
block straddles two neurons; the sum is then two fixed-shape axis reductions, which
have a deterministic reduction tree. The same layout drives the NumPy path, so both
backends perform the same additions in the same order. Cost: **0.251 ms per call
against 0.248 ms** for the atomic scatter it replaced, plus 2.8 MB + 10 MB of
layout buffers.

**Result** (`results/final/mlx_determinism.json`, 5 same-seed trials per backend):
bit-for-bit identical on all four state fields *and* the KC readout, on **both**
backends. `worst_state_max_abs_diff_between_runs: 0.0`.

**What is still not true is cross-backend bit-equality.** `mx.sum` and `np.sum` use
different reduction trees, so CPU and MLX differ in the last bits of every step. See
Performance below for how far the agreement holds and why reported numbers are CPU.

---

## Benchmark outcomes

Current run: **2026-09-04, `results/final/all_validations_F9_corrected.json`.** Each
of the five benchmarks was rebuilt on what its cited paper actually measured, after
four of six targets were found not to be in their sources. See
[the audit](docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md).

```
backend NumPy (CPU) | dt 0.1 ms | fast_mode false | 100 ms/trial
8 trials per stimulus | seeds 1001-1008 | 10,906 neurons
projection sklearn_pca (94.0 % variance) | glomerular mapping: position
```

| Benchmark | Now measures | Result | Outcome |
|---|---|---|---|
| Temporal dynamics | onset ≤ 200 ms; response is phasic | onset **50.0 ms** on 8/8 trials, all 3 odorants; phasic p = 0.0039 | **PASS** |
| Odor mixtures | sub-additivity vs the linear sum (Honegger 2011 Fig 7) | index **0.5048** and **0.4440**, both p = 0.0039 (published 0.7333) | **PASS** |
| Discrimination | blend-series psychometric ordering (Campbell 2013 Fig 2A-B) | endpoints correct (100:0 r = 0.1391 separable; 70:30 r = 0.0444 separable) but 60:40 r = 0.3177 **not** separable, so the series is non-monotone | **FAIL** |
| Similarity | Campbell 2013 Fig 4C ordering; Turner 2008 Fig 5 decorrelation | Part A ordering **wrong** (PA-BA 0.1296 vs BA-EL 0.4287); Part B 39/66 pairs, p = 0.0197 **passes** | **FAIL** |
| Learning | signed, dopamine-gated, odour-specific KC→MBON depression (Hige 2015) | depression 34.70 % and dopamine-dependence both pass; specificity p = 0.3227, d = 0.038 | **FAIL** |
| Concentration invariance | *not scored* | pattern r = **0.5417**; sparseness 0.059860 with SD exactly 0 | — |

**Two of five.** The F8 baseline before the repair was also 2/5, but a different two:
`learning` passed on a criterion that could not distinguish memory formation from
signal death, and `temporal_dynamics` failed.

**Why concentration invariance is not scored.** Neither quantity can be judged
against a published Drosophila number. The pattern correlation has no published
threshold — Turner et al. 2008, the cited source for `r > 0.70`, recorded every KC at
a single dilution and contains no concentration series. And the sparseness that
Honegger et al. 2011 *does* report is pinned to a constant by this readout.

**Learning detail, because the power analysis is the informative part.** Paired
depression 34.70 % against control 12.98 % looks like a large effect, but per-trial
Cohen's d is **0.038**, needing **n = 8,576** for 80 % power. It is not
underpowered — the specificity is genuinely swamped by variance. The depression
ceiling is **29.93 %** against Hige's 80-90 %, because only the 316 threshold-passing
KCs are depressed and they carry about 14 % of the KC→MBON amplitude. A raw-amplitude
variant reaches 79.96 % but has *negative* specificity (control 81.73 %). **The model
can produce a depression of the right size, or one aimed at the right synapses, but
not both.**

**Temporal dynamics removed a criterion, which makes a benchmark easier to pass.**
Peak time and adaptation magnitude are now reported but not scored, because no source
gives a band for either in Drosophila KCs. Stated plainly rather than buried: the
alternative was to keep scoring against a number that appears in no paper. In
exchange the phasic criterion is *stricter* than the one it replaces — it requires
statistical significance across trials rather than a magnitude landing anywhere
inside a 40-point window. Reported unscored: peak times 178/497/278 ms with SDs of
158-316 ms, adaptation 54.97-67.56 %.

**Mixture overlap baseline.** Two random 316-of-5,279 sets overlap at 5.99 % measured
as intersection over set size, or 3.09 % by Jaccard index. The legacy overlap
percentages (45.08 % and 52.27 %) are still reported for comparability, with their
citation flagged as non-Drosophila.

### Superseded: the pre-audit suite

Kept because the *results* column is a record of what those runs produced. **The
target column should not be used** — four of the six targets are not in their cited
papers. Run of 2026-09-03, `results/final/all_validations_cpu_seed42.json`, MLX, seed
42:

| Benchmark | Target (invalid — see audit) | Result | Outcome |
|---|---|---|---|
| Temporal dynamics | 30-70% adaptation | peak 275 ms, adaptation 9.05% | Did not reproduce |
| Odor mixtures | 30-50% overlap | 21.04% (chance floor ≈ 6.0%) | Did not reproduce |
| Discrimination | 10-20% JND | smallest step tested (5%) already discriminable | Did not reproduce |
| Odor similarity | r = 0.3-0.5 | `nan` — geosmin's zero pattern has zero variance | Did not reproduce |
| Learning / plasticity | ≥1% MBON change | 6.61% | Passed against a non-biological bar |

One of five. The earlier unseeded run on 2026-03-19 gave two of five, and the best
ever recorded was three of five on 2026-03-15 — in a suite where the learning test
was a stub that logged `Plasticity mechanism demonstrated (weight updates would occur
here)` without updating any weights.

### Why a score is quoted now, and what it still does not mean

The four reasons this README previously gave for refusing a summary score have been
addressed:

1. **Was unseeded and nondeterministic.** Now bit-for-bit reproducible on both
   backends, with declared trial seeds 1001-1008 fixed in source.
2. **Pass criteria were changed between runs.** Criteria are now fixed before the run
   and recorded in the result file under `target_corrections`, with the removed
   target, the reason, and the replacement quoted from source with a figure
   reference. The 2026-03-19 temporal pass came from narrowing the peak-time band
   from `100 <= mean <= 500` to `50 <= mean <= 150` in the same editing session as
   the pass it produced; that band is now retired, not moved.
3. **One of three test odors was a null stimulus.** Missing odorants now raise, and
   the 12-odorant panel is selected by paper provenance only, each entry recording
   the published measurement it comes from. All 12 verified present in the
   372-odorant matrix.
4. **The benchmark set was being revised.** The revision is done; two tests remain
   withdrawn as invalid and three remain reclassified as analytic models, below.

**What 2/5 still does not mean.** Both passes sit at **p = 0.0039**, which is the
floor for a one-sided Wilcoxon at n = 8 — the tests are saturated, not comfortably
significant, and whether n = 8 is adequate is listed as uncertain in the audit. And
the KC active set does not converge under timestep refinement (below), so roughly
half of any KC-identity result is discretisation artifact. Read the two passes as
"consistent with the published direction", not as "validated".

### The KC active set does not converge under timestep refinement

Measured with the stimulus held fixed as a function of real time, so only integrator
error varies (`results/final/dt_convergence_fixed_stimulus.json`, 3 seeds). This
required a shim that runs the full front-end once at dt = 0.002 ms and interpolates
it at each test timestep's times, because the production stimulus indexes plume
sample `step` — so a naive sweep changes the stimulus as well as the timestep.

Production dt = 0.1 ms against dt = 0.01 ms:

| | mean | range |
|---|---|---|
| KC pattern r | **0.6758** | [0.6260, 0.7287] |
| active-set Jaccard | **0.4827** | [0.4529, 0.5012] |

**And refinement does not help.** Agreement is non-monotone in dt for all three
seeds; for seed 1001 it gets *worse* as dt falls from 0.1 to 0.02 (Jaccard 0.5012 →
0.4202 → 0.4013). So the KC active set at production dt is not the solution of the
underlying equations. `similarity`, `discrimination`, `odor_mixtures` and the
pattern-correlation form of concentration invariance all read out a quantity that is
roughly half discretisation artifact.

A benchmark can still be a valid *comparison* under this, because both arms of every
contrast share the same timestep. Absolute KC identities should not be treated as
properties of the model's equations.

---

## Concentration invariance, with its ablation

Concentration invariance asks whether the KC response pattern stays similar when
odor concentration changes over a 100-fold range. The published figure is r = 0.724
against a 0.70 target. It should not be quoted, for two independent reasons.

**First, one of the three odors was a null stimulus.** The final run used
benzaldehyde, 2-heptanone and isoamyl acetate, and isoamyl acetate is not in the DoOR
database. Its zero pattern is identical at every concentration, so it correlates with
itself at exactly 1.0000 across all ten concentration pairs, pulling the mean up:

| Odor | n pairs | Mean r | Min | Max |
|---|---|---|---|---|
| benzaldehyde | 10 | 0.5546 | 0.4015 | 0.9583 |
| 2-heptanone | 10 | 0.6187 | 0.4909 | 0.8359 |
| **isoamyl acetate (null stimulus)** | 10 | **1.0000** | 1.0000 | 1.0000 |
| Published mean | 30 | **0.7244** | | |
| **Real odors only** | 20 | **0.5866** | | |

Excluding the null stimulus gives **r = 0.5866, below the 0.70 target the result was
reported as passing.**

**Second, two pipeline components independently produce invariance.** Recomputed on
real odors only, all four configurations ran 2026-03-15 between 21:32 and 21:56,
MLX backend, 10,906 neurons, `dt = 0.1 ms`, 100 ms per trial, unseeded:

| Configuration | Published | Real odors only | Result file |
|---|---|---|---|
| Wave dynamics alone — stochastic reset, linear scaling, no KC normalization | 0.149 | **0.201** | `results/superseded/concentration_invariance_results_RANDOM.json` |
| Deterministic reset, linear scaling, no KC normalization | 0.476 | 0.214 | `results/superseded/concentration_invariance_results_DETERMINISTIC_NO_NORM.json` |
| Deterministic reset, linear scaling, **with** KC rank normalization | 0.442 | 0.164 | `results/superseded/concentration_invariance_results_NORM_LINEAR.json` |
| Full pipeline — deterministic reset, **logarithmic** scaling, **with** KC normalization | 0.724 | **0.587** | `results/final/concentration_invariance_results.json` |

Every one of the four included a null odor: isoamyl acetate in the first and fourth
rows of the original set, ethyl acetate in the middle two.

**What this shows.** On real odors, the wave dynamics contribute r = 0.201 and the
full pipeline reaches r = 0.587. Almost all of the gain comes from the logarithmic
input compression (`base_strength * np.log10(1 + 10 * conc)`, a Weber-Fechner
receptor response), which by construction reduces sensitivity to concentration. The
honest statement is that the full pipeline produces r = 0.587 on real odors, below
target, and that the log transform accounts for most of the difference from baseline.
The model does not reproduce concentration invariance.

**Provenance caveats.**
- Only the final configuration's code is recoverable from git, as commit `6895ea6`
  (2026-03-15 22:20:59). The three ablations ran from uncommitted working-tree
  states between commits `502c772` and `6895ea6`; their exact source cannot be
  recovered, only inferred from the committed diff.
- The `_RANDOM` and `_DETERMINISTIC_NO_NORM` runs used a different odor set (ethyl
  acetate, benzaldehyde, 2-heptanone) than the `_NORM_LINEAR` and final runs
  (benzaldehyde, 2-heptanone, isoamyl acetate). Only `_NORM_LINEAR` is a matched
  control for the final run.
- r = 0.724 is a mean over 30 pairwise correlations (3 odors × 10 pairs) with
  standard deviation 0.228 and minimum 0.401.
- **Previously unreconciled discrepancy, now explained.** A later timestep sweep
  reported concentration invariance r = 0.1149 at the same `dt = 0.1 ms`, roughly 6×
  lower than 0.7244. The sweep's own source comment says "isoamyl acetate is missing
  from DB so skip it", so it ran on the two real odors while the headline figure
  included the null one. That accounts for the direction of the gap, though the
  sweep also used a different binarization threshold, so the two are still not
  numerically equivalent.

---

## Analytic models, not simulation results

Three components produce numbers that are widely quoted but that **do not come from
the wave simulation**. They are legitimate implementations of published filter
models, and they are useful, but they are implementations rather than validations
and are excluded from every count above.

- **T4 motion detection (DSI = 0.975).** Computed from a hand-written
  `BarlowLevickFilter`, not from brain neuron amplitudes. The test file says so
  directly in its own docstring. The reported figure is also
  `max(dsi_mean, dsi_peak, dsi_threshold)`, the best of three definitions.
- **HS/VS optic flow (DSI = 0.789).** `hive/validation/vision/test_hs_vs_optic_flow.py`
  never imports the wave engine at all. The connectome is queried only for neuron
  counts. The measured quantity is the output of two directional filters whose
  asymmetric spatial coupling encodes the direction selectivity being measured.
- **Johnston's Organ frequency tuning.** Each JO subtype is assigned a resonant
  frequency taken from Kamikouchi et al. (2009) in `JO_SUBTYPE_PARAMS`, driven as a
  damped harmonic oscillator, and the reported "peak frequency" is the argmax over a
  seven-point drive grid. The wave engine does not run; the connectome supplies only
  population sizes. Recovering the assigned frequencies does not test the connectome.

Two further vision numbers need the same caveat wherever they appear. Visual sparse
coding used a free gain parameter tuned into the pass range — the source comment
reads `R7_R8_GAIN = 0.15  # Reduced from 0.5× to bring medulla from 9.32% to ~3.5%
target`, against a pass criterion of 3-15%. Contrast invariance applies a logarithmic
transform at the input (`voltage = gain * np.log10(photon_rate / threshold)`) and
then measures invariance to input intensity.

### Withdrawn as invalid

Two tests supplied the expected answer to the model as an input and therefore could
not fail. Their code is preserved under `hive/validation/invalid/` with an
explanation, and their results have been removed.

- **Context-dependent recall** applied potentiation to MBON group A, then checked
  that MBON group A dominated.
- **Multisensory integration** injected external force directly onto AVLP, then
  checked that AVLP activity had increased.

---

## Performance

Measured on Apple M4 Pro, macOS 26.6.2, Python 3.14.3. Olfactory subgraph: 10,906
neurons, 446,388 edges. `dt = 0.1 ms`, `fast_mode=False`, 100 ms of simulated
biology, seed 42, **matched configuration**, 5 timed repeats after a warm-up.
Source: `results/final/cpu_vs_mlx_speedup.json`.

| Measurement | Value |
|---|---|
| MLX GPU wall time | **0.4867 s** median (SD 0.00045, range 0.4863-0.4874) |
| NumPy CPU wall time | **4.8673 s** median (SD 0.0080) |
| GPU speedup over CPU | **10.00× median** (worst 9.958, best 10.026) |
| Real-time factor, MLX | 0.205× |
| Real-time factor, CPU | 0.0205× |

The simulation runs **slower than real time on both backends**: 0.205× means 100 ms
of biology takes about 487 ms of wall clock.

> **The previously reported 86.3× is discarded.** It came from
> `results/superseded/cpu_vs_mlx_validation.json`, which records 1,283 active KCs
> where current runs give 62-316, a `null` `pattern_correlation`, an empty
> `kc_pattern`, and `validation_passed: true` against a 0.95 correlation criterion it
> never evaluated. The MLX run behind it was also not reproducible. Earlier versions
> of this README quoted 86.3× in three places.

### Cross-backend agreement, and why reported numbers are CPU

At the matched 100 ms configuration the two backends select the **same 62 active
KCs**, Jaccard 1.0000, KC pattern r = 0.99988, max absolute difference 0.00204. They
are not bit-identical and cannot be: `mx.sum` and `np.sum` use different reduction
trees.

Agreement was then tested over the longest trajectory any benchmark uses, against a
rule fixed **before the run and recorded in the result file**: Jaccard ≥ 0.95 and
Pearson r ≥ 0.99 at every 100 ms sample point of 2,000 ms, on 8 declared seeds, with
`on_failure: "report on CPU and record the divergence as a finding"`
(`results/final/cpu_vs_mlx_fullrun.json`).

**It failed.** Agreement holds at 100 ms (Jaccard 0.9627, r 0.9932 on seed 1001) and
collapses by 200 ms (0.1902, 0.5422). Worst over the whole trajectory across all 8
seeds: **Jaccard 0.1030, Pearson r 0.0650**. The old agreement claim held only
because it was measured at 100 ms from an all-zero initial phase, which is the
easiest possible case.

**Consequence:** every reported number comes from the 10× slower CPU backend.
Whether the divergence is bounded chaos in a legitimately chaotic system or a bug in
one backend has not been determined.

### The throughput is unremarkable — this is not a performance result

For context against the literature, wall-clock per **1 second** of simulated biology,
normalised per edge:

| System | Neurons | Edges | s / 1 s bio | per edge |
|---|---|---|---|---|
| Brian 2 reference in Sandia's Loihi 2 port (arXiv:2508.16792) | ~140 K | ~15 M | 4.42 | 0.295 µs |
| **This project, MLX** | 10,906 | 446,388 | **4.87** | **10.9 µs** |
| Flysim, C++, 4 threads (Huang et al. 2019) | 20,089 | 1.04 M | 35 | 33.5 µs |
| **This project, NumPy CPU** (all reported numbers) | 10,906 | 446,388 | **48.7** | **109 µs** |
| Shiu et al. 2024 own figure, per CPU thread | 127,400 | ~50 M | ~300 | 6.0 µs |

Per edge the MLX path is about 1.8× slower than Shiu et al.'s reported throughput and
about 37× slower than the Brian 2 reference above; the CPU path is an order of
magnitude worse again. It beats Flysim and that is the only comparison it wins. Note
that the two Brian 2 figures for essentially the same model differ by 68×, so this
table carries a wide uncertainty band and dt is not stated in every source.

**What the performance work actually bought** was a deterministic engine and a
diagnosis of why irregular fan-in defeats hand-written GPU kernels — not speed.

### Why the library scatter beats hand-written kernels

The same step equations were reimplemented in three languages against the same
exported connectome binaries (`benchmarks/real_connectome/`, 2026-03-23, 1,000 steps):

| Backend | Wall time | vs MLX | Failure mode |
|---|---|---|---|
| Python + MLX | **0.171 s** | — | library scatter primitive: internal sort + SIMD-group segmented reduction, insensitive to fan-in shape |
| Julia + Metal.jl (CSR) | 3.314 s | 19.4× slower | one thread per neuron: the hub thread runs **14,662 serial iterations** while 10,905 threads idle. Metal.jl 1.9.3 has no float atomics, which forced CSR |
| Rust + Metal (CAS atomics) | 6.188 s | 36.3× slower | one thread per edge balances the work, but **14,662 concurrent compare-and-swap writes** land on one address and the retry storm costs more than the imbalance did |

This inverted the ranking from a synthetic uniform-fan-in benchmark, where Rust was
far ahead — which is its own lesson about benchmark design.

**Two benchmark issues remain unresolved.** Rust-Metal is recorded at 6.19 s where
Python/MLX is 0.171 s in `benchmarks/real_connectome/`, but at 0.085 s where Python
is 1.37 s in `benchmarks/smell_test/` — one harness is measuring something different.
The two benchmark families also use opposite conventions under similar names:
`rt_factor` is biology-over-wall-clock, `realtime_ratio` is wall-clock-over-biology.

---

## Known limitations

- **The variance fields do not affect the simulation.** `var_amplitude` is set to
  0.01 at initialisation and at every `reset` and is **never updated by any step
  function**. `var_phase` *is* updated in all three step paths, but the coupling term
  uses a hardcoded `exp(-0.1/2)` constant rather than the live field
  (`hive/engine/sparse_probabilistic.py`, `_var_correction_scalar`), so `var_phase`
  is write-only. Therefore **`sigma_noise` provably cannot change any output**, even
  though it is recorded as a configuration parameter in every result file. The engine
  as written is a *deterministic* damped harmonic-oscillator network on a sparse
  graph; describing it as "probabilistic", "mean-field" or "Fokker-Planck" — as
  several documents under `docs/` still do — overstates what the code does. Not yet
  fixed. The right fix is structural: an assertion per subsystem that destroying it
  must change the output, as `tests/test_weights_on_signal_path.py` already does for
  the plasticity path.
- **The coupling has no excitation/inhibition sign.** `w · sin(φ_pre − φ_post) · A_pre`
  treats a GABAergic and a cholinergic synapse identically. `nt_type` and the six
  per-neuron neurotransmitter scores are loaded and stored
  (`hive/substrate/connectome.py`) and never used in the coupling. This is the
  largest biological gap in the model. Shiu et al. (2024) build their whole-brain LIF
  model from connectivity **plus** predicted neurotransmitter identity; this model has
  the first ingredient and discards the second.
- **The MBON amplitude readout is not monotone in KC→MBON synaptic weight.** Measured
  across 11 weight scales × 8 trials: Spearman ρ = **−0.0182**, p = 0.958, response
  peaks at *half* strength, dynamic range 14.6 % of max
  (`results/final/mbon_weight_monotonicity.json`). Coupling is a phase-pulling term
  and amplitude is driven by `|velocity|`, so tighter locking *lowers* amplitude.
  Hige et al. 2015 measures learning as a reduction in MBON response following
  synaptic depression, which presupposes monotonicity, so that measurement cannot be
  scored in its primary form. The KC→MBON coupling *current* is monotone
  (ρ = 1.0000) and is the analogue of Hige's Fig 3D charge-transfer measurement, so
  that is what the learning benchmark scores.
- **The model class is not novel, and the substrate is not either.** Phase
  oscillators on structural connectomes are standard in human whole-brain modelling
  (Kuramoto in The Virtual Brain; Hopf/Stuart-Landau for phase *plus* per-node
  amplitude, Deco et al. 2017, Sci. Rep. 7:3095). Ódor, Deco & Kelling have already
  published Kuramoto at one-oscillator-per-neuron on the Drosophila connectome — the
  hemibrain in 2022 (Phys. Rev. Research 4:023057, 21,662 nodes) and the **full
  FlyWire v630 connectome in 2025** (arXiv:2503.20708, **124,891 nodes**), using RK4
  and adaptive Bulirsch-Stoer rather than forward Euler, on GPU. Eight times the
  nodes and a better integrator. What those papers do not do is drive the model with
  a sensory stimulus or compare it against fly physiology — they are criticality
  studies, and their own text calls it a "brain toy model". That is the only gap this
  project occupies.
- **The mean-field justification does not transfer to single neurons.** In the human
  literature a Kuramoto or Hopf node is a *neural mass*, a population whose
  collective dynamics genuinely admit a phase reduction. One oscillator per single
  neuron discards that justification, so the oscillator here is phenomenological
  rather than derived.
- **Historical results record no configuration.** Files carry no timestep, duration,
  seed, or commit, and the two that do record physics parameters record values the
  engine discarded — `self.config` was assigned and never read, so a caller passing
  `dt=0.01` actually ran at `dt=0.1`. Both are fixed as of 2026-09-03: the engine now
  honours `dt`, `gamma` and `sigma_noise` and rejects unknown keys, and
  `validation_utils.run_metadata()` writes the full configuration into every result.
- **Everything before 2026-09-03 was unseeded**, hence the nondeterminism above.
- **Forward Euler integration**, and it does not converge — see the timestep section
  above. Timesteps above roughly 2 ms are also numerically unstable for the APL
  feedback loop. RK4 or an adaptive stepper is the obvious next change; Ódor et al.
  solve the same model class on the same connectome with exactly those.
- **KC sparsity is pinned by the readout** at `int(5279 × 0.06)/5279 = 0.059860`,
  standard deviation exactly zero. That is the quantity Honegger et al. 2011 reports
  for both its mixture and its concentration results, so both published comparisons
  are unavailable at the binary level. Replacing the rank threshold with a genuine
  dynamical loop through the two APL neurons already in the subgraph would make
  sparsity an output; it has not been done.
- Many validation scripts print results rather than writing them, so a number quoted
  in a document often has no artifact behind it. Of the 19 scripts under
  `hive/validation/` containing a `json.dump`, 14 of the expected output files do not
  exist. Where a documented number had no artifact, it was removed rather than kept.
- **The 372-odorant KC fingerprint database is stale.**
  `data/digital_smell_database_full.json` was generated under the old constant drive
  and the old amplitude ceiling — its `pn_pattern` fields contain literal `10.0`
  values, i.e. projection neurons pinned at that ceiling. It needs regenerating.
- Olfactory neuron classification is substring matching on concatenated cell-type
  strings with a neuropil-region fallback
  (`hive/substrate/olfactory_subgraph.py`, `classify_olfactory_neuron`). It produces
  plausible population counts but it is a heuristic, not a principled extraction.
- **Neuron coordinates carry no unit and are not rescaled.** They are stored exactly
  as exported, in FAFB voxel/nanometre scale, so the loaded cloud spans roughly
  445,000 × 303,000 × 231,000 (`hive/substrate/connectome.py`, `_load_coordinates`).
  Harmless for `SparseProbabilisticBrain`, which uses positions only for clustering
  and distance-based delays. **Fatal** for `ProbabilisticWaveBrain`, which derives a
  dense voxel grid from the bounding box: at its documented 100 µm spacing the shape
  is (4457, 3032, 2313) ≈ 31.3 billion voxels ≈ 116 GB per float32 field, and the
  process is killed with exit code 137. That engine carries a "do not use with real
  connectome data" banner and its claimed advantages have never been measured on real
  data. Not fixed because rescaling changes the coupling distances every recorded run
  used.
- Documents under `docs/`, `research/`, `thesis/` and `publication/` predate this
  audit. They carry a correction banner but have not been rewritten. In particular
  `ARCHITECTURE.md` §14 still lists the withdrawn `r = −0.51` decorrelation result as
  "Discovery 1" while §6 of the same file withdraws it, and both `ARCHITECTURE.md`
  and `.cursor/rules/Findings.mdc` state that random PN→KC wiring was "proven by
  Caron 2013" — superseded by Zheng et al. 2022 (Current Biology 32:3334-3349.e6),
  which found food-responsive PN types over-converge on individual KCs above chance.

### Fixed since the previous revision of this README

Recorded so that a reader who saw the earlier text knows what changed.

| Was stated as a limitation | Status |
|---|---|
| "Missing odorants fail silently … returns a zero vector" | **Fixed.** Raises `OdorantNotFoundError` with close matches. See the two-defects section above |
| "The DoOR 40-receptor to 20-glomerulus mapping is a **random projection**, not PCA … falls back" | **Fixed.** `DoorClient` takes an explicit `projection` argument, defaults to `sklearn_pca`, and raises if scikit-learn is absent rather than substituting. It is mean-centred PCA retaining **94.0 %** of variance. The old path stays selectable as `uncentered_svd` so pre-2026-09-03 numbers reproduce. Note the fallback was *not* a random projection either — it was uncentered SVD, which the code and docstrings had also mislabelled |
| "for any number you intend to quote, use the CPU backend … about **86× slower**" | **Corrected to 10.00×.** The 86.3× is discarded; see Performance |
| "The GPU path is not reproducible, and seeding does not fix it" | **Fixed.** Bit-for-bit reproducible on both backends. Reported numbers are still CPU, but for a different and measured reason — cross-backend divergence past 100 ms |

---

## Running it

```bash
pip install -r requirements.txt

# The current, repaired suite. Writes results/final/all_validations_F9_corrected.json
.venv/bin/python scripts/run_repaired_suite.py

# The pre-audit suite, kept so the superseded F8 numbers stay reproducible.
# Its targets are the misattributed ones — see the audit.
.venv/bin/python scripts/run_all_validations.py
```

**Use `.venv/bin/python`.** The repository ships two virtualenvs and only one has
scikit-learn, which the documented `sklearn_pca` projection requires. The system
interpreter and `./venv` do not.
`validation_utils.assert_reportable_environment()` fails fast on this rather than
raising deep inside `DoorClient` after a full connectome load.

See [QUICKSTART.md](QUICKSTART.md) for setup and
[docs/00_START_HERE.md](docs/00_START_HERE.md) for a guide to the rest of the
documentation.

Requires the FlyWire connectome data in `Fly Brain Female/`, which is not
distributed with this repository. First load parses four gzipped CSVs in about
2-3 minutes and then caches to a pickle for instant reload.

---

## Repository layout

```
experiment/
├── hive/            Core engine, substrate, and validation tests
├── benchmarks/      Cross-language timing harnesses (Python/MLX, Rust, Julia)
├── scripts/         Runnable entry points
├── tests/           Test and validation scripts
├── results/         Result artifacts: final/ and superseded/
├── docs/            Documentation
├── research/        Working notes and findings
└── thesis/          Long-form write-up
```

## License

Independent research project.

**Contact**: Vladyslav Byelozerskykh — vladorangeqwer@gmail.com
