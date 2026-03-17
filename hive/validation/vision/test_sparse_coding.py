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
from hive.vision.phototransduction import Phototransduction, PhototransductionState


def test_sparse_coding_vision(
    visual_connectome: Connectome,
    stimuli: List[VisualStimulus],
    simulation_duration_ms: float = 100.0  # Match olfaction validated duration
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
    print("SPARSE CODING TEST - VISION (WITH PHOTOTRANSDUCTION)")
    print("="*70)
    
    # Use simplified phototransduction model based on biological measurements
    # From Hardie & Raghu (2001): photoreceptors produce 10-40mV depolarization
    # Weber-Fechner law: V = k * log10(photon_rate) + baseline
    # Empirical fit from Drosophila data
    print("\nUsing simplified phototransduction model (Weber-Fechner law)...")
    
    def photon_rate_to_voltage(photon_rate: float) -> float:
        """
        Convert photon rate to photoreceptor voltage using empirical model.
        
        Based on Hardie & Raghu (2001) measurements:
        - Dark: 0 mV
        - Dim (10² photons/s): ~5 mV
        - Medium (10⁴ photons/s): ~20 mV  
        - Bright (10⁶ photons/s): ~35 mV (saturates)
        
        Args:
            photon_rate: Photons per second
            
        Returns:
            Depolarization in mV
        """
        if photon_rate < 1:
            return 0.0
        
        # Weber-Fechner logarithmic response
        # V = gain * log10(photon_rate / threshold)
        threshold = 10.0  # photons/s, detection threshold
        gain = 10.0  # mV per decade
        max_voltage = 40.0  # mV, saturation
        
        voltage = gain * np.log10(photon_rate / threshold)
        return float(np.clip(voltage, 0, max_voltage))
    
    # Test the model
    print(f"  Phototransduction response curve:")
    for test_rate in [1, 10, 100, 1000, 10000, 100000]:
        v = photon_rate_to_voltage(test_rate)
        print(f"    {test_rate:6.0e} photons/s → {v:5.1f} mV")
    
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
    
    # Identify L1/L2/L3 monopolar cells in lamina (receive R1-R6 input)
    lamina_monopolar_cells = []
    for neuron_id in regions['LAMINA']:
        neuron = visual_connectome.neurons.get(neuron_id)
        if neuron:
            cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
            if any(ct in cell_types_str for ct in ['L1', 'L2', 'L3', 'Lawf', 'Lai']):
                lamina_monopolar_cells.append(neuron_id)
    
    print(f"\nPhotoreceptor mapping:")
    print(f"  Lamina monopolar cells (L1/L2/L3): {len(lamina_monopolar_cells):,}")
    print(f"  Will map 800 ommatidia (6,400 R1-R6) → {min(len(lamina_monopolar_cells), 800)} neurons")
    
    # Storage for sparsity measurements
    sparsity_results = {region: [] for region in regions.keys()}
    
    # Test each stimulus
    print(f"\nTesting {len(stimuli)} stimuli...")
    
    for stim_idx, stimulus in enumerate(stimuli):
        if stim_idx % 1 == 0:
            print(f"  Stimulus {stim_idx+1}/{len(stimuli)}: {stimulus.name}")
        
        # Reset brain state
        brain._initialize_fields()
        
        # Convert photoreceptor responses to voltages via simplified phototransduction
        # stimulus.photoreceptor_pattern shape: (n_ommatidia, 8) with R1-R8 responses (0-1 normalized)
        photoreceptor_voltages = np.zeros((800, 8))  # 800 ommatidia × 8 receptors
        
        # Vectorized computation (GPU-friendly)
        pattern_subset = stimulus.photoreceptor_pattern[:800, :8]
        
        # Convert to photon rates: 1.0 sensitivity = 10^4 photons/s (bright daylight)
        photon_rates = pattern_subset * 1e4 * stimulus.intensity
        
        # Apply Weber-Fechner law to get voltages (vectorized)
        photoreceptor_voltages = np.vectorize(photon_rate_to_voltage)(photon_rates)
        
        # Map photoreceptor voltages to lamina neurons
        # Biology: R1-R6 (6 receptors per ommatidium) project to L1/L2/L3 monopolar cells
        if brain.use_mlx:
            import mlx.core as mx
            brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
            
            # Map R1-R6 to lamina monopolar cells (one-to-one or convergent mapping)
            num_lamina_targets = min(len(lamina_monopolar_cells), 800)
            for omm_idx in range(min(800, photoreceptor_voltages.shape[0])):
                if omm_idx < num_lamina_targets:
                    neuron_id = lamina_monopolar_cells[omm_idx]
                    if neuron_id in brain.id_to_idx:
                        idx = brain.id_to_idx[neuron_id]
                        # Average R1-R6 depolarization (biological convergence)
                        r1_r6_voltage = np.mean(photoreceptor_voltages[omm_idx, :6])
                        # Convert voltage (mV) to forcing strength
                        # Typical depolarization: 10-40mV → forcing scale
                        forcing_strength = float(r1_r6_voltage * 10.0)  # Scale mV to forcing
                        brain.external_force = brain.external_force.at[idx].add(forcing_strength)
        else:
            brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)
            
            num_lamina_targets = min(len(lamina_monopolar_cells), 800)
            for omm_idx in range(min(800, photoreceptor_voltages.shape[0])):
                if omm_idx < num_lamina_targets:
                    neuron_id = lamina_monopolar_cells[omm_idx]
                    if neuron_id in brain.id_to_idx:
                        idx = brain.id_to_idx[neuron_id]
                        r1_r6_voltage = np.mean(photoreceptor_voltages[omm_idx, :6])
                        forcing_strength = float(r1_r6_voltage * 10.0)
                        brain.external_force[idx] = forcing_strength
        
        # Run simulation
        brain.evolve(duration=simulation_duration_ms)
        
        # Measure sparsity in each region
        for region, neuron_ids in regions.items():
            if len(neuron_ids) == 0:
                continue
            
            # Get activation for neurons in this region
            indices = [brain.id_to_idx[nid] for nid in neuron_ids if nid in brain.id_to_idx]
            
            if len(indices) > 0:
                amplitudes = brain.mean_amplitude[indices]
                
                # Convert to numpy if using MLX
                if brain.use_mlx:
                    import mlx.core as mx
                    amplitudes = np.array(amplitudes)
                
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
    
    # Run test with corrected parameters:
    # - Duration: 100ms (matches olfaction validation)
    # - Forcing: 500× (vision has 10× coupling gain vs olfaction baseline)
    # - dt: 0.1ms (10× faster than original)
    # - Coupling: 10× gain for vision networks (>50K neurons)
    results = test_sparse_coding_vision(visual_conn, stimuli[:5], simulation_duration_ms=100.0)
    
    print("\n✓ Test complete")
