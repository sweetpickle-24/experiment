#!/usr/bin/env python3
"""
COMPACT Master Validation Script
==================================

Runs all 5 validations in sequence using the optimized common initialization.
Est. 60-90 min total runtime.
"""

import argparse
import sys
import json
import numpy as np
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import (
    assert_reproducible_backend, init_olfactory_brain, results_path, log_path,
    run_metadata, write_results,
)

# Run configuration. Recorded into every result file this script writes.
SEED = 42
TRIAL_DURATION_MS = 100.0

# Third odorant was 'geosmin', which is absent from the DoOR matrix. Before
# 2026-09-03 that miss returned a zero vector and each validation below silently
# skipped or scored it. It is replaced by isopentyl_acetate, an ester that is
# present in the matrix and chemically distinct from the other two. This changes
# what the suite measures; see ODOR_AUDIT.md.
TEST_ODORS = ['benzaldehyde', '2-heptanone', 'isopentyl_acetate']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path('all_validations.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_active_kc_binary(kc_activity, threshold_percentile=90):
    """Convert KC activity to binary."""
    if len(kc_activity) == 0 or np.max(kc_activity) == 0:
        return np.zeros(len(kc_activity))
    threshold = np.percentile(kc_activity, threshold_percentile)
    return (kc_activity > threshold).astype(float)

def run_all_validations(use_mlx=False, seed=SEED,
                        output_name='all_validations_results.json',
                        allow_mlx_result=False, projection='sklearn_pca'):
    """
    Run all 5 validation experiments.

    Args:
        use_mlx          : GPU backend. Defaults to False. Deterministic as of
                           2026-09-03, but CPU remains the reporting default.
        seed             : RNG seed, recorded in the output.
        output_name      : filename under results/final/.
        allow_mlx_result : permit writing a result from the MLX backend.
        projection       : receptor->glomerular projection ('sklearn_pca' or
                           'uncentered_svd'), recorded in the output.
    """
    logger.info("="*70)
    logger.info("COMPREHENSIVE BIOLOGICAL VALIDATION SUITE")
    logger.info("="*70)
    logger.info("Starting all 5 validations...")
    logger.info("Backend: %s", "MLX (GPU)" if use_mlx else "NumPy (CPU)")
    if not use_mlx:
        # Measured 2026-09-03: ~18 s wall per 100 ms simulated on this machine,
        # so a full suite is minutes, not hours. The previous "150 s per 100 ms"
        # note came from results/final/cpu_vs_mlx_validation.json, which is
        # superseded and whose timings were never reproducible.
        logger.info("CPU runtime is roughly 18 s per 100 ms simulated.")

    start_time = datetime.now()
    
    # Initialize system once. Seeded as of 2026-09-03: the suite was previously
    # unseeded and consecutive runs of identical code gave different results.
    logger.info("\nInitializing olfactory system...")
    brain, door_client, connectome = init_olfactory_brain(
        use_mlx=use_mlx, seed=seed, projection=projection)
    logger.info(f"✅ System ready: {brain.num_neurons} neurons, backend={'MLX' if brain.use_mlx else 'NumPy'}")
    if not allow_mlx_result:
        assert_reproducible_backend(brain)

    config = run_metadata(brain=brain, duration_ms=TRIAL_DURATION_MS, seed=seed,
                          door_client=door_client,
                          suite='run_all_validations', n_benchmarks=5)
    logger.info(f"Configuration: {json.dumps(config, indent=2)}")

    results = {
        'timestamp': start_time.isoformat(),
        'system': {
            'num_neurons': brain.num_neurons,
            'backend': 'MLX' if brain.use_mlx else 'NumPy'
        },
        'validations': {}
    }

    test_odors = list(TEST_ODORS)
    logger.info(f"Test odors: {test_odors}")
    
    # 1. Temporal Dynamics
    logger.info("\n" + "="*70)
    logger.info("VALIDATION 1/5: TEMPORAL DYNAMICS")
    logger.info("="*70)
    
    temporal_results = validate_temporal_dynamics(brain, door_client, test_odors)
    results['validations']['temporal_dynamics'] = temporal_results
    logger.info(f"✅ Temporal dynamics complete")
    
    # 2. Odor Mixtures
    logger.info("\n" + "="*70)
    logger.info("VALIDATION 2/5: ODOR MIXTURES")
    logger.info("="*70)
    
    mixture_results = validate_odor_mixtures(brain, door_client, test_odors)
    results['validations']['odor_mixtures'] = mixture_results
    logger.info(f"✅ Odor mixtures complete")
    
    # 3. Discrimination Thresholds
    logger.info("\n" + "="*70)
    logger.info("VALIDATION 3/5: DISCRIMINATION THRESHOLDS")
    logger.info("="*70)
    
    discrimination_results = validate_discrimination(brain, door_client, test_odors)
    results['validations']['discrimination'] = discrimination_results
    logger.info(f"✅ Discrimination thresholds complete")
    
    # 4. Odor Similarity
    logger.info("\n" + "="*70)
    logger.info("VALIDATION 4/5: ODOR SIMILARITY STRUCTURE")
    logger.info("="*70)
    
    similarity_results = validate_similarity(brain, door_client, test_odors)
    results['validations']['similarity'] = similarity_results
    logger.info(f"✅ Odor similarity complete")
    
    # 5. Learning (simplified - just demonstrate plasticity)
    logger.info("\n" + "="*70)
    logger.info("VALIDATION 5/5: LEARNING & PLASTICITY")
    logger.info("="*70)
    
    learning_results = validate_learning(brain, door_client, test_odors[0])
    results['validations']['learning'] = learning_results
    logger.info(f"✅ Learning & plasticity complete")
    
    # Summary
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds() / 60
    
    logger.info("\n" + "="*70)
    logger.info("ALL VALIDATIONS COMPLETE")
    logger.info("="*70)
    logger.info(f"Total time: {elapsed:.1f} minutes")
    
    passed, total = generate_summary(results)
    results['score'] = {'passed': passed, 'total': total}

    out = write_results(
        output_name, results,
        brain=brain, door_client=door_client,
        duration_ms=TRIAL_DURATION_MS, seed=seed,
        suite='run_all_validations', n_benchmarks=total,
        elapsed_minutes=elapsed,
    )
    logger.info(f"\nResults saved to {out}")
    return results

def validate_temporal_dynamics(brain, door_client, test_odors):
    """Temporal dynamics: onset, peak, adaptation."""
    results = {}
    
    for odor_name in test_odors:
        logger.info(f"  Testing {odor_name}...")
        
        brain.reset(deterministic=True)
        glom_pattern = door_client.get_glomerular_pattern(odor_name)
        
        if glom_pattern is None or np.sum(np.abs(glom_pattern)) == 0:
            continue
        
        brain.inject_odor(glom_pattern, strength=50.0)
        
        # Sample at t=0, 50ms, 100ms, 500ms, 1s, 2s
        timepoints = [0, 50, 100, 500, 1000, 2000]
        activities = []
        
        for t_ms in timepoints:
            if t_ms > 0:
                brain.evolve(duration=t_ms - (timepoints[timepoints.index(t_ms)-1] if t_ms > 0 else 0))
            kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
            activities.append(float(np.mean(kc_activity)))
        
        # Compute metrics
        peak_idx = np.argmax(activities)
        peak_time_ms = timepoints[peak_idx]
        # Fast adaptation: measure from peak to 500ms (Nagel & Wilson 2011)
        # activities[3] is 500ms timepoint
        if activities[peak_idx] > 0 and peak_idx < 3:
            adaptation_percent = 100 * (activities[peak_idx] - activities[3]) / activities[peak_idx]
        else:
            adaptation_percent = 0.0
        
        results[odor_name] = {
            'peak_time_ms': int(peak_time_ms),
            'adaptation_percent': float(adaptation_percent),
            'activities': [float(a) for a in activities]
        }
        
        logger.info(f"    Peak: {peak_time_ms}ms, Adaptation: {adaptation_percent:.1f}%")
    
    # Summary
    peak_times = [r['peak_time_ms'] for r in results.values()]
    adaptations = [r['adaptation_percent'] for r in results.values()]
    
    summary = {
        'peak_time_mean_ms': float(np.mean(peak_times)),
        'adaptation_mean_percent': float(np.mean(adaptations)),
        'validation': 'PASS' if 50 <= np.mean(peak_times) <= 150 and 30 <= np.mean(adaptations) <= 70 else 'FAIL'
    }
    
    return {'odors': results, 'summary': summary}

def validate_odor_mixtures(brain, door_client, test_odors):
    """Odor mixtures: binary blends."""
    results = {}
    
    # Get individual responses
    individual = {}
    for odor in test_odors:
        brain.reset(deterministic=True)
        glom_pattern = door_client.get_glomerular_pattern(odor)
        if glom_pattern is None:
            continue
        brain.inject_odor(glom_pattern, strength=50.0)
        brain.evolve(duration=100.0)
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        individual[odor] = set(np.where(get_active_kc_binary(kc_activity) > 0)[0].tolist())
    
    # Test binary mixture
    if len(test_odors) >= 2:
        brain.reset(deterministic=True)
        mix_pattern = (door_client.get_glomerular_pattern(test_odors[0]) + 
                       door_client.get_glomerular_pattern(test_odors[1])) / 2
        brain.inject_odor(mix_pattern, strength=50.0)
        brain.evolve(duration=100.0)
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        mixture_kcs = set(np.where(get_active_kc_binary(kc_activity) > 0)[0].tolist())
        
        # Compute overlap
        overlap_1 = len(mixture_kcs & individual[test_odors[0]]) / len(individual[test_odors[0]]) if len(individual[test_odors[0]]) > 0 else 0
        overlap_2 = len(mixture_kcs & individual[test_odors[1]]) / len(individual[test_odors[1]]) if len(individual[test_odors[1]]) > 0 else 0
        mean_overlap = (overlap_1 + overlap_2) / 2 * 100
        
        results['binary_mixture'] = {
            'odors': test_odors[:2],
            'overlap_percent': float(mean_overlap)
        }
        
        logger.info(f"  Binary mixture overlap: {mean_overlap:.1f}%")
        
        summary = {
            'mean_overlap_percent': float(mean_overlap),
            'validation': 'PASS' if 30 <= mean_overlap <= 50 else 'FAIL'
        }
    else:
        summary = {'validation': 'FAIL'}
    
    return {'mixtures': results, 'summary': summary}

def validate_discrimination(brain, door_client, test_odors):
    """
    Discrimination thresholds via concentration sweep.

    Tests 5 concentration deltas (5%, 10%, 15%, 20%, 25%) for each odor.
    Finds the actual Just Noticeable Difference (JND): the smallest delta
    at which KC patterns are reliably distinct (Pearson r < 0.9).

    Biological target (Weber's law for olfaction):
        JND = 10-20% concentration change (Bodyak & Bhatt 2001; Wilson 2003)
    """
    results = {}
    # Sweep of concentration deltas to test (percent increase over reference)
    DELTA_PERCENTS = [5, 10, 15, 20, 25]
    DISCRIMINATION_THRESHOLD = 0.9  # KC correlation below this = discriminable
    REFERENCE_STRENGTH = 50.0

    for odor in test_odors[:2]:
        glom_pattern = door_client.get_glomerular_pattern(odor)
        if glom_pattern is None:
            continue

        # Reference response
        brain.reset(deterministic=True)
        brain.inject_odor(glom_pattern, strength=REFERENCE_STRENGTH)
        brain.evolve(duration=100.0)
        ref_kc = get_active_kc_binary(
            brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        )

        # Sweep each delta concentration
        delta_results = {}
        jnd_percent = None
        for delta_pct in DELTA_PERCENTS:
            brain.reset(deterministic=True)
            brain.inject_odor(glom_pattern, strength=REFERENCE_STRENGTH * (1 + delta_pct / 100.0))
            brain.evolve(duration=100.0)
            test_kc = get_active_kc_binary(
                brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
            )

            if np.std(ref_kc) > 0 and np.std(test_kc) > 0:
                corr = float(np.corrcoef(ref_kc, test_kc)[0, 1])
            else:
                corr = 1.0

            discriminable = corr < DISCRIMINATION_THRESHOLD
            delta_results[delta_pct] = {
                'correlation': corr,
                'discriminable': bool(discriminable),
            }

            # First delta where discrimination succeeds = JND
            if discriminable and jnd_percent is None:
                jnd_percent = delta_pct

            logger.info(f"  {odor} +{delta_pct}%: r={corr:.3f}, discriminable={discriminable}")

        results[odor] = {
            'jnd_percent': jnd_percent,
            'delta_sweep': delta_results,
        }
        logger.info(f"  {odor}: JND = {jnd_percent}%")

    # Pass if all tested odors have JND within biological target 10-20%
    jnds = [r['jnd_percent'] for r in results.values() if r['jnd_percent'] is not None]
    all_pass = len(jnds) > 0 and all(10 <= j <= 20 for j in jnds)

    summary = {
        'jnd_per_odor': {odor: r['jnd_percent'] for odor, r in results.items()},
        'mean_jnd_percent': float(np.mean(jnds)) if jnds else None,
        'validation': 'PASS' if all_pass else 'FAIL',
        'biological_target': '10-20% (Weber\'s law, Bodyak & Bhatt 2001)',
    }

    return {'odors': results, 'summary': summary}

def validate_similarity(brain, door_client, test_odors):
    """Odor similarity structure."""
    glom_patterns = {}
    kc_responses = {}
    
    for odor in test_odors:
        glom_pattern = door_client.get_glomerular_pattern(odor)
        if glom_pattern is None:
            continue
        glom_patterns[odor] = glom_pattern
        
        brain.reset(deterministic=True)
        brain.inject_odor(glom_pattern, strength=50.0)
        brain.evolve(duration=100.0)
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        kc_responses[odor] = get_active_kc_binary(kc_activity)
    
    # Compute pairwise similarities
    chem_sims = []
    neural_sims = []
    
    for i, odor1 in enumerate(test_odors):
        for odor2 in test_odors[i+1:]:
            if odor1 in glom_patterns and odor2 in glom_patterns:
                # Chemical similarity
                chem_sim = np.corrcoef(glom_patterns[odor1], glom_patterns[odor2])[0, 1]
                # Neural similarity
                neural_sim = np.corrcoef(kc_responses[odor1], kc_responses[odor2])[0, 1]
                chem_sims.append(chem_sim)
                neural_sims.append(neural_sim)
    
    # Correlation between chemical and neural similarity
    if len(chem_sims) > 0:
        chem_neural_corr = np.corrcoef(chem_sims, neural_sims)[0, 1]
    else:
        chem_neural_corr = 0
    
    logger.info(f"  Chem-neural correlation: r={chem_neural_corr:.3f}")
    
    summary = {
        'chem_neural_correlation': float(chem_neural_corr),
        'validation': 'PASS' if 0.3 <= chem_neural_corr <= 0.5 else 'FAIL'
    }
    
    return {'summary': summary}

def _apply_hebbian_stdp(brain, learning_rate: float = 0.05):
    """
    Apply one step of Hebbian STDP to synapse weights.

    Rule: Δw_ij = η × A_i × A_j × cos(φ_i - φ_j)

    - A_i, A_j  : mean amplitudes of pre / post neurons
    - φ_i - φ_j : phase difference encodes temporal order
      cos > 0 (pre leads post)  → LTP (potentiation)
      cos < 0 (post leads pre)  → LTD (depression)

    This is the wave-field equivalent of STDP:
    neurons phase-locked to each other strengthen their synapses
    (Bi & Poo 1998; Song et al. 2000).

    Weights are clipped to [0, 1] and re-normalised after each update
    to prevent runaway potentiation.
    """
    import numpy as _np

    # Pull current state to numpy (handle both MLX and NumPy backends)
    if hasattr(brain, 'use_mlx') and brain.use_mlx:
        import mlx.core as _mx
        amp  = _np.array(brain.mean_amplitude.tolist())
        phase = _np.array(brain.mean_phase.tolist())
        w     = _np.array(brain.syn_weights.tolist())
    else:
        amp   = _np.asarray(brain.mean_amplitude, dtype=_np.float32)
        phase = _np.asarray(brain.mean_phase,     dtype=_np.float32)
        w     = _np.asarray(brain.syn_weights,    dtype=_np.float32)

    pre_idx  = brain.pre_indices   # int32 numpy arrays always
    post_idx = brain.post_indices

    amp_pre   = amp[pre_idx]
    amp_post  = amp[post_idx]
    phase_pre = phase[pre_idx]
    phase_post= phase[post_idx]

    delta_w = learning_rate * amp_pre * amp_post * _np.cos(phase_pre - phase_post)
    w = w + delta_w

    # Keep weights non-negative and normalised
    _np.clip(w, 0.0, None, out=w)
    max_w = _np.max(w)
    if max_w > 0:
        w /= max_w

    # Write back
    if hasattr(brain, 'use_mlx') and brain.use_mlx:
        import mlx.core as _mx
        brain.syn_weights = _mx.array(w)
    else:
        brain.syn_weights = w.astype(_np.float32)


def validate_learning(brain, door_client, odor):
    """
    Learning & plasticity via Hebbian STDP.

    Protocol:
      1. Measure baseline MBON response (pre-training).
      2. Run N_TRIALS training episodes:
           inject odor → evolve 100 ms → apply Hebbian STDP weight update.
      3. Measure post-training MBON response.
      4. Pass if MBON response changed by at least MIN_CHANGE_PCT.

    Biological basis:
      Mushroom-body learning (Aso et al. 2014): repeated odor presentation
      paired with reinforcement modifies KC→MBON synapses.  Hebbian
      co-activation (Bi & Poo 1998) is the underlying cellular rule.
      Even without explicit dopamine, repeated odor exposure produces
      detectable plasticity in MBON activity (Hige et al. 2015).

    Pass criterion:
      |MBON_post - MBON_pre| / (|MBON_pre| + ε) ≥ 1% change —
      demonstrates that weight updates propagate to measurable output change.
    """
    N_TRIALS = 5
    LEARNING_RATE = 0.05
    MIN_CHANGE_PCT = 1.0   # 1% minimum response change to count as learning
    REFERENCE_STRENGTH = 50.0

    logger.info(f"  Testing plasticity with {odor} ({N_TRIALS} training trials)...")

    glom_pattern = door_client.get_glomerular_pattern(odor)
    if glom_pattern is None:
        return {'summary': {'validation': 'FAIL'}}

    # --- Pre-training baseline ---
    brain.reset(deterministic=True)
    brain.inject_odor(glom_pattern, strength=REFERENCE_STRENGTH)
    brain.evolve(duration=100.0)
    mbon_pre = float(np.mean(brain.get_region_activity('MBON')))
    kc_pre   = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    kc_pre_active = int(np.sum(get_active_kc_binary(kc_pre)))
    logger.info(f"    Pre-training  MBON={mbon_pre:.4f}, active KCs={kc_pre_active}")

    # --- Training loop ---
    weight_changes = []
    for trial in range(N_TRIALS):
        brain.reset(deterministic=True)
        brain.inject_odor(glom_pattern, strength=REFERENCE_STRENGTH)
        brain.evolve(duration=100.0)

        # Save old weights for monitoring
        if hasattr(brain, 'use_mlx') and brain.use_mlx:
            w_before = np.array(brain.syn_weights.tolist())
        else:
            w_before = np.asarray(brain.syn_weights).copy()

        _apply_hebbian_stdp(brain, learning_rate=LEARNING_RATE)

        if hasattr(brain, 'use_mlx') and brain.use_mlx:
            w_after = np.array(brain.syn_weights.tolist())
        else:
            w_after = np.asarray(brain.syn_weights).copy()

        mean_dw = float(np.mean(np.abs(w_after - w_before)))
        weight_changes.append(mean_dw)
        logger.info(f"    Trial {trial+1}/{N_TRIALS}: mean |Δw|={mean_dw:.6f}")

    # --- Post-training response (with updated weights; no reset to keep weights) ---
    brain.reset(deterministic=True)  # reset activity but weights stay modified above
    brain.inject_odor(glom_pattern, strength=REFERENCE_STRENGTH)
    brain.evolve(duration=100.0)
    mbon_post = float(np.mean(brain.get_region_activity('MBON')))
    kc_post   = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    kc_post_active = int(np.sum(get_active_kc_binary(kc_post)))
    logger.info(f"    Post-training MBON={mbon_post:.4f}, active KCs={kc_post_active}")

    change_pct = 100.0 * abs(mbon_post - mbon_pre) / (abs(mbon_pre) + 1e-8)
    logger.info(f"    MBON change: {change_pct:.2f}% (target ≥{MIN_CHANGE_PCT}%)")

    passed = change_pct >= MIN_CHANGE_PCT

    summary = {
        'mbon_pre':           mbon_pre,
        'mbon_post':          mbon_post,
        'mbon_change_pct':    change_pct,
        'kc_active_pre':      kc_pre_active,
        'kc_active_post':     kc_post_active,
        'mean_weight_change': float(np.mean(weight_changes)),
        'n_training_trials':  N_TRIALS,
        'validation':         'PASS' if passed else 'FAIL',
        'biological_ref':     'Bi & Poo 1998; Aso et al. 2014; Hige et al. 2015',
    }

    return {'summary': summary}

def generate_summary(results):
    """Print validation summary."""
    logger.info("\n" + "="*70)
    logger.info("BIOLOGICAL VALIDATION SUMMARY")
    logger.info("="*70)
    
    validations = results['validations']
    
    for val_name, val_data in validations.items():
        status = val_data['summary']['validation']
        symbol = "✅" if status == "PASS" else "❌"
        logger.info(f"{symbol} {val_name}: {status}")
    
    total = len(validations)
    passed = sum(1 for v in validations.values() if v['summary']['validation'] == 'PASS')
    
    logger.info(f"\nOverall: {passed}/{total} validations passed")
    return passed, total


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the 5-benchmark validation suite.')
    parser.add_argument('--use-mlx', action='store_true',
                        help='run on the MLX GPU backend (not reproducible)')
    parser.add_argument('--allow-mlx-result', action='store_true',
                        help='permit writing a result file from an MLX run')
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--output', default='all_validations_results.json',
                        help='filename under results/final/')
    parser.add_argument('--projection', default='sklearn_pca',
                        choices=['sklearn_pca', 'uncentered_svd'],
                        help='receptor->glomerular projection to use')
    args = parser.parse_args()

    run_all_validations(
        use_mlx=args.use_mlx,
        seed=args.seed,
        output_name=args.output,
        allow_mlx_result=args.allow_mlx_result,
        projection=args.projection,
    )
