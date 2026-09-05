"""
Shared measurement harness for the five olfactory benchmarks.

Why this module exists
======================

**The model has no trial-to-trial variability under the protocol every benchmark
used.** Measured 2026-09-04: with ``brain.reset(deterministic=True)``, the same
stimulus at seeds 42, 7 and 1234 produces *bit-identical* KC readouts. Nothing in
``evolve`` draws from an RNG — ``sigma_noise`` feeds the phase-variance field,
which is a deterministic ODE, not a noise term. So:

* "run it N times and average" produces N identical numbers;
* the single-sample statistics in the old suite were not an oversight, they were
  the only thing that protocol could produce;
* the noise floor is exactly r = 1.0, so *any* threshold below 1.0 declares a
  stimulus discriminable from itself.

The model does have a variability source, already implemented and in fact the
signature default: ``reset(deterministic=False)`` draws initial phase from
``np.random.uniform(-pi, pi, n)``. Measured same-stimulus replicate binary KC
correlation under it: **r = 0.5658** (seeds 42 vs 7). That is the real noise
floor, and it sits *above* several of the "+delta" correlations the old
discrimination benchmark called discriminable (0.36, 0.45, 0.37, 0.20).

Using stochastic reset with an **explicitly declared seed list** keeps runs
exactly reproducible while giving the suite variance for the first time. This
changes no model parameter, no noise level and no readout sparsity. It changes an
initial condition, and it is the branch the engine already had.

Campbell et al. 2013 (J Neurosci 33:10568) present each stimulus **six times in
random order** and correlate mean response patterns; they also identify
trial-to-trial variability as the factor that limits discrimination. Eight trials
here is that protocol rounded up.

What a "noise floor" means here
===============================
For any stimulus, the eight trials give ``C(8,2) = 28`` within-stimulus pairwise
correlations. That distribution is the null: it is what "the same thing twice"
looks like. Two stimuli are separable only if their between-stimulus correlations
are significantly *lower* than that null. No fixed constant is used anywhere.
"""

import itertools
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validation_utils import init_olfactory_brain, set_seed  # noqa: E402

# ── Declared constants. Fixed before any result was seen. ────────────────────

#: Trial seeds. Eight trials per stimulus, matching Campbell et al. 2013's six
#: presentations per stimulus rounded up. Declared here so no run can pick them
#: after seeing an outcome.
TRIAL_SEEDS = (1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008)

#: `strength=50.0` is `OdorStimulusDriver.REFERENCE_STRENGTH`, i.e. relative
#: concentration 1.0. Unchanged from the old suite.
REFERENCE_STRENGTH = 50.0

#: Unchanged from the old suite. Listed here so it is visible that the repair
#: did not touch it.
TARGET_SPARSITY = 0.06

#: Percentile used to binarise the KC readout, unchanged from the old suite's
#: ``get_active_kc_binary``.
ACTIVE_PERCENTILE = 90

#: Default trial duration, unchanged from the old suite.
TRIAL_DURATION_MS = 100.0


#: The 12-odorant panel, selected **by paper provenance only**. Every entry
#: records which published measurement it comes from. No odorant was added,
#: removed or reordered after a number was seen. All 12 verified present in the
#: 372-odorant DoOR matrix on 2026-09-04.
ODOR_PANEL = {
    'pentyl_acetate':
        'Campbell et al. 2013 Fig 4C (PA); Honegger et al. 2011 Fig 7B; '
        'Hige et al. 2015 Fig 7C-E',
    'butyl_acetate':
        'Campbell et al. 2013 Fig 4C (BA); Hige et al. 2015 Fig 7C-E',
    'ethyl_lactate':
        'Campbell et al. 2013 Fig 4C (EL); Hige et al. 2015 Fig 7F-H, the '
        'non-overlapping odour whose response was unaffected by pairing',
    '3-octanol':
        'Campbell et al. 2013 Fig 2A (OCT); Honegger et al. 2011 Fig 7A; '
        'Hige et al. 2015 Fig 1E-F',
    '4-methylcyclohexanol':
        'Campbell et al. 2013 Fig 2A (MCH); Honegger et al. 2011 Fig 7A; '
        'Xia & Tully 2007 saturation assay',
    '2-heptanone':
        'Honegger et al. 2011 Fig 7B',
    'benzaldehyde':
        'Turner et al. 2008 Fig 3I, the odour whose recorded PN responses '
        'drove the model KC population',
    '2,3-butanedione':
        'Turner et al. 2008 Fig 1C',
    'methyl_salicylate':
        'Turner et al. 2008 Fig 5, the narrowly tuned odour whose pairs '
        'reversed in angular separation',
    'ethyl_acetate':
        'Honegger et al. 2011; Wang et al. 2004 MB calcium imaging',
    '1-hexanol':
        'Hige et al. 2015 (hexanol, HP)',
    'isopentyl_acetate':
        'Honegger et al. 2011 Fig 6C (isoamyl acetate)',
}

PANEL = tuple(ODOR_PANEL)


# ── Trial execution ──────────────────────────────────────────────────────────

def kc_readout(brain, target_sparsity=TARGET_SPARSITY):
    """KC activity after the suite's rank (APL-like) normalisation."""
    return brain.get_region_activity('KC', normalize_kc=True,
                                     target_sparsity=target_sparsity)


def binarise(kc_activity, percentile=ACTIVE_PERCENTILE):
    """
    Binary active-KC vector, identical in behaviour to the old suite's
    ``get_active_kc_binary``.
    """
    kc_activity = np.asarray(kc_activity)
    if kc_activity.size == 0 or np.max(kc_activity) == 0:
        return np.zeros(kc_activity.size)
    threshold = np.percentile(kc_activity, percentile)
    return (kc_activity > threshold).astype(float)


def run_trial(brain, pattern, seed, strength=REFERENCE_STRENGTH,
              duration_ms=TRIAL_DURATION_MS, dan_drive=None,
              target_sparsity=TARGET_SPARSITY):
    """
    One stochastic trial: seed, random-phase reset, inject, evolve, read out.

    ``dan_drive`` is an optional ``(indices, amplitude)`` pair applied to
    ``brain.external_force`` **after** ``inject_odor``, because ``inject_odor``
    calls ``reset_forces()`` and would otherwise erase it. Used by the learning
    benchmark to supply the dopaminergic pairing that Hige et al. 2015 requires.

    Returns the continuous KC readout. Binarise separately when needed, so a
    caller can measure on either representation without re-running.
    """
    set_seed(seed)
    brain.reset(deterministic=False)
    brain.inject_odor(pattern, strength=strength)

    if dan_drive is not None:
        indices, amplitude = dan_drive
        force = np.zeros(brain.num_neurons, dtype=np.float32)
        force[indices] = amplitude
        if getattr(brain, 'use_mlx', False):
            import mlx.core as mx
            brain.external_force = mx.array(force)
        else:
            brain.external_force = force

    brain.evolve(duration=duration_ms)
    return kc_readout(brain, target_sparsity=target_sparsity)


def trial_set(brain, pattern, seeds=TRIAL_SEEDS, **kwargs):
    """
    ``len(seeds)`` independent stochastic trials of one stimulus.

    Returns an array of shape ``(n_trials, n_kc)``.
    """
    return np.array([run_trial(brain, pattern, s, **kwargs) for s in seeds])


def region_trial_set(brain, pattern, region, seeds=TRIAL_SEEDS, **kwargs):
    """
    As ``trial_set`` but reading out an arbitrary region (e.g. 'MBON').

    Kept separate because the KC path applies rank normalisation and other
    regions must not.
    """
    out = []
    for s in seeds:
        run_trial(brain, pattern, s, **kwargs)
        out.append(np.asarray(brain.get_region_activity(region), dtype=float))
    return np.array(out)


# ── Correlation and the null distribution ────────────────────────────────────

def _corr(a, b):
    """Pearson r, or None when either vector is constant."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if np.std(a) == 0 or np.std(b) == 0:
        # Returned as None, never as 1.0. Scoring a degenerate readout as
        # perfectly correlated is how a dead signal passes a correlation test.
        return None
    return float(np.corrcoef(a, b)[0, 1])


def within_stimulus_correlations(trials, binary=True):
    """
    The null distribution: all ``C(n,2)`` pairwise correlations among repeated
    trials of the *same* stimulus.

    This is what "the same thing twice" looks like in this model, and every
    separability claim in the repaired benchmarks is judged against it.
    """
    vecs = [binarise(t) if binary else t for t in trials]
    out = [_corr(vecs[i], vecs[j])
           for i, j in itertools.combinations(range(len(vecs)), 2)]
    return [c for c in out if c is not None]


def between_stimulus_correlations(trials_a, trials_b, binary=True,
                                  exclude_same_seed=True):
    """
    Cross correlations between trials of stimulus A and trials of stimulus B.

    ``exclude_same_seed`` drops the diagonal, i.e. pairs at the same index of
    both trial sets. It must stay on for a matched comparison, and the reason is
    not cosmetic: both trial sets are run on the same declared seed list, so
    trial ``i`` of A and trial ``i`` of B were reset from the *identical* initial
    phase. Within-stimulus pairs never share an initial phase, so keeping the
    diagonal would compare "same phase, different odour" against "different
    phase, same odour" and confound the two factors.
    """
    va = [binarise(t) if binary else t for t in trials_a]
    vb = [binarise(t) if binary else t for t in trials_b]
    out = []
    for i, x in enumerate(va):
        for j, y in enumerate(vb):
            if exclude_same_seed and i == j:
                continue
            out.append(_corr(x, y))
    return [c for c in out if c is not None]


def separability(trials_a, trials_b, binary=True, alpha=0.05):
    """
    Is stimulus B separable from stimulus A, given this model's own noise?

    Between-stimulus correlations are compared against the pooled
    within-stimulus null with a one-sided Mann-Whitney U test (between <
    within). Mann-Whitney rather than a t-test because correlation
    distributions over a small number of trials are not reliably normal and the
    samples are not paired.

    Requires both trial sets to have been run on the **same seed list**, and
    drops the same-seed diagonal from the between distribution. This is not
    fussiness. Measured 2026-09-04, an unmatched design -- the same odorant on
    seeds 1001-1008 versus seeds 2001-2008 -- reported the stimulus separable
    from *itself* at p = 0.0017 (within r = 0.5822, between r = 0.5210),
    because consecutive-seed blocks carry enough structure to shift the mean by
    0.06, and with 56 within and 64 between pairs that reaches significance.
    Under the matched design the two distributions become the same multiset when
    the stimuli are identical, so p is 0.5 by construction and the null is
    calibrated.

    Reports an effect size as well as a p value, because with samples this size
    a difference too small to matter can still be significant.
    """
    from scipy.stats import mannwhitneyu

    if len(trials_a) != len(trials_b):
        raise ValueError(
            "separability() requires both trial sets on the same seed list, so "
            f"they must be the same length; got {len(trials_a)} and "
            f"{len(trials_b)}. See this function's docstring for why an "
            "unmatched design reports a stimulus separable from itself."
        )

    within = (within_stimulus_correlations(trials_a, binary)
              + within_stimulus_correlations(trials_b, binary))
    between = between_stimulus_correlations(trials_a, trials_b, binary,
                                            exclude_same_seed=True)

    if len(within) < 2 or len(between) < 2:
        return {
            'separable': None,
            'reason': 'too few defined correlations to test',
            'n_within': len(within), 'n_between': len(between),
        }

    stat, p = mannwhitneyu(between, within, alternative='less')
    # Common-language effect size: P(a between pair is lower than a within pair).
    auc = 1.0 - stat / (len(between) * len(within))
    return {
        'separable': bool(p < alpha),
        'within_mean': float(np.mean(within)),
        'within_std': float(np.std(within, ddof=1)),
        'between_mean': float(np.mean(between)),
        'between_std': float(np.std(between, ddof=1)),
        'n_within': len(within),
        'n_between': len(between),
        'mannwhitney_u': float(stat),
        'p_value': float(p),
        'effect_size_auc': float(auc),
        'test': 'one-sided Mann-Whitney U, between < within',
        'design': 'seed-matched; same-seed diagonal excluded from between',
        'alpha': alpha,
    }


def mean_pattern(trials, binary=False):
    """
    Mean response pattern across trials.

    Campbell et al. 2013 correlate *mean* response patterns across presentations
    (Fig 4C), so this is the quantity their published r values describe.
    """
    if binary:
        return np.mean([binarise(t) for t in trials], axis=0)
    return np.mean(trials, axis=0)


# ── Reporting helpers ────────────────────────────────────────────────────────

def protocol_block(seeds=TRIAL_SEEDS, duration_ms=TRIAL_DURATION_MS,
                   binary=True, extra=None):
    """
    The protocol description every repaired result file embeds, so a reader can
    tell what was measured without reading the source.
    """
    block = {
        'n_trials_per_stimulus': len(seeds),
        'trial_seeds': list(seeds),
        'seed_selection_rule':
            'declared in the plan before any result was seen; eight trials '
            'matches Campbell et al. 2013 six presentations per stimulus, '
            'rounded up',
        'reset': 'deterministic=False (seeded random initial phase)',
        'reset_rationale':
            'with reset(deterministic=True) the trajectory carries no '
            'randomness at all: measured 2026-09-04, the same stimulus at '
            'seeds 42, 7 and 1234 gives bit-identical KC readouts, so repeats '
            'cannot be averaged and the noise floor is exactly r = 1.0. '
            'reset(deterministic=False) is the engine signature default and '
            'changes an initial condition, not a model parameter, a noise '
            'level or the readout sparsity',
        'trial_duration_ms': duration_ms,
        'reference_strength': REFERENCE_STRENGTH,
        'target_sparsity': TARGET_SPARSITY,
        'active_percentile': ACTIVE_PERCENTILE,
        'representation': 'binary active-KC vector' if binary
                          else 'continuous KC amplitude',
        'noise_floor':
            'every separability claim is judged against the within-stimulus '
            'replicate distribution from these same seeds, never against a '
            'fixed constant',
        'separability_design':
            'seed-matched: both stimuli run on the same seed list, and the '
            'same-seed diagonal is excluded from the between distribution so '
            'that both distributions consist only of differing-initial-phase '
            'pairs. An unmatched design (same odorant, seeds 1001-1008 vs '
            '2001-2008) reported the stimulus separable from itself at '
            'p = 0.0017',
    }
    if extra:
        block.update(extra)
    return block


def panel_block(names=None):
    """Odorant panel with the published measurement each entry comes from."""
    names = list(names) if names is not None else list(PANEL)
    return {
        'odorants': names,
        'selection_rule':
            'by paper provenance only; no odorant added, removed or reordered '
            'after a number was seen',
        'provenance': {n: ODOR_PANEL[n] for n in names if n in ODOR_PANEL},
    }


# ── Stimulus-path configuration, for ablation ladders ────────────────────────
#
# The five benchmarks all build their engine through build(), so a ladder that
# varies the input pipeline needs one place to say so. These read the
# environment rather than taking arguments, because each benchmark runs as its
# own process (`python -m benchmarks_repaired.X`) and an environment variable is
# the only channel that survives the process boundary without editing all six
# modules' argument parsers.
#
# Defaults are the CURRENT pipeline as of 2026-09-05 -- the one that produced
# results/final/all_validations_G2.json (5/5). They previously reproduced the
# pre-repair pipeline (2/5), which meant an unset environment silently gave the
# worse configuration while the README reported the better one. Nothing here can be
# applied silently either way: build() prints the configuration, and
# validation_utils.run_metadata reads the values back off the constructed brain and
# DoOR client, so a result file records what actually ran rather than what was
# requested.
#
# To reproduce the superseded 2/5 baseline, set all three back:
#   FLYBRAIN_PROJECTION=sklearn_pca FLYBRAIN_GLOM_MAPPING=position FLYBRAIN_STRICT=0

#: Environment variable -> (init_olfactory_brain kwarg, default, allowed values)
_ENV_CONFIG = {
    'FLYBRAIN_PROJECTION': ('projection', 'glomerular',
                            ('sklearn_pca', 'uncentered_svd', 'glomerular')),
    'FLYBRAIN_GLOM_MAPPING': ('glomerular_mapping', 'glomerulus',
                              ('glomerulus', 'position', 'index')),
    'FLYBRAIN_STRICT': ('strict_classification', '1', ('0', '1')),
}

#: The configuration the defaults now select, for the build() printout. Kept as a
#: named constant so the printout cannot drift out of step with _ENV_CONFIG the way
#: it did when the defaults were flipped.
_CURRENT_PIPELINE = {
    'projection': 'glomerular',
    'glomerular_mapping': 'glomerulus',
    'strict_classification': True,
}


def stimulus_path_config():
    """
    Resolved stimulus-path configuration for this process.

    Raises on an unrecognised value rather than falling back to the default,
    for the same reason the engine rejects unknown config keys: a run that
    silently ignored what it was told cannot be attributed afterwards.
    """
    resolved = {}
    for env_name, (kwarg, default, allowed) in _ENV_CONFIG.items():
        value = os.environ.get(env_name, default)
        if value not in allowed:
            raise ValueError(
                f"{env_name}={value!r} is not recognised; expected one of "
                f"{allowed}. Refusing to fall back to {default!r}, because a "
                "run that ignored its own configuration cannot be attributed."
            )
        resolved[kwarg] = value
    resolved['strict_classification'] = resolved['strict_classification'] == '1'
    return resolved


def build(use_mlx, seed=42):
    """
    Engine built exactly as the suite builds it.

    Stimulus-path options come from the environment; see stimulus_path_config.
    With none set this is the **current** pipeline: the published one-to-one
    receptor-to-glomerulus map, PN assignment read off the connectome's glomerulus
    annotations, and strict neuron classification.
    """
    cfg = stimulus_path_config()
    differing = {k: v for k, v in cfg.items() if v != _CURRENT_PIPELINE[k]}
    if differing:
        print(f"[benchmark_harness] stimulus path DIFFERS from current: {differing}")
    else:
        print("[benchmark_harness] stimulus path: current "
              "(glomerular / glomerulus / strict)")
    return init_olfactory_brain(use_mlx=use_mlx, seed=seed, **cfg)
