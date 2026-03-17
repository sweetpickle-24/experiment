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
            # Convert to forcing
            from hive.validation.vision.test_sparse_coding import convert_photoreceptor_to_forcing
            lamina_neurons = list(brain.neuron_ids)[:800]
            forcing = convert_photoreceptor_to_forcing(stimulus.photoreceptor_pattern, lamina_neurons)
            
            # Simulate frame
            num_steps = int(frame_duration_ms / brain.dt)
            for _ in range(num_steps):
                brain.step(forcing)
            
            # Record T4/T5 activation
            if len(t4_t5_indices) > 0:
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
