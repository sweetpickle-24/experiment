# Wave-based simulation of the Drosophila connectome

**Last Updated**: 2026-09-04

This project simulates a fruit fly's brain by treating each neuron as a damped
oscillator and letting activity spread as waves across the real wiring diagram of
the fly brain (the FAFB/FlyWire connectome). Instead of modelling individual
spikes, it tracks the mean phase and amplitude of every neuron and evolves them
forward in time, which makes it cheap enough to run a 139,255-neuron brain on a
laptop.

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

---

## What was built

- **Connectome ingestion** — loads the FlyWire female brain: 139,255 neurons and
  5,342,446 synapses (`results/final/full_brain_smell_results.json`).
- **Subgraph extraction** — pulls the olfactory pathway out of the full graph:
  10,906 neurons and 446,388 synapses, comprising 2,279 ORNs, 2,198 PNs, 721 LNs,
  5,279 KCs, 331 DANs, 96 MBONs and 2 APL neurons
  (`benchmarks/real_connectome/network_meta.json`). A visual pathway extractor
  exists for the optic lobe.
- **Wave engine** (`hive/engine/sparse_probabilistic.py`) — sparse coupled-oscillator
  integrator with an MLX (Apple GPU) backend and a NumPy CPU fallback. Forward
  Euler, `dt = 0.1 ms`, or `dt = 0.5 ms` when `fast_mode=True`.
- **Benchmark harness** — the same olfactory step loop reimplemented in Python/MLX,
  Rust, and Julia for cross-language timing comparison (`benchmarks/`).

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

## Two defects that affect every olfactory number below

### One of the three test odors is a null stimulus

`DoorClient.get_receptor_response` returns a zero vector for any odorant missing from
the DoOR database, printing a warning and continuing. Three odorants used throughout
this repository are missing:

| Odorant | Glomerular pattern |
|---|---|
| benzaldehyde | 9 of 20 channels active |
| 2-heptanone | 12 of 20 channels active |
| 1-hexanol | 10 of 20 channels active |
| **geosmin** | **all zeros** |
| **isoamyl acetate** | **all zeros** |
| **ethyl acetate** | **all zeros** |

The core validation suite uses `['benzaldehyde', '2-heptanone', 'geosmin']`, so one
of its three odors delivers no stimulus. The brain still evolves under its noise term
and the readout still selects 316 "active" KCs, so a null odor produces
plausible-looking output rather than an obvious failure. The effect on the
concentration invariance result is quantified below and it is not small.

### The GPU path is not reproducible, and seeding does not fix it

Two runs of identical code on 2026-03-19, at 12:22 and 12:23, gave different numbers:
2-heptanone adaptation 91.0% then 92.7%, chemical-neural correlation 0.634 then 0.632,
MBON change 30.10% then 22.99%, and post-training active KCs 7 then 1.

Seeding was added on 2026-09-03. **It did not fix the problem.** Two seeded runs still
diverge: temporal peak time 75 ms then 275 ms, mixture overlap 21.68% then 14.87%.

The cause is not the RNG. Isolating it:

| Component | Two processes, same seed | Reproducible |
|---|---|---|
| DoOR glomerular patterns | identical hash | yes |
| Wave evolution, **NumPy CPU** backend | identical hash, sum 0.623327434 | **yes** |
| Wave evolution, **MLX GPU** backend | sums 4.226922989 vs 4.226953506 after 20 ms | **no** |

The step function contains no RNG, and `reset(deterministic=True)` gives fixed initial
conditions, so the model is deterministic in principle. The divergence comes from the
MLX/Metal backend: the synaptic scatter-add over 446,388 synapses is a non-associative
floating-point reduction whose ordering the GPU does not guarantee. The difference
starts around 1 part in 10^5.

That would be negligible on its own, but the KC rank threshold turns it into a
discrete difference: a tiny amplitude change flips which neurons land in the top 316,
and every downstream metric is computed on that set. This is the mechanism that makes
run-to-run variation large.

It also bears on the CPU/GPU equivalence claim in `cpu_vs_mlx_validation.json`, which
asserts equivalence while never computing the pattern correlation it declares as its
criterion. The two backends do not produce identical output.

**Practical consequence:** for any number you intend to quote, use the CPU backend
(`use_mlx=False`), which is reproducible and about 86× slower.

---

## Benchmark outcomes

Most recent run: 2026-09-03, `results/final/all_validations_results.json`. This is the
first run with a recorded configuration and a fixed seed:

```
backend MLX | dt 0.1 ms | fast_mode false | 100 ms/trial | seed 42
10,906 neurons | Python 3.14.3 | macOS 26.6.2 arm64 | commit 2e41e13-dirty
```

| Benchmark | Result | Target | Outcome |
|---|---|---|---|
| Temporal dynamics | peak 275 ms, adaptation 9.05% | 30-70% adaptation | **Did not reproduce** |
| Odor mixtures | 21.04% overlap | 30-50% | **Did not reproduce** |
| Discrimination | smallest step tested (5%) discriminable | 10-20% JND | **Did not reproduce** |
| Odor similarity | not computable (`nan`) | 0.3-0.5 | **Did not reproduce** |
| Learning / plasticity | 6.61% MBON change | ≥1% change | Passed against a non-biological bar |

One of five. The previous unseeded run on 2026-03-19 gave two of five, and the best
ever recorded was three of five on 2026-03-15 — in a suite where the learning test was
a stub that logged `Plasticity mechanism demonstrated (weight updates would occur
here)` without updating any weights.

**Similarity now returns `nan`** because geosmin's zero pattern gives zero variance.
Previously this silently produced a number (+0.632 on 2026-03-19, −0.511 on
2026-03-16 — opposite signs, both recorded FAIL).

**Learning caveat.** The pass bar is a ≥1% change in MBON amplitude, which is not a
quantitative biological benchmark. It is the only benchmark that passes.

**Mixture overlap baseline.** Two random 316-of-5,279 sets overlap at 5.99% measured
as intersection over set size, or 3.09% by Jaccard index. Read the measured value
against that floor, not against zero.

**Discrimination detail.** Every step from 5% to 25% was marked discriminable, so the
threshold was never bracketed — 5% is simply the smallest step tested.

### Why there is no summary score

1. The suite was unseeded and nondeterministic for its entire recorded history.
2. Pass criteria were changed between runs. The 2026-03-19 temporal dynamics pass came
   from widening the peak-time band from `100 <= mean <= 500` to `50 <= mean <= 150`
   in the same editing session, not from a change in the measurement.
3. One of three test odors is a null stimulus.
4. The benchmark set is being revised: two tests withdrawn as invalid, three
   reclassified as analytic models.

A single fraction would imply a stability this suite does not have.

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

Measured on Apple M4 Pro, macOS 26.6.2, Python 3.14.3, MLX 0.31.1. Olfactory
subgraph: 10,906 neurons, 446,388 synapses. `dt = 0.1 ms`, `fast_mode=False`,
100 ms of simulated biology, unseeded.

| Measurement | Value | Source |
|---|---|---|
| MLX GPU wall time | 0.171 s | `benchmarks/real_connectome/results_python_mlx.json` (2026-03-23) |
| NumPy CPU wall time | 149.8 s | `results/final/cpu_vs_mlx_validation.json` (2026-03-16) |
| GPU speedup over CPU | 86.3× | `results/final/cpu_vs_mlx_validation.json` |
| Real-time factor (GPU) | 0.59× | `benchmarks/real_connectome/results_python_mlx.json` |

The simulation runs **slower than real time** on all hardware tested: 0.59× means
100 ms of biology takes about 170 ms of wall clock.

**The CPU/GPU equivalence claim does not hold.** `cpu_vs_mlx_validation.json` records
`validation_passed: true`, but its `pattern_correlation` field is `null` and
`kc_pattern` is empty — the 0.95 correlation criterion it declares was never
computed. The only quantity actually compared is a scalar active-KC count, 24.30%
versus 24.28%. The speedup is real; equivalence of the *outputs* is untested.

Two benchmark issues remain unresolved. Rust-Metal is recorded at 6.19 s where
Python/MLX is 0.171 s in `benchmarks/real_connectome/`, but at 0.085 s where Python
is 1.37 s in `benchmarks/smell_test/` — one harness is measuring something
different. The two benchmark families also use opposite conventions under similar
names: `rt_factor` is biology-over-wall-clock, `realtime_ratio` is wall-clock-over-biology.

---

## Known limitations

- **Missing odorants fail silently.** `DoorClient.get_receptor_response` returns a
  zero vector for any odorant absent from DoOR, with only a printed warning. Callers
  do not check. This is why one of three test odors delivers no stimulus.
- **The DoOR 40-receptor to 20-glomerulus mapping is a random projection**, not PCA.
  The code attempts PCA, catches the missing `scikit-learn` import, and falls back to
  a random projection, logging `sklearn not available, using random projection`. That
  fallback line is present in the 2026-03-15 logs too, so every recorded run used a
  random projection.
- **Historical results record no configuration.** Files carry no timestep, duration,
  seed, or commit, and the two that do record physics parameters record values the
  engine discarded — `self.config` was assigned and never read, so a caller passing
  `dt=0.01` actually ran at `dt=0.1`. Both are fixed as of 2026-09-03: the engine now
  honours `dt`, `gamma` and `sigma_noise` and rejects unknown keys, and
  `validation_utils.run_metadata()` writes the full configuration into every result.
- **Everything before 2026-09-03 was unseeded**, hence the nondeterminism above.
- Forward Euler integration. Timesteps above roughly 2 ms are numerically unstable
  for the APL feedback loop.
- Many validation scripts print results rather than writing them, so a number quoted
  in a document often has no artifact behind it. Of the 19 scripts under
  `hive/validation/` containing a `json.dump`, 14 of the expected output files do not
  exist. Where a documented number had no artifact, it was removed rather than kept.
- Documents under `docs/`, `research/`, `thesis/` and `publication/` predate this
  audit. They carry a correction banner but have not been rewritten.

---

## Running it

```bash
pip install -r requirements.txt
python3 scripts/run_all_validations.py
```

Results are written to `results/final/all_validations_results.json`. See
[QUICKSTART.md](QUICKSTART.md) for setup and [docs/00_START_HERE.md](docs/00_START_HERE.md)
for a guide to the rest of the documentation.

Requires the FlyWire connectome data in `Fly Brain Female/`, which is not
distributed with this repository.

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
