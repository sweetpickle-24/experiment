"""
Batched simulation: execute multiple steps in parallel for GPU efficiency.
"""

import sys
import os
sys.path.insert(0, '/Users/vladyslav/Documents/GitHub/experiment')
os.chdir('/Users/vladyslav/Documents/GitHub/experiment')

import mlx.core as mx
import numpy as np
from hive.gpu_utils import synchronize


def step_batched(brain, n_steps=100):
    """
    Execute multiple simulation steps in batched GPU operations.
    
    Instead of: step() → sync → step() → sync → ...
    Do: build_graph(100 steps) → execute_once → sync
    
    This allows MLX to:
    1. Fuse operations across steps
    2. Minimize CPU-GPU synchronization
    3. Build larger compute graphs for better Metal utilization
    
    Returns: Number of steps actually executed
    """
    # Disable monitoring during batched execution (monitor only at end)
    orig_monitoring = getattr(brain, '_monitoring_enabled', True)
    brain._monitoring_enabled = False
    
    try:
        # Execute n_steps without intermediate syncs
        for i in range(n_steps):
            # Standard step but defer evaluation
            coupling_force = brain.coupling.compute_coupling_forces(
                brain.oscillator.phase,
                brain.oscillator.amplitude
            )
            brain.oscillator.set_coupling_force(coupling_force)
            
            # Modulation
            modulated_omega = brain.neuromodulation.compute_modulated_omega()
            modulated_gamma = brain.neuromodulation.compute_modulated_gamma()
            brain.oscillator.set_frequencies(modulated_omega)
            brain.oscillator.set_damping(modulated_gamma)
            
            # Oscillator step (this builds MLX compute graph without executing)
            brain.oscillator.step()
            
            brain.step_count += 1
            brain.current_time += brain.oscillator.dt
        
        # Now force evaluation of entire batched graph
        synchronize()
        
        return n_steps
        
    finally:
        # Re-enable monitoring
        brain._monitoring_enabled = orig_monitoring


def run_experiment_batched(brain, total_steps, batch_size=100, progress_callback=None):
    """
    Run simulation with batched execution for maximum GPU efficiency.
    
    Args:
        brain: FlyBrainSystem instance
        total_steps: Total simulation steps to execute
        batch_size: Number of steps per batch (larger = better GPU utilization)
        progress_callback: Optional callback(completed_steps, total_steps)
    
    Returns: Total steps executed
    """
    completed = 0
    
    while completed < total_steps:
        remaining = total_steps - completed
        current_batch = min(batch_size, remaining)
        
        # Execute batch
        executed = step_batched(brain, current_batch)
        completed += executed
        
        # Progress callback
        if progress_callback:
            progress_callback(completed, total_steps)
    
    return completed


# Benchmark
if __name__ == "__main__":
    import sys
    import time
    sys.path.insert(0, '/Users/vladyslav/Documents/GitHub/experiment')
    import os
    os.chdir('/Users/vladyslav/Documents/GitHub/experiment')
    
    from hive.main import FlyBrainSystem
    
    print("="*70)
    print("BATCHED EXECUTION BENCHMARK")
    print("="*70)
    
    # Initialize
    print("\nInitializing brain...")
    brain = FlyBrainSystem(config_path='/Users/vladyslav/Documents/GitHub/experiment/hive/config.yaml')
    print("✓ Initialized")
    
    # Warm-up
    print("\nWarming up...")
    for _ in range(10):
        brain.step()
    synchronize()
    
    # Test 1: Standard sequential execution
    print("\n1. Sequential execution (100 steps):")
    t0 = time.time()
    for _ in range(100):
        brain.step()
    synchronize()
    t1 = time.time()
    time_sequential = t1 - t0
    print(f"   Time: {time_sequential:.3f}s ({time_sequential/100*1000:.2f}ms/step)")
    
    # Test 2: Batched execution
    print("\n2. Batched execution (100 steps, batch_size=100):")
    t0 = time.time()
    step_batched(brain, 100)
    t1 = time.time()
    time_batched = t1 - t0
    print(f"   Time: {time_batched:.3f}s ({time_batched/100*1000:.2f}ms/step)")
    print(f"   Speedup: {time_sequential/time_batched:.2f}×")
    
    # Test 3: Different batch sizes
    print("\n3. Batch size scaling:")
    for batch_size in [10, 50, 100, 200, 500]:
        t0 = time.time()
        step_batched(brain, batch_size)
        t1 = time.time()
        time_per_step = (t1 - t0) / batch_size
        print(f"   Batch {batch_size:3d}: {time_per_step*1000:.2f}ms/step")
    
    print("\n" + "="*70)
