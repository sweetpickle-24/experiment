#!/usr/bin/env python3
"""
Temporal Dynamics Validation
=============================

Validates that KC responses show realistic temporal evolution:
- Onset latency: ~50-100ms (Stopfer et al. 2003)
- Response duration: 200-500ms transient + sustained
- Adaptation: ~50% reduction over 1-2 seconds (Nagel & Wilson 2011)

Biological Benchmark:
    Stopfer et al. (2003) "Impaired odour discrimination on desynchronization"
    Nagel & Wilson (2011) "Biophysical mechanisms underlying olfactory receptor neuron dynamics"
"""

import sys
import numpy as np
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import log_path, write_results

from legacy_validation_support import build_brain, resolve_odor_list

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path('temporal_dynamics_output.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def measure_temporal_response(brain, odor_name, door_client, duration_ms=3000, sample_interval_ms=10):
    """
    Measure KC activity over time with odor injection.
    
    Args:
        brain: SparseProbabilisticBrain instance
        odor_name: Name of odor to test
        door_client: DoorClient for glomerular patterns
        duration_ms: Total simulation time (ms)
        sample_interval_ms: How often to sample KC activity
    
    Returns:
        dict with temporal dynamics data
    """
    logger.info(f"Testing temporal dynamics for: {odor_name}")
    
    # Reset brain deterministically
    brain.reset(deterministic=True)
    
    # Get glomerular pattern
    receptor_response = door_client.get_odorant_response(odor_name)
    glom_pattern = door_client.map_to_glomerular_pattern(receptor_response)
    
    if glom_pattern is None or np.sum(np.abs(glom_pattern)) == 0:
        logger.warning(f"Odor {odor_name} has zero glomerular pattern, skipping")
        return None
    
    # Inject odor at t=0
    base_strength = 50.0
    brain.inject_odor(glom_pattern, strength=base_strength)
    
    # Sample activity over time
    num_samples = int(duration_ms / sample_interval_ms)
    time_points = []
    kc_activity_over_time = []
    kc_active_counts = []
    kc_mean_activity = []
    
    for i in range(num_samples):
        # Evolve brain
        brain.evolve(duration=sample_interval_ms)
        
        # Measure KC activity
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        
        time_ms = (i + 1) * sample_interval_ms
        time_points.append(time_ms)
        kc_activity_over_time.append(kc_activity.copy())
        
        # Count active KCs (threshold at 10% of max)
        if len(kc_activity) > 0 and np.max(kc_activity) > 0:
            threshold = 0.1 * np.max(kc_activity)
            active_count = np.sum(kc_activity > threshold)
        else:
            active_count = 0
        
        kc_active_counts.append(int(active_count))
        kc_mean_activity.append(float(np.mean(kc_activity)))
        
        if i % 10 == 0:
            logger.info(f"  t={time_ms}ms: {active_count} active KCs, mean={np.mean(kc_activity):.4f}")
    
    return {
        'odor': odor_name,
        'time_points_ms': time_points,
        'kc_active_counts': kc_active_counts,
        'kc_mean_activity': kc_mean_activity,
        'sample_interval_ms': sample_interval_ms,
        'total_kcs': len(kc_activity_over_time[0]) if kc_activity_over_time else 0
    }

def analyze_temporal_dynamics(temporal_data):
    """
    Analyze temporal response properties.
    
    Returns:
        dict with onset latency, peak time, adaptation metrics
    """
    time_points = np.array(temporal_data['time_points_ms'])
    activity = np.array(temporal_data['kc_mean_activity'])
    active_counts = np.array(temporal_data['kc_active_counts'])
    
    # Find baseline (first 50ms)
    baseline_idx = np.where(time_points <= 50)[0]
    if len(baseline_idx) > 0:
        baseline_activity = np.mean(activity[baseline_idx])
        baseline_count = np.mean(active_counts[baseline_idx])
    else:
        baseline_activity = activity[0]
        baseline_count = active_counts[0]
    
    # Find onset latency (when activity rises above baseline + 2 std)
    threshold = baseline_activity + 2 * np.std(activity[baseline_idx]) if len(baseline_idx) > 1 else baseline_activity * 1.5
    onset_idx = np.where(activity > threshold)[0]
    onset_latency_ms = time_points[onset_idx[0]] if len(onset_idx) > 0 else None
    
    # Find peak response
    peak_idx = np.argmax(activity)
    peak_time_ms = time_points[peak_idx]
    peak_activity = activity[peak_idx]
    peak_count = active_counts[peak_idx]
    
    # Measure adaptation (compare activity at 1s vs 2s)
    idx_1s = np.argmin(np.abs(time_points - 1000))
    idx_2s = np.argmin(np.abs(time_points - 2000))
    
    activity_1s = activity[idx_1s]
    activity_2s = activity[idx_2s]
    
    if activity_1s > 0:
        adaptation_percent = 100 * (activity_1s - activity_2s) / activity_1s
    else:
        adaptation_percent = 0
    
    # Calculate sustained response (last 500ms average)
    sustained_idx = np.where(time_points >= time_points[-1] - 500)[0]
    sustained_activity = np.mean(activity[sustained_idx])
    sustained_count = np.mean(active_counts[sustained_idx])
    
    return {
        'onset_latency_ms': float(onset_latency_ms) if onset_latency_ms is not None else None,
        'peak_time_ms': float(peak_time_ms),
        'peak_activity': float(peak_activity),
        'peak_active_kcs': int(peak_count),
        'baseline_activity': float(baseline_activity),
        'baseline_active_kcs': float(baseline_count),
        'activity_at_1s': float(activity_1s),
        'activity_at_2s': float(activity_2s),
        'adaptation_percent': float(adaptation_percent),
        'sustained_activity': float(sustained_activity),
        'sustained_active_kcs': float(sustained_count)
    }

def main():
    logger.info("="*70)
    logger.info("TEMPORAL DYNAMICS VALIDATION")
    logger.info("="*70)
    
    # Built the way scripts/run_all_validations.py builds it, so the numbers are
    # comparable with the suite's. This script was the one of the five
    # standalones never brought onto legacy_validation_support: it constructed
    # the brain by hand with use_mlx=True, requested 'geosmin' (absent from the
    # DoOR matrix, which now raises), and wrote a bare JSON file into the current
    # working directory with no configuration block.
    logger.info("Building brain (CPU, seed 42, sklearn_pca, position mapping)...")
    brain, door_client, connectome = build_brain(use_mlx=False, seed=42)
    logger.info(f"Backend: {'MLX (GPU)' if brain.use_mlx else 'NumPy (CPU)'}")
    logger.info(f"Extracted {brain.num_neurons} neurons")

    requested_odors = ['benzaldehyde', '2-heptanone', 'geosmin']
    test_odors, odor_report = resolve_odor_list(door_client, requested_odors,
                                                logger=logger)
    
    results = {
        'experiment': 'temporal_dynamics',
        'description': 'Validation of temporal response properties',
        'biological_benchmarks': {
            'onset_latency_ms': [50, 100],
            'adaptation_percent': [30, 70],
            'peak_time_ms': [100, 500]
        },
        # See docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md: the bands above are
        # attributed to Stopfer et al. 2003 and Nagel & Wilson 2011, and neither
        # paper contains them. They are kept here unchanged so this script stays
        # comparable with its own history; the corrected criterion lives in
        # scripts/run_all_validations.py.
        'odorants_requested': requested_odors,
        'odorants_used': test_odors,
        'odorant_resolution': odor_report,
        'brain_parameters': {
            'num_neurons': brain.num_neurons,
            'dt_ms': float(brain.dt),
            'backend': 'MLX' if brain.use_mlx else 'NumPy'
        },
        'test_parameters': {
            'duration_ms': 3000,
            'sample_interval_ms': 10,
            'base_injection_strength': 50.0
        },
        'odor_responses': []
    }
    
    # Test each odor
    for odor_name in test_odors:
        logger.info(f"\n{'='*70}")
        logger.info(f"Testing odor: {odor_name}")
        logger.info(f"{'='*70}")
        
        temporal_data = measure_temporal_response(
            brain, odor_name, door_client,
            duration_ms=3000,
            sample_interval_ms=10
        )
        
        if temporal_data is None:
            continue
        
        # Analyze dynamics
        analysis = analyze_temporal_dynamics(temporal_data)
        
        logger.info(f"\n📊 Temporal Analysis for {odor_name}:")
        onset_str = f"{analysis['onset_latency_ms']:.1f} ms" if analysis['onset_latency_ms'] is not None else "N/A (no threshold crossing)"
        logger.info(f"  Onset latency: {onset_str} (target: 50-100 ms)")
        logger.info(f"  Peak time: {analysis['peak_time_ms']:.1f} ms (target: 100-500 ms)")
        logger.info(f"  Peak activity: {analysis['peak_active_kcs']} KCs")
        logger.info(f"  Adaptation (1s→2s): {analysis['adaptation_percent']:.1f}% (target: 30-70%)")
        logger.info(f"  Sustained response: {analysis['sustained_active_kcs']:.1f} KCs")
        
        # Store results
        results['odor_responses'].append({
            'odor': odor_name,
            'temporal_data': temporal_data,
            'analysis': analysis
        })
    
    # Summary statistics
    logger.info(f"\n{'='*70}")
    logger.info("SUMMARY - TEMPORAL DYNAMICS")
    logger.info(f"{'='*70}")
    
    onset_latencies = [r['analysis']['onset_latency_ms'] for r in results['odor_responses'] if r['analysis']['onset_latency_ms'] is not None]
    peak_times = [r['analysis']['peak_time_ms'] for r in results['odor_responses']]
    adaptations = [r['analysis']['adaptation_percent'] for r in results['odor_responses']]
    
    if onset_latencies:
        logger.info(f"\n📊 Onset Latency:")
        logger.info(f"   Mean: {np.mean(onset_latencies):.1f} ms")
        logger.info(f"   Range: [{np.min(onset_latencies):.1f}, {np.max(onset_latencies):.1f}] ms")
        logger.info(f"   Target: [50, 100] ms")
        logger.info(f"   Status: {'✅ PASS' if 50 <= np.mean(onset_latencies) <= 100 else '❌ FAIL'}")
    
    logger.info(f"\n📊 Peak Time:")
    logger.info(f"   Mean: {np.mean(peak_times):.1f} ms")
    logger.info(f"   Range: [{np.min(peak_times):.1f}, {np.max(peak_times):.1f}] ms")
    logger.info(f"   Target: [100, 500] ms")
    logger.info(f"   Status: {'✅ PASS' if 100 <= np.mean(peak_times) <= 500 else '❌ FAIL'}")
    
    logger.info(f"\n📊 Adaptation (1s→2s):")
    logger.info(f"   Mean: {np.mean(adaptations):.1f}%")
    logger.info(f"   Range: [{np.min(adaptations):.1f}, {np.max(adaptations):.1f}]%")
    logger.info(f"   Target: [30, 70]%")
    logger.info(f"   Status: {'✅ PASS' if 30 <= np.mean(adaptations) <= 70 else '❌ FAIL'}")
    
    # Validation summary
    results['summary'] = {
        'onset_latency_ms': {
            'mean': float(np.mean(onset_latencies)) if onset_latencies else None,
            'std': float(np.std(onset_latencies)) if onset_latencies else None,
            'range': [float(np.min(onset_latencies)), float(np.max(onset_latencies))] if onset_latencies else None
        },
        'peak_time_ms': {
            'mean': float(np.mean(peak_times)),
            'std': float(np.std(peak_times)),
            'range': [float(np.min(peak_times)), float(np.max(peak_times))]
        },
        'adaptation_percent': {
            'mean': float(np.mean(adaptations)),
            'std': float(np.std(adaptations)),
            'range': [float(np.min(adaptations)), float(np.max(adaptations))]
        },
        'biological_validation': {
            'onset_latency': 'PASS' if onset_latencies and 50 <= np.mean(onset_latencies) <= 100 else 'FAIL',
            'peak_time': 'PASS' if 100 <= np.mean(peak_times) <= 500 else 'FAIL',
            'adaptation': 'PASS' if 30 <= np.mean(adaptations) <= 70 else 'FAIL'
        }
    }
    
    # Written through write_results so the file carries seed, git commit, dt,
    # backend and projection path. It previously dumped a bare JSON into the
    # current working directory.
    output_file = write_results(
        'temporal_dynamics_standalone.json', results,
        brain=brain, door_client=door_client,
        duration_ms=3000.0, seed=42,
        suite='validate_temporal_dynamics_standalone',
    )
    logger.info(f"\n✅ Results saved to {output_file}")
    
    logger.info("\n" + "="*70)
    logger.info("TEMPORAL DYNAMICS VALIDATION COMPLETE")
    logger.info("="*70)

if __name__ == '__main__':
    main()
