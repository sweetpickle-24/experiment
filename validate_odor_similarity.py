#!/usr/bin/env python3
"""
Odor Similarity Structure Validation
=====================================

Validates that chemically similar odors produce similar KC patterns:
- Correlation between chemical similarity and neural similarity (Bhandawat et al. 2007)
- Expected r ≈ 0.3-0.5 (moderate correlation)
- Tests representational geometry

Biological Benchmark:
    Bhandawat et al. (2007) "Sensory processing in the Drosophila antennal lobe"
    Mathew et al. (2013) "Functional diversity among sensory receptors in a Drosophila olfactory circuit"
"""

import sys
import numpy as np
import json
import logging
from pathlib import Path
from itertools import combinations

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.data.door_client import DoorClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('odor_similarity_output.log'),
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

def measure_odor_response(brain, odor_name, door_client):
    """Measure KC response to odor."""
    brain.reset(deterministic=True)
    
    glom_pattern = door_client.project_to_pca_basis(odor_name)
    if glom_pattern is None or np.sum(np.abs(glom_pattern)) == 0:
        return None
    
    base_strength = 50.0
    brain.inject_external_input('ORN', glom_pattern, strength=base_strength)
    brain.evolve(duration=100.0)
    
    kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    
    return kc_activity

def compute_chemical_similarity(odor1_pattern, odor2_pattern):
    """
    Compute chemical similarity from glomerular patterns.
    
    Uses correlation of glomerular activation as proxy for chemical similarity.
    """
    if odor1_pattern is None or odor2_pattern is None:
        return None
    
    if np.std(odor1_pattern) == 0 or np.std(odor2_pattern) == 0:
        return None
    
    correlation = np.corrcoef(odor1_pattern, odor2_pattern)[0, 1]
    
    return float(correlation)

def compute_neural_similarity(kc1, kc2):
    """
    Compute neural similarity from KC patterns.
    
    Uses binary correlation.
    """
    if kc1 is None or kc2 is None:
        return None
    
    kc1_binary = get_active_kc_binary(kc1)
    kc2_binary = get_active_kc_binary(kc2)
    
    if np.std(kc1_binary) == 0 or np.std(kc2_binary) == 0:
        return None
    
    correlation = np.corrcoef(kc1_binary, kc2_binary)[0, 1]
    
    return float(correlation)

def main():
    logger.info("="*70)
    logger.info("ODOR SIMILARITY STRUCTURE VALIDATION")
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
    
    # Test odors (diverse set)
    test_odors = [
        'benzaldehyde',
        '2-heptanone',
        'geosmin',
        'ethyl acetate',
        'isoamyl acetate',
        '1-hexanol',
        'E2-hexenal'
    ]
    
    results = {
        'experiment': 'odor_similarity',
        'description': 'Validation of chemical vs neural similarity structure',
        'biological_benchmarks': {
            'chem_neural_correlation': [0.3, 0.5],
            'representational_geometry': 'preserved'
        },
        'brain_parameters': {
            'num_neurons': brain.num_neurons,
            'dt_ms': float(brain.dt),
            'backend': 'MLX' if brain.use_mlx else 'NumPy'
        },
        'test_odors': test_odors,
        'odor_responses': {},
        'pairwise_comparisons': []
    }
    
    # Measure all odor responses
    logger.info(f"\n{'='*70}")
    logger.info("MEASURING ODOR RESPONSES")
    logger.info(f"{'='*70}")
    
    glom_patterns = {}
    kc_responses = {}
    
    for odor_name in test_odors:
        logger.info(f"Testing: {odor_name}")
        
        glom_pattern = door_client.project_to_pca_basis(odor_name)
        kc_activity = measure_odor_response(brain, odor_name, door_client)
        
        if glom_pattern is not None and kc_activity is not None:
            glom_patterns[odor_name] = glom_pattern
            kc_responses[odor_name] = kc_activity
            
            num_active = np.sum(get_active_kc_binary(kc_activity))
            logger.info(f"  Active KCs: {num_active}")
            
            results['odor_responses'][odor_name] = {
                'glomerular_pattern': glom_pattern.tolist(),
                'num_active_kcs': int(num_active)
            }
    
    # Compute pairwise similarities
    logger.info(f"\n{'='*70}")
    logger.info("COMPUTING PAIRWISE SIMILARITIES")
    logger.info(f"{'='*70}")
    
    chemical_similarities = []
    neural_similarities = []
    
    for odor1, odor2 in combinations(test_odors, 2):
        if odor1 not in glom_patterns or odor2 not in glom_patterns:
            continue
        
        # Chemical similarity (glomerular correlation)
        chem_sim = compute_chemical_similarity(glom_patterns[odor1], glom_patterns[odor2])
        
        # Neural similarity (KC correlation)
        neural_sim = compute_neural_similarity(kc_responses[odor1], kc_responses[odor2])
        
        if chem_sim is not None and neural_sim is not None:
            logger.info(f"{odor1} vs {odor2}: chem={chem_sim:.3f}, neural={neural_sim:.3f}")
            
            chemical_similarities.append(chem_sim)
            neural_similarities.append(neural_sim)
            
            results['pairwise_comparisons'].append({
                'odor1': odor1,
                'odor2': odor2,
                'chemical_similarity': chem_sim,
                'neural_similarity': neural_sim
            })
    
    # Compute correlation between chemical and neural similarity
    logger.info(f"\n{'='*70}")
    logger.info("SUMMARY - ODOR SIMILARITY STRUCTURE")
    logger.info(f"{'='*70}")
    
    if len(chemical_similarities) > 0:
        # Correlation between chemical and neural similarity
        if np.std(chemical_similarities) > 0 and np.std(neural_similarities) > 0:
            chem_neural_correlation = np.corrcoef(chemical_similarities, neural_similarities)[0, 1]
        else:
            chem_neural_correlation = 0
        
        logger.info(f"\n📊 Chemical vs Neural Similarity:")
        logger.info(f"   Correlation: r = {chem_neural_correlation:.3f}")
        logger.info(f"   Target: r ≈ [0.3, 0.5]")
        logger.info(f"   Status: {'✅ PASS' if 0.3 <= chem_neural_correlation <= 0.5 else '❌ FAIL'}")
        
        logger.info(f"\n📊 Chemical Similarity Distribution:")
        logger.info(f"   Mean: {np.mean(chemical_similarities):.3f}")
        logger.info(f"   Range: [{np.min(chemical_similarities):.3f}, {np.max(chemical_similarities):.3f}]")
        
        logger.info(f"\n📊 Neural Similarity Distribution:")
        logger.info(f"   Mean: {np.mean(neural_similarities):.3f}")
        logger.info(f"   Range: [{np.min(neural_similarities):.3f}, {np.max(neural_similarities):.3f}]")
        
        results['summary'] = {
            'chem_neural_correlation': float(chem_neural_correlation),
            'chemical_similarity': {
                'mean': float(np.mean(chemical_similarities)),
                'std': float(np.std(chemical_similarities)),
                'range': [float(np.min(chemical_similarities)), float(np.max(chemical_similarities))]
            },
            'neural_similarity': {
                'mean': float(np.mean(neural_similarities)),
                'std': float(np.std(neural_similarities)),
                'range': [float(np.min(neural_similarities)), float(np.max(neural_similarities))]
            },
            'biological_validation': {
                'chem_neural_correlation': 'PASS' if 0.3 <= chem_neural_correlation <= 0.5 else 'FAIL'
            }
        }
    else:
        logger.warning("No valid pairwise comparisons")
        results['summary'] = {
            'chem_neural_correlation': None,
            'biological_validation': {
                'chem_neural_correlation': 'FAIL'
            }
        }
    
    # Save results
    output_file = 'odor_similarity_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"\n✅ Results saved to {output_file}")
    
    logger.info("\n" + "="*70)
    logger.info("ODOR SIMILARITY STRUCTURE VALIDATION COMPLETE")
    logger.info("="*70)

if __name__ == '__main__':
    main()
