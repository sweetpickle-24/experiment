#!/usr/bin/env python3
"""
Python MLX (Apple GPU) benchmark — real olfactory connectome.
10,906 neurons, 446,388 synapses, 1000 steps (100ms biological).
"""

import sys, os
sys.path.insert(0, '/Users/vladyslav/Documents/GitHub/experiment')

import numpy as np
import json, time
from pathlib import Path

import mlx.core as mx

BASE = Path('/Users/vladyslav/Documents/GitHub/experiment/benchmarks/real_connectome')
meta = json.loads((BASE / 'network_meta.json').read_text())

N       = meta['n_neurons']
S       = meta['n_synapses']
N_KC    = meta['n_kc']
DT      = meta['dt']
GAMMA   = meta['gamma']
OMEGA0  = meta['omega0']
SIGMA   = meta['sigma_noise']
VARC    = meta['var_correction']
NSTEPS  = meta['n_steps']

print(f"Python MLX benchmark — real fly olfactory connectome")
print(f"  {N:,} neurons | {S:,} synapses | {NSTEPS} steps")

# ── load arrays ───────────────────────────────────────────────────────────────
pre  = mx.array(np.fromfile(BASE / 'pre_indices.bin',  dtype=np.int32))
post = mx.array(np.fromfile(BASE / 'post_indices.bin', dtype=np.int32))
wgt  = mx.array(np.fromfile(BASE / 'syn_weights.bin',  dtype=np.float32))
kc   = np.fromfile(BASE / 'kc_indices.bin', dtype=np.int32)

phase_init = np.fromfile(BASE / 'init_phase.bin', dtype=np.float32)
amp_init   = np.fromfile(BASE / 'init_amp.bin',   dtype=np.float32)
ext_force  = mx.array(np.fromfile(BASE / 'ext_force.bin', dtype=np.float32))
omega0_arr = mx.full((N,), OMEGA0, dtype=mx.float32)

# ── warm-up (compile Metal graph, 10 steps) ───────────────────────────────────
print("Warming up GPU …")

def make_state():
    phase = mx.array(phase_init.copy())
    vel   = mx.zeros(N, dtype=mx.float32)
    amp   = mx.array(amp_init.copy())
    varp  = mx.full((N,), 0.1, dtype=mx.float32)
    return phase, vel, amp, varp

def step(phase, vel, amp, varp):
    phase_pre  = phase[pre]
    phase_post = phase[post]
    amp_pre    = amp[pre]
    delta_phi  = phase_pre - phase_post
    syn_f      = wgt * mx.sin(delta_phi) * amp_pre * VARC
    coupling   = mx.zeros(N, dtype=mx.float32).at[post].add(syn_f)

    accel = (-2.0 * GAMMA * vel
             - omega0_arr**2 * phase
             + coupling
             + ext_force)
    vel   = vel + accel * DT
    phase = phase + vel * DT
    phase = mx.arctan2(mx.sin(phase), mx.cos(phase))

    varp  = varp * (1.0 - 2.0 * GAMMA * DT) + SIGMA**2 * DT
    varp  = mx.clip(varp, 0.01, 10.0)

    amp_drive = mx.abs(vel) * 0.1
    amp = amp * (1.0 - GAMMA * DT) + amp_drive * DT
    amp = mx.clip(amp, 0.001, 10.0)

    return phase, vel, amp, varp

phase, vel, amp, varp = make_state()
for _ in range(10):
    phase, vel, amp, varp = step(phase, vel, amp, varp)
mx.eval(phase, vel, amp, varp)
print("  GPU warm-up done")

# ── timed run ─────────────────────────────────────────────────────────────────
phase, vel, amp, varp = make_state()
t_start = time.perf_counter()

for s in range(NSTEPS):
    phase, vel, amp, varp = step(phase, vel, amp, varp)
    if s % 100 == 99:
        mx.eval(phase, vel, amp, varp)   # flush every 100 steps

mx.eval(phase, vel, amp, varp)           # final flush
wall = time.perf_counter() - t_start

# ── KC sparsity ───────────────────────────────────────────────────────────────
amp_np = np.array(amp)
kc_amp = amp_np[kc]
active = int((kc_amp > 0.01).sum())
sparsity = active / N_KC * 100.0

bio_ms      = NSTEPS * DT
rt_factor   = bio_ms / 1000.0 / wall   # >1 = faster than real time
ms_per_step = wall / NSTEPS * 1000.0

print(f"\n{'='*55}")
print(f"  Wall time      : {wall:.3f} s")
print(f"  Bio time       : {bio_ms:.0f} ms")
print(f"  Real-time factor: {rt_factor:.3f}×  ({'faster' if rt_factor>1 else 'slower'} than RT)")
print(f"  ms per step    : {ms_per_step:.3f} ms")
print(f"  KC sparsity    : {sparsity:.2f}%  ({active}/{N_KC})")
print(f"{'='*55}")

results = {
    'backend': 'python_mlx_gpu',
    'n_neurons': N,
    'n_synapses': S,
    'n_steps': NSTEPS,
    'wall_time_s': wall,
    'bio_time_ms': bio_ms,
    'rt_factor': rt_factor,
    'ms_per_step': ms_per_step,
    'kc_sparsity_pct': sparsity,
    'active_kc': active,
    'total_kc': N_KC,
}
import json
out = BASE / 'results_python_mlx.json'
out.write_text(json.dumps(results, indent=2))
print(f"  Results → {out.name}")
