"""
Quick diagnostic: Check actual step timing with batching
"""

import sys
from pathlib import Path
import os
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(str(Path(__file__).resolve().parents[1]))

from hive.main import FlyBrainSystem
from hive.gpu_utils import synchronize

print("="*70)
print("STEP TIMING DIAGNOSTIC")
print("="*70)

# Initialize
print("\nInitializing...")
brain = FlyBrainSystem(config_path=str(Path(__file__).resolve().parents[1] / 'hive' / 'config.yaml'))
print("✓ Initialized")

# Test 1: Sequential steps (what we're trying to replace)
print("\n1. Sequential (with sync after each step):")
t0 = time.time()
for i in range(10):
    brain.step()
    synchronize()  # Force evaluation after each step
t1 = time.time()
seq_time = (t1 - t0) / 10
print(f"   {seq_time*1000:.2f}ms/step")

# Test 2: Batched steps (what we implemented)
print("\n2. Batched (sync after 10 steps):")
t0 = time.time()
for i in range(10):
    brain.step()
# Only sync once at end
synchronize()
t1 = time.time()
batch_time = (t1 - t0) / 10
print(f"   {batch_time*1000:.2f}ms/step (amortized)")
print(f"   Speedup: {seq_time/batch_time:.2f}×")

# Test 3: Larger batch
print("\n3. Larger batch (100 steps):")
t0 = time.time()
for i in range(100):
    brain.step()
synchronize()
t1 = time.time()
large_batch = (t1 - t0) / 100
print(f"   {large_batch*1000:.2f}ms/step (amortized)")
print(f"   Speedup vs sequential: {seq_time/large_batch:.2f}×")

# Test 4: What about just step() without any sync?
print("\n4. No sync at all (100 steps, measure wall time):")
t0 = time.time()
for i in range(100):
    brain.step()
t1 = time.time()
no_sync = (t1 - t0) / 100
print(f"   {no_sync*1000:.2f}ms/step (wall time, deferred)")
print(f"   This is misleading - computation deferred to later sync")

# Test 5: Check if monitoring is the issue
print("\n5. Disable monitoring, batch 100 steps:")
brain._monitoring_enabled = False
t0 = time.time()
for i in range(100):
    brain.step()
synchronize()
t1 = time.time()
no_monitor = (t1 - t0) / 100
brain._monitoring_enabled = True
print(f"   {no_monitor*1000:.2f}ms/step (no monitoring)")
print(f"   Monitoring overhead: {(batch_time/no_monitor - 1)*100:.1f}%")

print("\n" + "="*70)
print("CONCLUSION:")
print(f"  Sequential:        {seq_time*1000:.2f}ms/step")
print(f"  Batched:           {batch_time*1000:.2f}ms/step ({seq_time/batch_time:.1f}× faster)")
print(f"  No monitoring:     {no_monitor*1000:.2f}ms/step ({seq_time/no_monitor:.1f}× faster)")
print(f"\n  For 11M steps:")
print(f"    Sequential:      {seq_time*11e6/3600:.1f} hours")
print(f"    Batched:         {batch_time*11e6/3600:.1f} hours")
print(f"    No monitoring:   {no_monitor*11e6/3600:.1f} hours")
print("="*70)
