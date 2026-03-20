#!/usr/bin/env python3
"""
Chromatic Motion Blindness Test - Standalone
"""
import numpy as np
import json
import sys
from pathlib import Path

sys.path.insert(0, '/Users/vladyslav/Documents/GitHub/experiment')

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import extract_visual_pathway, get_visual_region_neurons
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain

# Constants from test_emergent_properties.py
N_COLS = 20
N_ROWS = 40
N_OMMATIDIA = N_COLS * N_ROWS
AZ_RANGE = 90.0
EL_RANGE = 40.0
SPATIAL_PERIOD_DEG = 30.0
VOLTAGE_TO_FIRING_RATE = 50.0
FIRING_TO_FORCING = 10.0
R7_R8_GAIN = 0.02

def build_ommatidium_positions():
    az_spacing = (2 * AZ_RANGE) / N_COLS
    el_spacing = (2 * EL_RANGE) / N_ROWS
    azimuths, elevations = [], []
    for row in range(N_ROWS):
        for col in range(N_COLS):
            az = -AZ_RANGE + (col + 0.5) * az_spacing
            el = -EL_RANGE + (row + 0.5) * el_spacing
            if row % 2 == 1:
                az += az_spacing * 0.5
            azimuths.append(az)
            elevations.append(el)
    return np.array(azimuths), np.array(elevations)

def compute_grating(azimuths, elevations, orientation_deg, tf_hz, t_ms, contrast=1.0):
    dx = np.cos(np.radians(orientation_deg))
    dy = np.sin(np.radians(orientation_deg))
    mag = np.sqrt(dx**2 + dy**2)
    if mag > 0:
        dx, dy = dx / mag, dy / mag
    t_sec = t_ms / 1000.0
    spatial_phase = (2 * np.pi / SPATIAL_PERIOD_DEG) * (dx * azimuths + dy * elevations)
    temporal_phase = 2 * np.pi * tf_hz * t_sec
    return 0.5 + 0.5 * contrast * np.sin(spatial_phase - temporal_phase)

def photon_rate_to_voltage(photon_rate):
    if photon_rate < 1:
        return 0.0
    threshold = 10.0
    gain = 10.0
    return float(np.clip(gain * np.log10(max(photon_rate, threshold) / threshold), 0, 40))

def test_chromatic_motion_blindness(visual_connectome, stimulus_duration_ms=300.0, dt_ms=0.5):
    print("\n" + "─" * 60)
    print("CHROMATIC MOTION BLINDNESS TEST")
    print("─" * 60)
    
    azimuths, elevations = build_ommatidium_positions()
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    
    all_medulla = list(get_visual_region_neurons(visual_connectome, 'MEDULLA'))
    lobula_neurons = list(get_visual_region_neurons(visual_connectome, 'LOBULA'))
    motion_readout = lobula_neurons if len(lobula_neurons) > 10 else all_medulla
    
    num_steps = int(stimulus_duration_ms / dt_ms)
    measurement_start = num_steps // 2
    TF_HZ = 2.0
    
    stimulus_types = {
        'luminance': {'r1r6_contrast': 1.0, 'r7_contrast': 0.0, 'r8_contrast': 0.0},
        'uv_only':   {'r1r6_contrast': 0.0, 'r7_contrast': 1.0, 'r8_contrast': 0.0},
        'visible_only': {'r1r6_contrast': 0.0, 'r7_contrast': 0.0, 'r8_contrast': 1.0},
    }
    
    dsi_results = {}
    
    for stim_name, contrasts in stimulus_types.items():
        print(f"\n  Stimulus: {stim_name}")
        dsi_per_direction = {}
        
        for direction in ['rightward', 'leftward']:
            brain._initialize_fields()
            if brain.use_mlx:
                import mlx.core as mx
                brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
            else:
                brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)
            
            amplitudes_meas = []
            tf_sign = 1.0 if direction == 'rightward' else -1.0
            
            for step in range(num_steps):
                t_ms = step * dt_ms
                luminance = compute_grating(azimuths, elevations, 0.0, TF_HZ * tf_sign, t_ms,
                                            contrast=contrasts['r1r6_contrast'])
                uv_grating = compute_grating(azimuths, elevations, 0.0, TF_HZ * tf_sign, t_ms,
                                             contrast=contrasts['r7_contrast'])
                vis_grating = compute_grating(azimuths, elevations, 0.0, TF_HZ * tf_sign, t_ms,
                                              contrast=contrasts['r8_contrast'])
                
                for i, nid in enumerate(all_medulla):
                    if nid not in brain.id_to_idx:
                        continue
                    omm = i % N_OMMATIDIA
                    lum_v = photon_rate_to_voltage(luminance[omm] * 1e4)
                    idx = brain.id_to_idx[nid]
                    brain.external_force[idx] = lum_v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * 0.01
                
                for i, nid in enumerate(all_medulla[:len(all_medulla) // 2]):
                    if nid not in brain.id_to_idx:
                        continue
                    omm = i % N_OMMATIDIA
                    uv_v = photon_rate_to_voltage(uv_grating[omm] * 1e4)
                    idx = brain.id_to_idx[nid]
                    brain.external_force[idx] += uv_v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN
                
                for i, nid in enumerate(all_medulla[len(all_medulla) // 2:]):
                    if nid not in brain.id_to_idx:
                        continue
                    omm = i % N_OMMATIDIA
                    vis_v = photon_rate_to_voltage(vis_grating[omm] * 1e4)
                    idx = brain.id_to_idx[nid]
                    brain.external_force[idx] += vis_v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN
                
                brain.evolve(duration=dt_ms)
                
                if step >= measurement_start:
                    state = brain.get_state()
                    readout_idx = [brain.id_to_idx[nid] for nid in motion_readout
                                   if nid in brain.id_to_idx]
                    if readout_idx:
                        amplitudes_meas.append(state.mean_amplitude[readout_idx].mean())
            
            dsi_per_direction[direction] = float(np.mean(amplitudes_meas))
        
        pref = dsi_per_direction['rightward']
        null = dsi_per_direction['leftward']
        dsi = (pref - null) / (pref + null + 1e-8)
        dsi_results[stim_name] = {'preferred': pref, 'null': null, 'dsi': dsi}
        print(f"    DSI: {dsi:.4f}")
    
    lum_dsi = dsi_results['luminance']['dsi']
    uv_dsi = dsi_results['uv_only']['dsi']
    vis_dsi = dsi_results['visible_only']['dsi']
    
    motion_blindness_uv = uv_dsi < 0.30
    motion_blindness_vis = vis_dsi < 0.30
    
    results = {
        'luminance_dsi': lum_dsi,
        'uv_only_dsi': uv_dsi,
        'visible_only_dsi': vis_dsi,
        'motion_blindness_uv': motion_blindness_uv,
        'motion_blindness_vis': motion_blindness_vis,
        'pass': motion_blindness_uv and motion_blindness_vis,
        'interpretation': f"Color motion {'blind' if motion_blindness_uv and motion_blindness_vis else 'sensitive'}"
    }
    
    return results

if __name__ == '__main__':
    print("Loading connectome...")
    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()
    
    print("Extracting visual pathway...")
    visual_connectome = extract_visual_pathway(connectome)
    
    print("Running test...")
    results = test_chromatic_motion_blindness(visual_connectome)
    
    output_path = Path("research/vision/findings/chromatic_motion_blindness_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print(f"Luminance DSI: {results['luminance_dsi']:.4f}")
    print(f"UV-only DSI: {results['uv_only_dsi']:.4f}")
    print(f"Visible-only DSI: {results['visible_only_dsi']:.4f}")
    print(f"Pass: {'✅' if results['pass'] else '❌'}")
    print(f"\nResults saved to {output_path}")
