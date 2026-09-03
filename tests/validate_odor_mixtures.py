#!/usr/bin/env python3
"""
Odor Mixture Validation
========================

Validates that binary/ternary odor mixtures produce realistic KC responses:
- Mixtures produce novel patterns (not simple addition)
- ~30-50% overlap with individual components (Stettler & Axel 2009)
- Synergistic and suppressive interactions possible

Biological Benchmark:
    Stettler & Axel (2009) "Representations of odor in the piriform cortex"
    Deisig et al. (2006) "Odour mixture processing in the honeybee"
"""

import sys
import numpy as np
import json
import logging
from pathlib import Path
from itertools import combinations

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import results_path, log_path

from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.data.door_client import DoorClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path('odor_mixtures_output.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_active_kc_set(kc_activity, threshold_percentile=90):
    """Get set of active KC indices above threshold."""
    if len(kc_activity) == 0 or np.max(kc_activity) == 0:
        return set()
    threshold = np.percentile(kc_activity, threshold_percentile)
    active_indices = np.where(kc_activity > threshold)[0]
    return set(active_indices.tolist())

def measure_mixture_response(brain, odor_names, door_client, mixture_ratios=None):
    """
    Measure KC response to odor mixture.
    
    Args:
        brain: SparseProbabilisticBrain instance
        odor_names: List of odor names in mixture
        door_client: DoorClient for glomerular patterns
        mixture_ratios: List of relative strengths (default: equal)
    
    Returns:
        dict with mixture response data
    """
    if mixture_ratios is None:
        mixture_ratios = [1.0] * len(odor_names)
    
    mixture_str = ' + '.join([f"{r:.1f}×{o}" for r, o in zip(mixture_ratios, odor_names)])
    logger.info(f"Testing mixture: {mixture_str}")
    
    # Reset brain
    brain.reset(deterministic=True)
    
    # Get glomerular patterns and mix them
    mixed_pattern = np.zeros(20)  # 20 PCA components
    valid_odors = []
    
    for odor_name, ratio in zip(odor_names, mixture_ratios):
        glom_pattern = door_client.project_to_pca_basis(odor_name)
        if glom_pattern is not None and np.sum(np.abs(glom_pattern)) > 0:
            mixed_pattern += ratio * glom_pattern
            valid_odors.append(odor_name)
        else:
            logger.warning(f"Odor {odor_name} has zero pattern, excluding from mixture")
    
    if len(valid_odors) == 0:
        logger.warning("No valid odors in mixture")
        return None
    
    # Normalize mixed pattern
    if np.sum(np.abs(mixed_pattern)) > 0:
        mixed_pattern = mixed_pattern / len(valid_odors)  # Average, not sum
    
    # Inject mixture
    base_strength = 50.0
    brain.inject_external_input('ORN', mixed_pattern, strength=base_strength)
    
    # Evolve brain
    duration_ms = 100.0
    brain.evolve(duration=duration_ms)
    
    # Measure KC response
    kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    
    active_kcs = get_active_kc_set(kc_activity)
    
    logger.info(f"  Mixture response: {len(active_kcs)} active KCs")
    
    return {
        'odors': valid_odors,
        'mixture_ratios': mixture_ratios[:len(valid_odors)],
        'kc_activity': kc_activity.tolist(),
        'active_kcs': list(active_kcs),
        'num_active_kcs': len(active_kcs),
        'mean_activity': float(np.mean(kc_activity)),
        'max_activity': float(np.max(kc_activity))
    }

def measure_component_responses(brain, odor_names, door_client):
    """Measure individual odor responses."""
    component_responses = {}
    
    for odor_name in odor_names:
        logger.info(f"Testing component: {odor_name}")
        
        brain.reset(deterministic=True)
        
        glom_pattern = door_client.project_to_pca_basis(odor_name)
        if glom_pattern is None or np.sum(np.abs(glom_pattern)) == 0:
            logger.warning(f"Odor {odor_name} has zero pattern, skipping")
            continue
        
        base_strength = 50.0
        brain.inject_external_input('ORN', glom_pattern, strength=base_strength)
        
        duration_ms = 100.0
        brain.evolve(duration=duration_ms)
        
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        active_kcs = get_active_kc_set(kc_activity)
        
        logger.info(f"  Component response: {len(active_kcs)} active KCs")
        
        component_responses[odor_name] = {
            'kc_activity': kc_activity.tolist(),
            'active_kcs': list(active_kcs),
            'num_active_kcs': len(active_kcs)
        }
    
    return component_responses

def analyze_mixture_interactions(mixture_response, component_responses):
    """
    Analyze how mixture compares to components.
    
    Returns:
        dict with overlap metrics, linearity, interaction type
    """
    mixture_kcs = set(mixture_response['active_kcs'])
    
    # Compute overlap with each component
    overlaps = {}
    for odor_name in mixture_response['odors']:
        if odor_name in component_responses:
            component_kcs = set(component_responses[odor_name]['active_kcs'])
            overlap = len(mixture_kcs & component_kcs)
            overlap_percent = 100 * overlap / len(component_kcs) if len(component_kcs) > 0 else 0
            overlaps[odor_name] = {
                'overlap_count': overlap,
                'overlap_percent': float(overlap_percent),
                'component_size': len(component_kcs)
            }
    
    # Compute expected linear sum
    all_component_kcs = set()
    for odor_name in mixture_response['odors']:
        if odor_name in component_responses:
            all_component_kcs |= set(component_responses[odor_name]['active_kcs'])
    
    expected_size = len(all_component_kcs)
    actual_size = len(mixture_kcs)
    
    # Determine interaction type
    if actual_size > expected_size * 1.2:
        interaction_type = "synergistic"
    elif actual_size < expected_size * 0.8:
        interaction_type = "suppressive"
    else:
        interaction_type = "near-linear"
    
    # Novel KCs (not in any component)
    novel_kcs = mixture_kcs - all_component_kcs
    novel_percent = 100 * len(novel_kcs) / len(mixture_kcs) if len(mixture_kcs) > 0 else 0
    
    return {
        'component_overlaps': overlaps,
        'expected_linear_size': int(expected_size),
        'actual_mixture_size': int(actual_size),
        'interaction_type': interaction_type,
        'novel_kcs': len(novel_kcs),
        'novel_percent': float(novel_percent),
        'linearity_ratio': float(actual_size / expected_size) if expected_size > 0 else 0
    }

def main():
    logger.info("="*70)
    logger.info("ODOR MIXTURE VALIDATION")
    logger.info("="*70)
    
    # Load connectome
    logger.info("Loading full brain connectome...")
    full_connectome = Connectome(data_dir="Fly Brain Female")
    full_connectome.load()
    logger.info(f"  Loaded {len(full_connectome.neurons)} total neurons")
    
    # Extract olfactory pathway
    logger.info("Extracting olfactory pathway...")
    connectome = extract_olfactory_pathway(full_connectome)
    neurons = connectome.neurons
    synapses = connectome.synapses
    logger.info(f"Extracted {len(neurons)} neurons, {len(synapses)} synapses")
    
    # Create brain
    logger.info("Creating sparse probabilistic brain...")
    brain = SparseProbabilisticBrain(
        num_neurons=len(neurons),
        dt=0.01,
        use_mlx=True
    )
    
    brain.load_connectome_simple(synapses)
    logger.info(f"Backend: {'MLX (GPU)' if brain.use_mlx else 'NumPy (CPU)'}")
    
    # Initialize DOoR client
    logger.info("Initializing DOoR database...")
    door_client = DoorClient()
    
    # Test odors
    test_odors = ['benzaldehyde', '2-heptanone', 'geosmin']
    
    results = {
        'experiment': 'odor_mixtures',
        'description': 'Validation of binary and ternary odor mixture responses',
        'biological_benchmarks': {
            'component_overlap_percent': [30, 50],
            'novel_kcs_expected': True,
            'nonlinear_interactions': True
        },
        'brain_parameters': {
            'num_neurons': brain.num_neurons,
            'dt_ms': float(brain.dt),
            'backend': 'MLX' if brain.use_mlx else 'NumPy'
        },
        'test_odors': test_odors,
        'component_responses': {},
        'binary_mixtures': [],
        'ternary_mixtures': []
    }
    
    # Measure individual component responses
    logger.info(f"\n{'='*70}")
    logger.info("MEASURING COMPONENT RESPONSES")
    logger.info(f"{'='*70}")
    results['component_responses'] = measure_component_responses(brain, test_odors, door_client)
    
    # Test binary mixtures
    logger.info(f"\n{'='*70}")
    logger.info("TESTING BINARY MIXTURES")
    logger.info(f"{'='*70}")
    
    for odor_pair in combinations(test_odors, 2):
        odor_pair = list(odor_pair)
        mixture_response = measure_mixture_response(brain, odor_pair, door_client)
        
        if mixture_response is None:
            continue
        
        analysis = analyze_mixture_interactions(mixture_response, results['component_responses'])
        
        logger.info(f"\n📊 Mixture Analysis: {' + '.join(odor_pair)}")
        logger.info(f"  Mixture KCs: {mixture_response['num_active_kcs']}")
        logger.info(f"  Expected (linear): {analysis['expected_linear_size']}")
        logger.info(f"  Interaction: {analysis['interaction_type']}")
        logger.info(f"  Novel KCs: {analysis['novel_kcs']} ({analysis['novel_percent']:.1f}%)")
        
        for odor_name, overlap_data in analysis['component_overlaps'].items():
            logger.info(f"  Overlap with {odor_name}: {overlap_data['overlap_percent']:.1f}%")
        
        results['binary_mixtures'].append({
            'mixture_response': mixture_response,
            'analysis': analysis
        })
    
    # Test ternary mixture
    logger.info(f"\n{'='*70}")
    logger.info("TESTING TERNARY MIXTURE")
    logger.info(f"{'='*70}")
    
    mixture_response = measure_mixture_response(brain, test_odors, door_client)
    if mixture_response is not None:
        analysis = analyze_mixture_interactions(mixture_response, results['component_responses'])
        
        logger.info(f"\n📊 Ternary Mixture Analysis: {' + '.join(test_odors)}")
        logger.info(f"  Mixture KCs: {mixture_response['num_active_kcs']}")
        logger.info(f"  Expected (linear): {analysis['expected_linear_size']}")
        logger.info(f"  Interaction: {analysis['interaction_type']}")
        logger.info(f"  Novel KCs: {analysis['novel_kcs']} ({analysis['novel_percent']:.1f}%)")
        
        results['ternary_mixtures'].append({
            'mixture_response': mixture_response,
            'analysis': analysis
        })
    
    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("SUMMARY - ODOR MIXTURES")
    logger.info(f"{'='*70}")
    
    all_overlaps = []
    for mix_data in results['binary_mixtures'] + results['ternary_mixtures']:
        for overlap_data in mix_data['analysis']['component_overlaps'].values():
            all_overlaps.append(overlap_data['overlap_percent'])
    
    if all_overlaps:
        logger.info(f"\n📊 Component Overlap:")
        logger.info(f"   Mean: {np.mean(all_overlaps):.1f}%")
        logger.info(f"   Range: [{np.min(all_overlaps):.1f}, {np.max(all_overlaps):.1f}]%")
        logger.info(f"   Target: [30, 50]%")
        logger.info(f"   Status: {'✅ PASS' if 30 <= np.mean(all_overlaps) <= 50 else '❌ FAIL'}")
    
    interaction_types = [mix_data['analysis']['interaction_type'] for mix_data in results['binary_mixtures'] + results['ternary_mixtures']]
    logger.info(f"\n📊 Interaction Types:")
    for itype in set(interaction_types):
        count = interaction_types.count(itype)
        logger.info(f"   {itype}: {count}/{len(interaction_types)}")
    
    results['summary'] = {
        'component_overlap_percent': {
            'mean': float(np.mean(all_overlaps)) if all_overlaps else None,
            'std': float(np.std(all_overlaps)) if all_overlaps else None,
            'range': [float(np.min(all_overlaps)), float(np.max(all_overlaps))] if all_overlaps else None
        },
        'interaction_types': {itype: interaction_types.count(itype) for itype in set(interaction_types)},
        'biological_validation': {
            'component_overlap': 'PASS' if all_overlaps and 30 <= np.mean(all_overlaps) <= 50 else 'FAIL',
            'nonlinear_interactions': 'PASS' if len(set(interaction_types) - {'near-linear'}) > 0 else 'FAIL'
        }
    }
    
    # Save results
    output_file = 'odor_mixtures_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"\n✅ Results saved to {output_file}")
    
    logger.info("\n" + "="*70)
    logger.info("ODOR MIXTURE VALIDATION COMPLETE")
    logger.info("="*70)

if __name__ == '__main__':
    main()
