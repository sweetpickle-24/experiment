"""
Test Decorrelation in Visual System

Tests if similar wavelengths produce anticorrelated medulla patterns.

Setup:
- Input: Similar wavelengths (e.g., 450nm vs 480nm blue-cyan)
- Photoreceptor correlation: r = +0.75 (similar input)
- Expected: Medulla pattern correlation r < 0 (anticorrelated)

Mechanism: Same as olfaction
- Random lamina→medulla connectivity (expansion 5,000→40,000)
- High threshold sparse activation
- Competition → anticorrelation
"""

import numpy as np
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from scipy.stats import pearsonr

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import get_visual_region_neurons
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.vision.spectral_stimuli import SpectralStimulusGenerator


def test_decorrelation_vision(
    visual_connectome: Connectome,
    similarity_threshold: float = 30.0,
    simulation_duration_ms: float = 100.0
) -> Dict:
    """
    Test decorrelation between similar wavelengths.
    
    Args:
        visual_connectome: Optic lobe connectome
        similarity_threshold: Wavelength similarity (nm)
        simulation_duration_ms: Simulation duration
    
    Returns:
        Dictionary with decorrelation results
    """
    print("\n" + "="*70)
    print("DECORRELATION TEST - VISION")
    print("="*70)
    
    # Initialize
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    generator = SpectralStimulusGenerator()
    
    # Get medulla neurons (where decorrelation should occur)
    medulla_neurons = get_visual_region_neurons(visual_connectome, 'MEDULLA')
    medulla_indices = [brain.id_to_idx[nid] for nid in medulla_neurons if nid in brain.id_to_idx]
    
    print(f"Medulla neurons: {len(medulla_neurons):,}")
    print(f"Similarity threshold: ±{similarity_threshold} nm")
    
    # Initialize lamina cartridge mapper
    print("\nInitializing lamina cartridge structure...")
    from hive.vision.lamina_cartridge import LaminaCartridgeMapper
    cartridge_mapper = LaminaCartridgeMapper(visual_connectome)
    cartridges = cartridge_mapper.create_cartridges(num_ommatidia=800)
    
    # Identify R7/R8 target neurons
    print("Identifying R7/R8 → MEDULLA pathways...")
    medulla_uv_cells = []
    medulla_blue_cells = []
    medulla_green_cells = []
    
    for neuron_id in medulla_neurons:
        neuron = visual_connectome.neurons.get(neuron_id)
        if neuron:
            cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
            if 'Mi1' in cell_types_str:
                medulla_uv_cells.append(neuron_id)
            elif 'Tm9' in cell_types_str:
                medulla_blue_cells.append(neuron_id)
            elif any(ct in cell_types_str for ct in ['Tm20', 'Tm5']):
                medulla_green_cells.append(neuron_id)
    
    # Identify T4/T5 neurons in lobula
    print("Identifying T4/T5 → LOBULA pathways...")
    lobula_neurons = get_visual_region_neurons(visual_connectome, 'LOBULA')
    lobula_t4_cells = []
    lobula_t5_cells = []
    
    for neuron_id in lobula_neurons:
        neuron = visual_connectome.neurons.get(neuron_id)
        if neuron:
            cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
            if 'T4' in cell_types_str:
                lobula_t4_cells.append(neuron_id)
            elif 'T5' in cell_types_str:
                lobula_t5_cells.append(neuron_id)
    
    # Test pairs of similar wavelengths
    test_wavelengths = [400, 450, 500, 550, 600]
    
    results = {
        'metadata': {
            'similarity_threshold_nm': similarity_threshold,
            'medulla_neurons': len(medulla_neurons),
            'test_wavelengths': test_wavelengths
        },
        'wavelength_pairs': []
    }
    
    print(f"\nTesting {len(test_wavelengths)} reference wavelengths...")
    
    all_input_correlations = []
    all_medulla_correlations = []
    
    for ref_wl in test_wavelengths:
        # Get similar wavelengths
        similar_wls = generator.get_similar_wavelengths(ref_wl, similarity_threshold)
        
        if len(similar_wls) == 0:
            continue
        
        print(f"\n{ref_wl}nm → similar: {[int(w) for w in similar_wls[:3]]}")
        
        # Generate stimuli
        ref_stimulus = generator.generate_pure_wavelengths()[
            list(generator.pure_wavelengths).index(ref_wl)
        ]
        
        for sim_wl in similar_wls[:3]:  # Test top 3 similar
            sim_stimulus = generator.generate_pure_wavelengths()[
                list(generator.pure_wavelengths).index(sim_wl)
            ]
            
            # Measure input correlation (photoreceptor patterns)
            input_corr, _ = pearsonr(
                ref_stimulus.photoreceptor_pattern.flatten(),
                sim_stimulus.photoreceptor_pattern.flatten()
            )
            
            # Simulate both stimuli
            ref_pattern = simulate_stimulus(
                brain, ref_stimulus, medulla_indices, simulation_duration_ms,
                cartridge_mapper, cartridges,
                medulla_uv_cells, medulla_blue_cells, medulla_green_cells,
                lobula_t4_cells, lobula_t5_cells
            )
            sim_pattern = simulate_stimulus(
                brain, sim_stimulus, medulla_indices, simulation_duration_ms,
                cartridge_mapper, cartridges,
                medulla_uv_cells, medulla_blue_cells, medulla_green_cells,
                lobula_t4_cells, lobula_t5_cells
            )
            
            # Measure medulla correlation
            medulla_corr, _ = pearsonr(ref_pattern, sim_pattern)
            
            all_input_correlations.append(input_corr)
            all_medulla_correlations.append(medulla_corr)
            
            pair_result = {
                'wavelength_1': int(ref_wl),
                'wavelength_2': int(sim_wl),
                'distance_nm': abs(ref_wl - sim_wl),
                'input_correlation': float(input_corr),
                'medulla_correlation': float(medulla_corr),
                'decorrelated': medulla_corr < 0
            }
            results['wavelength_pairs'].append(pair_result)
            
            print(f"  {ref_wl}nm vs {int(sim_wl)}nm: input r={input_corr:.3f} → medulla r={medulla_corr:.3f}")
    
    # Summary statistics
    all_input_correlations = np.array(all_input_correlations)
    all_medulla_correlations = np.array(all_medulla_correlations)
    
    mean_input_corr = np.mean(all_input_correlations)
    mean_medulla_corr = np.mean(all_medulla_correlations)
    
    num_decorrelated = np.sum(all_medulla_correlations < 0)
    pct_decorrelated = 100.0 * num_decorrelated / len(all_medulla_correlations)
    
    results['summary'] = {
        'mean_input_correlation': float(mean_input_corr),
        'mean_medulla_correlation': float(mean_medulla_corr),
        'num_pairs_tested': len(all_medulla_correlations),
        'num_decorrelated': int(num_decorrelated),
        'percent_decorrelated': float(pct_decorrelated),
        'decorrelation_strength': float(mean_input_corr - mean_medulla_corr)
    }
    
    # Check if decorrelation occurred
    # Target: mean medulla correlation < 0 (anticorrelated)
    target_correlation = 0.0
    passed = mean_medulla_corr < target_correlation
    
    print("\n" + "="*70)
    print("DECORRELATION RESULTS")
    print("="*70)
    print(f"\nMean input correlation: {mean_input_corr:.3f}")
    print(f"Mean medulla correlation: {mean_medulla_corr:.3f}")
    print(f"Decorrelation strength: {mean_input_corr - mean_medulla_corr:.3f}")
    print(f"\nPairs decorrelated: {num_decorrelated}/{len(all_medulla_correlations)} ({pct_decorrelated:.1f}%)")
    print(f"Target: r < {target_correlation}")
    
    if passed:
        print("\n✅ DECORRELATION TEST PASSED")
        print("Similar wavelengths produce anticorrelated medulla patterns")
    else:
        print("\n⚠️ DECORRELATION TEST: WEAK")
        print("Medulla patterns still positively correlated")
    
    results['test_passed'] = passed
    print("="*70)
    
    return results


def simulate_stimulus(
    brain: SparseProbabilisticBrain,
    stimulus,
    medulla_indices: List[int],
    duration_ms: float,
    cartridge_mapper,
    cartridges,
    medulla_uv_cells,
    medulla_blue_cells,
    medulla_green_cells,
    lobula_t4_cells,
    lobula_t5_cells
) -> np.ndarray:
    """Simulate stimulus and return medulla activation pattern."""
    brain._initialize_fields()
    
    # Constants (same as test_sparse_coding.py)
    VOLTAGE_TO_FIRING_RATE = 50.0
    FIRING_TO_FORCING = 10.0
    R7_R8_GAIN = 0.15
    T4_T5_GAIN = 0.20
    
    def photon_rate_to_voltage(photon_rate: float) -> float:
        if photon_rate < 1:
            return 0.0
        threshold = 10.0
        gain = 10.0
        max_voltage = 40.0
        voltage = gain * np.log10(photon_rate / threshold)
        return float(np.clip(voltage, 0, max_voltage))
    
    # Convert photoreceptor responses to voltages
    photoreceptor_voltages = np.zeros((800, 8))
    pattern_subset = stimulus.photoreceptor_pattern[:800, :8]
    photon_rates = pattern_subset * 1e4 * stimulus.intensity
    photoreceptor_voltages = np.vectorize(photon_rate_to_voltage)(photon_rates)
    
    # Apply forcing (5 pathways)
    if brain.use_mlx:
        import mlx.core as mx
        brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
        
        # PATHWAY 1: R1-R6 → LAMINA
        cartridge_outputs = []
        for cart_idx, cartridge in enumerate(cartridges[:800]):
            if cart_idx < photoreceptor_voltages.shape[0]:
                cartridge.r1_r6_voltages = photoreceptor_voltages[cart_idx, :6]
                outputs = cartridge.compute_lamina_inputs()
                cartridge_outputs.append(outputs)
        
        cartridge_outputs = cartridge_mapper.apply_lateral_inhibition(
            cartridge_outputs, kernel_size=3, inhibition_strength=0.3
        )
        
        for cart_idx, (cartridge, outputs) in enumerate(zip(cartridges[:800], cartridge_outputs)):
            for neuron_type in ['L1', 'L2', 'L3', 'Lai']:
                forcing_value = outputs.get(neuron_type, 0.0)
                if forcing_value > 0:
                    neuron_id = getattr(cartridge, f"{neuron_type}_id")
                    if neuron_id and neuron_id in brain.id_to_idx:
                        idx = brain.id_to_idx[neuron_id]
                        forcing = float(forcing_value * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING)
                        brain.external_force = brain.external_force.at[idx].add(forcing)
        
        # PATHWAY 2: R7 → MEDULLA Mi1
        num_r7_targets = min(800, len(medulla_uv_cells))
        for omm_idx in range(num_r7_targets):
            if omm_idx < photoreceptor_voltages.shape[0]:
                neuron_id = medulla_uv_cells[omm_idx]
                if neuron_id in brain.id_to_idx:
                    idx = brain.id_to_idx[neuron_id]
                    r7_voltage = photoreceptor_voltages[omm_idx, 6]
                    forcing = float(r7_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                    brain.external_force = brain.external_force.at[idx].add(forcing)
        
        # PATHWAY 3: R8 → MEDULLA Tm9/Tm5
        num_r8p_targets = min(int(800 * 0.7), len(medulla_blue_cells))
        for omm_idx in range(num_r8p_targets):
            if omm_idx < photoreceptor_voltages.shape[0]:
                neuron_id = medulla_blue_cells[omm_idx]
                if neuron_id in brain.id_to_idx:
                    idx = brain.id_to_idx[neuron_id]
                    r8_voltage = photoreceptor_voltages[omm_idx, 7]
                    forcing = float(r8_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                    brain.external_force = brain.external_force.at[idx].add(forcing)
        
        num_r8y_targets = min(int(800 * 0.3), len(medulla_green_cells))
        r8y_start = num_r8p_targets
        for omm_idx in range(r8y_start, min(r8y_start + num_r8y_targets, 800)):
            if omm_idx < photoreceptor_voltages.shape[0]:
                neuron_id = medulla_green_cells[omm_idx - r8y_start]
                if neuron_id in brain.id_to_idx:
                    idx = brain.id_to_idx[neuron_id]
                    r8_voltage = photoreceptor_voltages[omm_idx, 7]
                    forcing = float(r8_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                    brain.external_force = brain.external_force.at[idx].add(forcing)
        
        # PATHWAY 4: Mi1/Tm3 → T4
        num_t4_forced = min(int(len(lobula_t4_cells) * 0.5), 800 * 2 + 200)
        for omm_idx in range(num_t4_forced):
            neuron_id = lobula_t4_cells[omm_idx]
            if neuron_id in brain.id_to_idx:
                idx = brain.id_to_idx[neuron_id]
                omm_pos = omm_idx % 800
                if omm_pos < photoreceptor_voltages.shape[0]:
                    r7_v = photoreceptor_voltages[omm_pos, 6]
                    r1r6_mean = float(np.mean(photoreceptor_voltages[omm_pos, :6]))
                    combined_v = r7_v * 0.6 + r1r6_mean * 0.4
                    forcing = float(combined_v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * T4_T5_GAIN)
                    brain.external_force = brain.external_force.at[idx].add(forcing)
        
        # PATHWAY 5: Tm1/Tm4 → T5
        num_t5_forced = min(int(len(lobula_t5_cells) * 0.3), 800)
        for omm_idx in range(num_t5_forced):
            neuron_id = lobula_t5_cells[omm_idx]
            if neuron_id in brain.id_to_idx:
                idx = brain.id_to_idx[neuron_id]
                omm_pos = omm_idx % 800
                if omm_pos < photoreceptor_voltages.shape[0]:
                    r1r6_mean = float(np.mean(photoreceptor_voltages[omm_pos, :6]))
                    forcing = float(r1r6_mean * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * T4_T5_GAIN * 0.5)
                    brain.external_force = brain.external_force.at[idx].add(forcing)
    
    # Simulate
    brain.evolve(duration=duration_ms)
    
    # Extract medulla pattern
    if brain.use_mlx:
        pattern = np.array(brain.mean_amplitude[medulla_indices])
    else:
        pattern = brain.mean_amplitude[medulla_indices]
    return pattern


if __name__ == "__main__":
    print("Testing Decorrelation in Vision\n")
    
    # Load visual connectome
    visual_conn = Connectome(data_dir="data/vision/optic_lobe")
    visual_conn.load_json("data/vision/optic_lobe/flywire_optic_lobe.json")
    
    # Run test
    results = test_decorrelation_vision(visual_conn, similarity_threshold=30.0)
    
    print("\n✓ Test complete")
