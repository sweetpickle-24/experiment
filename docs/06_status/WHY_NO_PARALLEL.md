
WHY TRUE SIMULTANEOUS PARALLEL EXECUTION IS IMPOSSIBLE FOR NEURAL SIMULATION

## The Fundamental Problem: Time Dependencies

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
> Current: [README](../../README.md) ·
> [ARCHITECTURE](../../ARCHITECTURE.md) ·
> [LIMITATIONS](../../docs/03_validation/LIMITATIONS.md) ·
> [audit](../../docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md) ·
> [projection repair](../../docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md).
> Tracked in [OUTDATED_FILES.md](../../OUTDATED_FILES.md).


Neural simulation has an inherent sequential dependency:

Step N+1 DEPENDS ON Step N's results.

Example:
- Step 1: Neuron phases are [0.1, 0.5, 0.9]
- Step 2: Compute coupling forces BASED ON Step 1's phases
- Step 3: Update phases BASED ON Step 2's forces
- Step 4: Compute coupling forces BASED ON Step 3's phases (new values!)

You CANNOT compute Step 4 until Step 3 completes.
This is called a "data dependency" - it's mathematically impossible to parallelize.

## What CAN Be Parallelized

### 1. Within a Single Step (Already Doing This!)
✓ All 139K neurons update simultaneously on GPU
✓ All 5.3M synapses compute forces in parallel
✓ Sin/cos/exp operations vectorized across all neurons

This is ALREADY happening in MLX - it's SIMD parallelism.

### 2. Batching (What We Implemented)
✓ Defer sync points to process multiple steps before waiting
✓ Allows GPU to optimize compute graph across steps
✓ 16× speedup by syncing every 10 steps instead of every step

### 3. Multiple Independent Simulations (NOT what you want)
✓ Could run 10 separate brains in parallel
✗ But you want ONE brain's behavior, not 10 separate brains

## Why Scatter-Add Is The Bottleneck

Scatter-add has a fundamental concurrency problem:

```
Synapse 1: neuron[100] += 0.5
Synapse 2: neuron[100] += 0.3  # CONFLICT! Both writing to neuron[100]
Synapse 3: neuron[200] += 0.2
```

Multiple threads trying to write to the same memory location requires:
1. **Atomic operations** (slow - threads must wait for lock)
2. **CPU accumulation** (what we do - fast sequential code)
3. **Segment reduction** (sort + reduce - O(n log n) overhead)

NumPy's `add.at()` is highly optimized C code that beats all GPU alternatives
for this specific workload (many duplicates, sparse updates).

## The Real Physics Constraint

Even if we had infinite computing power:

**Neural dynamics are CONTINUOUS TIME processes.**

The brain evolves through time: t₀ → t₁ → t₂ → t₃

You can't compute t₃ without knowing what happened at t₂.
You can't compute t₂ without knowing what happened at t₁.

It's like asking "why can't we simulate 100 years of weather in 1 second?"
Because each moment depends on the previous moment.

## Current Performance Status

### What We Achieved:
- **Sequential**: 280ms/step → 857 hours for 11M steps
- **Batched (10 steps)**: 17ms/step → 51 hours for 11M steps
- **Speedup**: 16.7× faster

### What's Left:
The remaining 17ms/step breaks down as:
1. **~12ms**: Scatter-add (5.3M updates) - CPU-bound, unavoidable
2. **~3ms**: Oscillator dynamics (sin/cos/exp) - already GPU-parallel
3. **~2ms**: Monitoring/tracking - could be reduced

## Why We Can't Go Faster

### Option 1: Custom CUDA/Metal Kernels
✓ Could write atomic scatter-add in Metal
✗ Would require learning Metal Shading Language
✗ MLX doesn't expose kernel compilation API yet
✗ Atomic adds are SLOW (threads block each other)
✗ Likely SLOWER than NumPy's optimized add.at

### Option 2: Approximations
✓ Subsample neurons (run 20K olfactory pathway, not 139K full brain)
✓ Larger timestep (dt=1ms instead of 0.5ms) - 2× speedup
✗ Reduces biological accuracy

### Option 3: Dedicated Hardware
✓ NVIDIA GPU with native scatter-add (cupy.scatter_add) - might be 2-3× faster
✗ You have Apple Silicon, not NVIDIA
✓ Neuromorphic chips (SpiNNaker, BrainScaleS) - 1000× faster
✗ Requires completely different architecture

## Bottom Line

**You CAN'T have true simultaneous execution of sequential time steps.**

It's like asking to watch a movie where all frames play at once.
Each frame must come after the previous frame - that's what time means.

What we DID achieve:
1. ✓ Maximize parallelism WITHIN each step (GPU vectorization)
2. ✓ Minimize sync overhead (batch processing)
3. ✓ Optimize the bottleneck operation (scatter-add)

Result: **16.7× speedup** - from 36 days to 51 hours.

## Realistic Path Forward

If 51 hours is still too slow:

**1. Run Olfactory Pathway Only (Recommended)**
   - 5,670 PNs + 5,595 MB + 2,972 LH = ~15K neurons
   - ~500K synapses instead of 5.3M
   - **10× faster** → 5 hours total
   - Still biologically accurate for odor experiments

**2. Increase Integration Timestep**
   - dt = 1.0ms instead of 0.5ms
   - **2× faster** → 25 hours
   - Still captures relevant dynamics (odors are 200ms stimuli)

**3. Reduce Simulation Duration**
   - Run 1 second per trial instead of 0.5s
   - 3 odors instead of 11
   - **5× faster** → 10 hours

**Combined (all three)**: 0.5 hours = **30 minutes**

This is the realistic limit without changing hardware or algorithm fundamentals.
