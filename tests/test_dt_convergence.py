#!/usr/bin/env python3
"""
Is forward Euler integrating, or aliasing?

The engine advances a wrapped phase with forward Euler:

    velocity += accel * dt
    phase    += velocity * dt
    phase     = atan2(sin(phase), cos(phase))

That is only meaningful while the per-step phase advance |v| * dt stays well
below pi. Above pi the wrap discards whole cycles and the "trajectory" is an
aliasing artefact of the step size, not a solution of the equations.

Under the pre-2026-09-03 constant drive the measured peak |v| was 180.9 rad/ms
at dt = 0.1 ms, i.e. 18.09 rad per step, about 2.9 whole cycles discarded per
step. Wiring in the receptor front-end brought that to 1.23 rad. This script
records the number across a dt sweep and checks whether the solution converges
as dt shrinks.

Two sweeps are run, because they answer different questions:

  constant drive     inject_odor(time_varying=False). The stimulus is identical
                     at every dt, so any change in the result is purely the
                     integrator. This is the clean convergence test.
  front-end drive    the reported path. The plume is sampled on dt, so a
                     different dt draws a different turbulence realisation;
                     the comparison is therefore confounded and is reported
                     only for the per-step phase advance, which is unaffected
                     by that confound.

Usage:
    python tests/test_dt_convergence.py
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import init_olfactory_brain, set_seed, write_results  # noqa: E402

DEFAULT_SEED = 42
ODOR = 'benzaldehyde'
STRENGTH = 50.0
DURATION_MS = 100.0
DT_SWEEP = [0.1, 0.05, 0.02, 0.01]

#: Per-step phase advance above which the wrapped forward-Euler update is
#: discarding whole cycles rather than integrating.
ALIASING_LIMIT_RAD = np.pi


def run_at_dt(dt, time_varying, seed, duration_ms=DURATION_MS):
    brain, door, _ = init_olfactory_brain(use_mlx=True, seed=seed,
                                          config={'dt': dt})
    pattern = door.get_glomerular_pattern(ODOR)
    brain.reset(deterministic=True)
    brain.inject_odor(pattern, strength=STRENGTH, time_varying=time_varying)

    peak_v = 0.0
    n_chunks = 10
    for _ in range(n_chunks):
        brain.evolve(duration=duration_ms / n_chunks)
        v = np.array(brain.mean_velocity) if brain.use_mlx else brain.mean_velocity
        peak_v = max(peak_v, float(np.abs(v).max()))

    kc = np.asarray(brain.get_region_activity('KC', normalize_kc=True,
                                              target_sparsity=0.06),
                    dtype=np.float64)
    amp = np.array(brain.mean_amplitude) if brain.use_mlx else brain.mean_amplitude

    return {
        'dt_ms': dt,
        'steps': int(duration_ms / dt),
        'peak_abs_velocity': peak_v,
        'phase_advance_per_step_rad': peak_v * dt,
        'aliasing': bool(peak_v * dt > ALIASING_LIMIT_RAD),
        'amplitude_max': float(np.max(amp)),
        'at_amplitude_ceiling': brain.count_at_amplitude_ceiling(),
        'kc': kc,
    }


def sweep(time_varying, seed):
    runs = [run_at_dt(dt, time_varying, seed) for dt in DT_SWEEP]
    finest = runs[-1]

    out = []
    for r in runs:
        kc_a, kc_b = r['kc'], finest['kc']
        corr = (float(np.corrcoef(kc_a, kc_b)[0, 1])
                if np.std(kc_a) > 0 and np.std(kc_b) > 0 else None)
        act_a = set(np.where(kc_a > 0.01)[0].tolist())
        act_b = set(np.where(kc_b > 0.01)[0].tolist())
        union = len(act_a | act_b)
        out.append({
            'dt_ms': r['dt_ms'],
            'steps': r['steps'],
            'peak_abs_velocity': r['peak_abs_velocity'],
            'phase_advance_per_step_rad': r['phase_advance_per_step_rad'],
            'aliasing': r['aliasing'],
            'amplitude_max': r['amplitude_max'],
            'at_amplitude_ceiling': r['at_amplitude_ceiling'],
            'active_kc': len(act_a),
            'kc_r_vs_finest_dt': corr,
            'active_kc_jaccard_vs_finest_dt': (len(act_a & act_b) / union) if union else 1.0,
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seed', type=int, default=DEFAULT_SEED)
    ap.add_argument('--output', default='dt_convergence.json')
    args = ap.parse_args()

    set_seed(args.seed)
    results = {
        'dt_sweep_ms': DT_SWEEP,
        'duration_ms': DURATION_MS,
        'odor': ODOR,
        'strength': STRENGTH,
        'aliasing_limit_rad': ALIASING_LIMIT_RAD,
    }

    for label, tv in (('constant_drive', False), ('front_end_drive', True)):
        print(f"\n{'='*78}\n{label}\n{'='*78}")
        rows = sweep(tv, args.seed)
        results[label] = rows
        print(f"{'dt (ms)':>8} {'steps':>7} {'peak |v|':>10} "
              f"{'rad/step':>9} {'alias':>6} {'amp max':>9} {'ceil':>5} "
              f"{'act KC':>7} {'r vs finest':>12} {'jaccard':>8}")
        for r in rows:
            print(f"{r['dt_ms']:>8} {r['steps']:>7} {r['peak_abs_velocity']:>10.3f} "
                  f"{r['phase_advance_per_step_rad']:>9.3f} "
                  f"{'YES' if r['aliasing'] else 'no':>6} "
                  f"{r['amplitude_max']:>9.4f} {r['at_amplitude_ceiling']:>5} "
                  f"{r['active_kc']:>7} "
                  f"{(r['kc_r_vs_finest_dt'] if r['kc_r_vs_finest_dt'] is not None else float('nan')):>12.4f} "
                  f"{r['active_kc_jaccard_vs_finest_dt']:>8.4f}")

    const = results['constant_drive']
    front = results['front_end_drive']
    results['summary'] = {
        'production_dt_ms': 0.1,
        'phase_advance_at_production_dt_constant_drive':
            const[0]['phase_advance_per_step_rad'],
        'phase_advance_at_production_dt_front_end_drive':
            front[0]['phase_advance_per_step_rad'],
        'aliasing_at_production_dt_front_end_drive': front[0]['aliasing'],
        'kc_r_dt0p1_vs_dt0p01_constant_drive': const[0]['kc_r_vs_finest_dt'],
        'converges_under_constant_drive': bool(
            const[0]['kc_r_vs_finest_dt'] is not None
            and const[0]['kc_r_vs_finest_dt'] > 0.9
        ),
        'amplitude_ceiling_binds_anywhere': any(
            r['at_amplitude_ceiling'] > 0 for r in const + front
        ),
        'front_end_caveat': (
            'The plume is sampled on dt, so each dt in the front-end sweep '
            'draws a different turbulence realisation. Its KC correlations '
            'across dt therefore mix integrator error with stimulus '
            'resampling and are not a convergence measure; the per-step phase '
            'advance is unaffected by that confound.'
        ),
    }
    s = results['summary']
    print(f"\n{'='*78}")
    print(f"phase advance per step at production dt=0.1 ms: "
          f"{s['phase_advance_at_production_dt_front_end_drive']:.3f} rad "
          f"(limit {ALIASING_LIMIT_RAD:.3f}) -> "
          f"{'ALIASING' if s['aliasing_at_production_dt_front_end_drive'] else 'ok'}")
    print(f"KC pattern r, dt=0.1 vs dt=0.01, constant drive: "
          f"{s['kc_r_dt0p1_vs_dt0p01_constant_drive']:.4f} -> "
          f"{'converges' if s['converges_under_constant_drive'] else 'DOES NOT CONVERGE'}")
    print(f"amplitude guard binds anywhere in the sweep: "
          f"{s['amplitude_ceiling_binds_anywhere']}")

    for key in ('constant_drive', 'front_end_drive'):
        for r in results[key]:
            r.pop('kc', None)

    brain, door, _ = init_olfactory_brain(use_mlx=True, seed=args.seed)
    out = write_results(args.output, results, brain=brain, door_client=door,
                        duration_ms=DURATION_MS, seed=args.seed,
                        test='dt_convergence')
    print(f"\nWritten to {out}")


if __name__ == '__main__':
    main()
