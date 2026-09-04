# Benchmark validity audit

**Date**: 2026-09-04
**Last Updated**: 2026-09-04
**Scope**: the five olfactory benchmarks in `scripts/run_all_validations.py`, plus
the separately reported concentration invariance measurement.

Read this before quoting any number from the olfactory suite.

Every benchmark was checked against the full text of the paper it cites. The
question asked was not "did it pass" but "does the paper contain the target this
is scored against, and does the test measure the quantity the paper measured".

## Result

**2 of 5**, on the NumPy backend, 8 trials per stimulus on seeds 1001-1008.
`results/final/all_validations_F9_corrected.json`.

| benchmark | F8 | now | headline |
|---|---|---|---|
| `temporal_dynamics` | FAIL | **PASS** | onset 50.0 ms on 8/8 trials, all odorants; phasic p = 0.0039 |
| `odor_mixtures` | PASS | **PASS** | sub-additivity index 0.5048 and 0.4440, both p = 0.0039 |
| `discrimination` | FAIL | FAIL | blend series non-monotone in the middle, correct at both ends |
| `similarity` | FAIL | FAIL | Part A ordering wrong; Part B passes at p = 0.0197 |
| `learning` | PASS | FAIL | depression and dopamine-dependence pass; specificity fails |

The F8 baseline also scored 2/5, and that is not the same result. Its passing
pair was `odor_mixtures`, whose target band came from a mouse and a honeybee
paper, and `learning`, which passed on an unsigned 99.99 % collapse of the MBON
response caused by a renormalisation bug. The current pair is
`temporal_dynamics`, scored against the one quantitative claim the Drosophila
literature makes about KC onset, and `odor_mixtures`, now scored on the
sub-additivity Honegger et al. 2011 Fig 7 actually reports, on both of the pairs
it reports rather than one.

Three benchmarks fail. All three are well powered, and each fails for a stated
reason rather than for lack of resolution.

## Summary of the audit

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

### Measured: FAIL

Scored (thresholded) rule:

| criterion | result | |
|---|---|---|
| C1 paired odour depressed | **PASS** | p = 0.007382, depression 34.70 % |
| C2 dopamine required | **PASS** | p = 0.000205, odour alone 0.00 % |
| C3 odour-specific | **FAIL** | p = 0.3227 |

C3 is the criterion Hige et al. 2015 Fig 7F-H reports, and the power analysis
settles what kind of failure it is. The means separate substantially — paired
**34.70 %** against control **12.98 %** — but the per-trial effect size is
**d = 0.038**, so 80 % power would need **n = 8,576** per group against the 8
used. This is not an underpowered test of a real effect: trial-to-trial variance
swamps the specificity almost entirely. The distinction matters, which is why the
required n is computed from the observed effect and recorded rather than left as
a bare FAIL.

The magnitude also falls short. The thresholded rule saturates at a **29.93 %**
depression ceiling across five orders of magnitude of learning rate, against
Hige's 80 ± 5.7 % and 90 ± 3.7 %. That ceiling follows from the sparse code:
only the 316 KCs above the APL threshold have their synapses depressed, and they
carry about 14 % of the KC→MBON amplitude.

The raw-amplitude contrast variant reaches the published magnitude (**79.96 %**
at the calibrated rate) but has no specificity at all — the control odour is
depressed **more** than the paired one (81.73 % against 79.96 %), and the power
analysis returns "effect is zero or in the wrong direction; no n suffices".

**So the model can produce a depression of roughly the right size, or a
depression aimed at roughly the right synapses, but not both.**

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

### Measured: FAIL (both parts required)

**Part A — FAIL. The ordering is wrong, not merely weak.**

| pair | published | measured |
|---|---|---|
| PA-BA | **0.70** (highest) | **0.1296** |
| PA-EL | 0.15 | 0.1081 |
| BA-EL | **0.11** (lowest) | **0.4287** (highest) |

One-way ANOVA F = 102.263, p = 1.29 × 10⁻²⁹, so the differences are real and
well resolved — they are in the wrong order. The model makes butyl acetate and
ethyl lactate its *most* similar pair where the paper makes them its *least*, and
makes pentyl acetate and butyl acetate nearly its least similar where the paper
makes them clearly its most. This is consistent with
`results/final/kc_odor_specificity.json`, where those two odorants correlate at
raw r = 0.9318 in the KC amplitude field.

**Part B — PASS, weakly.** KC angular separation greater than input separation in
**39 of 66** pairs (59 %), Wilcoxon signed-rank p = **0.0197**; input separation
mean 0.3265 against KC 0.3802. The published figure is 24 of 28 (86 %) at
P < 10⁻⁴. Decorrelation is reproduced, at about a third of the published
prevalence and two orders of magnitude weaker significance.

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

### Measured: FAIL (primary). The endpoints are right and the middle is not.

| blend pair | between r | within r | separable | p | AUC |
|---|---|---|---|---|---|
| 100:0 vs 0:100 | 0.1391 | 0.4808 | **yes** | 7.03 × 10⁻²⁰ | 0.996 |
| 70:30 vs 30:70 | 0.0444 | 0.4096 | yes | 1.43 × 10⁻¹⁷ | 0.963 |
| 60:40 vs 40:60 | 0.3177 | 0.3391 | **no** | 0.164 | 0.554 |

Two of the four criteria hold. The pure pair is strongly separable, and the 60:40
pair is not separable at all — which matches Campbell's "performance just above
chance" at that ratio. But correlation must rise monotonically along the series
and it does not: the first step **falls** (0.1391 → 0.0444, wrong direction,
p = 1) before the second rises (0.0444 → 0.3177, p = 1.27 × 10⁻¹⁵).

**Secondary (Xia & Tully 2007), scored separately: PASS.** The two-fold intensity
step is separable, p = 4.83 × 10⁻⁵, AUC = 0.714.

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

### Measured: PASS

| odorant | onset | phasic p | peak (not scored) | adaptation (not scored) |
|---|---|---|---|---|
| benzaldehyde | 50.0 ms | 0.003906 | 178.1 ± 177.5 ms | 67.56 ± 3.79 % |
| 2-heptanone | 50.0 ms | 0.003906 | 496.9 ± 315.5 ms | 54.97 ± 5.78 % |
| isopentyl acetate | 50.0 ms | 0.003906 | 278.1 ± 158.4 ms | 66.26 ± 11.80 % |

Onset crossed on 8/8 trials for every odorant, against the 200 ms limit.
p = 0.003906 is the smallest value a one-sided Wilcoxon signed-rank test can
return at n = 8, so the phasic result is as strong as this sample size allows.

Two honest caveats:

- **Onset resolution.** Onset lands on the *second* sample of the 25 ms grid for
  every trial of every odorant, so the measurement resolves it only to
  (25, 50] ms. That is consistent with Gruntman & Turner's roughly 30 ms and is
  well inside the 200 ms limit, but the granularity is a limit of the sampling
  grid, not a measured value.
- **Adaptation lands inside the old band.** 54.97-67.56 % is within the retired
  30-70 % window. The band is still not used, because it is not in Nagel &
  Wilson 2011. Peak times are highly variable (standard deviations of 158-316 ms
  on means of 178-497 ms), which is exactly what the six-point grid could not
  have shown.

**This benchmark's first repaired run reported FAIL, and that run is superseded
for a flaw in the repair rather than in the model.** It used the first 50 ms
*after* stimulus onset as its baseline, which on a 25 ms grid is two samples and
which is already part of the rising response, so the threshold sat too high and
onset was reported at 365.6 ms for 2-heptanone. Every trial now evolves 200 ms
with no odour attached first, giving 8 genuine pre-stimulus samples
(baseline 0.000153291 ± 0.000158).

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

### Measured: PASS

| pair | sub-additivity index | p | KCs below linear sum | legacy overlap |
|---|---|---|---|---|
| 3-octanol + 4-methylcyclohexanol | **0.5048 ± 0.2694** | 0.00391 | 21.3 % | 45.08 % |
| 2-heptanone + pentyl acetate | **0.4440 ± 0.0959** | 0.00391 | 23.5 % | 52.27 % |

Published index 0.7333 (11 % mixture against a 15 % linear sum). Both pairs are
sub-additive at p = 0.00391, the smallest a one-sided Wilcoxon can return at
n = 8 — every trial below 1. **This model is more sub-additive than measured**
(0.44-0.50 against 0.73), a real quantitative gap in the published direction.

Worth noting against the retired criterion: with receptor-level mixing and 8
trials the legacy overlap reads 45.08 % and 52.27 %, and the second falls
**outside** the old [30, 50] band. The single mixture the old benchmark tested
was not representative of the two the paper reports.

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

### Measured

**Pattern correlation: r = 0.5417**, mean over 50 concentration pairs across 5
odorants, ascending order. Per odorant: benzaldehyde 0.5555, 2-heptanone 0.4773,
isopentyl acetate 0.4996, ethyl acetate 0.5305, 3-octanol 0.6458.

For comparison the F8 run gave 0.2719 on three odorants from single trials. The
difference is mostly methodological: this correlates 8-trial *mean* patterns,
which is the quantity Campbell et al. 2013's published r values describe. It
lands close to the 0.5866 that `README.md` reports for the withdrawn 0.7244 run
once the null odorant is excluded.

**Sparseness: 0.059860, standard deviation exactly zero** — identical at every
concentration for every odorant. That is `int(5279 × 0.06) / 5279`. The
limitation above is therefore confirmed from the data, not assumed.

Neither number is scored. The correlation has no published threshold, and the
sparseness is pinned.

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

## The deepest problem: the KC active set does not converge under timestep refinement

This is not fixed by anything in this repair, and it limits how much any
KC-identity benchmark can mean.

Neither existing measurement in `results/final/dt_convergence.json` answered the
question for the production configuration. The constant-drive sweep gave a clean
number (r = 0.3081, Jaccard = 0.0601) on the superseded constant-DC stimulus
path. The front-end sweep used the production path, but its own summary records
why its numbers are not a convergence measure:
`OdorStimulusDriver.concentration_at_step(step)` indexes plume sample `step`, one
per integration step, so at dt = 0.01 ms the same 100 ms of biology draws ten
times as many plume samples and the stimulus itself is a different, faster
signal.

`tests/test_dt_convergence_fixed_stimulus.py` separates the two. The full
front-end runs once at dt = 0.002 ms to produce a channel-force trace, which is
then sampled by interpolation at whatever times each test timestep needs, through
a shim exposing the same `channel_forces(step0, num_steps)` interface the engine
already calls. Every timestep integrates the identical continuous stimulus from
the identical initial condition, so any difference is integrator error alone. The
engine is not modified.

Result, 3 seeds, production dt = 0.1 ms against dt = 0.01 ms:

| | mean | range |
|---|---|---|
| KC pattern r | **0.6758** | [0.6260, 0.7287] |
| active-set Jaccard | **0.4827** | [0.4529, 0.5012] |

Better than either previous figure, and still not convergence. About **half the
KC active set at the production timestep is absent at ten times finer**. And the
decisive point: **refinement does not help.** Agreement is non-monotone in dt for
all three seeds. For seed 1001 it gets *worse* as dt falls from 0.1 to 0.02
(Jaccard 0.5012 → 0.4202 → 0.4013) before the trivial self-comparison at the
finest step.

So the KC active set at production dt is not the solution of the underlying
equations, and `similarity`, `discrimination`, `odor_mixtures` and the
pattern-correlation form of concentration invariance all read out a quantity that
is roughly half discretisation artifact. A benchmark can still be a valid
*comparison* under this — both arms of every contrast share the same timestep —
but the absolute KC identities should not be treated as properties of the model's
equations.

---

## What is still broken, and what is uncertain

**Still broken**

- The KC active set does not converge under timestep refinement (above). This is
  the most consequential unresolved problem.
- CPU and MLX diverge past 100 ms, so the 10× faster backend cannot be used for
  any reported number. The cause is not identified beyond "different reduction
  trees"; whether the divergence is bounded chaos or an outright bug in one
  backend was not determined.
- The KC rank threshold pins population sparseness, which is the exact quantity
  Honegger et al. 2011 reports for both its mixture and its concentration
  results. Two published comparisons are therefore unavailable at the binary
  level. Readout sparsity was fixed for this repair; changing it is the obvious
  next experiment.
- The MBON amplitude field is not monotone in KC→MBON synaptic weight, so the
  spike-rate analogue of Hige's measurement cannot be scored at all.
- `scripts/run_all_validations.py` still contains the five original benchmarks
  with their misattributed targets. It was left in place so the F8 numbers remain
  reproducible; the repaired benchmarks live in `benchmarks_repaired/` and are
  scored by `scripts/run_repaired_suite.py`.

**Uncertain**

- Whether the wrong similarity *ordering* originates in the DoOR receptor data,
  the 40→20 PCA projection, or the network. The projection retains 94.0 % of
  variance, and butyl acetate and ethyl lactate correlate at raw r = 0.9318 in
  the KC field, which points upstream of the network — but this was not traced.
- Whether `n = 8` is adequate for the two passing benchmarks. Both pass at
  p = 0.0039, the floor for a one-sided Wilcoxon at that n, so the tests are
  saturated rather than comfortably significant.
- Whether the 200 ms pre-stimulus window is long enough for the baseline to be
  free of the initial-condition transient. 200 ms is about 20 amplitude time
  constants, which should be ample, but it was not swept.
- The learning benchmark's single free parameter (`eta_d × D`) is calibrated to
  Hige's published magnitude. The specificity criterion is a contrast and should
  be insensitive to it, and the reported sweep supports that, but the sweep is
  seven points on one axis.

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
