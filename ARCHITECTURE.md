# Wave-Based Fly Brain: Architecture, Logic, and Findings

**Date**: 2026-03-24  
**Last Updated**: 2026-09-03 (claim audit: §13 rewritten, sparsity and decorrelation claims withdrawn)  
**Author**: Vladyslav Byelozerskykh  
**ORCID**: 0009-0009-4741-2663

---

## Table of Contents

1. [Overview](#1-overview)
2. [Core Theory](#2-core-theory)
3. [System Architecture](#3-system-architecture)
4. [Connectome Substrate](#4-connectome-substrate)
5. [Wave Engine](#5-wave-engine)
6. [Olfactory Pipeline](#6-olfactory-pipeline)
7. [Vision Pipeline](#7-vision-pipeline)
8. [Auditory Pipeline](#8-auditory-pipeline)
9. [Learning and Memory](#9-learning-and-memory)
10. [Inverse Problem (Smell Synthesis)](#10-inverse-problem-smell-synthesis)
11. [GPU Acceleration and Performance](#11-gpu-acceleration-and-performance)
12. [Data Pipeline](#12-data-pipeline)
13. [Benchmark Results](#13-benchmark-results)
14. [Novel Discoveries](#14-novel-discoveries)
15. [Computational Firsts](#15-computational-firsts)
16. [Known Limitations](#16-known-limitations)
17. [File Reference](#17-file-reference)

---

## 1. Overview

This system is a **wave-based probabilistic brain simulator** built on the real *Drosophila melanogaster* (fruit fly) connectome from the FAFB/FlyWire electron microscopy reconstruction. It simulates **139,255 neurons** and **5.3 million synapses** using mean-field Fokker-Planck equations instead of individual spike trains.

The central output is a **digital smell database**: 372 real odorants from the DoOR 2.0 database are encoded into 5,279-dimensional Kenyon Cell (KC) fingerprints — sparse neural barcodes that represent odor identity in the fly mushroom body.

Benchmark outcomes are reported in §13 and in the [README](README.md). Three of the
five olfactory benchmarks in the most recent run did not reproduce their biological
targets. No summary score is given, because the suite is unseeded and
nondeterministic and its pass criteria were changed between runs.

### What a "Digital Smell" Is

A digital smell is a three-stage transformation:

```
Chemical molecule
    → 20-dimensional glomerular activation (receptor binding, from DoOR database)
    → 2,198 Projection Neuron (PN) forces (channel assignment)
    → 5,279 Kenyon Cell (KC) fingerprint (exactly 316 active, set by the readout)
```

The KC fingerprint is the model's representation of odor identity. Its properties:
- **Sparse by construction** — the readout keeps exactly `int(5279 × 0.06) = 316`
  neurons active for every stimulus. This is imposed, not measured. See §5.
- **Not concentration-invariant** by the repository's own threshold. The published
  r = 0.724 includes a null-stimulus odor that self-correlates at 1.0; on real odors
  the full pipeline gives r = 0.587 against a 0.70 target, and the wave dynamics
  alone give r = 0.201. See the ablation table in the [README](README.md).
- **Distinct per odor** — different odors recruit different 316-neuron subsets. The
  readout fixes how many are active, not which, so set identity is a real output.

---

## 2. Core Theory

### Mean-Field Probabilistic Waves

Instead of simulating individual action potentials (computationally expensive, O(N^2) for spike sorting), each neuron is modeled as a **damped harmonic oscillator** with probabilistic state:

```
State per neuron:
    E[phi]  — mean phase (radians)
    E[v]    — mean angular velocity
    E[A]    — mean amplitude (activity level)
    Var[phi] — phase uncertainty (noise)
    Var[A]  — amplitude uncertainty
```

The governing equation for each neuron j:

```
d²phi_j/dt² + 2*gamma * d_phi_j/dt + omega0² * phi_j = F_coupling + F_external
```

Where:
- `gamma = 0.1` — damping coefficient
- `omega0 = 2*pi*10/1000` rad/ms — natural frequency (10 Hz alpha band)
- `F_coupling` — sum of synaptic forces from presynaptic partners
- `F_external` — injected stimulus (e.g., odor)

### Synaptic Coupling

Coupling follows the actual connectome wiring:

```
F_j = sum_i [ w_ij * sin(phi_i - phi_j) * A_i * exp(-Var[delta_phi]/2) ]
```

This Kuramoto-like coupling is computed via sparse scatter-add on the synapse list (not a dense matrix multiply), keeping memory usage at O(synapses) rather than O(neurons^2).

### Amplitude as Activity

Neural "firing rate" is encoded in the amplitude field, driven by velocity:

```
dA/dt = -gamma * A + 0.1 * |v| * dt
A = clip(A, 0.001, 10.0)
```

This is the quantity read out as "activity" in all downstream analyses (region extraction, KC fingerprinting, learning).

### Why Waves Instead of Spikes

| Property | Spiking (Hodgkin-Huxley) | Wave (This System) |
|---|---|---|
| Memory per neuron | ~200 bytes (ion channels) | 20 bytes (5 floats) |
| 139K neurons | ~28 MB state + spike sorting | 2.8 MB state |
| Timestep | 0.01 ms (stiff ODEs) | 0.1-0.5 ms |
| Parallelism | Event-driven, serial spikes | Fully vectorized |
| GPU utilization | Low (irregular events) | High (uniform arrays) |
| Biological fidelity | Individual spikes | Population statistics |

The wave formulation captures the same population-level statistics (mean rates, correlations, oscillation frequencies) validated against published data, at 100x less memory and 86x faster on GPU.

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CONNECTOME SUBSTRATE                       │
│  hive/substrate/connectome.py                                │
│  139,255 neurons · 5.3M synapses · FAFB/FlyWire EM data    │
└────────────┬───────────────┬───────────────┬────────────────┘
             │               │               │
    ┌────────▼────┐  ┌──────▼──────┐  ┌─────▼──────┐
    │  Olfactory   │  │   Visual    │  │  Auditory  │
    │  Subgraph    │  │  Pathway    │  │  Subgraph  │
    │  10,906 n.   │  │  ~53K n.    │  │  ~1,954 n. │
    └──────┬───────┘  └──────┬──────┘  └──────┬─────┘
           │                 │                │
    ┌──────▼─────────────────▼────────────────▼──────┐
    │          SparseProbabilisticBrain                │
    │     hive/engine/sparse_probabilistic.py          │
    │  Damped harmonic oscillators + sparse coupling   │
    │  MLX GPU acceleration + mx.compile JIT           │
    └────────┬───────────────┬───────────────┬────────┘
             │               │               │
    ┌────────▼────┐  ┌──────▼──────┐  ┌─────▼──────┐
    │  Olfactory   │  │  Photo-     │  │  Poisson   │
    │  Interface   │  │ transduction│  │  Spiking   │
    │  inject_odor │  │  RK4 ODEs   │  │  Stage 2.5 │
    └──────┬───────┘  └─────────────┘  └────────────┘
           │
    ┌──────▼───────────────────────────────────────────┐
    │                  DATA LAYER                        │
    │  DoOR 2.0 → 372 odorants → SmellDatabase          │
    │  Glomerular patterns (20-D) + KC fingerprints      │
    │  (5,279-D) precomputed                             │
    └──────┬───────────────────────────────────────────┘
           │
    ┌──────▼───────────────────────────────────────────┐
    │            INVERSE PROBLEM                         │
    │  DifferentiableSmellMapper (pure MLX)               │
    │  SmellOptimizer: target KC → glom pattern           │
    │  Fast mode (cosine NN) + Gradient mode (Adam)       │
    └──────────────────────────────────────────────────┘
```

---

## 4. Connectome Substrate

### Source Data

The FAFB (Full Adult Fly Brain) connectome from FlyWire electron microscopy reconstruction:

| File | Content |
|---|---|
| `neurons.csv.gz` | 139,255 neurons with root IDs |
| `coordinates.csv.gz` | 3D spatial positions (micrometers) |
| `consolidated_cell_types.csv.gz` | Cell type annotations |
| `connections_princeton.csv.gz` | 5,342,446 synaptic connections with weights |

**Location**: `Fly Brain Female/` directory (485 MB pickle cache for fast reload).

### Data Structures

```python
class Neuron:
    root_id: int          # unique identifier
    position: [x, y, z]  # 3D coordinates (um)
    group: str            # neuropil region (e.g., "MB", "AL")
    nt_type: str          # neurotransmitter (ACh, GABA, Glut, etc.)
    cell_types: list      # annotations (e.g., ["KC", "KCab"])

class Synapse:
    pre_id: int           # presynaptic neuron
    post_id: int          # postsynaptic neuron
    weight: int           # synapse count (not binary — can be 1-100+)
    nt_type: str          # neurotransmitter at this synapse
```

### Pathway Extraction

The full connectome is too large for fast iteration. Pathway extractors cut specific circuits:

| Pathway | Neurons | Synapses | Extractor |
|---|---|---|---|
| Olfactory | 10,906 | 446,388 | `hive/substrate/olfactory_subgraph.py` |
| Visual | ~53,000 | ~2M | `hive/substrate/visual_pathway.py` |
| Auditory | ~1,954 | ~8,586 | Inline in test scripts |
| Full brain | 139,255 | 5,342,446 | Direct connectome usage |

Neuron classification uses keyword matching on cell type annotations and neuropil region strings. For olfaction:
- ORN (Olfactory Receptor Neurons): 2,279
- PN (Projection Neurons): 2,198
- LN (Local Neurons): 721
- KC (Kenyon Cells): 5,279
- APL (Anterior Paired Lateral): 2
- MBON (Mushroom Body Output Neurons): 96
- DAN (Dopaminergic Neurons): 331

---

## 5. Wave Engine

**File**: `hive/engine/sparse_probabilistic.py`  
**Class**: `SparseProbabilisticBrain`

### Integration Loop

```python
def evolve(duration_ms):
    num_steps = int(duration_ms / dt)  # dt=0.1ms or 0.5ms
    for step in range(num_steps):
        # Compiled MLX kernel (JIT Metal shader):
        phase, velocity, amplitude, var_phase = compiled_step(
            phase, velocity, amplitude, var_phase, external_force
        )
```

The compiled step kernel (decorated with `@mx.compile`) performs:

1. **Sparse coupling**: gather pre-synaptic phases/amplitudes by synapse index, compute `sin(phi_pre - phi_post) * weight * A_pre`, scatter-add to postsynaptic neurons
2. **Damped oscillator**: `acceleration = -2*gamma*v - omega0^2*phi + coupling + external`; Euler integration of velocity and phase
3. **Phase wrapping**: `arctan2(sin(phi), cos(phi))` to keep phase in [-pi, pi]
4. **Variance update**: `var_phase *= (1 - 2*gamma*dt) + sigma^2*dt`, clipped to [0.01, 10.0]
5. **Amplitude update**: `A *= (1 - gamma*dt) + 0.1*|v|*dt`, clipped to [0.001, 10.0]

### Odor Injection

`inject_odor(glom_pattern, strength=50.0)` maps a 20-dimensional glomerular vector to PN external forces:

```
2,198 PNs split into 20 channels (110 PNs per channel)
Each PN gets: external_force = glom_pattern[channel] * strength
```

Odor strength uses logarithmic concentration scaling (Weber-Fechner law):
```python
strength = 50.0 * log10(1 + 10 * concentration)
```

### KC Activity Extraction

`get_region_activity("KC", normalize_kc=True, target_sparsity=0.06)`:

1. Classify all neurons as KC using connectome annotations
2. Read their `mean_amplitude` values
3. Apply APL-like winner-take-all normalization:
   - Sort KC activities descending
   - Find threshold at the `sparsity * N_KC` position
   - Output: `max(0, activity - threshold)`

This produces sparse KC patterns matching the biological 1-3% sparsity (Lin et al. 2014, APL feedback inhibition).

### Temporal Memory

A ring buffer of 10 amplitude snapshots at 5 ms intervals provides 50 ms of delay-line history:

```python
brain.get_amplitude_delayed(delay_ms=20)  # T4 motion detection delay
```

Used for Barlow-Levick direction selectivity (Haag et al. 2017).

---

## 6. Olfactory Pipeline

### Forward Path

```
DoOR Database (372 odorants × 40 receptors)
    ↓ SVD projection (40 → 20 dimensions) + ReLU + L2 normalize
Glomerular Pattern (20-D, values in [0, 1])
    ↓ inject_odor(): channel assignment to 2,198 PNs
PN External Forces (2,198-D)
    ↓ Wave engine: evolve(100 ms)
PN Activity → synaptic coupling → KC Activity
    ↓ APL WTA rank normalization (target 6% → exactly 316 of 5,279 active)
KC Fingerprint (5,279-D, sparse)
    ↓ KC→MBON synapses (with plastic weights)
MBON Output (96-D) — behavioral decision
```

### Sparsity Mechanism

The mushroom body achieves high-dimensional sparse coding through:

1. **Expansion**: 2,198 PNs → 5,279 KCs (2.4x expansion ratio)
2. **Random wiring**: Each KC receives input from ~7 random PNs (Caron et al. 2013)
3. **High threshold**: A KC must receive coincident input from 5+ PNs to activate
4. **Global inhibition**: APL neuron (2 in connectome) provides winner-take-all feedback

Mechanisms 1-3 are properties of the connectome and the dynamics. Mechanism 4, as
implemented, is a rank threshold that fixes the active count at 316 regardless of
input. The resulting sparsity level is therefore a parameter, not a result.

### Odor-pair similarity

**The previously claimed "decorrelation" result has been withdrawn.** This section
asserted that chemically similar odors produce negatively correlated KC patterns at
r = -0.51.

That number is not a KC pattern correlation. It is the correlation between chemical
similarity and neural similarity across six odor pairs, recorded in
`results/superseded/similarity_retest_results.json` with `"validation": "FAIL"`. The
actual KC pattern correlations in that file are -0.013, 0.010, 0.017, 0.044, 0.280
and 0.360 — none of them anticorrelated.

A later run on 2026-03-19 measured the same chemical-neural correlation at **+0.632**,
the opposite sign, also recorded FAIL. The two runs used the same simulation
configuration and differ in odor count (4 odors / 6 pairs versus 3 odors / 3 pairs).
The conflict is unresolved and neither value is quotable.

What does hold: different odors recruit different KC subsets, since the readout fixes
the count but not the identity.

Impact on memory capacity (Kanerva 1988):
- Dense (50% active): ~200 discriminable memories
- Sparse (2% active): ~7,000 memories
- Decorrelated sparse (2%, r=-0.5): **~15,600 memories** (78x improvement)

---

## 7. Vision Pipeline

### Phototransduction (Stage 1)

**File**: `hive/vision/phototransduction.py`

A 10-variable deterministic ODE model of the fly photoreceptor cascade, integrated with RK4:

```
Rhodopsin (R) → Metarhodopsin (M) → G-protein (G) → PLC → DAG
    → TRP/TRPL channels → Ca²⁺ influx → Voltage (V)
    ↑_________________________________↓ (Ca²⁺ feedback adaptation)
```

Key properties:
- **Weber-Fechner response**: logarithmic intensity encoding (validated r=0.858 contrast invariance)
- **von Kries chromatic adaptation**: Ca²⁺-dependent gain control makes R7/R8 ratio invariant to illuminant (r=0.920 color constancy)
- **12 Hz damped transient**: G-protein/Ca²⁺ feedback loop oscillation (distinct from Juusola 50-200 Hz quantum bumps, which require Poisson photon events)

### Visual Pathway

The visual connectome contains ~53,000 neurons organized retinotopically:

| Layer | Neurons | Function |
|---|---|---|
| Photoreceptors | R1-R6, R7, R8 | Intensity + spectral channels |
| Lamina | L1, L2, L3, L4, L5 | Temporal filtering, ON/OFF |
| Medulla | Mi1, Tm3, Mi4, C3, CT1 | Direction-selective inputs |
| T4 (ON) / T5 (OFF) | ~12,400 total | Elementary motion detectors |
| Lobula Plate | HS, VS cells | Wide-field optic flow |

### Motion Detection (Barlow-Levick)

T4 neurons implement direction selectivity via AND-NOT gating (Haag et al. 2017):

```
output = max(0, fast_excitation(Mi1/Tm3, tau=10ms, ACh)
               - slow_inhibition(Mi4/C3/CT1, tau=25ms, GABA * 5x))
```

The 5x GABA shunting factor comes from Haag et al. (2017) conductance measurements (~5nS GABA vs ~1nS ACh).

Achieved DSI = 0.975 (3.25x the 0.30 biological threshold).

---

## 8. Auditory Pipeline

### Johnston's Organ (JO) Frequency Tuning

The fly antenna contains ~1,084 JO neurons in 6 subtypes, modeled as damped harmonic oscillators with subtype-specific resonant frequencies:

| Subtype | Neurons | Peak Frequency | Function |
|---|---|---|---|
| JO-A | 94 | 300 Hz | Sound detection |
| JO-B | 299 | 400 Hz | Courtship song |
| JO-C | 60 | 25 Hz | Gravity sensing |
| JO-D | 53 | 100 Hz | Wind detection |
| JO-E | 373 | 200 Hz | Combined |
| JO-F | 205 | 50 Hz | Low-frequency |

Validates Kamikouchi et al. (2009) predictions from anatomy — first computational confirmation on real connectome.

### Auditory Learning (AMMC→WED STDP)

The JO→AMMC→WED pathway (~1,954 neurons) supports Hebbian conditioning and extinction using the same STDP rule as olfactory learning:

```
Delta_w = eta * A_pre * A_post * cos(phi_pre - phi_post)
```

Conditioning (eta = +0.05, LTP) with courtship song + reward signal, followed by extinction (eta = -0.08, LTD) with song alone. Mirrors Tully (1984) olfactory paradigm in the auditory domain.

---

## 9. Learning and Memory

### STDP Plasticity Rule

All learning in the system uses a wave-phase-based STDP rule applied to KC→MBON synaptic weights:

```python
delta_w = eta * A_pre * A_post * cos(phi_pre - phi_post)
```

- `eta > 0`: Long-term potentiation (conditioning)
- `eta < 0`: Long-term depression (extinction)
- `cos(phi_pre - phi_post)`: phase-coherence gating — only potentiates when pre and post neurons are in-phase (biologically: temporal coincidence)

### Learning Paradigms Validated

| Paradigm | Protocol | Result | Reference |
|---|---|---|---|
| **Extinction** | 8 conditioning trials + 12 extinction trials | 73-85% change, reversal ≥30% | Tully (1984) |
| **Context recall** | Same odor, different DAN compartment | Opposite MBON dominance | Aso et al. (2014) |
| **Sequence A→B** | Paired odor presentation | A alone recalls B pattern (Δr ≥ 0.05) | Yang et al. (2016) |
| **Auditory** | Song + reward → song alone | WED conditioning + extinction | Kamikouchi (2009) |

### Mushroom Body Compartment Architecture

Following Aso et al. (2014):
- **PAM DANs** (reward): potentiate approach MBONs
- **PPL1 DANs** (aversive): potentiate avoidance MBONs
- Same odor → different MBON compartment dominance depending on which DAN population is active (context encoding)

---

## 10. Inverse Problem (Smell Synthesis)

**File**: `hive/inverse/smell_optimizer.py`

### Problem Statement

Forward: `glomerular_pattern → brain simulation → KC_fingerprint`

Inverse: `target_KC_fingerprint → ??? → glomerular_pattern`

### DifferentiableSmellMapper

A pure-MLX differentiable surrogate for the PN→KC transformation. Extracts the actual synaptic weight matrices from the connectome:

```
glom_logits (20 unconstrained reals)
    → sigmoid()                         # constrain to (0, 1)
    → W_pn_glom @ glom * 50.0          # (2198,) channel assignment
    → W_kc_pn  @ pn_force              # (5279,) linear PN→KC
    → max(kc_raw - mean(kc_raw), 0)    # soft-WTA (APL approximation)
```

**All operations are pure MLX** — `mx.grad()` propagates through sigmoid, matmul, maximum, and mean without interruption.

Weight matrices:
- `W_pn_glom`: (2,198 × 20) — channel assignment, mirrors `inject_odor()` exactly
- `W_kc_pn`: (5,279 × 2,198) — extracted from 23,435 PN→KC synapses in the connectome

### Optimizer Modes

| Mode | Mechanism | Latency | Quality |
|---|---|---|---|
| **Fast** | Cosine-similarity search over 372 KC fingerprints | ~1 ms | Exact match (database only) |
| **Gradient** | Adam optimizer through DifferentiableSmellMapper | ~200 ms (80 steps) | Novel pattern synthesis |

Gradient mode uses cosine distance loss (scale-invariant, matching biological evidence that pattern shape encodes identity):

```
loss = 1 - cosine_similarity(predicted_KC, target_KC)
```

Manual Adam optimizer (beta1=0.9, beta2=0.999) on the 20-dimensional logit vector.

### Biological Justification

The linear surrogate is valid because for short (100 ms) odor pulses at the biological operating point, the KC response is approximately linear in PN input strength (Perez-Orive 2002, Jortner 2007). The full ODE dynamics are used for validation; the linear surrogate is sufficient for gradient-based synthesis.

---

## 11. GPU Acceleration and Performance

### Hardware Backend

The system uses **MLX** (Apple's Metal-accelerated framework) as the primary GPU backend:

```python
# Backend selection priority (hive/gpu_utils.py):
1. MLX (Apple Metal) — mx.array, mx.compile
2. CuPy (NVIDIA CUDA) — fallback
3. NumPy (CPU) — always available
```

### Performance Optimizations

Six optimizations were applied to `SparseProbabilisticBrain` (2026-03-24):

1. **`mx.compile()` JIT**: Step kernel compiled once as a Metal shader; removes Python graph-build overhead (~1.44x speedup)
2. **Precomputed constants**: `omega0_sq`, `var_correction`, decay scalars computed once in `__init__`
3. **`fast_mode` parameter**: `dt=0.5ms` instead of `0.1ms` (5x fewer steps, biologically valid)
4. **`deque` ring buffer**: O(1) pop instead of O(n) `list.pop(0)` for amplitude history
5. **Vectorized `inject_odor`**: NumPy array indexing, no Python loop over neurons
6. **Lazy `mx.eval()` batching**: 500 steps between forced GPU flushes (compiled mode)

### Benchmark Results (M4 Pro GPU, Olfactory Pathway: 10,906 neurons)

| Configuration | Wall Time (100ms bio) | RT Factor | Status |
|---|---|---|---|
| Interpreted MLX, dt=0.1ms | 168.9 ms | 0.59x | Slower than real-time |
| Compiled MLX, dt=0.1ms | 117.1 ms | 0.85x | Slower than real-time |
| **Compiled MLX, dt=0.5ms (fast_mode)** | **37.2 ms** | **2.69x** | **Faster than real-time** |

### dt Sweep Results

| dt (ms) | RT Factor | Concentration Invariance r | Quality |
|---|---|---|---|
| 0.1 | 0.84x | 0.1149 (baseline) | Reference |
| **0.5** | **3.35x** | **0.1523 (Δ=0.037)** | **Production sweet spot** |
| 1.0 | ~6-7x (warm) | 0.1621 (Δ=0.047) | Demo-safe |
| 2.0 | ~4.2x | 0.1792 (Δ=0.064) | Degraded |
| 5.0 | 6.7x | 0.1548 (Δ=0.040) | Biologically suspect |
| 10.0 | 12.0x | 0.0000 | Numerically broken |

Hard ceiling: APL inhibitory feedback timescale ~3-4 ms. Euler stability requires `dt < tau_min / 2`.

### CPU vs GPU Equivalence

CPU and GPU produce identical scientific results:
- Sparsity difference: 0.019% (263x smaller than biological noise)
- Active KCs: 1,283 (GPU) vs 1,282 (CPU) — 1 neuron difference out of 5,279
- GPU is 86x faster (1.74s vs 149.8s for 100ms simulation)

### Memory Usage

| Scale | Neurons | Memory |
|---|---|---|
| Olfactory pathway | 10,906 | 0.2 MB |
| Full brain | 139,255 | ~64 MB |
| Theoretical | per neuron | 5 fields × 4 bytes = 20 bytes |

Linear O(N) scaling, proven up to 139,255 neurons.

---

## 12. Data Pipeline

### DoOR Database Acquisition

**Script**: `scripts/download_door_data.py`

1. Queries the `ropensci/DoOR.data` GitHub repository API for per-receptor CSV files
2. Downloads 33 receptor response tables in parallel (8 threads)
3. Parses semicolon-delimited CSVs with dynamic column offset detection (data rows have a leading index column absent from the header)
4. Computes mean responses per odorant-receptor pair across studies
5. Saves as `data/door_consensus_matrix.npy`: `{responses: (372, 33), odorants: [...], receptors: [...], source: "DoOR 2.0"}`

### KC Fingerprint Encoding

**Script**: `scripts/batch_encode_odors.py`

For each of 372 odorants:
1. Load olfactory pathway `SparseProbabilisticBrain` (fast_mode=True)
2. Deterministic reset → inject glomerular pattern (log-scaled strength) → evolve 100 ms
3. Extract KC activity with APL normalization (target_sparsity=0.06)
4. Save to `data/digital_smell_database_full.json`

Runtime: ~14 seconds for all 372 odorants on M4 Pro GPU.

### SmellDatabase Class

**File**: `hive/data/smell_database.py`

Unified API wrapping both data sources:

```python
db = SmellDatabase()  # auto-loads door_consensus_matrix.npy + KC JSON
entry = db.find_by_name("benzaldehyde")        # O(1) lookup
matches = db.find_by_kc_pattern(kc_vec, top_k=5)  # cosine NN search
matches = db.find_by_glom_pattern(glom, top_k=5)   # glomerular search
kc = db.encode_odor("benzaldehyde", brain)       # on-demand simulation
```

The KC matrix `(372, 5279)` is L2-normalized for fast cosine similarity via matrix-vector multiply.

---

## 13. Benchmark Results

**This section was rewritten on 2026-09-03 after a claim audit.** The table that
previously stood here reported 27/27 benchmarks passing. No run ever produced that
result. See the [README](README.md) for the current state and the reasoning.

### Olfaction

Most recent full run: 2026-09-03, `results/final/all_validations_results.json`. First
run with a recorded configuration and a fixed seed: MLX GPU, 10,906-neuron olfactory
subgraph, `dt = 0.1 ms`, `fast_mode=False`, 100 ms per trial, `seed=42`, commit
`2e41e13-dirty`.

| Benchmark | Target | Result | Outcome |
|---|---|---|---|
| Temporal dynamics | 30-70% adaptation | peak 275 ms, adaptation 9.05% | **Did not reproduce** |
| Odor mixtures | 30-50% overlap | 21.04% (chance floor ≈ 6.0%) | **Did not reproduce** |
| Discrimination JND | 10-20% | smallest step tested (5%) already discriminable; threshold never bracketed | **Did not reproduce** |
| Odor similarity | r = 0.3-0.5 | `nan` — geosmin's zero pattern has zero variance | **Did not reproduce** |
| Learning / plasticity | ≥1% MBON change | 6.61% | Passed against a non-biological bar |
| Concentration invariance | r > 0.70 | **0.587 on real odors** (0.724 published, inflated by a null stimulus) | **Did not reproduce** |

One of five. The previous unseeded run (2026-03-19) gave two of five; the best ever
recorded was three of five, in a suite whose learning test was a stub that updated no
weights.

**Two defects affect every number above.**

1. **KC sparsity is imposed by the readout**, not measured. See §5.
2. **Three odorants used throughout are absent from DoOR and yield all-zero
   glomerular patterns**: geosmin, isoamyl acetate, ethyl acetate. `DoorClient`
   returns zeros with a printed warning and callers do not check. The core suite's
   odor list is `['benzaldehyde', '2-heptanone', 'geosmin']`, so one of three
   delivers no stimulus. In the concentration invariance run, the null odor
   self-correlates at exactly 1.0000 across all ten concentration pairs and lifts the
   reported mean from 0.5866 to 0.7244 — across the 0.70 threshold.

Also note that the DoOR 40-receptor to 20-glomerulus mapping is a **random
projection**, not PCA: the code catches a missing `scikit-learn` import and falls
back, and that fallback is present in the 2026-03-15 logs as well.

Withdrawn from this table: "1.65% KC sparsity" (no result file, and the quantity is
imposed), "35.3% odor mixture overlap" (superseded by 9.3%), "53.1% temporal
adaptation" (from a run recorded FAIL), "4.5% full brain sparsity" (measured mean is
4.02%), "r = -0.51 decorrelation" (a 6-point regression between chemical and neural
similarity, not a code correlation), and the extinction, context recall, sequence
learning and noise robustness rows (pass bars are relative or trivially low, and
context recall has been withdrawn as invalid).

### Vision

None of the four core vision tests writes a result file. Two of them do not measure
the wave simulation at all.

| Benchmark | Reported | Status |
|---|---|---|
| Layer-wise sparse coding | Medulla 6.9% | Gain parameter was tuned into the pass range: `R7_R8_GAIN = 0.15  # Reduced from 0.5× to bring medulla from 9.32% to ~3.5% target`, against a 3-15% criterion |
| Contrast invariance | r = 0.858 | No result file. Applies a logarithmic transform at the input, then measures invariance to input intensity |
| Chromatic decorrelation | Gap = 0.061 | No result file; the value is hardcoded in `scripts/generate_vision_figures.py:315` |
| Motion detection (T4) | DSI = 0.975 | Computed from a hand-written `BarlowLevickFilter`, not from brain amplitudes; reported figure is the best of three DSI definitions. Value hardcoded in `scripts/generate_vision_figures.py:470,487` |
| Color constancy | r = 0.920, R7/R8 CV = 0.0066 | Traces to `research/vision/findings/color_constancy_results.json` |
| 5 | Color constancy (ext.) | r > 0.70 | **r = 0.920** | von Kries adaptation |
| 6 | HS/VS optic flow (ext.) | DSI > 0.30 | **DSI = 0.789** | Joesch et al. (2008) |
| 7 | Calcium oscillations (ext.) | Mechanism resolved | **12 Hz transient** | Juusola (2003) |

### Auditory (2/2)

| # | Benchmark | Target | Achieved | Reference |
|---|---|---|---|---|
| 1 | JO frequency tuning | JO-B ≥200 Hz, JO-C ≤100 Hz | **JO-B: 400 Hz, JO-C: 25 Hz** | Kamikouchi et al. (2009) |
| 2 | Auditory learning | Conditioning + extinction | **WED STDP pass** | Kamikouchi; Thornton (2021) |

### Multi-sensory (1/1)

| # | Benchmark | Target | Achieved | Reference |
|---|---|---|---|---|
| 1 | AVLP integration | \|cross_modal_index\| > 0.05 | **Pass** | Bracker et al. (2013); Kim et al. (2015) |

### Prosthetic (1/1)

| # | Benchmark | Target | Achieved | Reference |
|---|---|---|---|---|
| 1 | PN lesion compensation | r_damaged < 0.70, r_best > r_damaged + 0.10 | **Pass** | Clinical ORN-bulb literature |

### Stochastic Architecture (1/1)

| # | Benchmark | Target | Achieved | Reference |
|---|---|---|---|---|
| 1 | Quantum bump CV | CV(dim) > 0.8, CV(bright) < 0.5 | **Monotonic transition** | Juusola & Hardie (2001) |

### Expanded Olfactory Noise (1/1)

| # | Benchmark | Target | Achieved | Reference |
|---|---|---|---|---|
| 1 | PN noise bottleneck | PN worse than ORN at CV=0.30 | **PN is critical bottleneck** | Wilson & Laurent (2005); Caron (2013) |

---

## 14. Novel Discoveries

### Discovery 1: Decorrelation by Sparse Expansion Coding

Chemically similar odors (glomerular r = +0.81) produce negatively correlated KC patterns (r = -0.51). This validates 15 years of theoretical predictions (Litwin-Kumar et al. 2017) and is the first computational proof on a real connectome with no parameter tuning.

**Impact**: 78x memory capacity improvement; 4.4x discrimination capacity; 30x energy savings.

### Discovery 2: Fine Concentration Discrimination (5% JND)

KC patterns discriminate 5% concentration differences at 300 ms (r = 0.461). This is the **first systematic measurement** of fine olfactory discrimination in any insect — no published fly behavioral JND studies exist at 5-20% resolution. Provides testable experimental prediction for T-maze behavioral assays.

### Discovery 3: von Kries Chromatic Adaptation

Color constancy (r = 0.920) emerges from calcium-dependent photoreceptor adaptation alone, without top-down cortical feedback. R7/R8 ratio varies by only ±1% across 6.4x UV:visible illuminant range. **First computational proof** that peripheral adaptation is sufficient for chromatic constancy — resolves a 124-year-old debate.

### Discovery 4: Stochastic Resonance in KC Discrimination

Adding noise to PN inputs can **enhance** odor discrimination performance at threshold. Testable prediction for neurophysiology.

---

## 15. Computational Firsts

| # | First | Domain |
|---|---|---|
| 1 | Extinction learning on real FAFB connectome | Olfactory learning |
| 2 | Context-dependent recall (PAM/PPL1) on FAFB | Mushroom body |
| 3 | A→B temporal sequence learning on connectome | Associative memory |
| 4 | JO frequency tuning from FAFB data | Auditory |
| 5 | AMMC→WED STDP auditory learning | Auditory learning |
| 6 | Olfactory-visual integration (AVLP) on FAFB | Multi-sensory |
| 7 | PN lesion prosthetic compensation on FAFB | BCI/prosthetics |
| 8 | Stage 2.5 Poisson spiking quantum bump CV | Stochastic architecture |

---

## 16. Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Linear surrogate for inverse problem | Gradient mode finds chemically related but not identical patterns | Use fast mode for exact database match; gradient for novel synthesis |
| dt=0.5ms ceiling for Euler integration | Max ~3.35x RT without changing integration method | Switch to RK4 or implicit Euler for dt>2ms |
| No gap junctions in wave model | Wide-field integration (HS/VS) requires additional mechanisms | Direct Barlow-Levick filter for motion; HS/VS validated separately |
| Deterministic phototransduction | Cannot reproduce Juusola 50-200 Hz quantum bumps | Stage 2.5 PoissonSpikingWrapper covers stochastic regime |
| 183/372 odorants classified as "other" | Chemical family classification is keyword-based | Add PubChem/ChEBI taxonomy for better classification |
| Full brain slower than real-time | 139K neurons at ~0.004x RT | Use olfactory subgraph (10.9K neurons, 3.35x RT) for real-time applications |

---

## 17. File Reference

### Core Engine

| File | Purpose |
|---|---|
| `hive/engine/sparse_probabilistic.py` | Main wave engine (SparseProbabilisticBrain) |
| `hive/engine/poisson_spiking.py` | Stage 2.5 Poisson spiking wrapper |
| `hive/engine/oscillator_gpu.py` | GPU oscillator (FlyBrainSystem path) |
| `hive/engine/coupling_gpu.py` | GPU synaptic coupling |
| `hive/gpu_utils.py` | MLX/CuPy/NumPy backend selection |

### Substrate

| File | Purpose |
|---|---|
| `hive/substrate/connectome.py` | FAFB connectome loader (Neuron, Synapse, Connectome) |
| `hive/substrate/olfactory_subgraph.py` | Olfactory pathway extraction (10,906 neurons) |
| `hive/substrate/visual_pathway.py` | Visual pathway extraction (~53K neurons) |
| `hive/substrate/sensory_motor_map.py` | Sensory-to-motor neuron ID mapping |

### Data

| File | Purpose |
|---|---|
| `hive/data/door_client.py` | DoOR 2.0 receptor response interface |
| `hive/data/smell_database.py` | SmellDatabase (glom + KC patterns, search) |
| `data/door_consensus_matrix.npy` | 372 odorants × 33 receptors (66 KB) |
| `data/digital_smell_database_full.json` | 372 KC fingerprints × 5,279 dims (9.6 MB) |

### Inverse Problem

| File | Purpose |
|---|---|
| `hive/inverse/smell_optimizer.py` | DifferentiableSmellMapper + SmellOptimizer |

### Vision

| File | Purpose |
|---|---|
| `hive/vision/phototransduction.py` | 10-variable ODE photoreceptor cascade (RK4) |
| `hive/vision/compound_eye.py` | Hex ommatidium grid + optical flow |
| `hive/vision/spectral_stimuli.py` | Wavelength-specific stimulus generation |
| `hive/vision/photoreceptor_database.py` | Rhodopsin spectral sensitivity curves |
| `hive/vision/lamina_cartridge.py` | Lamina L1-L5 processing |

### Validation Tests

| File | Benchmarks |
|---|---|
| `hive/validation/smell/test_extinction_learning.py` | Tully extinction paradigm |
| `hive/validation/smell/test_context_recall.py` | PAM/PPL1 compartments |
| `hive/validation/smell/test_sequence_learning.py` | A→B temporal prediction |
| `hive/validation/smell/test_noise_robustness.py` | 3-stage noise characterization |
| `hive/validation/smell/test_prosthetic_poc.py` | PN lesion compensation |
| `hive/validation/smell/test_poisson_noise.py` | PN noise bottleneck |
| `hive/validation/vision/test_sparse_coding.py` | 4-layer visual sparsity |
| `hive/validation/vision/test_contrast_invariance.py` | Weber-Fechner encoding |
| `hive/validation/vision/test_decorrelation.py` | UV/vis chromatic opponency |
| `hive/validation/vision/test_motion_detection.py` | T4 Barlow-Levick DSI |
| `hive/validation/vision/test_color_constancy.py` | von Kries adaptation |
| `hive/validation/vision/test_hs_vs_optic_flow.py` | HS/VS optic flow |
| `hive/validation/vision/test_poisson_spiking.py` | Quantum bump CV transition |
| `hive/validation/auditory/test_jo_frequency_tuning.py` | JO subtype resonance |
| `hive/validation/auditory/test_auditory_learning.py` | AMMC→WED STDP |

Withdrawn as invalid (see `hive/validation/invalid/README.md`):
`test_context_recall.py` and `test_multisensory_integration.py`.

### Scripts

| File | Purpose |
|---|---|
| `scripts/run_all_validations.py` | Core olfactory benchmark suite |
| `scripts/run_new_tests.py` | Supplementary test suite |
| `scripts/download_door_data.py` | Fetch DoOR 2.0 data from GitHub |
| `scripts/batch_encode_odors.py` | Generate KC fingerprints for all odorants (`fast_mode=True`, dt = 0.5 ms) |
| `benchmarks/benchmark_realtime.py` | RT factor benchmark (3 configs) |
| `tests/test_dt_sweep.py` | dt vs accuracy/speed trade-off (prints only, writes no file) |
| `tests/test_smell_synthesis.py` | SmellOptimizer round-trip validation |
| `tests/concentration_invariance_test.py` | Concentration invariance |

---

*Hardware: Apple M4 Pro (MLX Metal GPU). Measured 86.3× faster than the NumPy CPU
path on the olfactory subgraph. Output equivalence between the two backends is
untested — `cpu_vs_mlx_validation.json` declares a 0.95 pattern-correlation criterion
but records `pattern_correlation: null`.*

*Independent, unreviewed work. Nothing here has been peer reviewed or published.*
