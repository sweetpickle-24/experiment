#!/usr/bin/env python3
"""
Quick olfactory demo - shows wave-based smell processing without full brain initialization.

Rewritten against the current 20-channel glomerular interface. The previous
version targeted a retired 50-channel receptor API and could not run: it called
create_odor_library() with an argument the function does not take, then read
Odor.receptor_signature, Odor.frequency_bias and Odor.baseline_amplitude, none
of which exist on the current dataclass, constructed OdorReceptorArray with a
channel count, read receptor_frequencies, indexed the library by 'food' and
'danger', and omitted OdorPlume's required concentration argument.
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

print("=" * 70)
print(" WAVE-BASED OLFACTORY SYSTEM - QUICK DEMO")
print("=" * 70)
print()

# Load config
import yaml

with open("hive/config.yaml") as f:
    config = yaml.safe_load(f)

from hive.interface.olfactory import (
    NUM_GLOM_CHANNELS,
    GLOM_LABELS,
    OdorPlume,
    OdorReceptorArray,
    create_odor_library,
)

# The demo picks two odors from the library by key. These are semantic library
# entries, not DoOR chemical names.
PRIMARY_ODOR = "fruit_ferment"
CONTRAST_ODOR = "danger_mold"

print(f"[1] Creating odor library ({NUM_GLOM_CHANNELS} glomerular channels)...")
odor_library = create_odor_library()

print(f"✓ Created {len(odor_library)} odors:")
for name, odor in odor_library.items():
    active_channels = int(np.sum(odor.glom_pattern > 0.1))
    print(f"  - {name:17s}: family={odor.family:11s} "
          f"{active_channels:2d}/{NUM_GLOM_CHANNELS} channels above 0.1 — {odor.description}")

print()
print("[2] Testing receptor array...")
receptors = OdorReceptorArray(config)
print(f"✓ {receptors.num_channels} channels initialized")
print(f"  Frequency range: {receptors.channel_frequencies.min():.1f} - "
      f"{receptors.channel_frequencies.max():.1f} Hz")

primary = odor_library[PRIMARY_ODOR]
receptors.set_activation(primary.glom_pattern)
print(f"✓ Set activation for '{PRIMARY_ODOR}'")

# Compute forces at different times
print()
print("[3] Testing sinusoidal forcing...")
print("    NOTE: forces below are constant across time. That is a units defect in")
print("    OdorReceptorArray.compute_forces, not a property of the odor: the carrier")
print("    advances f cycles per millisecond instead of per second, so whole-ms")
print("    samples land on the same phase every time. See the docstring there.")
times = [0, 50, 100, 150, 200]  # ms
for t in times:
    forces = receptors.compute_forces(t, amplitude_scale=10.0)
    active_forces = int(np.sum(np.abs(forces) > 0.1))
    mean_force = float(np.mean(np.abs(forces[np.abs(forces) > 0.1]))) if active_forces > 0 else 0.0
    print(f"  t={t:3d}ms: {active_forces} active channels, mean force = {mean_force:.3f}")

print()
print("[4] Testing odor plume dynamics...")
plume = OdorPlume(primary, duration_ms=500.0, concentration=1.0, config=config)
print(f"✓ Generated plume for {plume.duration:.0f}ms at concentration {plume.concentration:.2f}")
print(f"  {plume.num_steps} timesteps")

sample_times = [0, 50, 100, 200, 400]
print("  Concentration samples (first 5 channels):")
for t_ms in sample_times:
    step_idx = int(t_ms / config['oscillator']['dt'])
    if step_idx < plume.num_steps:
        conc = plume.get_concentration(step_idx)
        vals = ", ".join(f"{conc[i]:.3f}" for i in range(5))
        print(f"    t={t_ms:3d}ms: [{vals}]")

print()
print("[5] Testing all odors - Pattern Comparison")
print("-" * 70)
print(f"{'Odor':17s} {'Active Channels':>17s} {'Mean Activation':>17s} {'Family':>12s}")
print("-" * 70)

for name, odor in odor_library.items():
    active = int(np.sum(odor.glom_pattern > 0.1))
    mean_act = float(np.mean(odor.glom_pattern[odor.glom_pattern > 0.1])) if active > 0 else 0.0
    print(f"{name:17s} {active:>17d} {mean_act:>17.3f} {odor.family:>12s}")

print()
print("[6] Pattern Similarity Matrix")
print("-" * 70)

odor_names = list(odor_library.keys())
print(f"{'':17s}", end="")
for name in odor_names:
    print(f"{name[:10]:>12s}", end="")
print()

for name1 in odor_names:
    print(f"{name1[:17]:17s}", end="")
    sig1 = odor_library[name1].glom_pattern
    sig1_norm = sig1 / (np.linalg.norm(sig1) + 1e-10)

    for name2 in odor_names:
        sig2 = odor_library[name2].glom_pattern
        sig2_norm = sig2 / (np.linalg.norm(sig2) + 1e-10)
        similarity = float(np.dot(sig1_norm, sig2_norm))
        print(f"{similarity:>12.3f}", end="")
    print()

print()
print(f"[7] Wave Forcing Example - '{CONTRAST_ODOR}' odor")
print("-" * 70)

contrast = odor_library[CONTRAST_ODOR]
receptors.set_activation(contrast.glom_pattern)

print(f"Odor: {contrast.name}")
print(f"Family: {contrast.family}")
print(f"Description: {contrast.description}")
print(f"Peak channel activation: {contrast.glom_pattern.max():.3f}")
print()

# Show wave forcing over 100ms for the three most strongly activated channels
top_channels = np.argsort(contrast.glom_pattern)[-3:]
print("Wave forcing over time (channels with highest activation):")
for c in top_channels:
    print(f"  channel {c:2d} ({GLOM_LABELS[c]}): activation={contrast.glom_pattern[c]:.3f}, "
          f"{receptors.channel_frequencies[c]:.1f} Hz")
print()

print(f"{'Time (ms)':>10s}", end="")
for c in top_channels:
    print(f"{'ch' + str(c):>12s}", end="")
print()

for t in range(0, 101, 10):
    forces = receptors.compute_forces(t, amplitude_scale=10.0)
    print(f"{t:>10.0f}", end="")
    for c in top_channels:
        print(f"{forces[c]:>12.3f}", end="")
    print()

print()
print("=" * 70)
print(" WAVE-BASED OLFACTORY DEMO COMPLETE")
print("=" * 70)
print()
print("Demonstrated:")
print("  - Sinusoidal forcing at channel-specific frequencies")
print("  - Turbulent plume dynamics (whiff train plus noise)")
print(f"  - {len(odor_library)} odor patterns over {NUM_GLOM_CHANNELS} glomerular channels")
print("  - Pairwise pattern similarity")
print("  - Wave forcing over time")
print()
