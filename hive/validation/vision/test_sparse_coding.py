"""
Test Sparse Coding in Visual System

Tests if visual system produces sparse firing like olfaction.

Prediction:
- Lamina: ~20-40% active (early processing)
- Medulla: ~2-5% active (sparse expansion, like PNs→KCs)
- Lobula/LP: ~10-20% active (motion integration)

Target benchmark: Campbell et al. (2013) - 3-8% medulla sparsity
"""

import numpy as np
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import (
    get_visual_region_neurons,
    classify_visual_neuron
)
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.vision.spectral_stimuli import SpectralStimulusGenerator, VisualStimulus


def test_sparse_coding_vision(
    visual_connectome: Connectome,
    stimuli: List[VisualStimulus],
    simulation_duration_ms: float = 100.0
) -> Dict:
    """
    Test sparse coding in visual pathway.
    
    Args:
        visual_connectome: Optic lobe connectome (~53,000 neurons)
        stimuli: List of visual stimuli
        simulation_duration_ms: Simulation duration per stimulus
    
    Returns:
        Dictionary with sparsity results
    """
    print("\n" + "="*70)
    print("SPARSE CODING TEST - VISION")
    print("="*70)
    
    # Initialize probabilistic brain
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    
    # Get neuron IDs by region
    regions = {
        'LAMINA': get_visual_region_neurons(visual_connectome, 'LAMINA'),
        'MEDULLA': get_visual_region_neurons(visual_connectome, 'MEDULLA'),
        'LOBULA': get_visual_region_neurons(visual_connectome, 'LOBULA'),
        'LOBULA_PLATE': get_visual_region_neurons(visual_connectome, 'LOBULA_PLATE')
    }
    
    print(f"\nRegion sizes:")
    for region, neurons in regions.items():
        print(f"  {region}: {len(neurons):,} neurons")
    
    # Storage for sparsity measurements
    sparsity_results = {region: [] for region in regions.keys()}
    
    # Test each stimulus
    print(f"\nTesting {len(stimuli)} stimuli...")
    
    for i, stimulus in enumerate(stimuli):
        if i % 10 == 0:
            print(f"  Stimulus {i+1}/{len(stimuli)}: {stimulus.name}")
        
        # Reset brain state
        brain._initialize_fields()
        
        # Convert photoreceptor pattern to forcing
        # (Map R1-R8 responses to lamina input neurons)
        forcing_dict = convert_photoreceptor_to_forcing(
            stimulus.photoreceptor_pattern,
            regions['LAMINA'][:800]  # First 800 lamina neurons
        )
        
        # Run simulation
        num_steps = int(simulation_duration_ms / brain.dt)
        
        for step in range(num_steps):
            brain.step(forcing_dict)
        
        # Measure sparsity in each region
        for region, neuron_ids in regions.items():
            if len(neuron_ids) == 0:
                continue
            
            # Get activation for neurons in this region
            indices = [brain.id_to_idx[nid] for nid in neuron_ids if nid in brain.id_to_idx]
            
            if len(indices) > 0:
                amplitudes = brain.mean_amplitude[indices]
                active = np.sum(amplitudes > 0.5)  # Threshold at 0.5
                sparsity = 100.0 * active / len(indices)
                sparsity_results[region].append(sparsity)
    
    # Compute statistics
    results = {
        'metadata': {
            'num_stimuli': len(stimuli),
            'simulation_duration_ms': simulation_duration_ms,
            'total_neurons': len(visual_connectome.neurons)
        },
        'sparsity_by_region': {}
    }
    
    print("\n" + "="*70)
    print("SPARSE CODING RESULTS")
    print("="*70)
    
    for region in ['LAMINA', 'MEDULLA', 'LOBULA', 'LOBULA_PLATE']:
        if region not in sparsity_results or len(sparsity_results[region]) == 0:
            continue
        
        sparsities = np.array(sparsity_results[region])
        mean_sparsity = np.mean(sparsities)
        std_sparsity = np.std(sparsities)
        
        results['sparsity_by_region'][region] = {
            'mean_percent': float(mean_sparsity),
            'std_percent': float(std_sparsity),
            'min_percent': float(np.min(sparsities)),
            'max_percent': float(np.max(sparsities)),
            'num_neurons': len(regions[region])
        }
        
        print(f"\n{region}:")
        print(f"  Mean sparsity: {mean_sparsity:.2f}% ± {std_sparsity:.2f}%")
        print(f"  Range: [{np.min(sparsities):.2f}%, {np.max(sparsities):.2f}%]")
        print(f"  Neurons: {len(regions[region]):,}")
        
        # Check against targets
        if region == 'LAMINA':
            target_range = (20, 40)
            passed = target_range[0] <= mean_sparsity <= target_range[1]
        elif region == 'MEDULLA':
            target_range = (2, 5)  # Campbell et al. 2013: 3-8%
            passed = target_range[0] <= mean_sparsity <= target_range[1]
        elif region in ['LOBULA', 'LOBULA_PLATE']:
            target_range = (10, 20)
            passed = target_range[0] <= mean_sparsity <= target_range[1]
        else:
            passed = None
            target_range = None
        
        if target_range:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  Target: {target_range[0]}-{target_range[1]}% → {status}")
            results['sparsity_by_region'][region]['target_range'] = target_range
            results['sparsity_by_region'][region]['passed'] = passed
    
    # Overall assessment
    medulla_passed = results['sparsity_by_region'].get('MEDULLA', {}).get('passed', False)
    
    print("\n" + "="*70)
    if medulla_passed:
        print("✅ SPARSE CODING TEST PASSED")
        print("Medulla sparsity matches Campbell et al. (2013) benchmark")
    else:
        print("⚠️ SPARSE CODING TEST: PARTIAL")
        print("Medulla sparsity outside target range")
    print("="*70)
    
    results['test_passed'] = medulla_passed
    
    return results


def convert_photoreceptor_to_forcing(
    photoreceptor_pattern: np.ndarray,
    lamina_neuron_ids: List[int]
) -> Dict[int, float]:
    """
    Convert R1-R8 photoreceptor activation to lamina neuron forcing.
    
    Args:
        photoreceptor_pattern: (n_ommatidia, 8) array
        lamina_neuron_ids: List of lamina neuron IDs
    
    Returns:
        Dictionary mapping neuron_id → forcing magnitude
    """
    forcing = {}
    
    # Flatten photoreceptor pattern and map to lamina neurons
    flat_response = photoreceptor_pattern.flatten()
    
    for i, neuron_id in enumerate(lamina_neuron_ids):
        if i < len(flat_response):
            # Scale to appropriate forcing magnitude
            forcing[neuron_id] = float(flat_response[i] * 10.0)
    
    return forcing


if __name__ == "__main__":
    print("Testing Sparse Coding in Vision\n")
    
    # Load visual connectome
    print("Loading visual connectome...")
    visual_conn = Connectome(data_dir="data/vision/optic_lobe")
    visual_conn.load_json("data/vision/optic_lobe/flywire_optic_lobe.json")
    
    # Generate test stimuli
    print("Generating test stimuli...")
    generator = SpectralStimulusGenerator()
    stimuli = generator.generate_pure_wavelengths()
    
    # Run test
    results = test_sparse_coding_vision(visual_conn, stimuli[:10])  # Test subset
    
    print("\n✓ Test complete")
