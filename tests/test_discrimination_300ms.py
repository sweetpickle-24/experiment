#!/usr/bin/env python3
"""
Discrimination Test at 300ms - Testing Temporal Stabilization Hypothesis

Tests whether extending evolution from 100ms to 300ms allows chaotic
near-threshold KC dynamics to stabilize into consistent attractors,
reducing the non-monotonic correlations observed at 100ms.

Hypothesis:
- At 100ms: Chaotic transients, non-monotonic correlations
- At 300ms: Stable attractors, monotonic correlation decay with delta
- Expected JND: 10-20% (matching behavioral Weber's law)

Date: 2026-03-18
"""

import numpy as np
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import init_olfactory_brain, results_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_active_kc_binary(kc_activity, threshold_percentile=90):
    """Convert KC activity to binary (top 10% active)."""
    if len(kc_activity) == 0 or np.max(kc_activity) == 0:
        return np.zeros(len(kc_activity))
    threshold = np.percentile(kc_activity, threshold_percentile)
    return (kc_activity > threshold).astype(float)

def run_discrimination_300ms():
    """Run discrimination test with 300ms evolution time."""
    
    logger.info("="*70)
    logger.info("DISCRIMINATION TEST - 300ms EVOLUTION")
    logger.info("="*70)
    logger.info("Hypothesis: Longer time allows attractors to stabilize")
    logger.info("Expected: Monotonic correlation decay, JND = 10-20%")
    logger.info("")
    
    start_time = datetime.now()
    
    # Initialize system
    brain, door_client, _ = init_olfactory_brain(use_mlx=True)
    logger.info(f"✅ System ready: {brain.num_neurons} neurons, backend=MLX")
    logger.info("")
    
    test_odors = ['benzaldehyde', '2-heptanone']
    DELTA_PERCENTS = [5, 10, 15, 20, 25]
    REFERENCE_STRENGTH = 50.0
    DURATION_MS = 300.0  # ← KEY CHANGE: 300ms instead of 100ms
    
    results = {
        'timestamp': start_time.isoformat(),
        'duration_ms': DURATION_MS,
        'test_type': 'discrimination_300ms',
        'odors': {}
    }
    
    for odor in test_odors:
        logger.info(f"Testing {odor}...")
        glom_pattern = door_client.get_glomerular_pattern(odor)
        if glom_pattern is None:
            logger.warning(f"  Skipping {odor} (no pattern)")
            continue
        
        # Reference response at 300ms
        logger.info(f"  Reference (strength={REFERENCE_STRENGTH})...")
        brain.reset(deterministic=True)
        brain.inject_odor(glom_pattern, strength=REFERENCE_STRENGTH)
        brain.evolve(duration=DURATION_MS)
        ref_kc = get_active_kc_binary(
            brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        )
        ref_active = int(np.sum(ref_kc))
        logger.info(f"    Active KCs: {ref_active}/5279")
        
        # Sweep deltas
        delta_results = {}
        jnd_percent = None
        
        for delta_pct in DELTA_PERCENTS:
            strength = REFERENCE_STRENGTH * (1 + delta_pct / 100.0)
            logger.info(f"  Testing +{delta_pct}% (strength={strength:.2f})...")
            
            brain.reset(deterministic=True)
            brain.inject_odor(glom_pattern, strength=strength)
            brain.evolve(duration=DURATION_MS)
            test_kc = get_active_kc_binary(
                brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
            )
            test_active = int(np.sum(test_kc))
            
            if np.std(ref_kc) > 0 and np.std(test_kc) > 0:
                corr = float(np.corrcoef(ref_kc, test_kc)[0, 1])
            else:
                corr = 1.0
            
            discriminable = corr < 0.9
            delta_results[delta_pct] = {
                'correlation': corr,
                'discriminable': discriminable,
                'active_kcs': test_active
            }
            
            if discriminable and jnd_percent is None:
                jnd_percent = delta_pct
            
            logger.info(f"    r={corr:.3f}, active KCs={test_active}, discriminable={discriminable}")
        
        results['odors'][odor] = {
            'jnd_percent': jnd_percent,
            'ref_active_kcs': ref_active,
            'delta_sweep': delta_results
        }
        logger.info(f"  {odor}: JND = {jnd_percent}%")
        logger.info("")
    
    # Summary
    jnds = [r['jnd_percent'] for r in results['odors'].values() if r['jnd_percent'] is not None]
    all_pass = len(jnds) > 0 and all(10 <= j <= 20 for j in jnds)
    
    results['summary'] = {
        'jnd_per_odor': {odor: r['jnd_percent'] for odor, r in results['odors'].items()},
        'mean_jnd_percent': float(np.mean(jnds)) if jnds else None,
        'validation': 'PASS' if all_pass else 'FAIL',
        'biological_target': '10-20% (Weber\'s law)',
        'elapsed_seconds': (datetime.now() - start_time).total_seconds()
    }
    
    logger.info("="*70)
    logger.info("RESULTS SUMMARY")
    logger.info("="*70)
    for odor, data in results['odors'].items():
        logger.info(f"{odor}: JND = {data['jnd_percent']}%")
    logger.info(f"Mean JND: {results['summary']['mean_jnd_percent']}%")
    logger.info(f"Status: {results['summary']['validation']}")
    logger.info(f"Target: {results['summary']['biological_target']}")
    logger.info("")
    
    # Save results
    output_file = results_path('discrimination_300ms_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"✅ Results saved to {output_file}")
    
    return results

if __name__ == '__main__':
    run_discrimination_300ms()
