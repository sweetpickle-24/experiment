"""
Test Contrast Invariance in Visual System

Tests if wavelength representation is stable across intensity changes.

Setup:
- Same wavelength (e.g., 500nm green) at 10 intensities (1-100%)
- Measure medulla pattern correlation across intensities

Target: r > 0.70 (like concentration invariance in smell)

Mechanisms:
- Photoreceptor adaptation (calcium feedback in TRP channels)
- Lamina gain control (L1-L3 lateral inhibition)
- Medulla normalization
"""

import numpy as np
import sys
from pathlib import Path
from typing import Dict, List
from scipy.stats import pearsonr

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import get_visual_region_neurons
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.vision.spectral_stimuli import SpectralStimulusGenerator


def test_contrast_invariance_vision(
    visual_connectome: Connectome,
    test_wavelengths: List[float] = [450, 500, 600],
    num_intensities: int = 10,
    simulation_duration_ms: float = 100.0
) -> Dict:
    """
    Test contrast invariance across intensity changes.
    
    Args:
        visual_connectome: Optic lobe connectome
        test_wavelengths: Wavelengths to test (nm)
        num_intensities: Number of intensity levels
        simulation_duration_ms: Simulation duration
    
    Returns:
        Dictionary with contrast invariance results
    """
    print("\n" + "="*70)
    print("CONTRAST INVARIANCE TEST - VISION")
    print("="*70)
    
    # Initialize
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    generator = SpectralStimulusGenerator()
    
    # Get medulla neurons
    medulla_neurons = get_visual_region_neurons(visual_connectome, 'MEDULLA')
    medulla_indices = [brain.id_to_idx[nid] for nid in medulla_neurons if nid in brain.id_to_idx]
    
    print(f"Medulla neurons: {len(medulla_neurons):,}")
    print(f"Test wavelengths: {test_wavelengths}")
    print(f"Intensity levels: {num_intensities}")
    
    results = {
        'metadata': {
            'test_wavelengths': test_wavelengths,
            'num_intensities': num_intensities,
            'medulla_neurons': len(medulla_neurons)
        },
        'wavelength_results': []
    }
    
    all_correlations = []
    
    for wavelength in test_wavelengths:
        print(f"\n{wavelength}nm:")
        
        # Generate intensity series
        intensity_series = generator.generate_intensity_series(
            wavelength,
            num_intensities=num_intensities,
            intensity_range=(0.1, 1.0)
        )
        
        # Simulate all intensities
        patterns = []
        intensities = []
        
        for stimulus in intensity_series:
            pattern = simulate_stimulus_vision(
                brain, stimulus, medulla_indices, simulation_duration_ms
            )
            patterns.append(pattern)
            intensities.append(stimulus.intensity)
        
        # Compute pairwise correlations
        correlations = []
        for i in range(len(patterns)):
            for j in range(i+1, len(patterns)):
                if np.std(patterns[i]) > 0 and np.std(patterns[j]) > 0:
                    corr, _ = pearsonr(patterns[i], patterns[j])
                    correlations.append(corr)
                    
                    intensity_ratio = intensities[j] / intensities[i]
                    if intensity_ratio >= 2.0:  # Log major intensity changes
                        print(f"  {intensities[i]:.2f}x vs {intensities[j]:.2f}x ({intensity_ratio:.1f}×): r={corr:.3f}")
        
        if len(correlations) > 0:
            mean_corr = np.mean(correlations)
            std_corr = np.std(correlations)
            min_corr = np.min(correlations)
            
            all_correlations.extend(correlations)
            
            wl_result = {
                'wavelength_nm': int(wavelength),
                'mean_correlation': float(mean_corr),
                'std_correlation': float(std_corr),
                'min_correlation': float(min_corr),
                'num_comparisons': len(correlations)
            }
            results['wavelength_results'].append(wl_result)
            
            print(f"  Mean correlation: {mean_corr:.3f} ± {std_corr:.3f}")
            print(f"  Min correlation: {min_corr:.3f}")
    
    # Overall statistics
    all_correlations = np.array(all_correlations)
    overall_mean = np.mean(all_correlations)
    overall_std = np.std(all_correlations)
    overall_min = np.min(all_correlations)
    
    results['summary'] = {
        'mean_correlation': float(overall_mean),
        'std_correlation': float(overall_std),
        'min_correlation': float(overall_min),
        'total_comparisons': len(all_correlations)
    }
    
    # Check against target (r > 0.70 like concentration invariance)
    target_correlation = 0.70
    passed = overall_mean >= target_correlation
    
    print("\n" + "="*70)
    print("CONTRAST INVARIANCE RESULTS")
    print("="*70)
    print(f"\nOverall mean correlation: {overall_mean:.3f} ± {overall_std:.3f}")
    print(f"Min correlation: {overall_min:.3f}")
    print(f"Target: r > {target_correlation}")
    
    if passed:
        print("\n✅ CONTRAST INVARIANCE TEST PASSED")
        print("Wavelength representation stable across intensity changes")
    else:
        print("\n⚠️ CONTRAST INVARIANCE TEST: WEAK")
        print(f"Correlation {overall_mean:.3f} below target {target_correlation}")
    
    results['test_passed'] = passed
    print("="*70)
    
    return results


def simulate_stimulus_vision(
    brain: SparseProbabilisticBrain,
    stimulus,
    medulla_indices: List[int],
    duration_ms: float
) -> np.ndarray:
    """Simulate stimulus and return medulla pattern."""
    from hive.vision.lamina_cartridge import LaminaCartridgeMapper
    
    brain._initialize_fields()
    
    # Constants
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
    
    # Initialize cartridge mapper (cached if possible)
    if not hasattr(simulate_stimulus_vision, '_cartridge_mapper'):
        simulate_stimulus_vision._cartridge_mapper = LaminaCartridgeMapper(brain.connectome)
        simulate_stimulus_vision._cartridges = simulate_stimulus_vision._cartridge_mapper.create_cartridges(800)
        
        # Identify target neurons
        medulla_neurons = get_visual_region_neurons(brain.connectome, 'MEDULLA')
        lobula_neurons = get_visual_region_neurons(brain.connectome, 'LOBULA')
        
        medulla_uv_cells = []
        medulla_blue_cells = []
        medulla_green_cells = []
        lobula_t4_cells = []
        lobula_t5_cells = []
        
        for nid in medulla_neurons:
            neuron = brain.connectome.neurons.get(nid)
            if neuron:
                cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
                if 'Mi1' in cell_types_str:
                    medulla_uv_cells.append(nid)
                elif 'Tm9' in cell_types_str:
                    medulla_blue_cells.append(nid)
                elif any(ct in cell_types_str for ct in ['Tm20', 'Tm5']):
                    medulla_green_cells.append(nid)
        
        for nid in lobula_neurons:
            neuron = brain.connectome.neurons.get(nid)
            if neuron:
                cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
                if 'T4' in cell_types_str:
                    lobula_t4_cells.append(nid)
                elif 'T5' in cell_types_str:
                    lobula_t5_cells.append(nid)
        
        simulate_stimulus_vision._medulla_uv = medulla_uv_cells
        simulate_stimulus_vision._medulla_blue = medulla_blue_cells
        simulate_stimulus_vision._medulla_green = medulla_green_cells
        simulate_stimulus_vision._lobula_t4 = lobula_t4_cells
        simulate_stimulus_vision._lobula_t5 = lobula_t5_cells
    
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
        for cart_idx, cartridge in enumerate(simulate_stimulus_vision._cartridges[:800]):
            if cart_idx < photoreceptor_voltages.shape[0]:
                cartridge.r1_r6_voltages = photoreceptor_voltages[cart_idx, :6]
                outputs = cartridge.compute_lamina_inputs()
                cartridge_outputs.append(outputs)
        
        cartridge_outputs = simulate_stimulus_vision._cartridge_mapper.apply_lateral_inhibition(
            cartridge_outputs, kernel_size=3, inhibition_strength=0.3
        )
        
        for cart_idx, (cartridge, outputs) in enumerate(zip(simulate_stimulus_vision._cartridges[:800], cartridge_outputs)):
            for neuron_type in ['L1', 'L2', 'L3', 'Lai']:
                forcing_value = outputs.get(neuron_type, 0.0)
                if forcing_value > 0:
                    neuron_id = getattr(cartridge, f"{neuron_type}_id")
                    if neuron_id and neuron_id in brain.id_to_idx:
                        idx = brain.id_to_idx[neuron_id]
                        forcing = float(forcing_value * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING)
                        brain.external_force = brain.external_force.at[idx].add(forcing)
        
        # PATHWAY 2: R7 → MEDULLA Mi1
        for omm_idx in range(min(800, len(simulate_stimulus_vision._medulla_uv))):
            if omm_idx < photoreceptor_voltages.shape[0]:
                neuron_id = simulate_stimulus_vision._medulla_uv[omm_idx]
                if neuron_id in brain.id_to_idx:
                    idx = brain.id_to_idx[neuron_id]
                    r7_voltage = photoreceptor_voltages[omm_idx, 6]
                    forcing = float(r7_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                    brain.external_force = brain.external_force.at[idx].add(forcing)
        
        # PATHWAY 3: R8 → MEDULLA Tm9/Tm5
        num_r8p = min(int(800 * 0.7), len(simulate_stimulus_vision._medulla_blue))
        for omm_idx in range(num_r8p):
            if omm_idx < photoreceptor_voltages.shape[0]:
                neuron_id = simulate_stimulus_vision._medulla_blue[omm_idx]
                if neuron_id in brain.id_to_idx:
                    idx = brain.id_to_idx[neuron_id]
                    r8_voltage = photoreceptor_voltages[omm_idx, 7]
                    forcing = float(r8_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                    brain.external_force = brain.external_force.at[idx].add(forcing)
        
        num_r8y = min(int(800 * 0.3), len(simulate_stimulus_vision._medulla_green))
        r8y_start = num_r8p
        for omm_idx in range(r8y_start, min(r8y_start + num_r8y, 800)):
            if omm_idx < photoreceptor_voltages.shape[0]:
                neuron_id = simulate_stimulus_vision._medulla_green[omm_idx - r8y_start]
                if neuron_id in brain.id_to_idx:
                    idx = brain.id_to_idx[neuron_id]
                    r8_voltage = photoreceptor_voltages[omm_idx, 7]
                    forcing = float(r8_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                    brain.external_force = brain.external_force.at[idx].add(forcing)
        
        # PATHWAY 4: Mi1/Tm3 → T4
        num_t4 = min(int(len(simulate_stimulus_vision._lobula_t4) * 0.5), 800 * 2 + 200)
        for omm_idx in range(num_t4):
            neuron_id = simulate_stimulus_vision._lobula_t4[omm_idx]
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
        num_t5 = min(int(len(simulate_stimulus_vision._lobula_t5) * 0.3), 800)
        for omm_idx in range(num_t5):
            neuron_id = simulate_stimulus_vision._lobula_t5[omm_idx]
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
        return np.array(brain.mean_amplitude[medulla_indices])
    else:
        return brain.mean_amplitude[medulla_indices]


if __name__ == "__main__":
    print("Testing Contrast Invariance in Vision\n")
    
    # Load visual connectome
    visual_conn = Connectome(data_dir="data/vision/optic_lobe")
    visual_conn.load_json("data/vision/optic_lobe/flywire_optic_lobe.json")
    
    # Run test
    results = test_contrast_invariance_vision(
        visual_conn,
        test_wavelengths=[450, 500, 600],
        num_intensities=10
    )
    
    print("\n✓ Test complete")
