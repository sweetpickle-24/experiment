#!/usr/bin/env python3
"""
Discrimination Threshold Validation
====================================

Validates concentration discrimination following Weber's law:
- Minimum concentration difference detectable: ~10-20% (Borst & Heisenberg 1982)
- Weber's law: ΔC/C ≈ 0.15
- Psychophysical just-noticeable-difference (JND)

Biological Benchmark:
    Borst & Heisenberg (1982) "Osmotropotaxis in Drosophila melanogaster"
    Semmelhack & Wang (2009) "Select Drosophila glomeruli mediate innate olfactory attraction"
"""

import sys
import numpy as np
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import results_path, log_path, write_results
from legacy_validation_support import (
    build_brain, inject, kc_mbon_weight_stats, resolve_odor_list,
)

from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.data.door_client import DoorClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path('discrimination_threshold_output.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

#: Same seed as scripts/run_all_validations.py so the two are comparable.
SEED = 42

def get_active_kc_binary(kc_activity, threshold_percentile=90):
    """Convert KC activity to binary active/inactive."""
    if len(kc_activity) == 0 or np.max(kc_activity) == 0:
        return np.zeros(len(kc_activity))
    threshold = np.percentile(kc_activity, threshold_percentile)
    return (kc_activity > threshold).astype(float)

def measure_concentration_response(brain, odor_name, concentration, door_client):
    """
    Measure KC response at specific concentration.
    
    Args:
        brain: SparseProbabilisticBrain instance
        odor_name: Odor name
        concentration: Relative concentration (1.0 = baseline)
        door_client: DoorClient for glomerular patterns
    
    Returns:
        KC activity vector
    """
    brain.reset(deterministic=True)
    
    glom_pattern = door_client.project_to_pca_basis(odor_name)
    if glom_pattern is None or np.sum(np.abs(glom_pattern)) == 0:
        return None
    
    # Apply logarithmic scaling (as in concentration invariance)
    base_strength = 50.0
    scaled_strength = base_strength * np.log10(1 + 10 * concentration)
    
    inject(brain, glom_pattern, strength=scaled_strength)
    brain.evolve(duration=100.0)
    
    kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    
    return kc_activity

def find_discrimination_threshold(brain, odor_name, door_client, base_concentration=1.0, correlation_threshold=0.9):
    """
    Find minimum concentration difference detectable (JND).
    
    Strategy: Start at base concentration, increase incrementally until
    correlation drops below threshold.
    
    Args:
        brain: SparseProbabilisticBrain instance
        odor_name: Odor to test
        door_client: DoorClient
        base_concentration: Reference concentration
        correlation_threshold: Correlation below which concentrations are "discriminable"
    
    Returns:
        dict with JND data
    """
    logger.info(f"Finding discrimination threshold for: {odor_name}")
    
    # Measure reference response
    ref_activity = measure_concentration_response(brain, odor_name, base_concentration, door_client)
    if ref_activity is None:
        logger.warning(f"Odor {odor_name} has zero pattern")
        return None
    
    ref_binary = get_active_kc_binary(ref_activity)
    
    # Test concentration increments
    test_increments = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.0]
    
    jnd_data = []
    jnd_found = None
    
    for increment in test_increments:
        test_concentration = base_concentration * (1 + increment)
        
        test_activity = measure_concentration_response(brain, odor_name, test_concentration, door_client)
        if test_activity is None:
            continue
        
        test_binary = get_active_kc_binary(test_activity)
        
        # Compute correlation
        if np.std(ref_binary) > 0 and np.std(test_binary) > 0:
            correlation = np.corrcoef(ref_binary, test_binary)[0, 1]
        else:
            correlation = 1.0
        
        discriminable = correlation < correlation_threshold
        
        logger.info(f"  Δ={increment*100:.0f}%: conc={test_concentration:.2f}, r={correlation:.3f}, discriminable={discriminable}")
        
        jnd_data.append({
            'concentration_increment_percent': float(increment * 100),
            'test_concentration': float(test_concentration),
            'correlation': float(correlation),
            'discriminable': bool(discriminable)
        })
        
        # Find JND (first discriminable difference)
        if discriminable and jnd_found is None:
            jnd_found = increment
    
    return {
        'odor': odor_name,
        'base_concentration': float(base_concentration),
        'correlation_threshold': float(correlation_threshold),
        'jnd_percent': float(jnd_found * 100) if jnd_found is not None else None,
        'jnd_data': jnd_data
    }

def main():
    logger.info("="*70)
    logger.info("DISCRIMINATION THRESHOLD VALIDATION")
    logger.info("="*70)
    
    # Build the engine exactly as scripts/run_all_validations.py does, so this
    # script's numbers are comparable with the suite's. The original code here
    # called SparseProbabilisticBrain(num_neurons=..., dt=0.01, use_mlx=True)
    # followed by brain.load_connectome_simple(synapses); the constructor takes
    # a connectome and has no num_neurons or dt keyword, and
    # load_connectome_simple has never existed, so this raised TypeError and
    # the script had never run. CPU because it writes reported numbers.
    logger.info("Building olfactory brain (CPU, seed %d)...", SEED)
    brain, door_client, connectome = build_brain(use_mlx=False, seed=SEED)
    neurons = connectome.neurons
    synapses = connectome.synapses
    logger.info(f"Extracted {len(neurons)} neurons, {len(synapses)} synapses")
    logger.info(f"Backend: {'MLX (GPU)' if brain.use_mlx else 'NumPy (CPU)'}")
    
    # 'geosmin' is not a key in the DoOR matrix. Before 2026-09-03 the lookup
    # returned a zero vector, and a zero pattern correlates with itself at
    # exactly 1.0 at every concentration, so it contributed a perfect score
    # without simulating anything. resolve_odor_list substitutes it with
    # isopentyl_acetate, the same substitution scripts/run_all_validations.py
    # makes, and records the substitution. See ODOR_AUDIT.md.
    test_odors, odor_report = resolve_odor_list(
        door_client, ['benzaldehyde', '2-heptanone', 'geosmin'], logger)
    
    results = {
        'experiment': 'discrimination_threshold',
        'description': 'Validation of concentration discrimination (Weber\'s law)',
        'biological_benchmarks': {
            'jnd_percent': [10, 20],
            'weber_fraction': 0.15
        },
        'brain_parameters': {
            'num_neurons': brain.num_neurons,
            'dt_ms': float(brain.dt),
            'backend': 'MLX' if brain.use_mlx else 'NumPy'
        },
        'test_parameters': {
            'base_concentration': 1.0,
            'correlation_threshold': 0.9
        },
        'discrimination_tests': []
    }
    
    # Test each odor
    for odor_name in test_odors:
        logger.info(f"\n{'='*70}")
        logger.info(f"Testing discrimination threshold: {odor_name}")
        logger.info(f"{'='*70}")
        
        jnd_data = find_discrimination_threshold(
            brain, odor_name, door_client,
            base_concentration=1.0,
            correlation_threshold=0.9
        )
        
        if jnd_data is not None:
            results['discrimination_tests'].append(jnd_data)
            
            if jnd_data['jnd_percent'] is not None:
                logger.info(f"\n📊 JND for {odor_name}: {jnd_data['jnd_percent']:.1f}%")
    
    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("SUMMARY - DISCRIMINATION THRESHOLDS")
    logger.info(f"{'='*70}")
    
    jnds = [test['jnd_percent'] for test in results['discrimination_tests'] if test['jnd_percent'] is not None]
    
    if jnds:
        logger.info(f"\n📊 Just-Noticeable-Difference (JND):")
        logger.info(f"   Mean: {np.mean(jnds):.1f}%")
        logger.info(f"   Range: [{np.min(jnds):.1f}, {np.max(jnds):.1f}]%")
        logger.info(f"   Target: [10, 20]%")
        logger.info(f"   Weber fraction: {np.mean(jnds)/100:.3f} (target: ~0.15)")
        logger.info(f"   Status: {'✅ PASS' if 10 <= np.mean(jnds) <= 20 else '❌ FAIL'}")
    else:
        logger.warning("No valid JND measurements")
    
    results['summary'] = {
        'jnd_percent': {
            'mean': float(np.mean(jnds)) if jnds else None,
            'std': float(np.std(jnds)) if jnds else None,
            'range': [float(np.min(jnds)), float(np.max(jnds))] if jnds else None
        },
        'weber_fraction': float(np.mean(jnds) / 100) if jnds else None,
        'biological_validation': {
            'jnd_in_range': 'PASS' if jnds and 10 <= np.mean(jnds) <= 20 else 'FAIL'
        }
    }
    
    # Save results
    # Written through write_results so the file lands under results/final/ and
    # carries its configuration block (seed, commit, backend, dt, projection,
    # glomerular mapping). It previously json.dump'd to a bare filename in the
    # working directory with no provenance at all.
    results['odor_resolution'] = odor_report
    output_file = write_results(
        'discrimination_threshold_results.json', results,
        brain=brain, door_client=door_client, seed=SEED,
        test='discrimination_threshold', duration_ms=100.0,
    )
    logger.info(f"\n✅ Results saved to {output_file}")
    
    logger.info("\n" + "="*70)
    logger.info("DISCRIMINATION THRESHOLD VALIDATION COMPLETE")
    logger.info("="*70)

if __name__ == '__main__':
    main()
