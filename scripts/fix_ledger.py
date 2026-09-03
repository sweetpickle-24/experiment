#!/usr/bin/env python3
"""
Per-fix measurement ledger.

Every behavioural change in this repository has to be measurable in isolation,
so this script records one labelled entry per fix into
results/final/fix_ledger.json. An entry carries:

  * the five suite benchmarks, each with its measured value AND the threshold it
    is judged against, so a reader does not have to open the suite source to
    know what "FAIL" meant;
  * the concentration-invariance block;
  * stimulus-path diagnostics (driven PN count, force peak, how many driven PNs
    sit at the engine's amplitude ceiling, peak |v|, and the resulting phase
    advance per integration step).

The diagnostics exist because the reported benchmarks are downstream of a
stimulus path that was saturating: a metric block alone cannot distinguish "the
model responded this way" from "the drive pinned every driven neuron at a clip
boundary before the first sample".

Usage
-----
    # full entry: diagnostics + concentration invariance + suite  (~9 min CPU)
    python scripts/fix_ledger.py --label F0_after

    # diagnostics only (~20 s), for cheap before/after on the drive itself
    python scripts/fix_ledger.py --label F0_before --diagnostics-only \
        --projection uncentered_svd

    # adopt already-committed result files as an entry, without re-running
    python scripts/fix_ledger.py --label F0_before --adopt \
        --suite-file all_validations_cpu_seed42.json \
        --invariance-file concentration_invariance_cpu_seed42.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'tests'))

from validation_utils import (  # noqa: E402
    git_commit, init_olfactory_brain, results_path, set_seed,
)

LEDGER_NAME = 'fix_ledger.json'
SEED = 42

# The five suite criteria, transcribed from scripts/run_all_validations.py so
# each recorded value sits next to the bound it was judged against.
THRESHOLDS = {
    'temporal_dynamics': {
        'peak_time_mean_ms': '50 <= x <= 150',
        'adaptation_mean_percent': '30 <= x <= 70',
    },
    'odor_mixtures': {'mean_overlap_percent': '30 <= x <= 50'},
    'discrimination': {'jnd_percent_per_odor': '10 <= x <= 20 (all odours)'},
    'similarity': {'chem_neural_correlation': '0.3 <= x <= 0.5'},
    'learning': {'mbon_change_pct': 'x >= 1.0'},
}

# Concentration invariance verdict bands, from
# tests/concentration_invariance_test.py::analyze_concentration_invariance.
INVARIANCE_THRESHOLDS = {
    'binary_correlation_mean': 'strong > 0.7, moderate > 0.5, else weak',
    'jaccard_similarity_mean': 'strong > 0.6, moderate > 0.4',
}

DIAG_ODOR = 'benzaldehyde'


# ── Metric extraction ────────────────────────────────────────────────────────

def suite_metrics(payload: dict) -> dict:
    """Flatten a run_all_validations payload into value/threshold/verdict rows."""
    v = payload['validations']
    out = {}

    td = v['temporal_dynamics']['summary']
    out['temporal_dynamics'] = {
        'peak_time_mean_ms': td.get('peak_time_mean_ms'),
        'adaptation_mean_percent': td.get('adaptation_mean_percent'),
        'thresholds': THRESHOLDS['temporal_dynamics'],
        'verdict': td.get('validation'),
        'per_odor': {
            name: {
                'peak_time_ms': d.get('peak_time_ms'),
                'adaptation_percent': d.get('adaptation_percent'),
                'activities': d.get('activities'),
            }
            for name, d in v['temporal_dynamics'].get('odors', {}).items()
        },
    }

    om = v['odor_mixtures']['summary']
    out['odor_mixtures'] = {
        'mean_overlap_percent': om.get('mean_overlap_percent'),
        'thresholds': THRESHOLDS['odor_mixtures'],
        'verdict': om.get('validation'),
    }

    di = v['discrimination']['summary']
    out['discrimination'] = {
        'jnd_per_odor': di.get('jnd_per_odor'),
        'mean_jnd_percent': di.get('mean_jnd_percent'),
        'thresholds': THRESHOLDS['discrimination'],
        'verdict': di.get('validation'),
    }

    si = v['similarity']['summary']
    out['similarity'] = {
        'chem_neural_correlation': si.get('chem_neural_correlation'),
        'thresholds': THRESHOLDS['similarity'],
        'verdict': si.get('validation'),
    }

    le = v['learning']['summary']
    out['learning'] = {
        'mbon_pre': le.get('mbon_pre'),
        'mbon_post': le.get('mbon_post'),
        'mbon_change_pct': le.get('mbon_change_pct'),
        'kc_active_pre': le.get('kc_active_pre'),
        'kc_active_post': le.get('kc_active_post'),
        'thresholds': THRESHOLDS['learning'],
        'verdict': le.get('validation'),
    }

    out['score'] = payload.get('score')
    out['projection_method'] = payload.get('config', {}).get('projection_method')
    out['glomerular_mapping'] = payload.get('config', {}).get('glomerular_mapping')
    out['backend'] = payload.get('config', {}).get('backend')
    out['dt_ms'] = payload.get('config', {}).get('dt_ms')
    return out


def invariance_metrics(payload: dict) -> dict:
    """Flatten a concentration_invariance payload."""
    s = payload['summary']
    per_odor = {}
    for odor, r in payload.get('odor_results', {}).items():
        per_odor[odor] = {
            str(conc): {
                'active_count': d.get('active_count'),
                'sparsity': d.get('sparsity'),
                'mean_amplitude': d.get('mean_amplitude'),
                'max_amplitude': d.get('max_amplitude'),
            }
            for conc, d in r.get('concentrations', {}).items()
        }
    return {
        'binary_correlation': s['binary_correlation'],
        'jaccard_similarity': s['jaccard_similarity'],
        'verdict': s.get('validation'),
        'thresholds': INVARIANCE_THRESHOLDS,
        'per_odor_active_counts': per_odor,
        'projection_method': payload.get('config', {}).get('projection_method'),
        'backend': payload.get('config', {}).get('backend'),
    }


# ── Stimulus-path diagnostics ────────────────────────────────────────────────

def diagnostics(projection='sklearn_pca', odor=DIAG_ODOR, strength=50.0,
                duration_ms=100.0, use_mlx=True, seed=SEED,
                glomerular_mapping='position') -> dict:
    """
    Probe the drive itself, independently of any benchmark.

    Runs on MLX by default because this is a diagnostic, not a reported
    benchmark, and the numbers of interest (how many neurons sit at a clip
    boundary, peak |v|) are far larger than any backend difference.
    """
    brain, door, connectome = init_olfactory_brain(
        use_mlx=use_mlx, seed=seed, projection=projection,
        glomerular_mapping=glomerular_mapping,
    )
    from hive.substrate.olfactory_subgraph import classify_olfactory_neuron

    pattern = door.get_glomerular_pattern(odor)
    brain.reset(deterministic=True)
    brain.inject_odor(pattern, strength=strength)

    force = np.array(brain.external_force)
    driven = force != 0

    # With a time-varying stimulus, external_force holds only the t=0 preview
    # row, which is one instant of a sinusoid and says nothing about the drive's
    # magnitude. Report the peak over the actual presentation window instead,
    # and the decay envelope, which is what receptor adaptation produces.
    drive_window = None
    stim = getattr(brain, '_odor_stimulus', None)
    if stim is not None:
        n_steps = int(duration_ms / brain.dt)
        w = stim.channel_forces(0, n_steps)   # separate driver query; no state shared
        per_10ms = max(1, int(10.0 / brain.dt))
        envelope = [float(np.abs(w[i:i + per_10ms]).max())
                    for i in range(0, len(w), per_10ms)]
        drive_window = {
            'window_peak_abs_force': float(np.abs(w).max()),
            'window_mean_abs_force': float(np.abs(w).mean()),
            'sign_changes_per_channel_median': float(
                np.median((np.diff(np.sign(w), axis=0) != 0).sum(axis=0))),
            'peak_abs_force_per_10ms': envelope,
            'adaptation_final': [float(x) for x in stim.receptors.adaptation[:4]],
            'concentration': float(stim.concentration),
            'amplitude_scale': float(stim.amplitude_scale),
        }

    brain.reset(deterministic=True)
    brain.inject_odor(pattern, strength=strength)
    brain.evolve(duration=duration_ms)

    amp = np.array(brain.mean_amplitude)
    vel = np.array(brain.mean_velocity)

    # The engine's amplitude guard; read off the engine so this cannot drift
    # away from the code it describes.
    ceiling = float(getattr(brain, 'amplitude_max', 10.0))
    at_ceiling = amp >= ceiling * (1.0 - 1e-6)

    regions = {}
    for region in ('PN', 'KC'):
        ids = {nid for nid, n in connectome.neurons.items()
               if classify_olfactory_neuron(n) == region}
        idx = np.array([i for i, nid in enumerate(brain.neuron_ids) if nid in ids],
                       dtype=np.int64)
        regions[region] = {
            'n': int(idx.size),
            'n_at_amplitude_ceiling': int(at_ceiling[idx].sum()),
            'amplitude_max': float(amp[idx].max()) if idx.size else None,
            'amplitude_mean': float(amp[idx].mean()) if idx.size else None,
        }

    kc_raw = brain.get_region_activity('KC')
    kc_norm = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)

    max_abs_v = float(np.abs(vel).max())
    return {
        'odor': odor,
        'strength_arg': strength,
        'duration_ms': duration_ms,
        'projection_method': door.projection_method,
        'glomerular_mapping': brain._pn_channel_source,
        'backend': 'MLX' if brain.use_mlx else 'NumPy',
        'dt_ms': float(brain.dt),
        'amplitude_ceiling': ceiling,
        'drive': {
            'n_driven_neurons': int(driven.sum()),
            # t=0 snapshot; meaningful only for the old constant drive.
            'force_at_t0_peak': float(force.max()) if driven.any() else 0.0,
            'force_peak': (drive_window['window_peak_abs_force']
                           if drive_window else
                           (float(force.max()) if driven.any() else 0.0)),
            'time_varying': bool(getattr(brain, 'has_time_varying_drive', False)),
            'window': drive_window,
        },
        'driven_at_amplitude_ceiling': int(at_ceiling[driven].sum()) if driven.any() else 0,
        'regions': regions,
        'peak_abs_velocity': max_abs_v,
        # The reason saturation matters numerically: phase advance per step.
        # Above ~pi the forward-Euler phase update is aliasing, not integrating.
        'phase_advance_per_step_rad': max_abs_v * float(brain.dt),
        'kc_raw_max': float(np.max(kc_raw)),
        'kc_raw_mean': float(np.mean(kc_raw)),
        'kc_norm_mean': float(np.mean(kc_norm)),
        'kc_active_above_0p01': int(np.sum(kc_norm > 0.01)),
    }


# ── Ledger IO ────────────────────────────────────────────────────────────────

def load_ledger() -> dict:
    path = results_path(LEDGER_NAME)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        'purpose': (
            'One entry per fix, so the effect of each individual change is '
            'visible rather than inferred from a final score. Each entry '
            'records every benchmark value next to the threshold it is judged '
            'against, plus stimulus-path diagnostics.'
        ),
        'entries': [],
    }


def append_entry(label: str, entry: dict) -> Path:
    ledger = load_ledger()
    entry = dict(entry)
    entry['label'] = label
    entry['recorded_at'] = datetime.now(timezone.utc).isoformat()
    entry['git_commit'] = git_commit()
    # Replace an entry with the same label rather than accumulating duplicates.
    ledger['entries'] = [e for e in ledger['entries'] if e.get('label') != label]
    ledger['entries'].append(entry)
    path = results_path(LEDGER_NAME)
    with open(path, 'w') as f:
        json.dump(ledger, f, indent=2)
    return path


# ── Entry points ─────────────────────────────────────────────────────────────

def build_entry(label, projection, run_suite=True, run_invariance=True,
                run_diagnostics=True, use_mlx_diag=True, seed=SEED,
                note=None, glomerular_mapping='position') -> dict:
    entry = {'note': note, 'projection_requested': projection, 'seed': seed,
             'glomerular_mapping_requested': glomerular_mapping}

    if run_diagnostics:
        print(f"\n=== [{label}] stimulus-path diagnostics ===")
        entry['diagnostics'] = diagnostics(projection=projection,
                                           use_mlx=use_mlx_diag, seed=seed,
                                           glomerular_mapping=glomerular_mapping)
        print(json.dumps(entry['diagnostics'], indent=2))

    if run_invariance:
        print(f"\n=== [{label}] concentration invariance (CPU, seed {seed}) ===")
        import concentration_invariance_test as ci
        ci.main(use_mlx=False, seed=seed,
                output_name=f'concentration_invariance_{label}.json',
                projection=projection,
                glomerular_mapping=glomerular_mapping)
        with open(results_path(f'concentration_invariance_{label}.json')) as f:
            entry['concentration_invariance'] = invariance_metrics(json.load(f))

    if run_suite:
        print(f"\n=== [{label}] five-benchmark suite (CPU, seed {seed}) ===")
        import run_all_validations as rav
        rav.run_all_validations(use_mlx=False, seed=seed,
                                output_name=f'all_validations_{label}.json',
                                projection=projection,
                                glomerular_mapping=glomerular_mapping)
        with open(results_path(f'all_validations_{label}.json')) as f:
            entry['suite'] = suite_metrics(json.load(f))

    return entry


def adopt_entry(suite_file, invariance_file, note=None) -> dict:
    entry = {'note': note, 'adopted_from': {}}
    if suite_file:
        with open(results_path(suite_file)) as f:
            entry['suite'] = suite_metrics(json.load(f))
        entry['adopted_from']['suite'] = suite_file
    if invariance_file:
        with open(results_path(invariance_file)) as f:
            entry['concentration_invariance'] = invariance_metrics(json.load(f))
        entry['adopted_from']['concentration_invariance'] = invariance_file
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--label', required=True, help='entry label, e.g. F0_after')
    ap.add_argument('--projection', default='sklearn_pca',
                    choices=['sklearn_pca', 'uncentered_svd'])
    ap.add_argument('--glomerular-mapping', default='position',
                    choices=['position', 'index'])
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--note', default=None, help='what this entry is measuring')
    ap.add_argument('--diagnostics-only', action='store_true')
    ap.add_argument('--no-diagnostics', action='store_true')
    ap.add_argument('--adopt', action='store_true',
                    help='build the entry from existing result files')
    ap.add_argument('--suite-file', default=None)
    ap.add_argument('--invariance-file', default=None)
    args = ap.parse_args()

    set_seed(args.seed)

    if args.adopt:
        entry = adopt_entry(args.suite_file, args.invariance_file, note=args.note)
    else:
        entry = build_entry(
            args.label, args.projection,
            run_suite=not args.diagnostics_only,
            run_invariance=not args.diagnostics_only,
            run_diagnostics=not args.no_diagnostics,
            seed=args.seed, note=args.note,
            glomerular_mapping=args.glomerular_mapping,
        )

    path = append_entry(args.label, entry)
    print(f"\nLedger entry '{args.label}' written to {path}")


if __name__ == '__main__':
    main()
