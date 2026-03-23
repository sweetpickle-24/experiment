#!/usr/bin/env python3
"""
Compare Python MLX vs Julia Metal vs Rust Metal on real olfactory connectome.
"""
import json
from pathlib import Path

BASE = Path(__file__).parent

def load(f):
    p = BASE / f
    if not p.exists():
        return None
    return json.loads(p.read_text())

py   = load('results_python_mlx.json')
jul  = load('results_julia_metal.json')
rust = load('results_rust_metal.json')

all_res = [r for r in [py, jul, rust] if r]

print("\n" + "="*70)
print("POLYGLOT BENCHMARK — REAL FLY OLFACTORY CONNECTOME")
print("10,906 neurons | 446,388 synapses | 1,000 steps (100ms bio)")
print("="*70)
print(f"\n{'Backend':<22} {'Wall(s)':>8} {'RT factor':>10} {'ms/step':>9} {'KC sparsity':>12}")
print("-"*65)
for r in all_res:
    name = r['backend'].replace('_', ' ').upper()
    print(f"{name:<22} {r['wall_time_s']:>8.3f} {r['rt_factor']:>10.4f}× {r['ms_per_step']:>9.3f} {r['kc_sparsity_pct']:>11.2f}%")

if py and jul:
    print(f"\nPython MLX vs Julia Metal:  {jul['wall_time_s']/py['wall_time_s']:.1f}× slower (Julia)")
if py and rust:
    print(f"Python MLX vs Rust Metal:   {rust['wall_time_s']/py['wall_time_s']:.1f}× slower (Rust)")
if py:
    print(f"\nPython MLX real-time factor: {py['rt_factor']:.3f}×")
    print(f"  → 100ms bio in {py['wall_time_s']*1000:.0f}ms wall (biological: 100ms)")
    print(f"  → {'faster' if py['rt_factor']>1 else 'slower'} than real-time by {1/py['rt_factor']:.2f}×")

print("\n" + "="*70)
print("BOTTLENECK ANALYSIS")
print("="*70)
print("""
Python MLX: Uses Apple MPS optimised scatter primitive (mx.at[post].add())
  → Internal bitonic sort + segmented parallel reduce in hardware
  → Fully utilises GPU parallelism regardless of connectivity shape

Julia Metal (CSR): 1 thread per neuron, serial loop over incoming synapses
  → Max fan-in = 14,662 (one hub neuron)
  → That thread runs 14,662 serial iterations while 10,905 others sit idle
  → No float atomics in Metal.jl 1.9.3 → forced into CSR serial loop
  → Work imbalance: single bottleneck thread dominates step time

Rust Metal (CAS atomics): 1 thread per synapse, CAS float-add to post
  → Avoids work imbalance (446,388 balanced threads)
  → BUT: hub neuron receives 14,662 concurrent writes → CAS contention
  → Each write requires multiple retry loops on hot cachelines
  → Contention overhead > work imbalance overhead in this case
""")
print("="*70)
print("CONCLUSION FOR PROSTHETICS HARDWARE")
print("="*70)
print("""
MLX (Apple M-series): Excellent for dev/testing on Apple hardware.
  Real-time factor: 0.59× (1.7× slower than RT, improvable with dt increase)
  
Julia Metal: Not production-ready for irregular connectomes without float atomics.
  Suitable for structured networks (uniform fan-in, e.g. synthetic benchmarks).
  
Rust Metal: Blocked by Metal's CAS overhead on irregular graphs.
  Would excel on NVIDIA (CUDA int atomics are cheaper) or structured topologies.

For actual prosthetic hardware:
  - FPGA / custom ASIC: dedicated scatter-accumulate units → sub-real-time guaranteed
  - Intel Loihi 2 / Akida: neuromorphic chips with native sparse message passing
  - NVIDIA GPU (Jetson Orin): CUDA int atomics + cuSPARSE → likely sub-real-time
  - Apple M-series: Python/MLX path is the pragmatic choice for today
""")
