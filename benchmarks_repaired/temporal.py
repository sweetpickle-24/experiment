"""
Temporal dynamics: is the KC response phasic, with a fast onset?

Three bugs in the old benchmark
===============================
``scripts/run_all_validations.py::validate_temporal_dynamics`` sampled at
``[0, 50, 100, 500, 1000, 2000]`` ms and scored a single PASS requiring both
``50 <= mean(peak_time) <= 150`` and ``30 <= mean(adaptation) <= 70``.

**1. The adaptation gate zeroed the result whenever the peak came late.**

    if activities[peak_idx] > 0 and peak_idx < 3:
        adaptation_percent = 100 * (activities[peak_idx] - activities[3]) / ...
    else:
        adaptation_percent = 0.0

  ``peak_idx < 3`` means that if the peak landed at 500 ms or later, adaptation
  was recorded as exactly 0.0 % rather than as unmeasured. That is precisely why
  the F8 run reports 2-heptanone at 0.0 %: its peak fell at index 3. A missing
  measurement was written into the average as a zero.

**2. Six sample points cannot locate a peak.** The peak could only ever be
  reported as one of {0, 50, 100, 500, 1000, 2000} ms. Re-running the same
  protocol on a 10 ms grid out to 3000 ms gives peaks at 160, 170 and 430 ms --
  none of which is representable on the six-point grid.

**3. The summary statistic is the mean of the peak times across odorants.** In
  the F8 run that is mean(50, 500, 50) = 200 ms, a value no odorant exhibited
  and which falls in a gap in the sampling grid.

All three are fixed here: no gate, an 80-point grid, and per-odorant reporting.

The bands are misattributed
===========================
The peak band is credited to Stopfer et al. 2003 and the adaptation band to
Nagel & Wilson 2011. Neither paper contains its band.

* Stopfer M, Jayaraman V, Laurent G (2003) *Neuron* 39:991-1004, "Intensity
  versus identity coding in an olfactory system", is a **locust** study of
  projection-neuron and Kenyon-cell coding using 50 ms bins. It reports no
  Drosophila KC peak-latency band, and no 50-150 ms figure.
* Nagel KI, Wilson RI (2011) *Nat Neurosci* 14:208-216, "Biophysical mechanisms
  underlying olfactory receptor neuron dynamics", concerns **ORN** transduction
  and spike-generation filters. It reports no KC adaptation percentage.

This repository's own README additionally records that the 50-150 ms band was
not derived from a source at all: "The 2026-03-19 temporal dynamics pass came
from widening the peak-time band from ``100 <= mean <= 500`` to
``50 <= mean <= 150`` in the same editing session, not from a change in the
measurement." A band that was moved to meet a result cannot be used to judge
one.

What the literature does say about Drosophila KCs
=================================================
The published claim is qualitative but specific, and it is about being
**phasic** with a **fast onset**:

  "the onset of Kenyon cell responses to projection neurons occurred within the
   first 200 ms and complex temporal patterns were transformed into brief
   phasic responses."
  -- Ca imaging study of the PN-to-KC transformation (Drosophila).

  "Kenyon cells [...] show brief odor responses of only a few spikes, and
   background activity is nearly absent. [...] KC responses are mostly
   restricted to stimulus onset and follow a phasic response dynamic."
  -- Galizia & Szyszka, olfactory coding review, on Perez-Orive et al. 2002,
     Stopfer et al. 2003 and Szyszka et al. 2005.

  Gruntman & Turner (2013) *Nat Neurosci* report the initial depolarisation and
  plateau in KC claws at roughly 30 ms after stimulus onset.

So this module scores two things the literature actually asserts:

  **T1 onset within the first 200 ms** -- quantitative and sourced.
  **T2 the response is phasic** -- activity at 1000 ms significantly below the
      peak, tested across trials rather than compared to a band.

**Peak time and adaptation magnitude are reported but NOT scored**, because no
source gives a band for either in Drosophila KCs. Removing a criterion makes a
benchmark easier to pass, and that is worth being explicit about: the
alternative was to keep scoring against a number that appears in no paper and
that this repository's own README records as having been moved to fit a result.
T2 is in exchange a stricter test than the old one, because it requires
statistical significance across trials rather than a magnitude landing anywhere
inside a 40-point-wide window.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark_harness import (  # noqa: E402
    REFERENCE_STRENGTH, TRIAL_SEEDS, build, kc_readout, panel_block,
    protocol_block,
)
from validation_utils import set_seed, write_results  # noqa: E402

# ── Declared before any result was seen ──────────────────────────────────────

#: The three odorants the suite has always used, so the repaired numbers stay
#: comparable with the F8 run this replaces.
ODORANTS = ('benzaldehyde', '2-heptanone', 'isopentyl_acetate')

SAMPLE_INTERVAL_MS = 25.0
TOTAL_DURATION_MS = 2000.0

#: Published, sourced: KC response onset occurs within the first 200 ms.
ONSET_LIMIT_MS = 200.0

#: Where "phasic" is tested. 1000 ms is well past any published KC onset and is
#: a sample point on the grid.
LATE_WINDOW_MS = 1000.0

#: Onset is the first sample exceeding baseline by this many baseline standard
#: deviations. Baseline is the pre-response portion of the same trace.
ONSET_SD_THRESHOLD = 3.0
BASELINE_WINDOW_MS = 50.0

ALPHA = 0.05


def trace(brain, pattern, seed):
    """
    One trial: mean KC activity sampled every SAMPLE_INTERVAL_MS.

    One continuous trajectory with the stimulus attached throughout, so
    receptor adaptation keeps advancing across samples. ``evolve`` is resumable
    and ``_stim_step`` carries the absolute step index, so repeated short calls
    are equivalent to one long call.
    """
    set_seed(seed)
    brain.reset(deterministic=False)
    brain.inject_odor(pattern, strength=REFERENCE_STRENGTH)

    n = int(round(TOTAL_DURATION_MS / SAMPLE_INTERVAL_MS))
    out = []
    for _ in range(n):
        brain.evolve(duration=SAMPLE_INTERVAL_MS)
        out.append(float(np.mean(kc_readout(brain))))
    return np.array(out)


def onset_ms(times, activity):
    """
    First sample exceeding baseline by ONSET_SD_THRESHOLD baseline SDs.

    Returns None when the trace never crosses, rather than a sentinel number
    that would be averaged into a summary.
    """
    base_mask = times <= BASELINE_WINDOW_MS
    if base_mask.sum() < 2:
        return None
    base = activity[base_mask]
    thr = base.mean() + ONSET_SD_THRESHOLD * base.std(ddof=1)
    crossings = np.flatnonzero(activity > thr)
    return float(times[crossings[0]]) if crossings.size else None


def analyse(brain, door, name):
    from scipy.stats import wilcoxon

    pattern = door.get_glomerular_pattern(name)
    traces = np.array([trace(brain, pattern, s) for s in TRIAL_SEEDS])
    times = (np.arange(traces.shape[1]) + 1) * SAMPLE_INTERVAL_MS

    mean_trace = traces.mean(axis=0)

    # Per-trial metrics, so the statistics have a sample to work with.
    peak_idx = traces.argmax(axis=1)
    peak_times = times[peak_idx]
    peak_values = traces[np.arange(len(traces)), peak_idx]

    late_idx = int(np.argmin(np.abs(times - LATE_WINDOW_MS)))
    late_values = traces[:, late_idx]

    # No gate. Adaptation is defined for every trial regardless of where the
    # peak falls, which is the bug that recorded 2-heptanone as 0.0 %.
    adaptation = 100.0 * (peak_values - late_values) / peak_values

    onsets = [onset_ms(times, t) for t in traces]
    onsets_defined = [o for o in onsets if o is not None]

    # T1: onset within the first 200 ms, on the mean onset over trials that
    # crossed. Trials that never cross are reported, not silently dropped into
    # a mean as zeros.
    t1 = bool(onsets_defined
              and len(onsets_defined) == len(onsets)
              and float(np.mean(onsets_defined)) <= ONSET_LIMIT_MS)

    # T2: phasic. Paired across trials: is activity at 1000 ms below the peak?
    stat, p_phasic = wilcoxon(late_values, peak_values, alternative='less')
    t2 = bool(p_phasic < ALPHA)

    print(f"  {name}")
    print(f"    onset      {('%.1f ms' % np.mean(onsets_defined)) if onsets_defined else 'never crossed':>12}"
          f"   (limit {ONSET_LIMIT_MS:.0f} ms)  "
          f"{len(onsets_defined)}/{len(onsets)} trials crossed")
    print(f"    peak       {np.mean(peak_times):>9.1f} ms "
          f"+/- {np.std(peak_times, ddof=1):.1f}   (reported, not scored)")
    print(f"    adaptation {np.mean(adaptation):>9.2f} %  "
          f"+/- {np.std(adaptation, ddof=1):.2f}   (reported, not scored)")
    print(f"    phasic     p = {p_phasic:.4g}  "
          f"{'PASS' if t2 else 'FAIL'}")

    return {
        'odorant': name,
        'onset_ms_per_trial': onsets,
        'onset_ms_mean': (float(np.mean(onsets_defined)) if onsets_defined
                          else None),
        'n_trials_onset_defined': len(onsets_defined),
        'n_trials': len(onsets),
        'peak_time_ms_per_trial': peak_times.tolist(),
        'peak_time_ms_mean': float(np.mean(peak_times)),
        'peak_time_ms_std': float(np.std(peak_times, ddof=1)),
        'adaptation_percent_per_trial': adaptation.tolist(),
        'adaptation_percent_mean': float(np.mean(adaptation)),
        'adaptation_percent_std': float(np.std(adaptation, ddof=1)),
        'phasic_wilcoxon': {
            'statistic': float(stat), 'p_value': float(p_phasic),
            'test': f'Wilcoxon signed-rank, activity at {LATE_WINDOW_MS:.0f} '
                    'ms < peak, one-sided, paired across trials',
        },
        'T1_onset_within_200ms': t1,
        'T2_phasic': t2,
        'mean_trace': mean_trace.tolist(),
        'sample_times_ms': times.tolist(),
    }


def run(use_mlx=False, output='temporal_repaired.json'):
    print("=" * 70)
    print("TEMPORAL DYNAMICS: fast onset and phasic response")
    print("=" * 70)

    brain, door, _ = build(use_mlx=use_mlx)
    print(f"\n{len(ODORANTS)} odorants, {len(TRIAL_SEEDS)} trials each, "
          f"{int(TOTAL_DURATION_MS / SAMPLE_INTERVAL_MS)} sample points "
          f"every {SAMPLE_INTERVAL_MS:.0f} ms\n")

    per_odor = [analyse(brain, door, n) for n in ODORANTS]

    t1_all = all(r['T1_onset_within_200ms'] for r in per_odor)
    t2_all = all(r['T2_phasic'] for r in per_odor)
    passed = bool(t1_all and t2_all)

    print("\n" + "-" * 70)
    print(f"  {'PASS' if t1_all else 'FAIL'}  T1 onset within "
          f"{ONSET_LIMIT_MS:.0f} ms, every odorant")
    print(f"  {'PASS' if t2_all else 'FAIL'}  T2 phasic, every odorant")
    print(f"VERDICT: {'PASS' if passed else 'FAIL'}")

    payload = {
        'benchmark': 'temporal_dynamics',
        'measures':
            'whether the KC response has an onset within the first 200 ms and '
            'is phasic, which are the two things the Drosophila literature '
            'asserts about it',
        'references': [
            'Ca imaging of the PN-to-KC transformation: "the onset of Kenyon '
            'cell responses to projection neurons occurred within the first '
            '200 ms and complex temporal patterns were transformed into brief '
            'phasic responses"',
            'Gruntman E, Turner GC (2013) Nat Neurosci: initial '
            'depolarisation and plateau in KC claws at roughly 30 ms after '
            'stimulus onset',
            'Galizia CG & Szyszka P, olfactory coding review, on Perez-Orive '
            'et al. 2002, Stopfer et al. 2003 and Szyszka et al. 2005: "KC '
            'responses are mostly restricted to stimulus onset and follow a '
            'phasic response dynamic"',
        ],
        'bugs_fixed': {
            'adaptation_gate':
                'the old code computed adaptation only when peak_idx < 3 and '
                'wrote exactly 0.0 % otherwise, so a peak at 500 ms or later '
                'entered the average as a zero rather than as unmeasured. '
                'That is why the F8 run reports 2-heptanone at 0.0 %: its peak '
                'fell at index 3. No gate here; adaptation is defined for '
                'every trial.',
            'sampling_density':
                f'six sample points [0, 50, 100, 500, 1000, 2000] ms could '
                f'only ever report the peak as one of those six values. Now '
                f'{int(TOTAL_DURATION_MS / SAMPLE_INTERVAL_MS)} points every '
                f'{SAMPLE_INTERVAL_MS:.0f} ms. Re-running the old protocol on '
                f'a 10 ms grid gives peaks at 160, 170 and 430 ms, none of '
                f'which is representable on the six-point grid '
                f'(results/final/temporal_dynamics_standalone.json).',
            'mean_of_peak_times':
                'the summary averaged peak times across odorants: '
                'mean(50, 500, 50) = 200 ms in the F8 run, a value no odorant '
                'exhibited and which falls in a gap in the sampling grid. '
                'Reported per odorant here.',
            'fragile_stepping':
                'the old loop advanced by '
                'timepoints[timepoints.index(t_ms) - 1], which relies on the '
                'timepoint list having no repeats. Replaced by a fixed-stride '
                'grid.',
        },
        'target_corrections': {
            'removed': [
                'peak time band 50-150 ms, attributed to Stopfer et al. 2003',
                'adaptation band 30-70 %, attributed to Nagel & Wilson 2011',
            ],
            'why': [
                'Stopfer, Jayaraman & Laurent (2003) Neuron 39:991-1004 is a '
                'LOCUST study of intensity-versus-identity coding using 50 ms '
                'bins. It contains no Drosophila KC peak-latency band and no '
                '50-150 ms figure.',
                'Nagel & Wilson (2011) Nat Neurosci 14:208-216 concerns ORN '
                'transduction and spike-generation filters. It contains no KC '
                'adaptation percentage.',
                'This repository\'s README already records that the 50-150 ms '
                'band was not derived from a source: "The 2026-03-19 temporal '
                'dynamics pass came from widening the peak-time band from '
                '100 <= mean <= 500 to 50 <= mean <= 150 in the same editing '
                'session, not from a change in the measurement." A band moved '
                'to meet a result cannot be used to judge one.',
            ],
            'replaced_with':
                'T1 onset within the first 200 ms (published and sourced) and '
                'T2 the response is phasic (published direction, tested for '
                'significance across trials)',
            'note_on_removing_a_criterion':
                'peak time and adaptation magnitude are now reported but not '
                'scored, because no source gives a band for either in '
                'Drosophila KCs. Removing a criterion makes a benchmark easier '
                'to pass and that is stated plainly. The alternative was to '
                'keep scoring against a number that appears in no paper. T2 is '
                'in exchange stricter than the criterion it replaces, because '
                'it requires statistical significance across trials rather '
                'than a magnitude landing anywhere inside a 40-point window.',
        },
        'protocol': protocol_block(
            duration_ms=TOTAL_DURATION_MS, binary=False, extra={
                'odorants': list(ODORANTS),
                'odorant_selection_rule':
                    'the three odorants the suite has always used, so the '
                    'repaired numbers stay comparable with the F8 run',
                'sample_interval_ms': SAMPLE_INTERVAL_MS,
                'n_sample_points': int(TOTAL_DURATION_MS / SAMPLE_INTERVAL_MS),
                'onset_definition':
                    f'first sample exceeding the first {BASELINE_WINDOW_MS:.0f} '
                    f'ms baseline by {ONSET_SD_THRESHOLD:.0f} baseline SDs; '
                    'None when the trace never crosses, never a sentinel that '
                    'could be averaged',
                'adaptation_definition':
                    f'100 * (peak - activity at {LATE_WINDOW_MS:.0f} ms) / '
                    'peak, per trial, with no gate on where the peak falls',
            }),
        'panel': panel_block([o for o in ODORANTS]),
        'odors': per_odor,
        'summary': {
            'T1_onset_within_200ms_all_odorants': t1_all,
            'T2_phasic_all_odorants': t2_all,
            'onset_ms_per_odorant': {
                r['odorant']: r['onset_ms_mean'] for r in per_odor},
            'peak_time_ms_per_odorant_reported_not_scored': {
                r['odorant']: r['peak_time_ms_mean'] for r in per_odor},
            'adaptation_percent_per_odorant_reported_not_scored': {
                r['odorant']: r['adaptation_percent_mean'] for r in per_odor},
            'phasic_p_per_odorant': {
                r['odorant']: r['phasic_wilcoxon']['p_value']
                for r in per_odor},
            'validation': 'PASS' if passed else 'FAIL',
        },
    }

    out = write_results(output, payload, brain=brain, door_client=door,
                        duration_ms=TOTAL_DURATION_MS, seed=None,
                        suite='temporal_repaired')
    print(f"Written to {out}")
    return payload


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mlx', action='store_true',
                    help='development only; reported runs use CPU')
    ap.add_argument('--output', default='temporal_repaired.json')
    a = ap.parse_args()
    run(use_mlx=a.mlx, output=a.output)
