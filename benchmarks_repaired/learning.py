"""
Learning: dopamine-gated depression of KC->MBON synapses (Hige et al. 2015).

What the paper measured
=======================
Hige T, Aso Y, Modi MN, Rubin GM, Turner GC (2015) "Heterosynaptic plasticity
underlies aversive olfactory learning in Drosophila." *Neuron* 88:985-998.

Quoted from the paper:

  "After 1-s pairing of odor presentation and PPL1-gamma1pedc activation, the
   EPSCs showed a marked depression in a stimulus-specific manner [...] The
   average reduction in charge transfer was **90 +/- 3.7 %** (mean +/- SEM;
   Fig 3D), which is of similar order to the **80 +/- 5.7 %** [reduction in
   spike rate]."

  "Pairing with PA effectively induced LTD not only for this odor, but also for
   the odors with overlapping KC representations, BA and HP [...] On the other
   hand, **EL responses were unaffected**." (Fig 7C-H)

  "Depression was significant for PA, BA and HP (p < 0.005, Tukey's post hoc
   test following repeated measures two-way ANOVA) but not for EL (p > 0.1)."

  "Magnitude of depression correlates with extent of overlap in KC response
   patterns (p < 0.005, Pearson's r = 0.90)." (Fig 7I)

So the measured quantity is a **signed depression** of the MBON response to the
**paired** odour, it **requires dopaminergic pairing**, and its diagnostic
feature is **odour specificity**: a non-overlapping odour is spared.

What the old benchmark measured instead
=======================================
``scripts/run_all_validations.py::validate_learning`` scored

    |MBON_post - MBON_pre| / (|MBON_pre| + eps) >= 1 %

with no dopaminergic pairing, no control odour, and no required direction. It
passed on an *unsigned* 99.99 % collapse of the MBON response
(0.03327 -> 0.0000044). That collapse was not learning. ``_apply_hebbian_stdp``
updated **all 446,388 synapses** in the network and then renormalised the whole
weight vector by its maximum:

    w = w + eta * A_pre * A_post * cos(phi_pre - phi_post)
    np.clip(w, 0.0, None, out=w)
    w /= np.max(w)                       # <- this

One synapse growing large drives every other weight toward zero, so the network
silences itself. A signal dying is not a memory forming, and a 1 % unsigned
threshold cannot tell the two apart.

What this module measures
=========================
Restricted to the 49,599 KC->MBON synapses identified by cell type (not by
index range), with no global renormalisation, and with the dopaminergic pairing
the paper requires.

The rule is heterosynaptic and presynaptic, as the paper found: dopamine acts at
the KC terminal and the depression is not explained by changes in the MBON. So
depression depends on presynaptic KC activity and the local dopamine level, and
not on postsynaptic MBON activity:

    dw_ij = -eta_d * A_KC(i) * D            for KC_i -> MBON_j
    w = max(w, 0)                           no renormalisation

This is odour-specific by construction only in so far as the KC representation
is odour-specific, which is exactly the mechanism Fig 7I attributes it to. There
are 5,286 DAN->KC synapses in this subgraph, which is the anatomical basis for
dopamine acting on KC terminals here.

Free parameters, and how they are pinned
========================================
``eta_d`` and the DAN drive amplitude ``D`` enter only as a product, so there is
one free parameter, not two. Nothing in the published record constrains it: it
stands for the strength of an optogenetic drive that has no counterpart in this
model.

It is therefore **calibrated, not tuned to pass**: bisected so that the
paired-odour depression lands as close as possible to Hige's **80 %** spike-rate
figure. That fixes the magnitude to the published effect size rather than to
whichever value scores best, and it is declared as calibration in the result
file. The full sweep over the product is reported alongside, so the calibration
cannot hide a shape.

The criteria then test the paper's actual claims, all three of which are
independent of that magnitude:

  C1  the paired odour is **depressed** (signed, not absolute)
  C2  the depression **requires dopamine**: an odour-only control, identical in
      every other respect, is significantly less depressed
  C3  the depression is **odour-specific**: the non-overlapping control odour
      ethyl lactate is significantly less depressed than the paired odour,
      which is Hige Fig 7F-H

Which readout, and why the obvious one cannot be used
=====================================================
Hige et al. 2015 reports two quantities: EPSC **charge transfer** at the MBON
(Fig 3D, 90 +/- 3.7 %, its primary synaptic result) and MBON **spike rate**
(80 +/- 5.7 %). This model has a candidate analogue for each: the summed
KC->MBON coupling current, and the MBON amplitude field.

Measured before this benchmark was built
(``results/final/mbon_weight_monotonicity.json``, 8 trials at each of 11 weight
scales from 1.0 down to 0.0):

* **MBON amplitude is not a monotone function of KC->MBON weight.**
  Spearman rho = **-0.0182, p = 0.958**. The response *peaks at half strength*
  (0.0313 at scale 0.5 against 0.0291 at full strength) and its entire dynamic
  range is 14.6 % of maximum. Depressing these synapses does not reduce this
  readout, and the sign of the effect is not even fixed.
* **KC->MBON coupling current is perfectly monotone.**
  Spearman rho = **1.0000, p = 0**, running 0.2814 at full strength down to
  0.0000 when the weights are zeroed.

The reason is mechanistic, not incidental. Coupling enters as
``w * sin(phi_pre - phi_post) * A_pre``, which pulls phases together rather than
adding excitation, and the amplitude field is driven by ``|velocity|``. Tighter
phase locking means lower ``|velocity|``, so stronger coupling can *lower*
amplitude.

This benchmark therefore scores the **coupling current**, which is the analogue
of the paper's primary figure, and reports MBON amplitude alongside as an
unscored diagnostic. That is more faithful to Hige et al. 2015, not less: Fig 3D
is the headline synaptic measurement. It is also the harder test, because the
current readout is directional and has full dynamic range where the amplitude
readout has almost none.

The unmeasurability of the spike-rate analogue is a real limitation of this
model and is recorded as such rather than worked around.

Odorants
========
Paired odour **pentyl acetate** and control odour **ethyl lactate** are the
paper's own pair (Fig 7C-H); ethyl lactate is specifically the odour it reports
as unaffected. Both are in the DoOR matrix. Chosen by paper provenance before
any result was seen.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    REFERENCE_STRENGTH, TRIAL_DURATION_MS, TRIAL_SEEDS, build, protocol_block,
    run_trial,
)
from validation_utils import set_seed, write_results  # noqa: E402

# ── Declared before any result was seen ──────────────────────────────────────

PAIRED_ODOR = 'pentyl_acetate'      # Hige et al. 2015 Fig 7C-E (PA)
CONTROL_ODOR = 'ethyl_lactate'      # Hige et al. 2015 Fig 7F-H (EL), unaffected

#: Hige et al. 2015: "After 1-s pairing of odor presentation and
#: PPL1-gamma1pedc activation". One pairing episode, 1000 ms.
PAIRING_DURATION_MS = 1000.0

#: DAN drive amplitude. Enters only as the product with eta_d, so it is held
#: fixed at the engine's odour forcing scale (`amplitude_scale` = 10.0 in
#: hive/config.yaml) and the product is what gets calibrated.
DAN_DRIVE = 10.0

#: Published figures the measured depression is reported against.
HIGE_SPIKE_RATE_DEPRESSION_PCT = 80.0
HIGE_SPIKE_RATE_SEM_PCT = 5.7
HIGE_CHARGE_TRANSFER_DEPRESSION_PCT = 90.0
HIGE_CHARGE_TRANSFER_SEM_PCT = 3.7

#: Calibration target: the spike-rate figure, being the more conservative of
#: the two the paper reports.
CALIBRATION_TARGET_PCT = HIGE_SPIKE_RATE_DEPRESSION_PCT

#: Sweep reported alongside the calibrated point, so the calibration cannot
#: conceal the shape of the response.
ETA_SWEEP = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0)

ALPHA = 0.05


# ── Synapse selection and the plasticity rule ────────────────────────────────

def kc_to_mbon_mask(brain, connectome):
    """
    Boolean mask over the synapse arrays selecting KC -> MBON synapses.

    Cell type is resolved through ``classify_olfactory_neuron``, the classifier
    the rest of the repository uses. The original standalone test identified
    these synapses by hardcoded index ranges ("KCs: 5198-10476, MBONs:
    10477-10572"), which select an arbitrary set of neurons because engine order
    is connectome iteration order and is not grouped by cell type.
    """
    from hive.substrate.olfactory_subgraph import classify_olfactory_neuron

    region_of_idx = {}
    for nid, neuron in connectome.neurons.items():
        i = brain.id_to_idx.get(nid)
        if i is not None:
            region_of_idx[i] = classify_olfactory_neuron(neuron)

    reg = np.array([region_of_idx.get(i, '?') for i in range(brain.num_neurons)])
    pre = np.asarray(brain.pre_indices)
    post = np.asarray(brain.post_indices)
    return (reg[pre] == 'KC') & (reg[post] == 'MBON')


def weights_as_numpy(brain):
    w = brain.syn_weights
    if hasattr(w, 'tolist'):
        return np.asarray(w.tolist(), dtype=np.float32)
    return np.asarray(w, dtype=np.float32).copy()


def write_weights(brain, w):
    if getattr(brain, 'use_mlx', False):
        import mlx.core as mx
        brain.syn_weights = mx.array(w.astype(np.float32))
    else:
        brain.syn_weights = w.astype(np.float32)


def amplitudes_as_numpy(brain):
    a = brain.mean_amplitude
    return np.asarray(a.tolist() if hasattr(a, 'tolist') else a,
                      dtype=np.float64)


#: Which KC activity the depression is proportional to.
#:
#: 'raw'         -- the raw KC amplitude field.
#: 'thresholded' -- KC activity after the APL-like rank normalisation, which is
#:                  zero for every KC outside the sparse code.
#:
#: 'thresholded' is the faithful one and is what gets scored. Hige et al. 2015
#: describes dopamine depressing the terminals of KCs that the odour actually
#: depolarised, and Fig 7I ties the magnitude of depression to KC pattern
#: overlap. The analogue of "depolarised by this odour" in this model is passing
#: the APL threshold, not merely having non-zero amplitude.
#:
#: The distinction is not cosmetic. Measured in
#: results/final/kc_odor_specificity.json: the raw field is non-zero on all
#: 5,279 KCs, and the 316 that pass the threshold carry only 12.5-14.1 % of the
#: total KC amplitude, so a raw-amplitude rule aims about 86 % of its depression
#: at KCs outside the sparse code, where the signal is close to odour-invariant.
#: Both variants are run and reported, because the comparison is what
#: distinguishes a limitation of the model from a defect in the rule.
RULE_VARIANTS = ('thresholded', 'raw')
SCORED_VARIANT = 'thresholded'


def kc_drive_for_rule(brain, variant):
    """
    Per-neuron presynaptic drive the depression rule is proportional to.

    Returns a full-length (num_neurons,) vector, zero outside KCs for the
    thresholded variant.
    """
    amp = amplitudes_as_numpy(brain)
    if variant == 'raw':
        return amp
    if variant != 'thresholded':
        raise ValueError(f"unknown rule variant {variant!r}")

    drive = np.zeros_like(amp)
    kc_idx = brain._region_indices('KC')
    if kc_idx is not None and len(kc_idx):
        drive[kc_idx] = brain.get_region_activity(
            'KC', normalize_kc=True, target_sparsity=0.06)
    return drive


def apply_dopamine_ltd(brain, kc_mbon_mask, eta_d, dan_active,
                       variant=SCORED_VARIANT):
    """
    One dopamine-gated depression step at KC->MBON synapses.

        dw_ij = -eta_d * KC_drive(i) * D

    Presynaptic and heterosynaptic, per Hige et al. 2015: dopamine acts at the
    KC terminal and the depression is not explained by MBON changes, so the
    postsynaptic amplitude does not appear.

    Weights are floored at zero. There is deliberately **no** renormalisation:
    the `w /= max(w)` in the old rule is what silenced the network.

    Returns the mean absolute weight change over the selected synapses.
    """
    w = weights_as_numpy(brain)
    drive = kc_drive_for_rule(brain, variant)
    pre = np.asarray(brain.pre_indices)

    dw = np.zeros_like(w, dtype=np.float64)
    dw[kc_mbon_mask] = -eta_d * drive[pre[kc_mbon_mask]] * dan_active

    w_new = np.maximum(w.astype(np.float64) + dw, 0.0)
    write_weights(brain, w_new.astype(np.float32))
    return float(np.mean(np.abs(w_new - w.astype(np.float64))[kc_mbon_mask]))


# ── Measurement ──────────────────────────────────────────────────────────────

def kc_to_mbon_current(brain, mask):
    """
    Total depolarising coupling current delivered to MBONs across KC->MBON
    synapses, using the engine's own coupling expression.

    This is the analogue of Hige et al. 2015's **primary** measurement: EPSC
    charge transfer at the MBON (Fig 3D, 90 +/- 3.7 % reduction). Only the
    positive half is summed, matching a measurement of *excitatory* current: the
    coupling term is signed and its negative half is a hyperpolarising
    contribution.

    Measured monotone in KC->MBON weight at Spearman rho = 1.0000
    (``results/final/mbon_weight_monotonicity.json``), unlike the MBON amplitude
    field, which is not (rho = -0.0182, p = 0.958).
    """
    phase = np.asarray(brain.mean_phase.tolist()
                       if hasattr(brain.mean_phase, 'tolist')
                       else brain.mean_phase, dtype=np.float64)
    amp = amplitudes_as_numpy(brain)
    w = np.asarray(weights_as_numpy(brain), dtype=np.float64)
    pre = np.asarray(brain.pre_indices)[mask]
    post = np.asarray(brain.post_indices)[mask]
    forces = w[mask] * np.sin(phase[pre] - phase[post]) * amp[pre]
    return float(np.sum(np.maximum(forces, 0.0)))


def mbon_response(brain, pattern, mask, seeds=TRIAL_SEEDS):
    """
    Per-trial MBON readouts during odour presentation.

    Returns ``(current, amplitude)``: the scored KC->MBON coupling current, and
    the MBON amplitude field reported alongside as an unscored diagnostic.
    """
    current, amplitude = [], []
    for seed in seeds:
        run_trial(brain, pattern, seed, strength=REFERENCE_STRENGTH,
                  duration_ms=TRIAL_DURATION_MS)
        current.append(kc_to_mbon_current(brain, mask))
        amplitude.append(float(np.mean(brain.get_region_activity('MBON'))))
    return np.array(current), np.array(amplitude)


def pair(brain, pattern, kc_mbon_mask, eta_d, dan_indices, with_dopamine,
         seed=TRIAL_SEEDS[0], variant=SCORED_VARIANT):
    """
    One pairing episode: present the odour for PAIRING_DURATION_MS, with or
    without concurrent DAN drive, then apply the depression step.

    The odour-only condition (`with_dopamine=False`) is identical in every other
    respect, which is what makes it a control for the dopamine requirement.
    """
    dan_drive = (dan_indices, DAN_DRIVE) if with_dopamine else None
    set_seed(seed)
    run_trial(brain, pattern, seed, strength=REFERENCE_STRENGTH,
              duration_ms=PAIRING_DURATION_MS, dan_drive=dan_drive)
    return apply_dopamine_ltd(brain, kc_mbon_mask, eta_d,
                              DAN_DRIVE if with_dopamine else 0.0,
                              variant=variant)


def depression_pct(pre, post):
    """Signed depression as a percentage. Positive means the response fell."""
    base = float(np.mean(pre))
    if base == 0:
        return None
    return 100.0 * (base - float(np.mean(post))) / abs(base)


def _condition(brain, door, connectome, mask, dan_indices, eta_d,
               with_dopamine, variant=SCORED_VARIANT):
    """
    Run one condition from a pristine weight vector and return the depression of
    both odours.

    The weight vector is saved and restored around every condition, so the
    conditions are independent rather than cumulative.
    """
    w0 = weights_as_numpy(brain)
    pa = door.get_glomerular_pattern(PAIRED_ODOR)
    el = door.get_glomerular_pattern(CONTROL_ODOR)

    pa_pre, pa_pre_amp = mbon_response(brain, pa, mask)
    el_pre, el_pre_amp = mbon_response(brain, el, mask)

    mean_dw = pair(brain, pa, mask, eta_d, dan_indices, with_dopamine,
                   variant=variant)

    pa_post, pa_post_amp = mbon_response(brain, pa, mask)
    el_post, el_post_amp = mbon_response(brain, el, mask)

    w1 = weights_as_numpy(brain)
    kc_mbon_sum_before = float(np.sum(w0[mask]))
    kc_mbon_sum_after = float(np.sum(w1[mask]))
    other_sum_before = float(np.sum(w0[~mask]))
    other_sum_after = float(np.sum(w1[~mask]))

    write_weights(brain, w0)

    return {
        'with_dopamine': with_dopamine,
        'eta_d': eta_d,
        'rule_variant': variant,
        'readout': 'KC->MBON coupling current (analogue of EPSC charge '
                   'transfer, Hige 2015 Fig 3D)',
        'paired_odor_depression_pct': depression_pct(pa_pre, pa_post),
        'control_odor_depression_pct': depression_pct(el_pre, el_post),
        'paired_pre': pa_pre.tolist(), 'paired_post': pa_post.tolist(),
        'control_pre': el_pre.tolist(), 'control_post': el_post.tolist(),
        # Unscored diagnostic: this readout is not monotone in KC->MBON weight
        # (Spearman rho = -0.0182, p = 0.958), so a depression percentage
        # computed on it is not interpretable. Recorded, not judged.
        'mbon_amplitude_unscored': {
            'paired_depression_pct': depression_pct(pa_pre_amp, pa_post_amp),
            'control_depression_pct': depression_pct(el_pre_amp, el_post_amp),
            'paired_pre': pa_pre_amp.tolist(),
            'paired_post': pa_post_amp.tolist(),
            'why_unscored':
                'MBON amplitude is not a monotone function of KC->MBON weight '
                'in this model; see results/final/mbon_weight_monotonicity.json',
        },
        'mean_abs_weight_change_kc_mbon': mean_dw,
        'kc_mbon_weight_sum_before': kc_mbon_sum_before,
        'kc_mbon_weight_sum_after': kc_mbon_sum_after,
        # Asserted rather than assumed: nothing outside KC->MBON may move.
        'non_kc_mbon_weight_sum_before': other_sum_before,
        'non_kc_mbon_weight_sum_after': other_sum_after,
        'non_kc_mbon_weights_unchanged':
            other_sum_before == other_sum_after,
    }


def calibrate(brain, door, connectome, mask, dan_indices,
              target_pct=CALIBRATION_TARGET_PCT, iterations=8,
              variant=SCORED_VARIANT):
    """
    Bisect the eta_d * D product so paired-odour depression approaches
    Hige's published 80 %.

    This pins an unconstrained test parameter to the published effect size. It
    is calibration, not scoring: the criteria that follow are all ratios or
    contrasts and do not depend on hitting the target.
    """
    lo, hi = 1e-8, 1e2
    trace = []
    best = None
    for _ in range(iterations):
        mid = float(np.sqrt(lo * hi))
        res = _condition(brain, door, connectome, mask, dan_indices, mid,
                         with_dopamine=True, variant=variant)
        d = res['paired_odor_depression_pct']
        trace.append({'eta_d': mid, 'paired_odor_depression_pct': d})
        if d is None:
            break
        if best is None or abs(d - target_pct) < abs(best[1] - target_pct):
            best = (mid, d)
        if d < target_pct:
            lo = mid
        else:
            hi = mid
    return {
        'target_pct': target_pct,
        'rule_variant': variant,
        'target_source':
            'Hige et al. 2015 Fig 3D/4: 80 +/- 5.7 % reduction in spike rate',
        'eta_d': None if best is None else best[0],
        'achieved_depression_pct': None if best is None else best[1],
        'iterations': len(trace),
        'trace': trace,
        'note':
            'eta_d and the DAN drive amplitude enter only as a product, so this '
            'calibrates one parameter, not two. It is pinned to the published '
            'effect size rather than chosen to pass; all three criteria are '
            'contrasts and are independent of it.',
    }


# ── Entry point ──────────────────────────────────────────────────────────────

def _score(paired, odor_only):
    """Apply the three criteria taken from Hige et al. 2015."""
    from scipy.stats import mannwhitneyu

    pa_pre = np.array(paired['paired_pre'])
    pa_post = np.array(paired['paired_post'])
    el_pre = np.array(paired['control_pre'])
    el_post = np.array(paired['control_post'])

    # C1: the paired odour is depressed. Signed and one-sided: an increase must
    #     fail, which the old |change| >= 1 % criterion could not enforce.
    u1, p1 = mannwhitneyu(pa_post, pa_pre, alternative='less')

    # C2: dopamine is required. Per-trial depression with pairing versus the
    #     odour-only control.
    pa_drop_paired = pa_pre - pa_post
    oo_pre = np.array(odor_only['paired_pre'])
    oo_post = np.array(odor_only['paired_post'])
    u2, p2 = mannwhitneyu(pa_drop_paired, oo_pre - oo_post,
                          alternative='greater')

    # C3: odour specificity. Hige Fig 7F-H: EL is spared.
    u3, p3 = mannwhitneyu(pa_drop_paired, el_pre - el_post,
                          alternative='greater')

    c1, c2, c3 = p1 < ALPHA, p2 < ALPHA, p3 < ALPHA
    return {
        'C1_paired_odor_depressed': {
            'passed': bool(c1), 'p_value': float(p1), 'u': float(u1),
            'test': 'one-sided Mann-Whitney U, post < pre',
            'source': 'Hige et al. 2015: pairing induces depression',
            'note': 'signed; an increase fails, unlike the old |change| >= 1 %',
        },
        'C2_dopamine_required': {
            'passed': bool(c2), 'p_value': float(p2), 'u': float(u2),
            'test': 'one-sided Mann-Whitney U, paired drop > odour-only drop',
            'source': 'Hige et al. 2015: pairing odour with DAN activation is '
                      'what induces the plasticity',
        },
        'C3_odor_specific': {
            'passed': bool(c3), 'p_value': float(p3), 'u': float(u3),
            'test': 'one-sided Mann-Whitney U, paired drop > control drop',
            'source': 'Hige et al. 2015 Fig 7F-H: EL responses were '
                      'unaffected (p > 0.1) while PA, BA and HP were depressed '
                      '(p < 0.005)',
        },
        '_passed': bool(c1 and c2 and c3),
    }


def specificity_power(paired, alpha=ALPHA, target_power=0.80):
    """
    How many trials would criterion C3 need, given the effect actually observed?

    C3 asks whether the paired odour is depressed more than the unpaired
    control. At the declared 8 trials the test can be directionally correct and
    still not significant, and reporting only "FAIL" would conflate "the model
    does not do this" with "this protocol cannot see it". Those are different
    findings and the user of a benchmark needs to know which one it is.

    The required n is computed from the observed per-trial drops, so it is a
    consequence of the measurement rather than a choice. Reported alongside the
    verdict at the declared n; it never changes the verdict at that n.
    """
    pa_drop = (np.array(paired['paired_pre'])
               - np.array(paired['paired_post']))
    el_drop = (np.array(paired['control_pre'])
               - np.array(paired['control_post']))

    diff = float(np.mean(pa_drop) - np.mean(el_drop))
    pooled_sd = float(np.sqrt(
        (np.var(pa_drop, ddof=1) + np.var(el_drop, ddof=1)) / 2.0))
    if pooled_sd == 0 or diff <= 0:
        return {
            'observed_mean_difference': diff,
            'pooled_sd': pooled_sd,
            'cohens_d': None,
            'required_n_per_group': None,
            'note': 'effect is zero or in the wrong direction; no n suffices',
        }

    d = diff / pooled_sd
    # Two-sample one-sided normal approximation:
    #   n per group = 2 * ((z_alpha + z_power) / d) ** 2
    from scipy.stats import norm
    z_a = norm.ppf(1 - alpha)
    z_b = norm.ppf(target_power)
    n_req = 2.0 * ((z_a + z_b) / d) ** 2
    return {
        'observed_mean_difference': diff,
        'pooled_sd': pooled_sd,
        'cohens_d': float(d),
        'alpha': alpha,
        'target_power': target_power,
        'required_n_per_group': int(np.ceil(n_req)),
        'n_used': len(pa_drop),
        'method': 'two-sample one-sided normal approximation, '
                  'n = 2 * ((z_alpha + z_power) / d)^2',
        'note':
            'computed from the observed effect, so it is a consequence of the '
            'measurement, not a choice. Does not alter the verdict at the '
            'declared n.',
    }


def _evaluate_variant(brain, door, connectome, mask, dan_indices, variant):
    """Calibrate and score one plasticity-rule variant."""
    print(f"\n{'=' * 70}\nRULE VARIANT: {variant}\n{'=' * 70}")
    print(f"Calibrating eta_d against Hige's "
          f"{CALIBRATION_TARGET_PCT:.0f} % depression...")
    cal = calibrate(brain, door, connectome, mask, dan_indices, variant=variant)
    if cal['eta_d'] is None:
        print("  calibration failed: depression undefined at every eta_d")
        return {'calibration': cal, 'criteria': None}
    print(f"  eta_d = {cal['eta_d']:.6g} -> "
          f"{cal['achieved_depression_pct']:.2f} % depression")
    eta_d = cal['eta_d']

    print("Conditions at the calibrated eta_d:")
    paired = _condition(brain, door, connectome, mask, dan_indices, eta_d,
                        with_dopamine=True, variant=variant)
    odor_only = _condition(brain, door, connectome, mask, dan_indices, eta_d,
                           with_dopamine=False, variant=variant)
    print(f"  odour + dopamine: paired "
          f"{paired['paired_odor_depression_pct']:.2f} %, control "
          f"{paired['control_odor_depression_pct']:.2f} %")
    print(f"  odour alone:      paired "
          f"{odor_only['paired_odor_depression_pct']:.2f} %, control "
          f"{odor_only['control_odor_depression_pct']:.2f} %")

    print("Sweep over eta_d (reported so the calibration hides nothing):")
    sweep = []
    for eta in ETA_SWEEP:
        r = _condition(brain, door, connectome, mask, dan_indices, eta,
                       with_dopamine=True, variant=variant)
        sweep.append({
            'eta_d': eta,
            'paired_odor_depression_pct': r['paired_odor_depression_pct'],
            'control_odor_depression_pct': r['control_odor_depression_pct'],
        })
        print(f"  eta_d={eta:<8g} paired "
              f"{r['paired_odor_depression_pct']:8.3f} %  control "
              f"{r['control_odor_depression_pct']:8.3f} %")

    criteria = _score(paired, odor_only)
    for name, c in criteria.items():
        if name.startswith('_'):
            continue
        print(f"  {'PASS' if c['passed'] else 'FAIL'}  {name}  "
              f"p={c['p_value']:.4g}")

    power = specificity_power(paired)
    if power.get('required_n_per_group'):
        print(f"  C3 power: d={power['cohens_d']:.3f}, "
              f"would need n={power['required_n_per_group']} per group "
              f"(used {power['n_used']})")
    else:
        print(f"  C3 power: {power['note']}")

    # The 'thresholded' rule can only depress the synapses of KCs inside the
    # sparse code, so the depression it can produce is bounded. That ceiling is
    # a measurable property worth reporting against Hige's 80-90 %.
    ceiling = max((s['paired_odor_depression_pct'] for s in sweep
                   if s['paired_odor_depression_pct'] is not None),
                  default=None)
    if ceiling is not None:
        print(f"  depression ceiling over the sweep: {ceiling:.2f} % "
              f"(Hige: {HIGE_SPIKE_RATE_DEPRESSION_PCT:.0f}-"
              f"{HIGE_CHARGE_TRANSFER_DEPRESSION_PCT:.0f} %)")

    return {
        'rule_variant': variant,
        'calibration': cal,
        'conditions': {'odor_plus_dopamine': paired,
                       'odor_only_control': odor_only},
        'eta_sweep': sweep,
        'criteria': criteria,
        'specificity_power': power,
        'depression_ceiling_pct': ceiling,
        'summary': {
            'paired_odor_depression_pct':
                paired['paired_odor_depression_pct'],
            'control_odor_depression_pct':
                paired['control_odor_depression_pct'],
            'odor_only_paired_depression_pct':
                odor_only['paired_odor_depression_pct'],
            'n_criteria_passed': sum(
                1 for k, c in criteria.items()
                if not k.startswith('_') and c['passed']),
            'validation': 'PASS' if criteria['_passed'] else 'FAIL',
        },
    }


def run(use_mlx=True, output='learning_repaired.json'):
    print("=" * 70)
    print("LEARNING: dopamine-gated KC->MBON depression (Hige et al. 2015)")
    print("=" * 70)

    brain, door, connectome = build(use_mlx=use_mlx)
    mask = kc_to_mbon_mask(brain, connectome)
    dan_indices = brain._region_indices('DAN')
    if dan_indices is None or len(dan_indices) == 0:
        raise RuntimeError("no DAN neurons found; the pairing cannot be applied")

    print(f"KC->MBON synapses selected by cell type: {int(mask.sum())}")
    print(f"DAN neurons available for pairing:        {len(dan_indices)}")

    variants = {v: _evaluate_variant(brain, door, connectome, mask,
                                     dan_indices, v)
                for v in RULE_VARIANTS}

    scored = variants[SCORED_VARIANT]
    criteria = scored['criteria']
    passed = bool(criteria and criteria['_passed'])
    paired = scored['conditions']['odor_plus_dopamine']
    odor_only = scored['conditions']['odor_only_control']
    cal = scored['calibration']
    sweep = scored['eta_sweep']

    print("\n" + "-" * 70)
    print(f"SCORED VARIANT: {SCORED_VARIANT}")
    print(f"VERDICT: {'PASS' if passed else 'FAIL'}")

    payload = {
        'benchmark': 'learning',
        'measures':
            'signed, dopamine-gated, odour-specific depression of the MBON '
            'response to a paired odour',
        'reference':
            'Hige T, Aso Y, Modi MN, Rubin GM, Turner GC (2015) Heterosynaptic '
            'plasticity underlies aversive olfactory learning in Drosophila. '
            'Neuron 88:985-998',
        'published_figures': {
            'charge_transfer_depression_pct':
                [HIGE_CHARGE_TRANSFER_DEPRESSION_PCT,
                 HIGE_CHARGE_TRANSFER_SEM_PCT],
            'spike_rate_depression_pct':
                [HIGE_SPIKE_RATE_DEPRESSION_PCT, HIGE_SPIKE_RATE_SEM_PCT],
            'specificity': 'EL unaffected (p > 0.1); PA, BA, HP depressed '
                           '(p < 0.005)',
            'overlap_correlation': 'Pearson r = 0.90, p < 0.005 (Fig 7I)',
        },
        'readout_choice': {
            'scored': 'KC->MBON coupling current',
            'scored_analogue_of':
                'MBON EPSC charge transfer, the primary synaptic result in '
                'Hige et al. 2015 Fig 3D (90 +/- 3.7 %)',
            'scored_monotonicity_in_weight':
                'Spearman rho = 1.0000, p = 0 over 11 weight scales, 8 trials '
                'each (results/final/mbon_weight_monotonicity.json)',
            'reported_unscored': 'MBON amplitude field',
            'reported_unscored_analogue_of':
                'MBON spike rate (80 +/- 5.7 %)',
            'why_unscored':
                'MBON amplitude is NOT a monotone function of KC->MBON '
                'synaptic weight in this model: Spearman rho = -0.0182, '
                'p = 0.958, with the response peaking at half weight strength '
                'and a total dynamic range of 14.6 % of maximum. Coupling '
                'enters as w * sin(phi_pre - phi_post) * A_pre, which pulls '
                'phases together rather than adding excitation, and amplitude '
                'is driven by |velocity|, so tighter phase locking lowers it. '
                'Depression of these synapses therefore does not reduce that '
                'readout and the sign is not fixed. This is a limitation of '
                'the model, recorded rather than worked around.',
        },
        'target_corrections': {
            'removed': 'MIN_CHANGE_PCT = 1.0 on |MBON_post - MBON_pre|',
            'why':
                'unsigned and directionless, so it passed on a 99.99 % '
                'collapse of the MBON response (0.03327 -> 0.0000044) caused by '
                'the `w /= max(w)` renormalisation in _apply_hebbian_stdp, '
                'which updated all 446,388 synapses in the network. A signal '
                'dying is not a memory forming and a 1 % unsigned threshold '
                'cannot distinguish them. Hige et al. 2015 measures a signed '
                'depression that requires dopaminergic pairing and is '
                'odour-specific; none of those three was tested.',
            'replaced_with':
                'three criteria taken from the paper: depression is signed, '
                'requires dopamine, and spares a non-overlapping odour',
        },
        'protocol': protocol_block(extra={
            'paired_odor': PAIRED_ODOR,
            'control_odor': CONTROL_ODOR,
            'odor_selection_rule':
                "Hige et al. 2015's own pair (Fig 7C-H); ethyl lactate is "
                'specifically the odour the paper reports as unaffected',
            'pairing_duration_ms': PAIRING_DURATION_MS,
            'pairing_duration_source':
                'Hige et al. 2015: "After 1-s pairing of odor presentation and '
                'PPL1-gamma1pedc activation"',
            'dan_drive': DAN_DRIVE,
            'n_dan_neurons': int(len(dan_indices)),
            'n_kc_to_mbon_synapses': int(mask.sum()),
            'synapse_selection': 'by cell type via classify_olfactory_neuron, '
                                 'not by hardcoded index range',
            'plasticity_rule':
                'dw_ij = -eta_d * KC_drive(i) * D for KC->MBON only; w floored '
                'at 0; NO renormalisation',
            'plasticity_rule_rationale':
                'presynaptic and heterosynaptic per Hige et al. 2015: dopamine '
                'acts at the KC terminal and the depression is not explained '
                'by MBON changes, so postsynaptic amplitude does not appear. '
                'This subgraph has 5,286 DAN->KC synapses.',
            'rule_variants_run': list(RULE_VARIANTS),
            'rule_variant_scored': SCORED_VARIANT,
            'rule_variant_rationale':
                "KC_drive is the KC activity the depression is proportional "
                "to. 'thresholded' uses activity after the APL-like rank "
                "normalisation, zero outside the sparse code, and is scored: "
                "Hige et al. 2015 describes dopamine depressing the terminals "
                "of KCs the odour actually depolarised, and the analogue of "
                "'depolarised by this odour' here is passing the APL "
                "threshold. 'raw' uses the raw amplitude field and is reported "
                "for contrast: measured in "
                "results/final/kc_odor_specificity.json, that field is "
                "non-zero on all 5,279 KCs and the 316 that pass the threshold "
                "carry only 12.5-14.1 % of the total, so a raw-amplitude rule "
                "aims about 86 % of its depression at KCs outside the sparse "
                "code. Both are reported because the comparison is what "
                "separates a limitation of the model from a defect in the rule.",
        }),
        'calibration': cal,
        'conditions': {
            'odor_plus_dopamine': paired,
            'odor_only_control': odor_only,
        },
        'eta_sweep': sweep,
        'criteria': criteria,
        'rule_variants': variants,
        'summary': {
            'readout': 'KC->MBON coupling current',
            'rule_variant_scored': SCORED_VARIANT,
            'paired_odor_depression_pct':
                paired['paired_odor_depression_pct'],
            'control_odor_depression_pct':
                paired['control_odor_depression_pct'],
            'odor_only_paired_depression_pct':
                odor_only['paired_odor_depression_pct'],
            'per_variant_validation': {
                v: (r['summary']['validation'] if r.get('summary') else 'ERROR')
                for v, r in variants.items()
            },
            'specificity_power': scored.get('specificity_power'),
            'depression_ceiling_pct': scored.get('depression_ceiling_pct'),
            'published_comparison':
                f'Hige et al. 2015 charge transfer '
                f'{HIGE_CHARGE_TRANSFER_DEPRESSION_PCT} +/- '
                f'{HIGE_CHARGE_TRANSFER_SEM_PCT} %, spike rate '
                f'{HIGE_SPIKE_RATE_DEPRESSION_PCT} +/- '
                f'{HIGE_SPIKE_RATE_SEM_PCT} %',
            'n_criteria_passed':
                scored['summary']['n_criteria_passed'] if scored.get('summary')
                else 0,
            'validation': 'PASS' if passed else 'FAIL',
        },
    }

    out = write_results(output, payload, brain=brain, door_client=door,
                        duration_ms=TRIAL_DURATION_MS, seed=None,
                        suite='learning_repaired')
    print(f"Written to {out}")
    return payload


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cpu', action='store_true')
    ap.add_argument('--output', default='learning_repaired.json')
    a = ap.parse_args()
    run(use_mlx=not a.cpu, output=a.output)
