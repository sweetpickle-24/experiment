# Benchmark validity audit

**Date**: 2026-09-04
**Last Updated**: 2026-09-04
**Scope**: the five olfactory benchmarks in `scripts/run_all_validations.py`, plus
the separately reported concentration invariance measurement.

Read this before quoting any number from the olfactory suite.

Every benchmark was checked against the full text of the paper it cites. The
question asked was not "did it pass" but "does the paper contain the target this
is scored against, and does the test measure the quantity the paper measured".

## Summary

Of six measurements, **four were scored against targets that are not in the
papers they cite**, and **one citation does not exist**.

- `learning` — cited paper is real and relevant, but the test measured none of
  the three things it reports. Test-validity failure plus a bug.
- `similarity` — target band has no locatable source, and was computed from
  three data points.
- `discrimination` — **citation does not exist**; target is rodent data; the
  measurement was unfalsifiable as constructed.
- `temporal_dynamics` — both bands misattributed; three separate bugs.
- `odor_mixtures` — target band comes from two non-Drosophila papers.
- `concentration invariance` — the 0.70 target is not in Turner et al. 2008,
  which contains no concentration series at all.

Two further defects were found that affect everything above:

- **The model had no trial-to-trial variability** under the protocol every
  benchmark used, so all of them were single-sample measurements with a noise
  floor of exactly r = 1.0.
- **The compiled MLX kernel captured the synaptic weights**, so every learning
  test run on that backend trained nothing.

---

## 1. learning

**Cited**: Bi & Poo 1998; Aso et al. 2014; Hige et al. 2015.

**Scored against**: `MIN_CHANGE_PCT = 1.0`, applied to
`|MBON_post − MBON_pre| / (|MBON_pre| + ε)`.

**What Hige et al. 2015 actually measured** (*Neuron* 88:985-998):

> "After 1-s pairing of odor presentation and PPL1-γ1pedc activation, the EPSCs
> showed a marked depression in a stimulus-specific manner [...] The average
> reduction in charge transfer was **90 ± 3.7 %** (mean ± SEM; Fig 3D), which is
> of similar order to the **80 ± 5.7 %** [reduction in spike rate]."

> "Pairing with PA effectively induced LTD not only for this odor, but also for
> the odors with overlapping KC representations, BA and HP [...] On the other
> hand, **EL responses were unaffected**." (Fig 7C-H)

> "Depression was significant for PA, BA and HP (p < 0.005, Tukey's post hoc test
> following repeated measures two-way ANOVA) but not for EL (p > 0.1)."

> "Magnitude of depression correlates with extent of overlap in KC response
> patterns (p < 0.005, Pearson's r = 0.90)." (Fig 7I)

**Verdict: test-validity failure, plus a bug.** The paper reports a *signed*
depression that *requires dopaminergic pairing* and is *odour-specific*. The
test had no dopaminergic pairing, no control odour, and no required direction.

It passed on an unsigned 99.99 % collapse of the MBON response
(0.03327 → 0.0000044) produced by a bug: `_apply_hebbian_stdp` updated **all
446,388 synapses** in the network and then renormalised by the maximum
(`w /= np.max(w)`), so one growing synapse drove every other weight toward zero
and the network silenced itself. A signal dying is not a memory forming, and a
1 % unsigned threshold cannot distinguish them.

**Replaced with**: three criteria taken from the paper — depression is signed,
requires dopamine, and spares a non-overlapping odour — with plasticity
restricted to the 49,599 KC→MBON synapses selected by cell type and no global
renormalisation. Paired odour pentyl acetate, control odour ethyl lactate: the
paper's own pair, ethyl lactate being specifically the odour it reports as
unaffected.

**Two model limitations found while building it**, both recorded rather than
worked around:

- `results/final/mbon_weight_monotonicity.json` — the **MBON amplitude field is
  not a monotone function of KC→MBON synaptic weight**. Spearman ρ = **−0.0182,
  p = 0.958** over 11 weight scales at 8 trials each; the response *peaks at
  half strength* and its entire dynamic range is 14.6 % of maximum. Coupling
  enters as `w · sin(φ_pre − φ_post) · A_pre`, which pulls phases together
  rather than adding excitation, and amplitude is driven by `|velocity|`, so
  tighter phase locking lowers it. The **KC→MBON coupling current** is by
  contrast perfectly monotone (ρ = **1.0000**, p = 0), so that is what is
  scored — and it is the analogue of Hige's *primary* figure (Fig 3D, EPSC
  charge transfer), making the choice more faithful to the paper, not less.
- `results/final/kc_odor_specificity.json` — the raw KC amplitude field is
  non-zero on **all 5,279 KCs**, and the 316 that pass the APL rank threshold
  carry only **12.5–14.1 %** of the total. A depression rule proportional to raw
  amplitude therefore aims about 86 % of its effect at KCs outside the sparse
  code. Hige's mechanism implies only KCs the odour actually depolarised are
  depressed, so the scored rule uses thresholded activity. Both variants are run
  and reported, because the comparison is what separates a limitation of the
  model from a defect in the rule.

---

## 2. similarity

**Cited**: Bhandawat et al. 2007; Mathew et al. 2013.

**Scored against**: chemical-versus-neural similarity correlation in [0.3, 0.5].

**Verdict: the target has no locatable source, and the measurement had no
power.**

Mathew et al. 2013 (*PNAS* 110:E2134) is a screen of 21 larval ORNs against
~500 odorants; it reports no chemical-versus-neural similarity correlation. No
paper reporting a 0.3-0.5 band for this quantity could be found. The upper bound
is also odd on its face: it fails a model for tracking input similarity *too
well*.

Separately, the test correlated **three** chemical-similarity values against
three neural-similarity values — three odorants give three pairs, leaving one
residual degree of freedom. The same code produced r = −0.97, −0.99 and −0.12
across the F4, F5 and F8 runs. That is not a measurement at any threshold.

**Replaced with** two measurements that have published numbers:

**Part A — Campbell et al. 2013** (*J Neurosci* 33:10568-10581) Fig 4C:

> "Across all recordings (n = 24), the correlation score of PA-BA (mean
> **r = 0.70**) is substantially and significantly greater than either PA-EL
> (mean **r = 0.15**; p < 0.05, one-way ANOVA followed by Tukey's post hoc test)
> or BA-EL (mean **r = 0.11**)."

Pentyl acetate, butyl acetate and ethyl lactate are all in the DoOR matrix, so
this is a direct comparison against published values, using the test the paper
used.

**Part B — Turner et al. 2008** (*J Neurophysiol* 99:734-746) Fig 5:

> "Overall, distances were significantly greater between KC vectors than between
> OSN vectors (Fig 5B; t-test: P < 10⁻⁷). Separation was greater in KC space for
> **24 of the 28** possible odor pairs (Fig 5C; Wilcoxon signed-rank test:
> P < 10⁻⁴)."

Angular separation `1 − cos θ`, computed over all 66 pairs of the 12-odorant
panel. **Caveat recorded in the result file**: Turner et al. compared OSN space
against KC space, and this model's entry point is the glomerular pattern
injected into projection neurons, so the comparison here is one stage downstream
of the paper's input layer and is therefore a weaker test.

Power: 3 pairs × 8 trials for Part A, 66 pairs for Part B, against three single
values before.

---

## 3. discrimination

**Cited**: `'biological_target': '10-20% (Weber\'s law, Bodyak & Bhatt 2001)'`.

### The citation does not exist

**There is no Bodyak & Bhatt 2001.** No paper by those two authors in that year
on this subject can be located. The nearest real work is:

> Bodyak N, Slotnick B (1999) "Performance of mice in an automated olfactometer:
> odor detection, discrimination and odor memory." *Chem Senses* 24:637-645.

A **mouse** study. This repository's own `.cursor/rules/Findings.mdc` already
records that the 10-20 % figure "was rodent data, not validated in flies".

**No published Drosophila concentration JND at 5-25 % resolution exists.** So
the benchmark scored the model against a number that no paper reports, for a
species it was not measured in, via a citation that cannot be found.

### The measurement was also unfalsifiable

It swept deltas of 5, 10, 15, 20 and 25 %, called a delta discriminable when the
KC correlation fell below a fixed 0.9, and reported the smallest discriminable
delta as the JND. Every delta scored discriminable for every odour, so the
reported JND was always **5 %: the smallest delta in the sweep**. The JND was set
by where the sweep started, not measured.

The fixed 0.9 threshold is worse than arbitrary. The same-stimulus replicate
correlation in this model is about **r = 0.54**, far below 0.9, so the test would
call a stimulus discriminable **from itself**. Four of the correlations it scored
as discriminable (0.36, 0.45, 0.37, 0.20) lie *below* that noise floor.

**Replaced with Campbell et al. 2013** Fig 2A-B, the published Drosophila
fine-discrimination benchmark, which uses **blend ratio** rather than
concentration:

> "Increasingly similar odors were constructed by blending OCT and MCH over
> three pairs of increasingly similar blend ratios. [...] Flies accurately
> discriminated pure OCT from pure MCH (100:0), but do progressively worse with
> blends of the two odors (70:30 and 60:40). Training on the more similar blend
> (60:40) produces performance just above chance."

> "KC patterns become increasingly overlapping and correlated when approaching
> the discrimination limit. Second, the variability of KC responses is an
> important limiting factor."

Scored on the psychometric ordering, against this model's own replicate
distribution rather than a fixed constant — which is also what Campbell et al.
identify as the limiting factor.

**Secondary, scored separately — Xia & Tully 2007** (*PLoS Biol* 5:e264), the one
published Drosophila intensity-discrimination result:

> "To saturate MCH as the background odor, naive flies were allowed to choose in
> the T-maze between **2 × [MCH] versus 1 × [MCH]**. As the concentration of MCH
> was increased, a threshold (i.e., about 10 %) was reached at which flies would
> fail to recognize the intensity difference, thereby yielding a PI of zero."

So the published quantity is a **two-fold** step, discriminable below saturation
— not a 5-25 % JND.

---

## 4. temporal_dynamics

**Cited**: Stopfer et al. 2003 (peak 50-150 ms); Nagel & Wilson 2011
(adaptation 30-70 %).

### Both bands are misattributed

- **Stopfer M, Jayaraman V, Laurent G (2003)** *Neuron* 39:991-1004, "Intensity
  versus identity coding in an olfactory system", is a **locust** study of
  projection-neuron and Kenyon-cell coding using 50 ms bins. It contains no
  Drosophila KC peak-latency band and no 50-150 ms figure.
- **Nagel KI, Wilson RI (2011)** *Nat Neurosci* 14:208-216, "Biophysical
  mechanisms underlying olfactory receptor neuron dynamics", concerns **ORN**
  transduction and spike-generation filters. It contains no KC adaptation
  percentage.

This repository's own README additionally records that the 50-150 ms band was
not derived from a source at all:

> "The 2026-03-19 temporal dynamics pass came from widening the peak-time band
> from `100 <= mean <= 500` to `50 <= mean <= 150` in the same editing session,
> not from a change in the measurement."

A band that was moved to meet a result cannot be used to judge one.

### Three bugs

**1. The adaptation gate wrote a missing measurement into the average as zero.**

```python
if activities[peak_idx] > 0 and peak_idx < 3:
    adaptation_percent = 100 * (activities[peak_idx] - activities[3]) / activities[peak_idx]
else:
    adaptation_percent = 0.0
```

`peak_idx < 3` means a peak at 500 ms or later recorded adaptation as exactly
0.0 %. This is precisely why the F8 run reports 2-heptanone at 0.0 %: its peak
fell at index 3.

**2. Six sample points cannot locate a peak.** With
`timepoints = [0, 50, 100, 500, 1000, 2000]`, the peak could only ever be
reported as one of those six values. Re-running the same protocol on a 10 ms grid
out to 3000 ms gives peaks at **160, 170 and 430 ms**
(`results/final/temporal_dynamics_standalone.json`) — none representable on the
six-point grid.

**3. The summary averaged peak times across odorants.** In the F8 run that is
mean(50, 500, 50) = **200 ms**, a value no odorant exhibited, falling in a gap in
the sampling grid.

A fourth, latent: the loop advanced by
`timepoints[timepoints.index(t_ms) - 1]`, which is correct only while the
timepoint list has no repeats.

### What the literature does say about Drosophila KCs

> "the onset of Kenyon cell responses to projection neurons occurred within the
> **first 200 ms** and complex temporal patterns were transformed into brief
> **phasic** responses."

> "Kenyon cells [...] show brief odor responses of only a few spikes, and
> background activity is nearly absent. [...] KC responses are mostly restricted
> to stimulus onset and follow a phasic response dynamic."

Gruntman & Turner (2013) *Nat Neurosci* report the initial depolarisation and
plateau in KC claws at roughly 30 ms after stimulus onset.

**Replaced with**: onset within the first 200 ms (quantitative and sourced), and
the response being phasic (published direction, tested for significance across
trials). **Peak time and adaptation magnitude are reported but not scored**,
because no source gives a band for either in Drosophila KCs.

Removing a criterion makes a benchmark easier to pass, and that is stated
plainly here rather than buried. The alternative was to keep scoring against a
number that appears in no paper and that this repository's README records as
having been moved to fit a result. The phasic criterion is in exchange stricter
than what it replaces, because it requires statistical significance across
trials rather than a magnitude landing anywhere inside a 40-point-wide window.

---

## 5. odor_mixtures

**Cited**: Stettler & Axel 2009; Deisig et al. 2006.

**Scored against**: mean KC overlap in [30, 50] %.

**Verdict: neither citation is a Drosophila mushroom-body measurement.** Stettler
& Axel 2009 is mouse piriform cortex; Deisig et al. 2006 is honeybee antennal
lobe. No source for a 30-50 % KC overlap band in Drosophila could be found. The
test also used exactly **one** mixture, formed from the first two of the three
suite odorants, and the F8 result of 30.06 % sat 0.06 points inside the band.

**What the Drosophila MB mixture paper reports** — Honegger KS, Campbell RAA,
Turner GC (2011) *J Neurosci* 31:11772-11785, Fig 7:

> "The odors 3-octanol and 4-methylcyclohexanol activate very different
> populations of KCs. Presented individually, each of these odors activates
> **9 %** of KCs on average. When presented simultaneously, however, this
> proportion increases only slightly (**11 %**) and is smaller than the linear
> sum of the two activity patterns, **15 %**. A different pair of odors,
> 2-heptanone and pentyl acetate, also did not show supra-additive responses.
> [...] most cells showing a weaker response to the mixture than predicted from
> the linear sum of the response to the components."

So the published quantity is **sub-additivity**, not a fixed overlap percentage.
Both published pairs are used; all four odorants are in the DoOR matrix.

### A limitation that cannot be worked around

Honegger et al. measured the **proportion of responding KCs**. *That proportion
cannot vary in this model.* The KC readout applies a rank threshold at
`int(n_kc × target_sparsity)`, giving exactly `int(5279 × 0.06) = 316` non-zero
KCs for every stimulus, always — verified in
`tests/test_benchmark_harness.py`. The readout pins the exact quantity the paper
reports.

Readout sparsity is fixed for this repair, so the published comparison is
unavailable at the binary level and this is recorded as a limitation.
Sub-additivity is measured instead on the **pre-threshold continuous KC
amplitude**, which is not pinned. The old overlap percentage is still computed
and reported as a secondary, with its citation flagged.

---

## 6. concentration invariance (reported separately, never scored)

**Cited**: `Turner et al. 2008 — Benchmark for concentration invariance
(r > 0.70)`.

### Turner et al. 2008 contains no concentration series

Read in full. Its stimulus protocol is a single dilution:

> "Vials contained odor diluted 1:100 in paraffin oil, which, combined with the
> 1:10 dilution in the constant air stream, resulted in a 1:1,000 effective odor
> dilution. [...] Seventy-one KCs were recorded under these stimulus
> conditions."

A second dataset of 40 KCs used one different protocol, again a single
concentration, chosen to match the conditions under which OSNs had been
characterised. The paper's measurements are KC response probability (**6 %**
against **59 %** in OSNs) and angular separation between odour pairs. **Neither
is a concentration invariance, and the paper contains no correlation
threshold.**

### Where the 0.70 probably came from

Campbell et al. 2013 Fig 4C, same laboratory, reports mean **r = 0.70** for the
pentyl acetate / butyl acetate **odour pair** (n = 24), significantly greater
than PA-EL 0.15 and BA-EL 0.11. That is similarity between two chemically
similar odorants, not invariance across concentrations of one odorant. The number
appears to have migrated between measurements.

### What the real Drosophila concentration paper measured

Honegger, Campbell & Turner (2011) *J Neurosci* 31:11772-11785 is the Drosophila
KC concentration study, and the quantity it found invariant is **population
sparseness**, not pattern correlation:

> "We found that response sparseness was relatively concentration-invariant.
> Within the concentration range we tested, the proportion of responding KCs
> remained **< 0.2**"

> "We found there was a significant effect of stimulus concentration
> (p < 0.0001, F(4,73) = 32.9). However, this was profoundly affected by the
> order in which the stimuli are presented. In the high-to-low condition,
> sparseness was significantly modulated by concentration (p < 0.0001,
> F(3,25) = 22.5), but **not in the low-to-high situation (p = 0.71,
> F(3,32) = 0.47)**."

The published invariance holds in the **ascending** order, which is why ascending
order is used here — declared in advance for that reason.

**And it cannot be tested in this model**, for the same reason as the mixture
benchmark: the rank threshold pins population sparseness to a constant, so
Honegger et al.'s result would be reproduced trivially and would mean nothing.
Both quantities are reported: the pattern correlation with the note that no
published Drosophila threshold exists for it, and the pinned sparseness value so
the limitation is visible in the data.

The previously published **r = 0.7244** is separately withdrawn, for a reason
already recorded in `README.md`: that mean included isoamyl acetate, which is
absent from the DoOR matrix and returned a zero vector that self-correlates at
exactly 1.0000 across all ten concentration pairs. On real odorants only, the
same run gives **0.5866**.

---

## Cross-cutting defects

### The model had no trial-to-trial variability

Measured 2026-09-04: with `brain.reset(deterministic=True)` — which **every**
benchmark used — the same stimulus at seeds 42, 7 and 1234 produces
**bit-identical** KC readouts. Nothing in `evolve` draws from an RNG;
`sigma_noise` feeds the phase-variance field, which is a deterministic ODE, not a
noise term.

Consequences:

- "Run it N times and average" produces N identical numbers. The single-sample
  statistics were not an oversight; they were the only thing that protocol could
  produce.
- The noise floor was exactly r = 1.0, so *any* threshold below 1.0 declares a
  stimulus discriminable from itself.

The engine already had a variability source, in fact its signature default:
`reset(deterministic=False)` draws initial phase from
`np.random.uniform(-π, π, n)`. The measured same-stimulus replicate binary KC
correlation under it is **r = 0.5658**. All repaired benchmarks use it with an
explicitly declared seed list, so runs stay exactly reproducible while having
variance for the first time. This changes an initial condition, not a model
parameter, a noise level or the readout sparsity — asserted in
`tests/test_benchmark_harness.py`, not merely claimed.

**The null had to be calibrated, and calibrating it caught a design flaw.** The
first separability design compared a stimulus against itself across two disjoint
consecutive seed blocks (1001-1008 against 2001-2008) and reported it separable
at **p = 0.0017** (within r = 0.5822, between r = 0.5210). Consecutive-seed
blocks carry enough structure to shift the mean by 0.06, and with 56 within and
64 between pairs that reaches significance. Seed-block structure alone
manufactures a result. The fix is a seed-matched design with the same-seed
diagonal excluded; a stimulus against itself then gives p = 0.4942, AUC = 0.501.

### The compiled MLX kernel captured the synaptic weights

`_build_compiled_step` bound `syn_w = self.syn_weights` into its closure before
`@mx.compile`, on the assumption its own docstring recorded: that weights "never
change between steps". They do — every plasticity test assigns to
`brain.syn_weights`. Because the closure held the array from construction time,
**on the MLX backend with compilation available every learning test silently
trained nothing.**

Measured before the fix: zeroing all 49,599 KC→MBON weights changed the MBON
response by exactly **0.000 %**, and the repaired learning benchmark reported
0.000 % depression at every learning rate from 1e-6 to 1.0 — including 1.0, which
drives every one of those weights to zero.

The F8 suite ran on NumPy, where the interpreted step reads `self.syn_weights`
directly, so its learning number did reflect weight changes. Any MLX learning run
did not. Regression test: `tests/test_weights_on_signal_path.py`.

### CPU and MLX do not agree beyond 100 ms

Rule fixed before the run: report on MLX only if Jaccard ≥ 0.95 and r ≥ 0.99 at
every sample point of a 2000 ms trajectory, for every seed. Measured over 8
seeds, 20 sample points each, from a generic (seeded random) initial phase:

| t (ms) | min Jaccard | min r |
|---|---|---|
| 100 | 0.9446 | 0.990126 |
| 200 | 0.1902 | 0.542241 |
| 400 | 0.1575 | 0.424504 |
| 800 | 0.1030 | 0.065012 |
| 2000 | 0.3982 | 0.694689 |

Worst Jaccard 0.1030, worst r 0.065012. The backends agree at 100 ms and have
essentially unrelated KC identities by 200 ms.

The previously recorded agreement (Jaccard 1.0000, r 0.99988) was established
only at 100 ms and only from an all-zero initial phase, the easiest possible
case; from a generic initial condition even 100 ms gives 0.9446, already below
the rule.

**All reported numbers are therefore produced on the NumPy (CPU) backend.**
Evidence: `results/final/cpu_vs_mlx_fullrun.json`.

---

## Selection rules

Fixed before any result was seen, and recorded in every repaired result file.

- **Odorant panel** — 12 odorants selected **by paper provenance only**, each
  carrying the published measurement it comes from. No odorant was added,
  removed or reordered after a number was seen. All 12 verified present in the
  372-odorant DoOR matrix.
- **Repeats** — 8 trials per stimulus, seeds **1001-1008**, matching Campbell et
  al. 2013's six presentations per stimulus rounded up.
- **Noise floor** — every separability claim is judged against the
  within-stimulus replicate distribution from those same seeds, never a fixed
  constant.
- **Statistics** — the test the cited paper used, with statistic, n and p
  recorded.
- **Target changes** — any corrected target is quoted from source with a figure
  reference and recorded under `target_corrections`.
- **Interpreter** — `.venv/bin/python`; the system interpreter lacks
  scikit-learn, which the documented `sklearn_pca` projection requires.

## Files

- `results/final/cpu_vs_mlx_fullrun.json` — backend equivalence at full length
- `results/final/mbon_weight_monotonicity.json` — MBON readout non-monotonicity
- `results/final/kc_odor_specificity.json` — why depression is not odour-specific
- `results/final/dt_convergence_fixed_stimulus.json` — timestep convergence with
  the stimulus held fixed in real time
- `results/final/all_validations_F9_corrected.json` — the repaired suite score
- `benchmarks_repaired/` — the five rebuilt benchmarks
- `benchmark_harness.py` — shared stochastic-trial harness
- `tests/test_benchmark_harness.py` — harness and null-calibration checks
- `tests/test_weights_on_signal_path.py` — plasticity regression test
