"""
Profile one simulation step to see where the time goes.
"""

import sys
import time
import numpy as np

sys.path.insert(0, '/Users/vladyslav/Documents/GitHub/experiment')
import os
os.chdir('/Users/vladyslav/Documents/GitHub/experiment')

from hive.main import FlyBrainSystem
from hive.gpu_utils import synchronize, MLX_AVAILABLE

print("="*70)
print("PROFILING SINGLE SIMULATION STEP")
print("="*70)

# Initialize system
print("\nInitializing fly brain...")
t0 = time.time()
brain = FlyBrainSystem(config_path='/Users/vladyslav/Documents/GitHub/experiment/hive/config.yaml')
t1 = time.time()
print(f"✓ Initialized in {t1-t0:.1f}s")

# Warm-up (MLX compile time)
print("\nWarming up (5 steps for compilation)...")
for i in range(5):
    brain.step()
synchronize()
print("✓ Warmed up")

# Profile full steps
print("\n" + "="*70)
print("PROFILING FULL STEPS")
print("="*70)

t0 = time.time()
for i in range(100):
    brain.step()
synchronize()
t1 = time.time()

time_per_step = (t1 - t0) / 100
steps_per_sec = 100 / (t1 - t0)

print(f"\nTime per step:    {time_per_step*1000:.2f}ms")
print(f"Steps per second: {steps_per_sec:.1f}")
print(f"\n  For 11M steps: {time_per_step*11e6/3600:.1f} hours")
print(f"  For 1M steps:  {time_per_step*1e6/60:.1f} minutes")

# Profile scatter-add specifically  
print("\n" + "="*70)
print("SCATTER-ADD PROFILING")
print("="*70)

from hive.gpu_utils import scatter_add, zeros

if MLX_AVAILABLE:
    import mlx.core as mx
    
    # Test full-scale scatter-add (what coupling does each step)
    n_updates = 5342446  # All synapses
    n_targets = 139255   # All neurons
    
    target = zeros(n_targets, dtype=np.float32)
    indices = mx.array(np.random.randint(0, n_targets, n_updates), dtype=mx.int32)
    values = mx.random.normal(shape=(n_updates,), dtype=mx.float32) * 0.001
    
    # Warm-up
    for _ in range(3):
        result = scatter_add(target, indices, values)
    synchronize()
    
    # Time it
    t0 = time.time()
    for _ in range(10):
        result = scatter_add(target, indices, values)
    synchronize()
    t1 = time.time()
    
    scatter_time = (t1 - t0) / 10
    print(f"\nFull scatter-add ({n_updates:,} updates): {scatter_time*1000:.2f}ms")
    print(f"  This is {scatter_time/time_per_step*100:.1f}% of step time")

print("\n" + "="*70)
