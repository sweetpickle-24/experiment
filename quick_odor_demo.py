#!/usr/bin/env python3
"""
Quick olfactory demo - shows wave-based smell processing without full brain initialization.
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print(" WAVE-BASED OLFACTORY SYSTEM - QUICK DEMO")
print("="*70)
print()

# Load config
import yaml
with open("hive/config.yaml") as f:
    config = yaml.safe_load(f)

# Create odor library
from hive.interface.olfactory import create_odor_library

print("[1] Creating 5 test odors...")
odor_library = create_odor_library(config['olfactory']['receptors']['num_channels'])

print(f"✓ Created {len(odor_library)} odors:")
for name, odor in odor_library.items():
    active_receptors = np.sum(odor.receptor_signature > 0.1)
    print(f"  - {name:15s}: {odor.frequency_bias:5s} band ({odor.baseline_amplitude:.2f} amplitude, {active_receptors} receptors)")

print()
print("[2] Testing receptor array...")
from hive.interface.olfactory import OdorReceptorArray

receptors = OdorReceptorArray(50, config)
print(f"✓ {receptors.num_channels} receptors initialized")
print(f"  Frequency range: {receptors.receptor_frequencies.min():.1f} - {receptors.receptor_frequencies.max():.1f} Hz")

# Set food odor
food_odor = odor_library['food']
receptors.set_activation(food_odor.receptor_signature)
print(f"✓ Set activation for 'food' odor")

# Compute forces at different times
print()
print("[3] Testing sinusoidal forcing...")
times = [0, 50, 100, 150, 200]  # ms
for t in times:
    forces = receptors.compute_forces(t, amplitude_scale=10.0)
    active_forces = np.sum(np.abs(forces) > 0.1)
    mean_force = np.mean(np.abs(forces[np.abs(forces) > 0.1])) if active_forces > 0 else 0
    print(f"  t={t:3d}ms: {active_forces} active channels, mean force = {mean_force:.3f}")

print()
print("[4] Testing odor plume dynamics...")
from hive.interface.olfactory import OdorPlume

plume = OdorPlume(food_odor, duration_ms=500, config=config)
print(f"✓ Generated plume for {plume.duration:.0f}ms")
print(f"  {plume.num_steps} timesteps")

# Sample concentrations
sample_times = [0, 50, 100, 200, 400]
print("  Concentration samples (first 5 receptors):")
for t_ms in sample_times:
    step_idx = int(t_ms / config['oscillator']['dt'])
    if step_idx < plume.num_steps:
        conc = plume.get_concentration(step_idx)
        print(f"    t={t_ms:3d}ms: [{conc[0]:.3f}, {conc[1]:.3f}, {conc[2]:.3f}, {conc[3]:.3f}, {conc[4]:.3f}]")

print()
print("[5] Testing all odors - Pattern Comparison")
print("-" * 70)

# Compare receptor signatures
print(f"{'Odor':15s} {'Active Receptors':>18s} {'Mean Activation':>18s} {'Freq Band':>12s}")
print("-" * 70)

for name, odor in odor_library.items():
    active = np.sum(odor.receptor_signature > 0.1)
    mean_act = np.mean(odor.receptor_signature[odor.receptor_signature > 0.1]) if active > 0 else 0
    print(f"{name:15s} {active:>18d} {mean_act:>18.3f} {odor.frequency_bias:>12s}")

print()
print("[6] Pattern Similarity Matrix")
print("-" * 70)

# Compute cosine similarity between odor signatures
odor_names = list(odor_library.keys())
print(f"{'':15s}", end="")
for name in odor_names:
    print(f"{name[:10]:>12s}", end="")
print()

for name1 in odor_names:
    print(f"{name1[:15]:15s}", end="")
    sig1 = odor_library[name1].receptor_signature
    sig1_norm = sig1 / (np.linalg.norm(sig1) + 1e-10)
    
    for name2 in odor_names:
        sig2 = odor_library[name2].receptor_signature
        sig2_norm = sig2 / (np.linalg.norm(sig2) + 1e-10)
        similarity = np.dot(sig1_norm, sig2_norm)
        print(f"{similarity:>12.3f}", end="")
    print()

print()
print("[7] Wave Forcing Example - 'danger' odor")
print("-" * 70)

danger_odor = odor_library['danger']
receptors.set_activation(danger_odor.receptor_signature)

print(f"Odor: {danger_odor.name}")
print(f"Amplitude: {danger_odor.baseline_amplitude}")
print(f"Frequency bias: {danger_odor.frequency_bias} band")
print()

# Show wave forcing over 100ms
print("Wave forcing over time (receptor channels with highest activation):")
top_receptors = np.argsort(danger_odor.receptor_signature)[-3:]  # Top 3
print(f"Tracking receptors: {top_receptors.tolist()}")
print()

print(f"{'Time (ms)':>10s}", end="")
for r in top_receptors:
    print(f"{'R'+str(r):>12s}", end="")
print()

for t in range(0, 101, 10):
    forces = receptors.compute_forces(t, amplitude_scale=10.0)
    print(f"{t:>10.0f}", end="")
    for r in top_receptors:
        print(f"{forces[r]:>12.3f}", end="")
    print()

print()
print("="*70)
print(" WAVE-BASED OLFACTORY DEMO COMPLETE")
print("="*70)
print()
print("Key Features Demonstrated:")
print("  ✓ Sinusoidal forcing (frequency-specific)")
print("  ✓ Turbulent plume dynamics (pulsed + noisy)")
print("  ✓ 5 distinct odor patterns")
print("  ✓ Pattern discrimination")
print("  ✓ Wave forcing over time")
print()
print("This is the BACKEND olfactory processing that will drive the fly's mind!")
print("Different odors → different wave patterns → different neural responses")
print()
