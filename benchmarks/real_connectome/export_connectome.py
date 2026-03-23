#!/usr/bin/env python3
"""
Export real olfactory connectome to portable binary format.
This creates the shared dataset for Python/Julia/Rust benchmarks.

Exports:
  network_meta.json    - network dimensions + physics params
  pre_indices.bin      - int32[n_syn]  presynaptic indices
  post_indices.bin     - int32[n_syn]  postsynaptic indices
  syn_weights.bin      - float32[n_syn] normalised weights
  init_phase.bin       - float32[n_neurons] seeded initial phase
  init_amp.bin         - float32[n_neurons] initial amplitude
  kc_indices.bin       - int32[n_kc]   KC neuron array positions
  ext_force.bin        - float32[n_neurons] external odour force (ethanol)
"""

import sys, os
sys.path.insert(0, '/Users/vladyslav/Documents/GitHub/experiment')

import numpy as np
import json, time
from pathlib import Path

OUT = Path('/Users/vladyslav/Documents/GitHub/experiment/benchmarks/real_connectome')

# ── load connectome ────────────────────────────────────────────────────────────
print("Loading connectome …")
t0 = time.time()
from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway, classify_olfactory_neuron

full = Connectome(data_dir='Fly Brain Female')
full.load()
olfa = extract_olfactory_pathway(full)
print(f"  connectome loaded in {time.time()-t0:.1f}s")

# ── build index + coupling (mirrors SparseProbabilisticBrain._build_coupling_structure) ──
neuron_ids = list(olfa.neurons.keys())
id_to_idx  = {nid: i for i, nid in enumerate(neuron_ids)}
N          = len(neuron_ids)

pre_list, post_list, w_list = [], [], []
for syn in olfa.synapses:
    if syn.pre_id in id_to_idx and syn.post_id in id_to_idx:
        pre_list.append(id_to_idx[syn.pre_id])
        post_list.append(id_to_idx[syn.post_id])
        w_list.append(float(syn.weight))

pre_arr  = np.array(pre_list,  dtype=np.int32)
post_arr = np.array(post_list, dtype=np.int32)
wgt_arr  = np.array(w_list,    dtype=np.float32)

# normalise weights (same as SparseProbabilisticBrain)
max_w = wgt_arr.max()
if max_w > 0:
    wgt_arr /= max_w

S = len(wgt_arr)
print(f"  {N:,} neurons, {S:,} synapses")

# ── deterministic initial state (seed=42) ─────────────────────────────────────
rng = np.random.default_rng(42)
init_phase = rng.uniform(-np.pi, np.pi, N).astype(np.float32)
init_amp   = np.full(N, 0.1, dtype=np.float32)

# ── KC indices ────────────────────────────────────────────────────────────────
kc_idx = np.array(
    [i for i, nid in enumerate(neuron_ids) if classify_olfactory_neuron(olfa.neurons[nid]) == 'KC'],
    dtype=np.int32
)
pn_idx = np.array(
    [i for i, nid in enumerate(neuron_ids) if classify_olfactory_neuron(olfa.neurons[nid]) == 'PN'],
    dtype=np.int32
)
print(f"  KC neurons: {len(kc_idx):,}   PN neurons: {len(pn_idx):,}")

# ── external force: ethanol odour, strength=50 (same as test_cpu_vs_mlx) ─────
ETHANOL_PATTERN = np.array([
    0.0, 0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.3,
    0.0, 0.0, 0.0, 0.6, 0.0, 0.0, 0.0, 0.1,
    0.0, 0.2, 0.0, 0.0
], dtype=np.float32)

STRENGTH = 50.0
ext_force = np.zeros(N, dtype=np.float32)
pns_per_channel = max(1, len(pn_idx) // len(ETHANOL_PATTERN))
for i, ch_str in enumerate(ETHANOL_PATTERN):
    s = i * pns_per_channel
    e = min(s + pns_per_channel, len(pn_idx))
    ext_force[pn_idx[s:e]] = ch_str * STRENGTH

# ── write binary files ────────────────────────────────────────────────────────
def save_bin(arr, name):
    p = OUT / name
    arr.tofile(p)
    print(f"  wrote {p.name}  ({arr.nbytes/1024:.0f} KB)")

save_bin(pre_arr,    'pre_indices.bin')
save_bin(post_arr,   'post_indices.bin')
save_bin(wgt_arr,    'syn_weights.bin')
save_bin(init_phase, 'init_phase.bin')
save_bin(init_amp,   'init_amp.bin')
save_bin(kc_idx,     'kc_indices.bin')
save_bin(ext_force,  'ext_force.bin')

# CSR format for Julia/Rust GPU (no atomics needed)
# Sort synapses by post index, compute row offsets
sort_order  = np.argsort(post_arr, stable=True)
csr_pre     = pre_arr[sort_order].astype(np.int32)
csr_post    = post_arr[sort_order].astype(np.int32)   # sanity
csr_wgt     = wgt_arr[sort_order].astype(np.float32)

# row_ptr[i] = start index in csr_pre/csr_wgt for post neuron i
row_ptr = np.zeros(N + 1, dtype=np.int32)
np.add.at(row_ptr[1:], csr_post, 1)
np.cumsum(row_ptr, out=row_ptr)

save_bin(csr_pre,  'csr_pre.bin')
save_bin(csr_wgt,  'csr_wgt.bin')
save_bin(row_ptr,  'csr_row_ptr.bin')

# ── metadata ──────────────────────────────────────────────────────────────────
meta = {
    'n_neurons': N,
    'n_synapses': S,
    'n_kc': int(len(kc_idx)),
    'n_pn': int(len(pn_idx)),
    'dt': 0.1,
    'gamma': 0.1,
    'omega0': float(2 * np.pi * 10.0 / 1000.0),
    'sigma_noise': 0.1,
    'var_correction': float(np.exp(-0.1 / 2.0)),
    'sim_duration_ms': 100.0,
    'n_steps': 1000,
    'max_row_nnz': int(np.diff(row_ptr).max()),
}
(OUT / 'network_meta.json').write_text(json.dumps(meta, indent=2))
print(f"  wrote network_meta.json")

print(f"\nExport complete. Files in {OUT}")
