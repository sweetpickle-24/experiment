#!/usr/bin/env python3
"""
Does the KC active set converge under timestep refinement?

Why the existing measurement does not answer this
=================================================
``results/final/dt_convergence.json`` reports two sweeps and neither settles the
question for the production configuration.

* The **constant-drive** sweep gives a clean convergence number, KC pattern
  r = 0.3081 and active-set Jaccard 0.0601 between dt = 0.1 ms and 0.01 ms, but
  it uses the superseded constant-DC stimulus, which bypasses the plume, the
  carrier and receptor adaptation.
* The **front-end** sweep uses the production stimulus path but its own summary
  records why its numbers are not a convergence measure:

    "The plume is sampled on dt, so each dt in the front-end sweep draws a
     different turbulence realisation. Its KC correlations across dt therefore
     mix integrator error with stimulus resampling and are not a convergence
     measure."

  Confirmed in the source: ``OdorStimulusDriver.concentration_at_step(step)``
  indexes plume sample ``step``, one sample per integration step. At dt = 0.01 ms
  the same 100 ms of biology draws ten times as many plume samples, so the
  stimulus itself is a different, faster-fluctuating signal.

So the reported r = 0.4416 for the production path conflates two effects, and
the clean r = 0.3081 belongs to a stimulus path no longer in use.

How this test separates them
============================
The stimulus is held fixed **as a function of real time**, not of step index.
The full front-end (plume, carrier, receptor adaptation) is run once at a
reference timestep to produce a channel-force trace, and that trace is then
sampled by linear interpolation at whatever times each test timestep needs. A
small shim supplies the same ``channel_forces(step0, num_steps)`` interface the
engine already calls, so the engine is not modified.

Every timestep therefore integrates the identical continuous stimulus from the
identical initial condition, and any difference in the KC readout is integrator
error alone.

Why the answer matters
======================
The KC readout is a rank threshold: whichever neurons occupy the top
``int(n_kc * target_sparsity)`` positions are "active". If that set is not
stable under refinement, then every benchmark that reads out KC identity --
similarity, discrimination, mixtures, and the pattern-correlation form of
concentration invariance -- is partly measuring a discretisation artifact rather
than a property of the model's equations.

Run: ``.venv/bin/python tests/test_dt_convergence_fixed_stimulus.py``
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import init_olfactory_brain, set_seed, write_results  # noqa: E402

# ── Declared before any result was seen ──────────────────────────────────────

#: Reference timestep at which the front-end trace is generated. Five times
#: finer than the finest tested timestep, so the interpolated stimulus is not
#: itself the limiting approximation.
DT_REFERENCE_MS = 0.002

#: Timesteps tested, coarsest first. 0.1 ms is the production value.
DT_SWEEP_MS = (0.1, 0.05, 0.02, 0.01)

DURATION_MS = 100.0
ODORANT = 'benzaldehyde'
STRENGTH = 50.0
TARGET_SPARSITY = 0.06

#: Three seeds, declared in advance, to check the conclusion is not a property
#: of one initial condition.
SEEDS = (1001, 1002, 1003)


class FixedTimeStimulus:
    """
    Supplies channel forces from a fixed function of real time.

    Same interface the engine calls on ``OdorStimulusDriver``, so nothing in the
    engine changes. Unlike that class, the returned force depends only on
    absolute time, so refining the timestep refines the integration without
    altering the stimulus.
    """

    def __init__(self, times_ms, forces, dt_ms):
        self.dt = float(dt_ms)
        self._t = np.asarray(times_ms, dtype=np.float64)
        self._f = np.asarray(forces, dtype=np.float64)

    def channel_forces(self, step0, num_steps):
        t = (np.arange(step0, step0 + num_steps, dtype=np.float64)) * self.dt
        out = np.empty((num_steps, self._f.shape[1]), dtype=np.float32)
        for c in range(self._f.shape[1]):
            out[:, c] = np.interp(t, self._t, self._f[:, c])
        return out


def reference_trace(pattern, duration_ms=DURATION_MS,
                    dt_ref_ms=DT_REFERENCE_MS):
    """
    Run the full front-end once at the reference timestep.

    Returns (times_ms, forces) with one row per reference step.
    """
    from hive.interface.olfactory import OdorStimulusDriver

    driver = OdorStimulusDriver(pattern, dt_ms=dt_ref_ms, strength=STRENGTH)
    n = int(round(duration_ms / dt_ref_ms))
    forces = driver.channel_forces(0, n)
    times = np.arange(n, dtype=np.float64) * dt_ref_ms
    return times, forces


def kc_at_dt(dt_ms, pattern, times, forces, seed):
    """KC readout after DURATION_MS at timestep dt_ms, fixed-time stimulus."""
    brain, door, _ = init_olfactory_brain(
        use_mlx=False, seed=42, config={'dt': dt_ms},
        projection='sklearn_pca', glomerular_mapping='position')

    set_seed(seed)
    brain.reset(deterministic=False)
    # Attach the real driver first so inject_odor sets up channel mapping and
    # force arrays, then swap in the fixed-time stimulus.
    brain.inject_odor(pattern, strength=STRENGTH)
    brain._odor_stimulus = FixedTimeStimulus(times, forces, dt_ms)
    brain._stim_step = 0

    brain.evolve(duration=DURATION_MS)
    return brain.get_region_activity('KC', normalize_kc=True,
                                     target_sparsity=TARGET_SPARSITY)


def active_set(kc):
    return set(np.flatnonzero(kc > 0).tolist())


def main():
    print("=" * 70)
    print("dt CONVERGENCE WITH THE STIMULUS HELD FIXED IN REAL TIME")
    print("=" * 70)
    print(f"reference dt {DT_REFERENCE_MS} ms, sweep {DT_SWEEP_MS} ms, "
          f"{DURATION_MS:.0f} ms, seeds {SEEDS}")

    # One brain purely to obtain the glomerular pattern.
    _, door, _ = init_olfactory_brain(use_mlx=False, seed=42)
    pattern = door.get_glomerular_pattern(ODORANT)

    print(f"\nGenerating the reference front-end trace at dt = "
          f"{DT_REFERENCE_MS} ms "
          f"({int(DURATION_MS / DT_REFERENCE_MS)} steps)...")
    times, forces = reference_trace(pattern)
    print(f"  trace shape {forces.shape}, "
          f"force range [{forces.min():.4f}, {forces.max():.4f}]")

    per_seed = []
    for seed in SEEDS:
        print(f"\nseed {seed}")
        kcs = {}
        for dt in DT_SWEEP_MS:
            kcs[dt] = kc_at_dt(dt, pattern, times, forces, seed)
            print(f"  dt = {dt:<6g} active KCs = "
                  f"{len(active_set(kcs[dt]))}")

        finest = DT_SWEEP_MS[-1]
        rows = []
        for dt in DT_SWEEP_MS:
            a, b = kcs[dt], kcs[finest]
            r = (float(np.corrcoef(a, b)[0, 1])
                 if np.std(a) > 0 and np.std(b) > 0 else None)
            sa, sb = active_set(a), active_set(b)
            jac = len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0
            rows.append({
                'dt_ms': dt,
                'n_active': len(sa),
                'kc_r_vs_finest': r,
                'active_jaccard_vs_finest': jac,
                'max_abs_diff_vs_finest': float(np.max(np.abs(a - b))),
            })
            print(f"  dt = {dt:<6g} vs {finest:g}:  r = "
                  f"{'n/a' if r is None else f'{r:.4f}'}   "
                  f"Jaccard = {jac:.4f}")
        per_seed.append({'seed': seed, 'rows': rows})

    # The production timestep is the one that matters.
    prod = [next(r for r in s['rows'] if r['dt_ms'] == DT_SWEEP_MS[0])
            for s in per_seed]
    prod_r = [r['kc_r_vs_finest'] for r in prod if r['kc_r_vs_finest'] is not None]
    prod_j = [r['active_jaccard_vs_finest'] for r in prod]

    # Is refinement even monotone? If coarse-to-fine agreement improves as dt
    # shrinks, the solution is converging, however slowly.
    monotone_per_seed = []
    for s in per_seed:
        js = [r['active_jaccard_vs_finest'] for r in s['rows']]
        monotone_per_seed.append(
            bool(all(js[i] <= js[i + 1] for i in range(len(js) - 1))))

    print("\n" + "-" * 70)
    print(f"At the production timestep dt = {DT_SWEEP_MS[0]} ms, against "
          f"dt = {DT_SWEEP_MS[-1]} ms:")
    print(f"  KC pattern r      mean {np.mean(prod_r):.4f}  "
          f"range [{min(prod_r):.4f}, {max(prod_r):.4f}]")
    print(f"  active-set Jaccard mean {np.mean(prod_j):.4f}  "
          f"range [{min(prod_j):.4f}, {max(prod_j):.4f}]")
    print(f"  agreement improves monotonically as dt shrinks: "
          f"{monotone_per_seed}")
    print("\nFor comparison, results/final/dt_convergence.json reported:")
    print("  r = 0.3081, Jaccard = 0.0601  (constant DC drive, clean but a "
          "superseded stimulus path)")
    print("  r = 0.4416, Jaccard = 0.1172  (production path, but confounded "
          "by plume resampling)")

    payload = {
        'question':
            'Does the KC active set converge under timestep refinement, with '
            'the stimulus held fixed as a function of real time so that only '
            'integrator error varies?',
        'why_existing_measurement_insufficient': {
            'constant_drive_sweep':
                'clean convergence number (r = 0.3081, Jaccard = 0.0601) but '
                'uses the superseded constant-DC stimulus, which bypasses the '
                'plume, the carrier and receptor adaptation',
            'front_end_sweep':
                'uses the production stimulus path, but '
                'OdorStimulusDriver.concentration_at_step(step) indexes plume '
                'sample `step`, one per integration step, so each dt draws a '
                'different and faster-fluctuating plume. Its own summary in '
                'dt_convergence.json records that its correlations "mix '
                'integrator error with stimulus resampling and are not a '
                'convergence measure".',
        },
        'method':
            'the full front-end is run once at a reference timestep to produce '
            'a channel-force trace, which is then sampled by linear '
            'interpolation at each test timestep\'s times through a shim '
            'exposing the same channel_forces(step0, num_steps) interface the '
            'engine already calls. Every timestep integrates the identical '
            'continuous stimulus from the identical initial condition, so any '
            'KC difference is integrator error alone. The engine is not '
            'modified.',
        'protocol': {
            'dt_reference_ms': DT_REFERENCE_MS,
            'dt_reference_rationale':
                'five times finer than the finest tested timestep, so the '
                'interpolated stimulus is not itself the limiting '
                'approximation',
            'dt_sweep_ms': list(DT_SWEEP_MS),
            'production_dt_ms': DT_SWEEP_MS[0],
            'duration_ms': DURATION_MS,
            'odorant': ODORANT,
            'strength': STRENGTH,
            'seeds': list(SEEDS),
            'reset': 'deterministic=False, seeded; initial phase is a '
                     'per-neuron draw independent of dt, so the initial '
                     'condition is identical across the sweep',
            'backend': 'NumPy',
            'target_sparsity': TARGET_SPARSITY,
        },
        'per_seed': per_seed,
        'summary': {
            'production_dt_kc_r_mean': float(np.mean(prod_r)),
            'production_dt_kc_r_range': [float(min(prod_r)), float(max(prod_r))],
            'production_dt_jaccard_mean': float(np.mean(prod_j)),
            'production_dt_jaccard_range':
                [float(min(prod_j)), float(max(prod_j))],
            'agreement_monotone_in_dt_per_seed': monotone_per_seed,
            'previously_reported': {
                'constant_drive_r': 0.30812737094715426,
                'constant_drive_jaccard': 0.06006006006006006,
                'front_end_r_confounded': 0.4415993635509286,
                'front_end_jaccard_confounded': 0.1171875,
            },
        },
    }

    out = write_results('dt_convergence_fixed_stimulus.json', payload,
                        brain=None, door_client=door,
                        duration_ms=DURATION_MS, seed=None,
                        suite='dt_convergence_fixed_stimulus',
                        backend='NumPy')
    print(f"\nWritten to {out}")


if __name__ == '__main__':
    main()
