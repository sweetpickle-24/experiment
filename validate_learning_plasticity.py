#!/usr/bin/env python3
"""
Learning & Plasticity Validation
=================================

Validates Hebbian plasticity and associative learning:
- KC→MBON synapses strengthen with reward pairing (Hige et al. 2015)
- ~2-3× weight increase after 10-20 pairings
- Demonstrates classical conditioning

Biological Benchmark:
    Hige et al. (2015) "Heterosynaptic plasticity underlies aversive olfactory learning"
    Cohn et al. (2015) "Coordinated and compartmentalized neuromodulation shapes sensory processing"
"""

import sys
import numpy as np
import json
import logging
from pathlib import Path

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
        logging.FileHandler('learning_plasticity_output.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_kc_mbon_weights(brain, kc_indices, mbon_indices):
    """
    Extract KC→MBON connection weights.
    
    Args:
        brain: SparseProbabilisticBrain instance
        kc_indices: List of KC neuron indices
        mbon_indices: List of MBON neuron indices
    
    Returns:
        dict mapping (kc_idx, mbon_idx) -> weight
    """
    weights = {}
    
    # Get connectivity from brain's synapse list
    for syn in brain.synapses:
        pre_idx, post_idx, weight = syn
        if pre_idx in kc_indices and post_idx in mbon_indices:
            weights[(int(pre_idx), int(post_idx))] = float(weight)
    
    return weights

def apply_hebbian_update(brain, kc_activity, mbon_activity, learning_rate=0.01, reward_signal=1.0):
    """
    Apply Hebbian plasticity rule: Δw = η · A_pre · A_post · reward
    
    Args:
        brain: SparseProbabilisticBrain instance
        kc_activity: KC activity levels
        mbon_activity: MBON activity levels
        learning_rate: Learning rate η
        reward_signal: Reward/punishment signal (+1 or -1)
    
    Returns:
        Number of synapses updated
    """
    updated_count = 0
    
    # Update KC→MBON synapses
    for i, syn in enumerate(brain.synapses):
        pre_idx, post_idx, weight = syn
        
        # Check if this is KC→MBON synapse
        is_kc_to_mbon = False
        
        # Get neuron types (simplified check based on index ranges from full brain)
        # ORNs: 0-2278, PNs: 2279-4476, LNs: 4477-5197, KCs: 5198-10476, MBONs: typically in range 10477-10572
        if 5198 <= pre_idx <= 10476 and 10477 <= post_idx <= 10572:
            is_kc_to_mbon = True
        
        if is_kc_to_mbon:
            # Get activities
            pre_activity = kc_activity[pre_idx - 5198] if (pre_idx - 5198) < len(kc_activity) else 0
            post_activity = mbon_activity[post_idx - 10477] if (post_idx - 10477) < len(mbon_activity) else 0
            
            # Hebbian update
            delta_w = learning_rate * pre_activity * post_activity * reward_signal
            
            # Update weight
            new_weight = weight + delta_w
            
            # Constrain weights (prevent runaway growth)
            new_weight = np.clip(new_weight, -10.0, 10.0)
            
            brain.synapses[i] = (pre_idx, post_idx, new_weight)
            updated_count += 1
    
    # Reload connectivity into brain
    brain.load_connectome_simple(brain.synapses)
    
    return updated_count

def conditioning_experiment(brain, odor_name, door_client, num_trials=20, learning_rate=0.01):
    """
    Run classical conditioning: pair odor with reward.
    
    Args:
        brain: SparseProbabilisticBrain instance
        odor_name: Odor to condition
        door_client: DoorClient for glomerular patterns
        num_trials: Number of conditioning trials
        learning_rate: Hebbian learning rate
    
    Returns:
        dict with pre/post weights and MBON responses
    """
    logger.info(f"Conditioning experiment: {odor_name} + reward × {num_trials} trials")
    
    # Get glomerular pattern
    glom_pattern = door_client.project_to_pca_basis(odor_name)
    if glom_pattern is None or np.sum(np.abs(glom_pattern)) == 0:
        logger.warning(f"Odor {odor_name} has zero pattern")
        return None
    
    # Measure pre-conditioning response
    brain.reset(deterministic=True)
    base_strength = 50.0
    brain.inject_external_input('ORN', glom_pattern, strength=base_strength)
    brain.evolve(duration=100.0)
    
    kc_activity_pre = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    mbon_activity_pre = brain.get_region_activity('MBON')
    
    pre_mbon_mean = float(np.mean(mbon_activity_pre))
    pre_mbon_max = float(np.max(mbon_activity_pre))
    
    logger.info(f"  Pre-conditioning MBON: mean={pre_mbon_mean:.4f}, max={pre_mbon_max:.4f}")
    
    # Get initial KC→MBON weights (sample)
    kc_indices = list(range(5198, 10477))  # KC range in full brain
    mbon_indices = list(range(10477, 10573))  # MBON range
    
    weights_pre = get_kc_mbon_weights(brain, kc_indices, mbon_indices)
    initial_weight_mean = np.mean(list(weights_pre.values())) if weights_pre else 0
    
    logger.info(f"  Initial KC→MBON weights: {len(weights_pre)} synapses, mean={initial_weight_mean:.4f}")
    
    # Conditioning trials
    mbon_responses_during_training = []
    
    for trial in range(num_trials):
        # Reset brain
        brain.reset(deterministic=True)
        
        # Present odor
        brain.inject_external_input('ORN', glom_pattern, strength=base_strength)
        brain.evolve(duration=100.0)
        
        # Measure activity
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        mbon_activity = brain.get_region_activity('MBON')
        
        mbon_mean = float(np.mean(mbon_activity))
        mbon_responses_during_training.append(mbon_mean)
        
        # Apply Hebbian plasticity with reward
        reward_signal = 1.0
        num_updated = apply_hebbian_update(brain, kc_activity, mbon_activity, learning_rate, reward_signal)
        
        if trial % 5 == 0:
            logger.info(f"  Trial {trial+1}/{num_trials}: MBON={mbon_mean:.4f}, updated {num_updated} synapses")
    
    # Measure post-conditioning response
    brain.reset(deterministic=True)
    brain.inject_external_input('ORN', glom_pattern, strength=base_strength)
    brain.evolve(duration=100.0)
    
    kc_activity_post = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    mbon_activity_post = brain.get_region_activity('MBON')
    
    post_mbon_mean = float(np.mean(mbon_activity_post))
    post_mbon_max = float(np.max(mbon_activity_post))
    
    logger.info(f"  Post-conditioning MBON: mean={post_mbon_mean:.4f}, max={post_mbon_max:.4f}")
    
    # Get final weights
    weights_post = get_kc_mbon_weights(brain, kc_indices, mbon_indices)
    final_weight_mean = np.mean(list(weights_post.values())) if weights_post else 0
    
    weight_change = final_weight_mean / initial_weight_mean if initial_weight_mean != 0 else 1.0
    
    logger.info(f"  Final KC→MBON weights: mean={final_weight_mean:.4f} ({weight_change:.2f}× initial)")
    
    response_change = post_mbon_mean / pre_mbon_mean if pre_mbon_mean != 0 else 1.0
    
    logger.info(f"  MBON response change: {response_change:.2f}× initial")
    
    return {
        'odor': odor_name,
        'num_trials': num_trials,
        'learning_rate': learning_rate,
        'pre_conditioning': {
            'mbon_mean': pre_mbon_mean,
            'mbon_max': pre_mbon_max
        },
        'post_conditioning': {
            'mbon_mean': post_mbon_mean,
            'mbon_max': post_mbon_max
        },
        'mbon_response_change_factor': float(response_change),
        'initial_weight_mean': float(initial_weight_mean),
        'final_weight_mean': float(final_weight_mean),
        'weight_change_factor': float(weight_change),
        'num_kc_mbon_synapses': len(weights_pre),
        'training_curve': mbon_responses_during_training
    }

def main():
    logger.info("="*70)
    logger.info("LEARNING & PLASTICITY VALIDATION")
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
    test_odors = ['benzaldehyde', '2-heptanone']
    
    results = {
        'experiment': 'learning_plasticity',
        'description': 'Validation of Hebbian plasticity and associative learning',
        'biological_benchmarks': {
            'weight_increase_factor': [2.0, 3.0],
            'num_trials': 10-20,
            'response_enhancement': True
        },
        'brain_parameters': {
            'num_neurons': brain.num_neurons,
            'dt_ms': float(brain.dt),
            'backend': 'MLX' if brain.use_mlx else 'NumPy'
        },
        'conditioning_experiments': []
    }
    
    # Run conditioning experiments
    for odor_name in test_odors:
        logger.info(f"\n{'='*70}")
        logger.info(f"Testing learning with: {odor_name}")
        logger.info(f"{'='*70}")
        
        conditioning_data = conditioning_experiment(
            brain, odor_name, door_client,
            num_trials=20,
            learning_rate=0.01
        )
        
        if conditioning_data is not None:
            results['conditioning_experiments'].append(conditioning_data)
    
    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("SUMMARY - LEARNING & PLASTICITY")
    logger.info(f"{'='*70}")
    
    weight_changes = [exp['weight_change_factor'] for exp in results['conditioning_experiments']]
    response_changes = [exp['mbon_response_change_factor'] for exp in results['conditioning_experiments']]
    
    if weight_changes:
        logger.info(f"\n📊 Weight Change (KC→MBON):")
        logger.info(f"   Mean: {np.mean(weight_changes):.2f}×")
        logger.info(f"   Range: [{np.min(weight_changes):.2f}, {np.max(weight_changes):.2f}]×")
        logger.info(f"   Target: [2.0, 3.0]×")
        logger.info(f"   Status: {'✅ PASS' if 2.0 <= np.mean(weight_changes) <= 3.0 else '❌ FAIL'}")
        
        logger.info(f"\n📊 MBON Response Change:")
        logger.info(f"   Mean: {np.mean(response_changes):.2f}×")
        logger.info(f"   Range: [{np.min(response_changes):.2f}, {np.max(response_changes):.2f}]×")
        logger.info(f"   Status: {'✅ PASS' if np.mean(response_changes) > 1.0 else '❌ FAIL'}")
    
    results['summary'] = {
        'weight_change_factor': {
            'mean': float(np.mean(weight_changes)) if weight_changes else None,
            'std': float(np.std(weight_changes)) if weight_changes else None,
            'range': [float(np.min(weight_changes)), float(np.max(weight_changes))] if weight_changes else None
        },
        'response_change_factor': {
            'mean': float(np.mean(response_changes)) if response_changes else None,
            'std': float(np.std(response_changes)) if response_changes else None,
            'range': [float(np.min(response_changes)), float(np.max(response_changes))] if response_changes else None
        },
        'biological_validation': {
            'weight_increase': 'PASS' if weight_changes and 2.0 <= np.mean(weight_changes) <= 3.0 else 'FAIL',
            'response_enhancement': 'PASS' if response_changes and np.mean(response_changes) > 1.0 else 'FAIL'
        }
    }
    
    # Save results
    output_file = 'learning_plasticity_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"\n✅ Results saved to {output_file}")
    
    logger.info("\n" + "="*70)
    logger.info("LEARNING & PLASTICITY VALIDATION COMPLETE")
    logger.info("="*70)

if __name__ == '__main__':
    main()
