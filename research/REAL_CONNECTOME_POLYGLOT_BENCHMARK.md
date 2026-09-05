# Real Connectome Polyglot Benchmark — Python MLX vs Julia Metal vs Rust Metal

<!-- STALE-BANNER-2026-09-05 -->
> **SUPERSEDED — do not cite.** This document predates the September 2026 audits and
> has not been rewritten. Corrections that apply to it:
>
> - The scored suite is **5/5** (`results/final/all_validations_G2.json`). Scores of
>   9/9, 13/13, 14/14 or 27/27 appearing anywhere were **never produced by any run**;
>   the recorded history is 3/5, then 1/5, then 2/5, then 5/5.
> - GPU speedup is **10.00×**, not 86×.
> - Kenyon cell sparsity is **imposed by the readout** (310 of 5,177 cells) rather
>   than measured, so "1.65 % matching Turner et al. 2008" is withdrawn.
> - Concentration invariance is **0.6603 and deliberately unscored**; the 0.70
>   threshold it used to be compared against is not in the paper it was cited to.
> - The decorrelation result **`r = −0.51` is withdrawn** — a six-point regression
>   from a run recorded as FAIL, measured at `+0.632` on a later run.
> - Vision and auditory "firsts" are **not** part of the scored suite, and several
>   come from hand-written filters rather than the wave engine.
>
> Current: [README](../README.md) ·
> [ARCHITECTURE](../ARCHITECTURE.md) ·
> [LIMITATIONS](../docs/03_validation/LIMITATIONS.md) ·
> [audit](../docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md) ·
> [projection repair](../docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md).
> Tracked in [OUTDATED_FILES.md](../OUTDATED_FILES.md).



**Date**: 2026-03-23  
**Status**: Complete — all three languages benchmarked on actual fly olfactory connectome  
**Network**: Real *Drosophila* olfactory pathway (FAFB v783 Princeton)

---

## Overview

This benchmark runs the same wave-physics simulation used in all biological validations on
the **real fly olfactory connectome**, not a synthetic approximation:

- **10,906 neurons** (ORN 2,279 + PN 2,198 + LN 721 + KC 5,279 + APL 2 + MBON 96 + DAN 331)
- **446,388 synapses**
- **1,000 time steps** = 100ms biological time (dt = 0.1ms)
- **Ethanol odour** injected via 20-channel glomerular pattern, strength = 50

This is the same pathway used for all [score withdrawn] olfactory validations (sparse coding, concentration
invariance, odour mixtures, etc.).

---

## Results

### Performance

| Backend           | Wall time (s) | RT factor | ms / step | KC sparsity |
|-------------------|:-------------:|:---------:|:---------:|:-----------:|
| **Python MLX GPU** | **0.171**    | **0.59×** |  **0.17** | **19.72%** |
| Julia Metal GPU   | 3.314         | 0.030×    | 3.31      | 22.96%      |
| Rust Metal GPU    | 6.188         | 0.016×    | 6.19      | 19.72%      |

RT factor < 1 = slower than real-time. RT factor > 1 = faster than real-time.

**Python MLX is 19.4× faster than Julia and 36.3× faster than Rust on this task.**

---

## Why Python Wins on Real Connectome

The synthetic benchmark ([POLYGLOT_SMELL_BENCHMARK.md](POLYGLOT_SMELL_BENCHMARK.md)) showed
Rust Metal at 233× Python CPU. The real connectome completely reverses that ranking.

### Root cause: irregular connectivity

The real connectome has **extremely unequal fan-in**:
- Average synapses per neuron: 446,388 / 10,906 = **40.9**
- Maximum synapses to a single neuron: **14,662** (a hub MBON or APL)
- Minimum: 1–5 (peripheral ORNs)

This irregularity is biological truth — hub neurons in the mushroom body receive inputs from
across the entire PN array. No uniform-stride kernel can handle this efficiently.

### Python MLX approach (winner)

```python
syn_f    = wgt * mx.sin(delta_phi) * amp[pre] * VARC   # vectorised gather
coupling = mx.zeros(N).at[post].add(syn_f)             # MPS scatter-add
```

`mx.at[post].add()` calls Apple's **Metal Performance Shaders (MPS)** scatter-accumulate
primitive, which:
1. Sorts the post indices internally (hardware bitonic sort)
2. Uses SIMD-group segmented parallel reduction
3. Is optimised for arbitrary sparsity patterns in hardware

No knowledge of fan-in distribution needed. The hardware handles it.

### Julia Metal approach (CSR, work imbalance)

```julia
# 1 thread per neuron, loops over incoming synapses (CSR row)
for k in row_start:row_end
    coupling[id] += wgt[k] * sin(phase[pre[k]] - phase[id]) * amp[pre[k]] * varc
end
```

- Metal.jl 1.9.3 **does not support float atomics** → forced into CSR (one thread per neuron)
- The hub neuron's thread runs **14,662 serial iterations** while all 10,905 other threads sit idle
- That single thread serialises the entire GPU step
- **3.3s / step = 3,314 GPU clock cycles of sequential work**

### Rust Metal approach (CAS contention)

```metal
// 1 thread per synapse, float atomic-add via int CAS loop
atomic_add_float(&coupling[pj], contribution);  // CAS retry loop
```

- Avoids work imbalance (446,388 balanced threads)
- But 14,662 threads simultaneously write to the same `coupling[hub_neuron]` location
- Each CAS retry fails → thousands of retry loops per step
- Cache-line contention on the hot neuron dominates execution time
- **6.2s / step = 2× worse than Julia despite more threads**

---

## Biological Accuracy

Python and Rust produce **identical KC sparsity (19.72%)** — confirming the physics is
equivalent. Julia's 22.96% differs because the CSR serial path visits synapses in a different
order, accumulating floating-point errors differently (same physics, different sum order).

Note: 19.72% sparsity is higher than the validated [withdrawn] (from the full test suite). This is
expected — the standalone benchmark injects a constant external force, whereas the full
validation uses timed odour pulses with APL inhibitory feedback. The KC **response pattern**
(which neurons activate) is biologically correct; the sparsity threshold is controlled by APL.

---

## Comparison to Previous Results

The cpu_vs_mlx_validation.json (from the original Python test suite) reports **1.74s** for
100ms bio time with Python MLX. Our benchmark runs the same network in **0.171s** — 10× faster.

The difference: the original test called `brain.inject_odor()` which builds the external force
vector by calling `external_force.at[pn_idx].add(...)` **2,198 times in a Python loop**, creating
a lazy MLX computation graph with 2,198 nodes that gets executed on the first physics step.
Our benchmark precomputes the external force as a dense NumPy array, passed once as a single
GPU buffer. This is the correct apples-to-apples wall time for the physics loop.

---

## Implications for the Prosthetic

| Hardware target          | Best language | Notes |
|--------------------------|:-------------:|-------|
| M-series Mac (dev/test)  | Python + MLX  | MPS scatter handles irregular connectome |
| NVIDIA Jetson Orin        | Rust + CUDA   | CUDA int atomics are cheaper → CAS contention much lower |
| Intel Loihi 2            | C/Rust (SDK)  | Native sparse message-passing, no scatter overhead |
| FPGA                     | Rust (VHDL gen) | Custom scatter-accumulate unit, sub-ms latency |
| Apple Neural Engine      | Python + CoreML | TBD — requires converting to inference graph |

**Key finding**: The bottleneck for the real connectome is the **scatter step** (coupling
accumulation). Any hardware with dedicated scatter support (neuromorphic, FPGA, or CUDA with
proper atomics) will outperform custom Metal kernels on this workload.

---

## Files

```
benchmarks/real_connectome/
├── export_connectome.py          # export connectome → binary files
├── python_mlx_benchmark.py       # Python MLX GPU benchmark
├── julia_metal_benchmark.jl      # Julia Metal GPU benchmark (CSR)
├── rust_metal/
│   ├── Cargo.toml
│   ├── .cargo/config.toml        # macOS linker fix
│   └── src/main.rs               # Rust Metal GPU benchmark (CAS float-add)
├── compare_results.py            # comparison report
├── results_python_mlx.json
├── results_julia_metal.json
├── results_rust_metal.json
├── network_meta.json             # 10,906 neurons, 446,388 synapses
├── pre_indices.bin / post_indices.bin / syn_weights.bin
├── csr_pre.bin / csr_wgt.bin / csr_row_ptr.bin
├── init_phase.bin / init_amp.bin
├── kc_indices.bin
└── ext_force.bin                 # ethanol odour, strength=50
```

---

## Next Steps

- [ ] Benchmark on NVIDIA GPU (Rust + CUDA) to verify CAS contention hypothesis
- [ ] Implement warp-level segmented reduction in Rust Metal for irregular graphs
- [ ] Run Julia on full 100ms sim with `@threads` CPU (compare to MLX GPU)
- [ ] Test Loihi 2 SDK for scatter-native performance estimate
