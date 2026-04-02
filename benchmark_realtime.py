"""
Real-time performance benchmark for SparseProbabilisticBrain.

Tests three configurations on the olfactory pathway (10,906 neurons):
  1. Interpreted MLX   dt=0.1ms  (original baseline)
  2. Compiled   MLX   dt=0.1ms  (mx.compile only)
  3. Compiled   MLX   dt=0.5ms  (compile + fast_mode)

Target: RT factor >= 1.0 (simulation faster than biological time).

Usage:
    python benchmark_realtime.py
"""

import sys
import time
import numpy as np

# ── Load connectome (olfactory subgraph only) ────────────────────────
print("Loading olfactory subgraph...")
t0 = time.perf_counter()

from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway

full_connectome = Connectome(data_dir="Fly Brain Female")
full_connectome.load()
connectome = extract_olfactory_pathway(full_connectome)
print(f"  Subgraph: {len(connectome.neurons):,} neurons, "
      f"{len(connectome.synapses):,} synapses  "
      f"({time.perf_counter()-t0:.1f}s)")

BIO_MS    = 100.0   # biological time to simulate per benchmark run
WARMUP_MS = 20.0    # warmup to trigger JIT compilation before measuring

results = []

# ── Configuration 1: Interpreted MLX, dt=0.1 ms (baseline) ──────────
print("\n" + "="*60)
print("Config 1: Interpreted MLX, dt=0.1 ms  (original baseline)")
print("="*60)
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain

brain1 = SparseProbabilisticBrain(connectome, use_mlx=True, fast_mode=False)
brain1._compiled_step = None   # disable compile path for fair baseline

# Warmup (not timed)
brain1.reset(deterministic=True)
brain1.evolve(WARMUP_MS)

r1 = brain1.benchmark(BIO_MS)
results.append(("Interpreted MLX  dt=0.1ms", r1))

# ── Configuration 2: Compiled MLX, dt=0.1 ms ────────────────────────
print("\n" + "="*60)
print("Config 2: Compiled MLX, dt=0.1 ms  (mx.compile only)")
print("="*60)

brain2 = SparseProbabilisticBrain(connectome, use_mlx=True, fast_mode=False)

# Warmup triggers JIT trace
brain2.reset(deterministic=True)
brain2.evolve(WARMUP_MS)

r2 = brain2.benchmark(BIO_MS)
results.append(("Compiled MLX     dt=0.1ms", r2))

# ── Configuration 3: Compiled MLX, dt=0.5 ms (fast_mode) ────────────
print("\n" + "="*60)
print("Config 3: Compiled MLX, dt=0.5 ms  (compile + fast_mode)")
print("="*60)

brain3 = SparseProbabilisticBrain(connectome, use_mlx=True, fast_mode=True)

brain3.reset(deterministic=True)
brain3.evolve(WARMUP_MS)

r3 = brain3.benchmark(BIO_MS)
results.append(("Compiled MLX     dt=0.5ms", r3))

# ── Summary table ────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"{'Configuration':<32} {'Wall(ms)':>9} {'RT factor':>10} {'Status':>18}")
print("-"*60)
for label, r in results:
    wall_ms  = r['wall_s'] * 1000
    rt       = r['rt_factor']
    status   = "✓ REAL-TIME" if rt >= 1.0 else f"{1/rt:.2f}× slow"
    print(f"{label:<32} {wall_ms:>9.1f} {rt:>10.3f}× {status:>18}")
print("="*60)

# Compute speedups relative to baseline
base_wall = results[0][1]['wall_s']
print(f"\nSpeedups vs baseline ({results[0][0].strip()}):")
for label, r in results[1:]:
    speedup = base_wall / r['wall_s']
    print(f"  {label.strip():<30}  {speedup:.2f}×")
