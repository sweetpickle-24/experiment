#!/usr/bin/env python3
"""Quick test of GPU engines without loading full connectome."""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

print("Testing GPU engines with synthetic data...")

from hive.gpu_utils import GPU_AVAILABLE
from hive.engine.oscillator_gpu import OscillatorEngineGPU
from hive.engine.coupling_gpu import CouplingEngineGPU

print(f"\n[1] GPU Status: {'✓ Available' if GPU_AVAILABLE else '✗ Not available (CPU fallback)'}")

# Test oscillator
print("\n[2] Testing OscillatorEngineGPU")
print("-" * 50)

num_neurons = 1000
config = {
    'oscillator': {
        'dt': 0.1,
        'damping_default': 0.1,
        'phase_init_random': True,
        'amplitude_init': 1.0,
        'use_delays': False
    }
}

osc = OscillatorEngineGPU(num_neurons, config)
print(f"✓ Created oscillator with {num_neurons} neurons")

# Set frequencies
freqs = 2 * np.pi * np.random.uniform(5, 50, num_neurons)
osc.set_frequencies(freqs)
print("✓ Set frequencies")

# Add some forces
forces = np.random.uniform(-0.1, 0.1, num_neurons)
osc.add_external_force(forces)
print("✓ Added forces")

# Run steps
for i in range(10):
    osc.step()
print(f"✓ Ran 10 integration steps")

state = osc.get_state()
print(f"  Phase range: [{state['phase'].min():.3f}, {state['phase'].max():.3f}]")
print(f"  Amplitude mean: {state['amplitude'].mean():.3f}")
print(f"  Energy: {osc.get_energy():.1f}")

# Test coupling
print("\n[3] Testing CouplingEngineGPU")
print("-" * 50)

# Create synthetic connectome
class SyntheticSynapse:
    def __init__(self, pre_id, post_id, weight, nt_type):
        self.pre_id = pre_id
        self.post_id = post_id
        self.weight = weight
        self.nt_type = nt_type

class SyntheticConnectome:
    def __init__(self, num_neurons, num_synapses):
        self.neurons = {i: f"neuron_{i}" for i in range(num_neurons)}
        self.synapses = []
        
        np.random.seed(42)
        for _ in range(num_synapses):
            pre = np.random.randint(0, num_neurons)
            post = np.random.randint(0, num_neurons)
            weight = np.random.uniform(10, 100)
            nt = np.random.choice(['ACH', 'GABA', 'GLUT'])
            self.synapses.append(SyntheticSynapse(pre, post, weight, nt))

num_synapses = 10000
config['neurotransmitters'] = {
    'ach': {'phase_offset': 0},
    'gaba': {'phase_offset': 180},
    'glut': {'phase_offset': 0}
}

connectome = SyntheticConnectome(num_neurons, num_synapses)
print(f"✓ Created synthetic connectome: {num_neurons} neurons, {num_synapses} synapses")

coupling = CouplingEngineGPU(connectome, config)
print("✓ Built coupling matrices")

# Compute forces
phase = state['phase']
amplitude = state['amplitude']
forces = coupling.compute_coupling_forces(phase, amplitude)
print(f"✓ Computed coupling forces")
print(f"  Force range: [{forces.min():.3f}, {forces.max():.3f}]")
print(f"  Force mean: {forces.mean():.3f}")

# Test modulation
coupling.modulate_coupling(1.2, np.array([0, 1, 2]))
print("✓ Tested weight modulation")

# Test memory operations
weights = coupling.snapshot_weights()
print(f"✓ Snapshotted weights: {len(weights)} values")

coupling.restore_weights(weights)
print("✓ Restored weights")

print("\n" + "="*50)
print("✓ All GPU engine tests passed!")
print("="*50)

if not GPU_AVAILABLE:
    print("\nNote: Tests ran in CPU fallback mode.")
    print("Install CuPy for GPU acceleration:")
    print("  pip install cupy-cuda12x")
