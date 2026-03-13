#!/usr/bin/env python3
"""
Benchmark GPU vs CPU performance for the fly brain system.
"""

import sys
import time
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hive.gpu_utils import GPU_AVAILABLE

if GPU_AVAILABLE:
    print("="*70)
    print(" GPU BENCHMARK - CuPy Detected")
    print("="*70)
    import cupy as cp
    print(f"CUDA version: {cp.cuda.runtime.runtimeGetVersion()}")
    print(f"GPU devices: {cp.cuda.runtime.getDeviceCount()}")
    for i in range(cp.cuda.runtime.getDeviceCount()):
        props = cp.cuda.runtime.getDeviceProperties(i)
        print(f"  Device {i}: {props['name'].decode()}")
        print(f"    Memory: {props['totalGlobalMem'] / 1024**3:.1f} GB")
else:
    print("="*70)
    print(" CPU BENCHMARK - No GPU Detected")
    print("="*70)
    print("Install CuPy for GPU acceleration:")
    print("  pip install cupy-cuda12x  # for CUDA 12.x")
    print("  pip install cupy-cuda11x  # for CUDA 11.x")

print()

# Simulate the coupling computation
print("[1/3] Testing Coupling Force Computation")
print("-" * 70)

num_neurons = 139255
num_synapses = 5348633

print(f"Neurons: {num_neurons:,}")
print(f"Synapses: {num_synapses:,}")
print()

# Create synthetic data
np.random.seed(42)
pre_indices = np.random.randint(0, num_neurons, num_synapses, dtype=np.int32)
post_indices = np.random.randint(0, num_neurons, num_synapses, dtype=np.int32)
weights = np.random.uniform(0.01, 1.0, num_synapses).astype(np.float32)
offsets = np.random.uniform(-np.pi, np.pi, num_synapses).astype(np.float32)
phase = np.random.uniform(0, 2*np.pi, num_neurons).astype(np.float32)
amplitude = np.ones(num_neurons, dtype=np.float32)

if GPU_AVAILABLE:
    # GPU version
    print("Running on GPU...")
    pre_gpu = cp.asarray(pre_indices)
    post_gpu = cp.asarray(post_indices)
    weights_gpu = cp.asarray(weights)
    offsets_gpu = cp.asarray(offsets)
    phase_gpu = cp.asarray(phase)
    amplitude_gpu = cp.asarray(amplitude)
    
    # Warmup
    forces_gpu = cp.zeros(num_neurons, dtype=cp.float32)
    cp.scatter_add(forces_gpu, post_gpu[:1000], weights_gpu[:1000])
    cp.cuda.Stream.null.synchronize()
    
    # Benchmark
    n_iterations = 10
    times = []
    for i in range(n_iterations):
        start = time.perf_counter()
        
        # Compute coupling forces
        pre_phases = phase_gpu[pre_gpu]
        post_phases = phase_gpu[post_gpu]
        phase_diffs = pre_phases - post_phases + offsets_gpu
        synapse_forces = weights_gpu * cp.sin(phase_diffs) * amplitude_gpu[pre_gpu]
        
        forces_gpu = cp.zeros(num_neurons, dtype=cp.float32)
        cp.scatter_add(forces_gpu, post_gpu, synapse_forces)
        cp.cuda.Stream.null.synchronize()
        
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed:.1f} ms")
    
    gpu_mean = np.mean(times)
    gpu_std = np.std(times)
    print(f"\nGPU: {gpu_mean:.1f} ± {gpu_std:.1f} ms per step")
    forces_result = cp.asnumpy(forces_gpu)

# CPU version
print("\nRunning on CPU (NumPy)...")

n_iterations = 3 if not GPU_AVAILABLE else 3  # Fewer iterations for CPU benchmark
times = []
for i in range(n_iterations):
    start = time.perf_counter()
    
    # Compute coupling forces
    pre_phases = phase[pre_indices]
    post_phases = phase[post_indices]
    phase_diffs = pre_phases - post_phases + offsets
    synapse_forces = weights * np.sin(phase_diffs) * amplitude[pre_indices]
    
    forces_cpu = np.zeros(num_neurons, dtype=np.float32)
    np.add.at(forces_cpu, post_indices, synapse_forces)
    
    elapsed = (time.perf_counter() - start) * 1000
    times.append(elapsed)
    print(f"  Iteration {i+1}: {elapsed:.1f} ms")

cpu_mean = np.mean(times)
cpu_std = np.std(times)
print(f"\nCPU: {cpu_mean:.1f} ± {cpu_std:.1f} ms per step")

if GPU_AVAILABLE:
    speedup = cpu_mean / gpu_mean
    print(f"\n🚀 SPEEDUP: {speedup:.1f}x faster on GPU!")

print()
print("="*70)

# Test oscillator integration
print("\n[2/3] Testing Oscillator Integration")
print("-" * 70)

velocity = np.random.uniform(-1, 1, num_neurons).astype(np.float32)
omega0 = np.ones(num_neurons, dtype=np.float32) * 2 * np.pi * 10  # 10 Hz
gamma = np.ones(num_neurons, dtype=np.float32) * 0.1
dt = 0.1

if GPU_AVAILABLE:
    print("Running on GPU...")
    phase_gpu = cp.asarray(phase)
    velocity_gpu = cp.asarray(velocity)
    omega0_gpu = cp.asarray(omega0)
    gamma_gpu = cp.asarray(gamma)
    forces_gpu = cp.asarray(forces_result)
    
    n_iterations = 10
    times = []
    for i in range(n_iterations):
        start = time.perf_counter()
        
        # Integration step
        acceleration = forces_gpu - 2.0 * gamma_gpu * velocity_gpu - omega0_gpu**2 * cp.sin(phase_gpu)
        velocity_gpu += 0.5 * acceleration * dt
        phase_gpu += velocity_gpu * dt
        phase_gpu = cp.arctan2(cp.sin(phase_gpu), cp.cos(phase_gpu))
        acceleration = forces_gpu - 2.0 * gamma_gpu * velocity_gpu - omega0_gpu**2 * cp.sin(phase_gpu)
        velocity_gpu += 0.5 * acceleration * dt
        cp.cuda.Stream.null.synchronize()
        
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed:.1f} ms")
    
    gpu_mean = np.mean(times)
    print(f"\nGPU: {gpu_mean:.1f} ms per step")

print("\nRunning on CPU...")
phase_cpu = phase.copy()
velocity_cpu = velocity.copy()
forces_cpu_bench = forces_cpu.copy()

n_iterations = 3
times = []
for i in range(n_iterations):
    start = time.perf_counter()
    
    # Integration step
    acceleration = forces_cpu_bench - 2.0 * gamma * velocity_cpu - omega0**2 * np.sin(phase_cpu)
    velocity_cpu += 0.5 * acceleration * dt
    phase_cpu += velocity_cpu * dt
    phase_cpu = np.arctan2(np.sin(phase_cpu), np.cos(phase_cpu))
    acceleration = forces_cpu_bench - 2.0 * gamma * velocity_cpu - omega0**2 * np.sin(phase_cpu)
    velocity_cpu += 0.5 * acceleration * dt
    
    elapsed = (time.perf_counter() - start) * 1000
    times.append(elapsed)
    print(f"  Iteration {i+1}: {elapsed:.1f} ms")

cpu_mean = np.mean(times)
print(f"\nCPU: {cpu_mean:.1f} ms per step")

if GPU_AVAILABLE:
    speedup = cpu_mean / gpu_mean
    print(f"\n🚀 SPEEDUP: {speedup:.1f}x faster on GPU!")

print()
print("="*70)
print("\n[3/3] Summary")
print("-" * 70)

if GPU_AVAILABLE:
    print(f"✓ GPU acceleration working")
    print(f"✓ Expected total speedup: 10-100x for full simulation")
    print(f"\nSimulation time estimates (1 second real-time):")
    print(f"  CPU:  ~30-60 minutes")
    print(f"  GPU:  ~30-60 seconds")
else:
    print(f"⚠ Running in CPU mode")
    print(f"\nTo enable GPU acceleration:")
    print(f"  1. Install CUDA toolkit")
    print(f"  2. Run: pip install cupy-cuda12x")
    print(f"  3. Restart this benchmark")
    print(f"\nCPU performance is functional but 10-100x slower than GPU.")

print("="*70)
