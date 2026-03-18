"""
Test Motion Detection in Visual System

Tests if T4/T5 neurons exhibit direction selectivity.

Setup:
- Temporal sequences: wavelength sweep 400nm→500nm vs 500nm→400nm
- T4/T5 neurons should respond to specific temporal directions

Target benchmark: Borst & Euler (2011) - T4/T5 direction tuning curves
"""

import numpy as np
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import get_visual_region_neurons, classify_visual_neuron
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.vision.spectral_stimuli import SpectralStimulusGenerator


def test_motion_detection_vision(
    visual_connectome: Connectome,
    frame_duration_ms: float = 50.0
) -> Dict:
    """
    Test motion detection via T4/T5 direction selectivity.
    
    Args:
        visual_connectome: Optic lobe connectome
        frame_duration_ms: Duration of each frame in sequence
    
    Returns:
        Dictionary with motion detection results
    """
    from hive.vision.lamina_cartridge import LaminaCartridgeMapper
    
    print("\n" + "="*70)
    print("MOTION DETECTION TEST - VISION")
    print("="*70)
    
    # Initialize
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    generator = SpectralStimulusGenerator()
    
    # Get T4/T5 neurons (motion detectors)
    lobula_neurons = get_visual_region_neurons(visual_connectome, 'LOBULA')
    
    # Filter for T4/T5 specifically
    t4_t5_neurons = []
    for nid in lobula_neurons:
        neuron = visual_connectome.neurons[nid]
        cell_types_str = ' '.join(neuron.cell_types).upper()
        if 'T4' in cell_types_str or 'T5' in cell_types_str:
            t4_t5_neurons.append(nid)
    
    t4_t5_indices = [brain.id_to_idx[nid] for nid in t4_t5_neurons if nid in brain.id_to_idx]
    
    print(f"Lobula neurons: {len(lobula_neurons):,}")
    print(f"T4/T5 neurons identified: {len(t4_t5_neurons):,}")
    print(f"Frame duration: {frame_duration_ms} ms")
    
    # Initialize lamina cartridge mapper and target neurons
    print("\nInitializing forcing pathways...")
    cartridge_mapper = LaminaCartridgeMapper(visual_connectome)
    cartridges = cartridge_mapper.create_cartridges(800)
    
    medulla_neurons = get_visual_region_neurons(visual_connectome, 'MEDULLA')
    medulla_uv_cells = []
    medulla_blue_cells = []
    medulla_green_cells = []
    lobula_t4_cells = []
    lobula_t5_cells = []
    
    for nid in medulla_neurons:
        neuron = visual_connectome.neurons.get(nid)
        if neuron:
            cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
            if 'Mi1' in cell_types_str:
                medulla_uv_cells.append(nid)
            elif 'Tm9' in cell_types_str:
                medulla_blue_cells.append(nid)
            elif any(ct in cell_types_str for ct in ['Tm20', 'Tm5']):
                medulla_green_cells.append(nid)
    
    for nid in lobula_neurons:
        neuron = visual_connectome.neurons.get(nid)
        if neuron:
            cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
            if 'T4' in cell_types_str:
                lobula_t4_cells.append(nid)
            elif 'T5' in cell_types_str:
                lobula_t5_cells.append(nid)
    
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
    
    # Define motion directions
    directions = {
        'forward': np.linspace(400, 500, 11),   # Blue → green
        'backward': np.linspace(500, 400, 11),  # Green → blue
        'stationary': [450] * 11                 # Control
    }
    
    results = {
        'metadata': {
            't4_t5_neurons': len(t4_t5_neurons),
            'frame_duration_ms': frame_duration_ms,
            'num_frames': 11
        },
        'direction_responses': []
    }
    
    print(f"\nTesting {len(directions)} motion directions...")
    
    direction_activations = {}
    
    for direction_name, wavelength_sequence in directions.items():
        print(f"\n{direction_name.upper()} motion:")
        print(f"  Sequence: {wavelength_sequence[0]:.0f}nm → {wavelength_sequence[-1]:.0f}nm")
        
        # Generate temporal sequence
        temporal_stimuli = generator.generate_temporal_sequence(
            wavelength_sequence,
            intensity=0.75,
            frame_duration_ms=frame_duration_ms
        )
        
        # Simulate sequence
        brain._initialize_fields()
        
        frame_activations = []
        
        for frame_idx, stimulus in enumerate(temporal_stimuli):
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
                for omm_idx in range(min(800, len(medulla_uv_cells))):
                    if omm_idx < photoreceptor_voltages.shape[0]:
                        neuron_id = medulla_uv_cells[omm_idx]
                        if neuron_id in brain.id_to_idx:
                            idx = brain.id_to_idx[neuron_id]
                            r7_voltage = photoreceptor_voltages[omm_idx, 6]
                            forcing = float(r7_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                            brain.external_force = brain.external_force.at[idx].add(forcing)
                
                # PATHWAY 3: R8 → MEDULLA Tm9/Tm5
                num_r8p = min(int(800 * 0.7), len(medulla_blue_cells))
                for omm_idx in range(num_r8p):
                    if omm_idx < photoreceptor_voltages.shape[0]:
                        neuron_id = medulla_blue_cells[omm_idx]
                        if neuron_id in brain.id_to_idx:
                            idx = brain.id_to_idx[neuron_id]
                            r8_voltage = photoreceptor_voltages[omm_idx, 7]
                            forcing = float(r8_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                            brain.external_force = brain.external_force.at[idx].add(forcing)
                
                num_r8y = min(int(800 * 0.3), len(medulla_green_cells))
                r8y_start = num_r8p
                for omm_idx in range(r8y_start, min(r8y_start + num_r8y, 800)):
                    if omm_idx < photoreceptor_voltages.shape[0]:
                        neuron_id = medulla_green_cells[omm_idx - r8y_start]
                        if neuron_id in brain.id_to_idx:
                            idx = brain.id_to_idx[neuron_id]
                            r8_voltage = photoreceptor_voltages[omm_idx, 7]
                            forcing = float(r8_voltage * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN)
                            brain.external_force = brain.external_force.at[idx].add(forcing)
                
                # PATHWAY 4: Mi1/Tm3 → T4
                num_t4 = min(int(len(lobula_t4_cells) * 0.5), 800 * 2 + 200)
                for omm_idx in range(num_t4):
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
                num_t5 = min(int(len(lobula_t5_cells) * 0.3), 800)
                for omm_idx in range(num_t5):
                    neuron_id = lobula_t5_cells[omm_idx]
                    if neuron_id in brain.id_to_idx:
                        idx = brain.id_to_idx[neuron_id]
                        omm_pos = omm_idx % 800
                        if omm_pos < photoreceptor_voltages.shape[0]:
                            r1r6_mean = float(np.mean(photoreceptor_voltages[omm_pos, :6]))
                            forcing = float(r1r6_mean * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * T4_T5_GAIN * 0.5)
                            brain.external_force = brain.external_force.at[idx].add(forcing)
            
            # Simulate frame
            brain.evolve(duration=frame_duration_ms)
            
            # Record T4/T5 activation
            if len(t4_t5_indices) > 0:
                if brain.use_mlx:
                    activation = np.array(brain.mean_amplitude[t4_t5_indices])
                else:
                    activation = brain.mean_amplitude[t4_t5_indices]
                frame_activations.append(np.mean(activation))
        
        # Compute average activation for this direction
        mean_activation = np.mean(frame_activations)
        peak_activation = np.max(frame_activations)
        
        direction_activations[direction_name] = {
            'mean': mean_activation,
            'peak': peak_activation,
            'time_course': frame_activations
        }
        
        print(f"  Mean T4/T5 activation: {mean_activation:.3f}")
        print(f"  Peak T4/T5 activation: {peak_activation:.3f}")
        
        results['direction_responses'].append({
            'direction': direction_name,
            'wavelength_sequence': [float(w) for w in wavelength_sequence],
            'mean_activation': float(mean_activation),
            'peak_activation': float(peak_activation)
        })
    
    # Compute direction selectivity index (DSI)
    # DSI = (preferred - null) / (preferred + null)
    forward_resp = direction_activations['forward']['mean']
    backward_resp = direction_activations['backward']['mean']
    stationary_resp = direction_activations['stationary']['mean']
    
    # Direction selectivity
    if forward_resp + backward_resp > 0:
        dsi_forward_backward = abs(forward_resp - backward_resp) / (forward_resp + backward_resp)
    else:
        dsi_forward_backward = 0.0
    
    # Motion vs stationary
    motion_responses = [forward_resp, backward_resp]
    mean_motion = np.mean(motion_responses)
    
    motion_enhancement = mean_motion / stationary_resp if stationary_resp > 0 else 0
    
    results['summary'] = {
        'direction_selectivity_index': float(dsi_forward_backward),
        'forward_response': float(forward_resp),
        'backward_response': float(backward_resp),
        'stationary_response': float(stationary_resp),
        'motion_enhancement': float(motion_enhancement)
    }
    
    # Check if directional tuning present
    # Target: DSI > 0.3 (moderate direction selectivity)
    target_dsi = 0.3
    passed = dsi_forward_backward >= target_dsi and motion_enhancement > 1.2
    
    print("\n" + "="*70)
    print("MOTION DETECTION RESULTS")
    print("="*70)
    print(f"\nDirection Selectivity Index (DSI): {dsi_forward_backward:.3f}")
    print(f"Motion enhancement: {motion_enhancement:.2f}x over stationary")
    print(f"\nResponses:")
    print(f"  Forward: {forward_resp:.3f}")
    print(f"  Backward: {backward_resp:.3f}")
    print(f"  Stationary: {stationary_resp:.3f}")
    print(f"\nTarget: DSI > {target_dsi}, Motion > 1.2x")
    
    if passed:
        print("\n✅ MOTION DETECTION TEST PASSED")
        print("T4/T5 neurons exhibit direction selectivity")
    else:
        print("\n⚠️ MOTION DETECTION TEST: WEAK")
        print("Limited direction selectivity detected")
    
    results['test_passed'] = passed
    print("="*70)
    
    return results


if __name__ == "__main__":
    print("Testing Motion Detection in Vision\n")
    
    # Load visual connectome
    visual_conn = Connectome(data_dir="data/vision/optic_lobe")
    visual_conn.load_json("data/vision/optic_lobe/flywire_optic_lobe.json")
    
    # Run test
    results = test_motion_detection_vision(visual_conn, frame_duration_ms=50.0)
    
    print("\n✓ Test complete")
