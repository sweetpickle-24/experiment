#!/usr/bin/env python3
"""
FIX: Odor Similarity Structure Validation
==========================================

The previous test failed with r=-0.99 because we only tested 3 odors (3 pairs).
This retest uses 7 diverse odors for robust correlation estimate.

Biological Target: r ≈ 0.3-0.5 (Bhandawat et al. 2007)
"""

import sys
import numpy as np
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import init_olfactory_brain, results_path, log_path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path('similarity_retest.log')),
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

def main():
    logger.info("="*70)
    logger.info("SIMILARITY STRUCTURE RETEST (7 odors)")
    logger.info("="*70)
    
    # Initialize
    logger.info("\nInitializing system...")
    brain, door_client, connectome = init_olfactory_brain(use_mlx=True)
    logger.info(f"✅ Ready: {brain.num_neurons} neurons")
    
    # Test with 7 diverse odors
    test_odors = [
        'benzaldehyde',
        '2-heptanone', 
        'geosmin',
        '1-hexanol',
        'E2-hexenal',
        'ethyl acetate',
        'methyl salicylate'
    ]
    
    logger.info(f"\nTesting {len(test_odors)} odors for {len(test_odors)*(len(test_odors)-1)//2} pairs")
    
    # Measure all responses
    glom_patterns = {}
    kc_responses = {}
    
    for odor in test_odors:
        logger.info(f"  Measuring {odor}...")
        
        glom_pattern = door_client.get_glomerular_pattern(odor)
        if glom_pattern is None or np.sum(np.abs(glom_pattern)) == 0:
            logger.warning(f"    Skipping {odor} (zero pattern)")
            continue
        
        glom_patterns[odor] = glom_pattern
        
        brain.reset(deterministic=True)
        brain.inject_odor(glom_pattern, strength=50.0)
        brain.evolve(duration=100.0)
        
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        kc_responses[odor] = get_active_kc_binary(kc_activity)
        
        num_active = np.sum(kc_responses[odor] > 0)
        logger.info(f"    Active KCs: {num_active}")
    
    # Compute pairwise similarities
    logger.info(f"\nComputing pairwise similarities...")
    
    chem_sims = []
    neural_sims = []
    pairs = []
    
    valid_odors = list(glom_patterns.keys())
    
    for i, odor1 in enumerate(valid_odors):
        for odor2 in valid_odors[i+1:]:
            # Chemical similarity (glomerular correlation)
            if np.std(glom_patterns[odor1]) > 0 and np.std(glom_patterns[odor2]) > 0:
                chem_sim = np.corrcoef(glom_patterns[odor1], glom_patterns[odor2])[0, 1]
            else:
                continue
            
            # Neural similarity (KC correlation)
            if np.std(kc_responses[odor1]) > 0 and np.std(kc_responses[odor2]) > 0:
                neural_sim = np.corrcoef(kc_responses[odor1], kc_responses[odor2])[0, 1]
            else:
                continue
            
            chem_sims.append(chem_sim)
            neural_sims.append(neural_sim)
            pairs.append((odor1, odor2))
            
            logger.info(f"  {odor1} vs {odor2}: chem={chem_sim:.3f}, neural={neural_sim:.3f}")
    
    # Compute correlation between chemical and neural similarity
    logger.info(f"\n{'='*70}")
    logger.info("RESULTS")
    logger.info(f"{'='*70}")
    
    if len(chem_sims) > 2:
        if np.std(chem_sims) > 0 and np.std(neural_sims) > 0:
            chem_neural_corr = np.corrcoef(chem_sims, neural_sims)[0, 1]
        else:
            chem_neural_corr = 0
        
        logger.info(f"\n📊 Chemical vs Neural Similarity:")
        logger.info(f"   Number of pairs: {len(pairs)}")
        logger.info(f"   Correlation: r = {chem_neural_corr:.3f}")
        logger.info(f"   Target: r ≈ [0.3, 0.5]")
        
        logger.info(f"\n📊 Chemical Similarity Distribution:")
        logger.info(f"   Mean: {np.mean(chem_sims):.3f}")
        logger.info(f"   Std: {np.std(chem_sims):.3f}")
        logger.info(f"   Range: [{np.min(chem_sims):.3f}, {np.max(chem_sims):.3f}]")
        
        logger.info(f"\n📊 Neural Similarity Distribution:")
        logger.info(f"   Mean: {np.mean(neural_sims):.3f}")
        logger.info(f"   Std: {np.std(neural_sims):.3f}")
        logger.info(f"   Range: [{np.min(neural_sims):.3f}, {np.max(neural_sims):.3f}]")
        
        # Validation
        passed = 0.3 <= chem_neural_corr <= 0.5
        logger.info(f"\n🎯 Validation: {'✅ PASS' if passed else '❌ FAIL'}")
        
        # Save results
        results = {
            'experiment': 'odor_similarity_retest',
            'num_odors': len(valid_odors),
            'num_pairs': len(pairs),
            'pairs_tested': [{'odor1': p[0], 'odor2': p[1], 'chem_sim': float(cs), 'neural_sim': float(ns)} 
                            for p, cs, ns in zip(pairs, chem_sims, neural_sims)],
            'summary': {
                'chem_neural_correlation': float(chem_neural_corr),
                'chemical_similarity': {
                    'mean': float(np.mean(chem_sims)),
                    'std': float(np.std(chem_sims)),
                    'range': [float(np.min(chem_sims)), float(np.max(chem_sims))]
                },
                'neural_similarity': {
                    'mean': float(np.mean(neural_sims)),
                    'std': float(np.std(neural_sims)),
                    'range': [float(np.min(neural_sims)), float(np.max(neural_sims))]
                },
                'validation': 'PASS' if passed else 'FAIL',
                'biological_benchmark': 'Bhandawat et al. 2007: r ≈ 0.3-0.5'
            }
        }
        
        with open(results_path('similarity_retest_results.json', 'superseded'), 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n✅ Results saved to similarity_retest_results.json")
    else:
        logger.error("Not enough valid pairs for correlation")
    
    logger.info(f"\n{'='*70}")
    logger.info("SIMILARITY RETEST COMPLETE")
    logger.info(f"{'='*70}")

if __name__ == '__main__':
    main()
