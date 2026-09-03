"""
Benchmark: CPU vs GPU scatter-add performance
Tests the actual speedup from native MLX array.at[].add()
"""

import numpy as np
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except:
    MLX_AVAILABLE = False
    print("MLX not available!")
    sys.exit(1)

print("="*70)
print("SCATTER-ADD PERFORMANCE BENCHMARK")
print("Testing CPU (numpy) vs GPU (MLX native)")
print("="*70)

# Realistic test case: 5.3M synapses → 139K neurons
n_targets = 139255
n_updates = 5342446

print(f"\nTest parameters:")
print(f"  Targets: {n_targets:,} neurons")
print(f"  Updates: {n_updates:,} synapses")
print(f"  Typical: Multiple synapses per neuron (duplicates)")

# Generate test data
print("\nGenerating test data...")
indices_np = np.random.randint(0, n_targets, n_updates, dtype=np.int32)
values_np = np.random.randn(n_updates).astype(np.float32) * 0.001

# Convert to MLX
indices_mx = mx.array(indices_np)
values_mx = mx.array(values_np)

print("✓ Data generated")

# Test 1: CPU method (current implementation)
print("\n" + "="*70)
print("METHOD 1: CPU (numpy.add.at with GPU→CPU→GPU transfers)")
print("="*70)

target_np = np.zeros(n_targets, dtype=np.float32)
target_mx = mx.array(target_np)

# Warm-up
for _ in range(3):
    result_np = np.array(target_mx)
    np.add.at(result_np, indices_np, values_np)
    result_mx = mx.array(result_np)
    mx.eval(result_mx)

# Benchmark
t0 = time.time()
for _ in range(10):
    # This is what the old code does:
    result_np = np.array(target_mx)  # GPU → CPU
    np.add.at(result_np, indices_np, values_np)  # CPU compute
    result_mx = mx.array(result_np)  # CPU → GPU
    mx.eval(result_mx)
t1 = time.time()

time_cpu = (t1 - t0) / 10
print(f"Average time: {time_cpu*1000:.2f}ms per operation")
print(f"Throughput: {n_updates/time_cpu/1e6:.2f}M updates/sec")

# Test 2: GPU native method (new implementation)
print("\n" + "="*70)
print("METHOD 2: GPU Native (MLX array.at[].add())")
print("="*70)

target_mx = mx.zeros(n_targets, dtype=mx.float32)

# Warm-up
for _ in range(3):
    result = target_mx.at[indices_mx].add(values_mx)
    mx.eval(result)

# Benchmark
t0 = time.time()
for _ in range(10):
    # This is what the new code does:
    result = target_mx.at[indices_mx].add(values_mx)
    mx.eval(result)
t1 = time.time()

time_gpu = (t1 - t0) / 10
print(f"Average time: {time_gpu*1000:.2f}ms per operation")
print(f"Throughput: {n_updates/time_gpu/1e6:.2f}M updates/sec")

# Comparison
print("\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"CPU method:    {time_cpu*1000:8.2f}ms")
print(f"GPU native:    {time_gpu*1000:8.2f}ms")
print(f"Speedup:       {time_cpu/time_gpu:8.2f}×")
print(f"\nFor 11M steps:")
print(f"  CPU:    {time_cpu*11e6/3600:6.1f} hours")
print(f"  GPU:    {time_gpu*11e6/3600:6.1f} hours")
print(f"  Saved:  {(time_cpu-time_gpu)*11e6/3600:6.1f} hours")
print("="*70)
