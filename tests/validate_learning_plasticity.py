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
        logging.FileHandler(log_path('learning_plasticity_output.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

#: Same seed as scripts/run_all_validations.py so the two are comparable.
SEED = 42

def get_kc_mbon_weights(brain, connectome):
    """
    Summarise KC→MBON connection weights.

    The original implementation iterated ``brain.synapses`` as
    ``(pre_idx, post_idx, weight)`` triples and identified KC→MBON synapses by
    hardcoded index ranges ("KCs: 5198-10476, MBONs: 10477-10572"). Neither
    held: the engine stores parallel ``pre_indices`` / ``post_indices`` /
    ``syn_weights`` arrays, and neuron order is connectome iteration order, not
    grouped by cell type, so those ranges selected an arbitrary neuron set.
    Cell type is now resolved through the repository's classifier.
    """
    return kc_mbon_weight_stats(brain, connectome)


def apply_hebbian_update(brain, connectome, learning_rate=0.01, reward_signal=1.0):
    """
    Apply Hebbian plasticity to KC→MBON synapses: Δw = η · A_pre · A_post · reward

    Uses the engine's own state arrays rather than a synapse triple list, and
    restricts the update to synapses whose presynaptic neuron classifies as KC
    and whose postsynaptic neuron classifies as MBON.

    The activity terms are read from the engine's mean_amplitude, indexed by
    the synapse's own endpoints. The original code indexed a region-local
    activity vector with a global neuron index offset by a hardcoded constant,
    which read the wrong neuron whenever the offset was wrong — and it always
    was, because neurons are not grouped by type.

    Returns the number of synapses updated.
    """
    from hive.substrate.olfactory_subgraph import classify_olfactory_neuron

    if getattr(brain, '_kc_mbon_mask', None) is None:
        region_of_idx = {}
        for nid, neuron in connectome.neurons.items():
            i = brain.id_to_idx.get(nid)
            if i is not None:
                region_of_idx[i] = classify_olfactory_neuron(neuron)
        pre = np.asarray(brain.pre_indices)
        post = np.asarray(brain.post_indices)
        brain._kc_mbon_mask = np.array(
            [region_of_idx.get(int(a)) == 'KC' and region_of_idx.get(int(b)) == 'MBON'
             for a, b in zip(pre, post)]
        )

    mask = brain._kc_mbon_mask
    if not mask.any():
        return 0

    amp = np.asarray(
        brain.mean_amplitude.tolist() if hasattr(brain.mean_amplitude, 'tolist')
        else brain.mean_amplitude, dtype=np.float32)
    w = np.asarray(
        brain.syn_weights.tolist() if hasattr(brain.syn_weights, 'tolist')
        else brain.syn_weights, dtype=np.float32).copy()

    pre = np.asarray(brain.pre_indices)[mask]
    post = np.asarray(brain.post_indices)[mask]

    delta_w = learning_rate * amp[pre] * amp[post] * reward_signal
    w[mask] = np.clip(w[mask] + delta_w, -10.0, 10.0)

    if getattr(brain, 'use_mlx', False):
        import mlx.core as mx
        brain.syn_weights = mx.array(w)
    else:
        brain.syn_weights = w

    # Coupling reads syn_weights directly, so there is nothing to reload; the
    # original code called brain.load_connectome_simple here, which never
    # existed.
    return int(mask.sum())

def conditioning_experiment(brain, odor_name, door_client, connectome,
                            num_trials=20, learning_rate=0.01):
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
    inject(brain, glom_pattern, strength=base_strength)
    brain.evolve(duration=100.0)
    
    kc_activity_pre = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    mbon_activity_pre = brain.get_region_activity('MBON')
    
    pre_mbon_mean = float(np.mean(mbon_activity_pre))
    pre_mbon_max = float(np.max(mbon_activity_pre))
    
    logger.info(f"  Pre-conditioning MBON: mean={pre_mbon_mean:.4f}, max={pre_mbon_max:.4f}")
    
    # KC and MBON membership comes from the classifier, not from hardcoded
    # index ranges; neurons are stored in connectome iteration order.
    weights_pre = get_kc_mbon_weights(brain, connectome)
    initial_weight_mean = weights_pre.get('weight_mean', 0.0)
    n_kc_mbon = weights_pre.get('n_kc_to_mbon_synapses', 0)

    logger.info(f"  Initial KC->MBON weights: {n_kc_mbon} synapses, mean={initial_weight_mean:.4f}")
    
    # Conditioning trials
    mbon_responses_during_training = []
    
    for trial in range(num_trials):
        # Reset brain
        brain.reset(deterministic=True)
        
        # Present odor
        inject(brain, glom_pattern, strength=base_strength)
        brain.evolve(duration=100.0)
        
        # Measure activity
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        mbon_activity = brain.get_region_activity('MBON')
        
        mbon_mean = float(np.mean(mbon_activity))
        mbon_responses_during_training.append(mbon_mean)
        
        # Apply Hebbian plasticity with reward
        reward_signal = 1.0
        num_updated = apply_hebbian_update(brain, connectome, learning_rate,
                                           reward_signal)
        
        if trial % 5 == 0:
            logger.info(f"  Trial {trial+1}/{num_trials}: MBON={mbon_mean:.4f}, updated {num_updated} synapses")
    
    # Measure post-conditioning response
    brain.reset(deterministic=True)
    inject(brain, glom_pattern, strength=base_strength)
    brain.evolve(duration=100.0)
    
    kc_activity_post = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    mbon_activity_post = brain.get_region_activity('MBON')
    
    post_mbon_mean = float(np.mean(mbon_activity_post))
    post_mbon_max = float(np.max(mbon_activity_post))
    
    logger.info(f"  Post-conditioning MBON: mean={post_mbon_mean:.4f}, max={post_mbon_max:.4f}")
    
    # Get final weights
    weights_post = get_kc_mbon_weights(brain, connectome)
    final_weight_mean = weights_post.get('weight_mean', 0.0)
    
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
        'num_kc_mbon_synapses': n_kc_mbon,
        'training_curve': mbon_responses_during_training
    }

def main():
    logger.info("="*70)
    logger.info("LEARNING & PLASTICITY VALIDATION")
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
    
    test_odors, odor_report = resolve_odor_list(
        door_client, ['benzaldehyde', '2-heptanone'], logger)
    
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
            brain, odor_name, door_client, connectome,
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
    # Written through write_results so the file lands under results/final/ and
    # carries its configuration block (seed, commit, backend, dt, projection,
    # glomerular mapping). It previously json.dump'd to a bare filename in the
    # working directory with no provenance at all.
    results['odor_resolution'] = odor_report
    output_file = write_results(
        'learning_plasticity_results.json', results,
        brain=brain, door_client=door_client, seed=SEED,
        test='learning_plasticity', duration_ms=100.0,
    )
    logger.info(f"\n✅ Results saved to {output_file}")
    
    logger.info("\n" + "="*70)
    logger.info("LEARNING & PLASTICITY VALIDATION COMPLETE")
    logger.info("="*70)

if __name__ == '__main__':
    main()
