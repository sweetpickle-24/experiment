"""
Smell Test — Python MLX GPU Implementation

Same physics as smell_test.py but all arrays live on the M4 Pro GPU (Metal).
Uses MLX (Apple's ML framework) for GPU scatter/gather ops.

Key differences from CPU version:
- All state arrays are mx.array (on GPU, unified memory)
- ext_force built via vectorized broadcast (no Python loops per step)
- Scatter: forces.at[post_g].add(syn_f)  — MLX native GPU scatter
- mx.eval() every 100 steps to prevent graph explosion
"""

import numpy as np
import time
import json

try:
    import mlx.core as mx
    assert mx.default_device() == mx.gpu
except Exception as e:
    raise RuntimeError(f"MLX GPU not available: {e}")

# ─── Constants (identical to CPU benchmark) ───────────────────────────────────
N_PN         = 2198
N_KC         = 5279
N_CHANNELS   = 20
KC_FAN_IN    = 7
SIM_MS       = 300.0
DT           = 0.1
SEED         = 42
GAMMA        = 0.1
SIGMA_NOISE  = 0.1
OMEGA0       = 2.0 * np.pi * 10.0 / 1000.0
EXT_STR      = 50.0
VAR_CORR     = float(np.exp(-0.1 / 2.0))

CHANNEL_FREQ = np.array([
    20.0, 18.0, 22.0,  8.0, 12.0, 16.0,
    14.0,  6.0, 10.0,  5.0,  9.0, 12.0,
     7.0,  6.0,  5.0,  5.0, 11.0, 13.0,
     7.0,  4.0], dtype=np.float32)
CHANNEL_OMEGA = (2.0 * np.pi * CHANNEL_FREQ / 1000.0).astype(np.float32)

def _norm(v):
    n = np.linalg.norm(v)
    return (v / n).astype(np.float32)

ODORS = {
    "fruit_ferment": _norm(np.array([
        0.85, 0.20, 0.70, 0.10, 0.15, 0.05,
        0.65, 0.25, 0.40, 0.00, 0.00, 0.00,
        0.00, 0.05, 0.00, 0.00, 0.15, 0.10,
        0.00, 0.05])),
    "fruit_ripe": _norm(np.array([
        0.90, 0.45, 0.35, 0.15, 0.20, 0.30,
        0.25, 0.05, 0.20, 0.00, 0.00, 0.10,
        0.00, 0.00, 0.00, 0.00, 0.10, 0.20,
        0.00, 0.05])),
    "danger_mold": _norm(np.array([
        0.00, 0.00, 0.05, 0.00, 0.00, 0.00,
        0.00, 0.20, 0.60, 0.70, 0.00, 0.05,
        0.90, 0.85, 0.00, 0.00, 0.05, 0.00,
        0.75, 0.00])),
    "social_female": _norm(np.array([
        0.00, 0.05, 0.00, 0.30, 0.10, 0.00,
        0.00, 0.00, 0.00, 0.20, 0.10, 0.10,
        0.00, 0.00, 0.90, 0.05, 0.05, 0.00,
        0.00, 0.05])),
    "clean_air": _norm(np.array([
        0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
        0.02, 0.05, 0.02, 0.00, 0.00, 0.02,
        0.00, 0.00, 0.00, 0.00, 0.05, 0.05,
        0.00, 0.90])),
}


def build_network(seed=SEED):
    rng = np.random.default_rng(seed)
    pre, post = [], []
    for kc in range(N_KC):
        pns = rng.choice(N_PN, size=KC_FAN_IN, replace=False)
        for pn in pns:
            pre.append(pn)
            post.append(kc)
    return (np.array(pre, dtype=np.int32),
            np.array(post, dtype=np.int32))


def run_simulation_gpu(odor_pattern, kc_pre, kc_post, seed=SEED):
    """
    Full simulation on GPU using MLX.
    
    Key GPU tricks:
    1. pn_omega_g / pn_strength_g: precomputed per-PN arrays — vectorized ext_force
    2. forces.at[post_g].add(syn_f): MLX scatter on GPU (no Python loop)
    3. mx.eval() every 100 steps: flush MLX lazy graph to prevent memory explosion
    """
    N = N_PN + N_KC
    rng = np.random.default_rng(seed)

    # ── Initial state on GPU ──────────────────────────────────────────────────
    phase  = mx.array(rng.uniform(-np.pi, np.pi, N).astype(np.float32))
    vel    = mx.zeros(N, dtype=mx.float32)
    amp    = mx.ones(N, dtype=mx.float32) * 0.1
    var_ph = mx.ones(N, dtype=mx.float32) * 0.1

    # ── Synapse arrays on GPU ─────────────────────────────────────────────────
    # post_g are KC indices in the full N array (offset by N_PN)
    pre_g  = mx.array(kc_pre)
    post_g = mx.array(kc_post + N_PN)
    wts    = mx.array(np.full(len(kc_pre), 1.0 / KC_FAN_IN, dtype=np.float32))

    # ── Per-PN forcing: vectorized (no Python loop per step) ──────────────────
    pns_per_ch = N_PN // N_CHANNELS
    pn_omega_np    = np.zeros(N_PN, dtype=np.float32)
    pn_strength_np = np.zeros(N_PN, dtype=np.float32)
    for ch in range(N_CHANNELS):
        s, e = ch * pns_per_ch, (ch + 1) * pns_per_ch
        pn_omega_np[s:e]    = CHANNEL_OMEGA[ch]
        pn_strength_np[s:e] = odor_pattern[ch] * EXT_STR

    pn_omega_g    = mx.array(pn_omega_np)        # (N_PN,) on GPU
    pn_strength_g = mx.array(pn_strength_np)     # (N_PN,) on GPU
    zeros_kc      = mx.zeros(N_KC, dtype=mx.float32)  # KC ext_force = 0

    num_steps = int(SIM_MS / DT)

    for step in range(num_steps):
        t = float(step * DT)

        # External force: one GPU vectorized op (no Python loop)
        pn_forces  = pn_strength_g * mx.sin(pn_omega_g * t)
        ext_force  = mx.concatenate([pn_forces, zeros_kc])  # (N,)

        # Coupling: gather → compute → scatter
        delta_phi  = phase[pre_g] - phase[post_g]
        syn_f      = wts * mx.sin(delta_phi) * amp[pre_g] * VAR_CORR
        coupling   = mx.zeros(N, dtype=mx.float32).at[post_g].add(syn_f)

        # Oscillator update
        accel = -2.0 * GAMMA * vel - OMEGA0**2 * phase + coupling + ext_force
        vel   = vel + accel * DT
        phase = phase + vel * DT
        phase = mx.arctan2(mx.sin(phase), mx.cos(phase))

        var_ph = var_ph * (1.0 - 2.0 * GAMMA * DT) + SIGMA_NOISE**2 * DT
        var_ph = mx.clip(var_ph, 0.01, 10.0)

        amp_drive = mx.abs(vel) * 0.1
        amp = amp * (1.0 - GAMMA * DT) + amp_drive * DT
        amp = mx.clip(amp, 0.001, 10.0)

        # Flush graph every 100 steps to avoid memory explosion
        if step % 100 == 0:
            mx.eval(amp, phase, vel, var_ph)

    # Final GPU sync + extract KC amplitudes
    mx.eval(amp)
    return np.array(amp)[N_PN:]


def compute_sparsity(kc_amp):
    threshold = kc_amp.mean() + kc_amp.std()
    return float(np.sum(kc_amp > threshold) / len(kc_amp))

def pearson_r(a, b):
    a = a - a.mean(); b = b - b.mean()
    denom = np.sqrt((a**2).sum() * (b**2).sum())
    return float(np.dot(a, b) / denom) if denom > 1e-10 else 0.0


def main():
    print("=" * 60)
    print("  SMELL TEST — Python MLX GPU")
    print(f"  Device: {mx.default_device()}")
    print(f"  Network: {N_PN} PNs + {N_KC} KCs, {KC_FAN_IN} PN/KC")
    print(f"  Simulation: {SIM_MS}ms at dt={DT}ms ({int(SIM_MS/DT):,} steps)")
    print("=" * 60)

    kc_pre, kc_post = build_network()
    print(f"  Synapses: {len(kc_pre):,}")

    # Warmup: avoid counting JIT compilation in timing
    print("\n  Warming up GPU kernels...")
    _ = run_simulation_gpu(list(ODORS.values())[0], kc_pre, kc_post)
    print("  Warmup complete.")

    odor_names  = list(ODORS.keys())
    kc_patterns = {}

    print("\n  Running simulations (GPU)...")
    total_t0 = time.perf_counter()

    for name, pattern in ODORS.items():
        t0 = time.perf_counter()
        kc_amp = run_simulation_gpu(pattern, kc_pre, kc_post)
        elapsed = time.perf_counter() - t0
        sp = compute_sparsity(kc_amp)
        kc_patterns[name] = kc_amp
        rt = elapsed / (SIM_MS / 1000.0)
        print(f"    {name:20s}  sparsity={sp*100:.2f}%  time={elapsed:.3f}s  "
              f"({'%.1f' % (1/rt)}x realtime)" if rt < 1.0 else
              f"    {name:20s}  sparsity={sp*100:.2f}%  time={elapsed:.3f}s  "
              f"({rt:.1f}x slower than realtime)")

    total_elapsed = time.perf_counter() - total_t0
    print(f"\n  Total wall time: {total_elapsed:.3f}s")
    print(f"  Per-odor:        {total_elapsed/len(ODORS):.3f}s")
    rt_avg = (total_elapsed / len(ODORS)) / (SIM_MS / 1000.0)
    if rt_avg < 1.0:
        print(f"  Real-time:       {1/rt_avg:.1f}x FASTER than real life")
    else:
        print(f"  Real-time:       {rt_avg:.1f}x SLOWER than real life")

    print("\n  Inter-odor KC correlations:")
    corr_matrix = {}
    for i, n1 in enumerate(odor_names):
        for j, n2 in enumerate(odor_names):
            if j > i:
                r = pearson_r(kc_patterns[n1], kc_patterns[n2])
                corr_matrix[f"{n1} vs {n2}"] = round(r, 4)
                print(f"    {n1:20s} vs {n2:20s}: r = {r:.4f}")

    avg_sp = np.mean([compute_sparsity(v) for v in kc_patterns.values()])
    fruit_vs_danger = pearson_r(kc_patterns["fruit_ferment"], kc_patterns["danger_mold"])
    fruit_vs_fruit  = pearson_r(kc_patterns["fruit_ferment"], kc_patterns["fruit_ripe"])
    per_odor_s = total_elapsed / len(ODORS)
    rt_ratio = per_odor_s / (SIM_MS / 1000.0)

    print(f"\n  KEY METRICS:")
    print(f"    Average KC sparsity:        {avg_sp*100:.2f}%")
    print(f"    fruit_ferment vs danger:    r = {fruit_vs_danger:.4f}")
    print(f"    fruit_ferment vs fruit_ripe:r = {fruit_vs_fruit:.4f}")
    print(f"    Real-time factor:           {rt_ratio:.2f}x {'(FASTER)' if rt_ratio < 1 else '(slower)'}")

    results = {
        "language": "python_mlx_gpu",
        "device": str(mx.default_device()),
        "n_pn": N_PN, "n_kc": N_KC, "kc_fan_in": KC_FAN_IN, "sim_ms": SIM_MS,
        "total_wall_time_s": round(total_elapsed, 4),
        "per_odor_s": round(per_odor_s, 4),
        "realtime_ratio": round(rt_ratio, 4),
        "avg_kc_sparsity_pct": round(avg_sp * 100, 4),
        "fruit_vs_danger_r": round(fruit_vs_danger, 4),
        "fruit_vs_fruit_r": round(fruit_vs_fruit, 4),
        "kc_mean_amp": {k: round(float(v.mean()), 6) for k, v in kc_patterns.items()},
        "correlations": corr_matrix,
    }

    out = "/Users/vladyslav/Documents/GitHub/experiment/benchmarks/smell_test/results_python_gpu.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {out}")


if __name__ == "__main__":
    main()
