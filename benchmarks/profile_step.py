"""
Profile one simulation step to see where the time goes.
"""

import sys
from pathlib import Path
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
os.chdir(str(Path(__file__).resolve().parents[1]))

from hive.main import FlyBrainSystem
from hive.gpu_utils import synchronize, MLX_AVAILABLE

print("="*70)
print("PROFILING SINGLE SIMULATION STEP")
print("="*70)

# Initialize system
print("\nInitializing fly brain...")
t0 = time.time()
brain = FlyBrainSystem(config_path=str(Path(__file__).resolve().parents[1] / 'hive' / 'config.yaml'))
t1 = time.time()
print(f"✓ Initialized in {t1-t0:.1f}s")

# Profile one step
print("\n" + "="*70)
print("PROFILING BREAKDOWN OF ONE STEP")
print("="*70)

# Warm-up (MLX needs compile time)
for _ in range(5):
    brain.step()

# Profile individual components
print("\n1. Oscillator step (without coupling):")
t0 = time.time()
for _ in range(10):
    # Just the oscillator dynamics
    brain.oscillator.external_force.fill(0.0)
    
    # Compute acceleration
    total_force = brain.oscillator.external_force
    if MLX_AVAILABLE:
        import mlx.core as mx
        acceleration = total_force - 2.0 * brain.oscillator.gamma * brain.oscillator.velocity - brain.oscillator.omega0**2 * mx.sin(brain.oscillator.phase)
    
    # Verlet integration
    brain.oscillator.velocity += 0.5 * acceleration * brain.oscillator.dt
    brain.oscillator.phase += brain.oscillator.velocity * brain.oscillator.dt
    
    if MLX_AVAILABLE:
        brain.oscillator.phase = mx.arctan2(mx.sin(brain.oscillator.phase), mx.cos(brain.oscillator.phase))
        acceleration = total_force - 2.0 * brain.oscillator.gamma * brain.oscillator.velocity - brain.oscillator.omega0**2 * mx.sin(brain.oscillator.phase)
    
    brain.oscillator.velocity += 0.5 * acceleration * brain.oscillator.dt
    brain.oscillator.amplitude *= mx.exp(-brain.oscillator.gamma * brain.oscillator.dt) if MLX_AVAILABLE else np.exp(-brain.oscillator.gamma * brain.oscillator.dt)

synchronize()
t1 = time.time()
time_oscillator = (t1 - t0) / 10
print(f"   {time_oscillator*1000:.2f}ms per step")

# Profile coupling
print("\n2. Coupling computation:")
t0 = time.time()
for _ in range(10):
    forces = brain.coupling.compute_coupling_forces(
        brain.oscillator.phase,
        brain.oscillator.amplitude
    )
synchronize()
t1 = time.time()
time_coupling = (t1 - t0) / 10
print(f"   {time_coupling*1000:.2f}ms per step")

# Profile full step
print("\n3. Full step (oscillator + coupling + modulation + monitoring):")
t0 = time.time()
for _ in range(10):
    brain.step()
synchronize()
t1 = time.time()
time_full = (t1 - t0) / 10
print(f"   {time_full*1000:.2f}ms per step")

# Breakdown
print("\n" + "="*70)
print("TIME BREAKDOWN")
print("="*70)
print(f"Oscillator dynamics:    {time_oscillator*1000:7.2f}ms  ({time_oscillator/time_full*100:5.1f}%)")
print(f"Coupling forces:        {time_coupling*1000:7.2f}ms  ({time_coupling/time_full*100:5.1f}%)")
print(f"Other (modulation etc): {(time_full-time_oscillator-time_coupling)*1000:7.2f}ms  ({(time_full-time_oscillator-time_coupling)/time_full*100:5.1f}%)")
print(f"{'='*30}")
print(f"Total per step:         {time_full*1000:7.2f}ms")
print(f"\nFor 11M steps: {time_full*11e6/3600:.1f} hours")

# Profile scatter-add specifically
print("\n" + "="*70)
print("SCATTER-ADD PROFILING")
print("="*70)

from hive.gpu_utils import scatter_add, zeros, to_gpu

if MLX_AVAILABLE:
    import mlx.core as mx
    
    # Test different scatter-add sizes
    for n_updates in [1000, 10000, 100000, 1000000, 5342446]:
        target = zeros(139255, dtype=np.float32)
        indices = mx.array(np.random.randint(0, 139255, n_updates), dtype=mx.int32)
        values = mx.random.normal(shape=(n_updates,), dtype=mx.float32) * 0.001
        
        t0 = time.time()
        result = scatter_add(target, indices, values)
        synchronize()
        t1 = time.time()
        
        print(f"{n_updates:>10,} updates: {(t1-t0)*1000:7.2f}ms")

print("\n" + "="*70)
