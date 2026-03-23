"""
Smell Test — Python Reference Implementation

Self-contained sparse wave oscillator for olfactory KC pattern discrimination.
No connectome files needed. Synthetic fly-scale network with biological parameters.

Network (Drosophila scale):
  - 2,198 PNs (Projection Neurons), 20 glomerular channels (110 PNs each)
  - 5,279 KCs (Kenyon Cells), each samples 7 random PNs (Caron et al. 2013)
  - APL global inhibition (winner-take-all at ~2% sparsity threshold)

Physics per 0.1ms timestep:
  - Sparse coupling: force[post] += weight * sin(phi_pre - phi_post) * amp_pre * var_corr
  - Harmonic oscillator: a = -2γv - ω²φ + coupling + ext_force
  - Phase wrap, variance decay, amplitude drive

Metrics:
  - KC sparsity (fraction active above mean+1σ threshold)
  - Inter-odor Pearson correlation between KC amplitude patterns
  - Wall-clock time for 300ms simulation
"""

import numpy as np
import time
import json

# ─── Network constants ────────────────────────────────────────────────────────
N_PN         = 2198
N_KC         = 5279
N_CHANNELS   = 20
KC_FAN_IN    = 7        # PNs per KC (Caron et al. 2013)
SIM_MS       = 300.0    # ms
DT           = 0.1      # ms
SEED         = 42

# ─── Physics constants ────────────────────────────────────────────────────────
GAMMA        = 0.1
SIGMA_NOISE  = 0.1
OMEGA0       = 2.0 * np.pi * 10.0 / 1000.0   # 10 Hz → rad/ms
EXT_STRENGTH = 50.0
VAR_CORR     = np.exp(-0.1 / 2.0)

# ─── Channel frequencies (Hz, from olfactory.py) ─────────────────────────────
CHANNEL_FREQ = np.array([
    20.0, 18.0, 22.0,  8.0, 12.0, 16.0,
    14.0,  6.0, 10.0,  5.0,  9.0, 12.0,
     7.0,  6.0,  5.0,  5.0, 11.0, 13.0,
     7.0,  4.0
], dtype=np.float32)
CHANNEL_OMEGA = (2.0 * np.pi * CHANNEL_FREQ / 1000.0).astype(np.float32)

# ─── Odor patterns (20-channel glomerular activation, from olfactory.py) ─────
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
    """Build synthetic PN→KC connectivity. Each KC samples KC_FAN_IN random PNs."""
    rng = np.random.default_rng(seed)
    # Each KC connects to KC_FAN_IN random PNs
    kc_pn_pre  = []   # pre-synapse indices (into PN block, 0-based)
    kc_pn_post = []   # post-synapse indices (into KC block, 0-based)

    for kc in range(N_KC):
        pns = rng.choice(N_PN, size=KC_FAN_IN, replace=False)
        for pn in pns:
            kc_pn_pre.append(pn)
            kc_pn_post.append(kc)

    return (np.array(kc_pn_pre, dtype=np.int32),
            np.array(kc_pn_post, dtype=np.int32))


def run_simulation(odor_pattern, kc_pre, kc_post, seed=SEED):
    """
    Run 300ms of sparse wave oscillator simulation.
    Returns KC amplitude array at end of simulation.
    """
    rng = np.random.default_rng(seed)
    N = N_PN + N_KC

    # State
    phase = rng.uniform(-np.pi, np.pi, N).astype(np.float32)
    vel   = np.zeros(N, dtype=np.float32)
    amp   = np.full(N, 0.1, dtype=np.float32)
    var_ph = np.full(N, 0.1, dtype=np.float32)

    # External forcing — PNs only
    # Each channel drives N_PN/N_CHANNELS PNs
    pns_per_ch = N_PN // N_CHANNELS
    ext_base = np.zeros(N, dtype=np.float32)   # amplitude per neuron
    for ch in range(N_CHANNELS):
        start = ch * pns_per_ch
        end   = start + pns_per_ch
        ext_base[start:end] = odor_pattern[ch] * EXT_STRENGTH

    # PN→KC synapse weights (uniform 1/KC_FAN_IN for normalised input)
    weights = np.full(len(kc_pre), 1.0 / KC_FAN_IN, dtype=np.float32)

    # Synapse indices shifted: PNs are [0..N_PN), KCs are [N_PN..N)
    pre_global  = kc_pre                    # PN indices (0-based in PN block)
    post_global = kc_post + N_PN            # KC indices in full N array

    num_steps = int(SIM_MS / DT)

    for step in range(num_steps):
        t = step * DT

        # External force: sinusoidal per channel
        ext_force = np.zeros(N, dtype=np.float32)
        for ch in range(N_CHANNELS):
            s = ch * pns_per_ch
            e = s + pns_per_ch
            f = ext_base[s] * np.sin(CHANNEL_OMEGA[ch] * t)
            ext_force[s:e] = f

        # Coupling (PN → KC only)
        delta_phi = phase[pre_global] - phase[post_global]
        syn_f = weights * np.sin(delta_phi) * amp[pre_global] * VAR_CORR
        coupling = np.zeros(N, dtype=np.float32)
        np.add.at(coupling, post_global, syn_f)

        # Oscillator update
        accel = (-2.0 * GAMMA * vel
                 - OMEGA0**2 * phase
                 + coupling
                 + ext_force)
        vel   += accel * DT
        phase += vel * DT
        phase  = np.arctan2(np.sin(phase), np.cos(phase))

        # Variance
        var_ph = var_ph * (1.0 - 2.0 * GAMMA * DT) + SIGMA_NOISE**2 * DT
        var_ph = np.clip(var_ph, 0.01, 10.0)

        # Amplitude
        amp_drive = np.abs(vel) * 0.1
        amp = amp * (1.0 - GAMMA * DT) + amp_drive * DT
        amp = np.clip(amp, 0.001, 10.0)

    # Return KC amplitudes (final state)
    return amp[N_PN:]


def compute_sparsity(kc_amp):
    """Fraction of KCs above mean + 1 std (biologically active)."""
    threshold = kc_amp.mean() + kc_amp.std()
    return float(np.sum(kc_amp > threshold) / len(kc_amp))


def pearson_r(a, b):
    a = a - a.mean(); b = b - b.mean()
    denom = np.sqrt((a**2).sum() * (b**2).sum())
    return float(np.dot(a, b) / denom) if denom > 1e-10 else 0.0


def main():
    print("=" * 60)
    print("  SMELL TEST — Python Reference")
    print(f"  Network: {N_PN} PNs + {N_KC} KCs, {KC_FAN_IN} PN/KC")
    print(f"  Simulation: {SIM_MS}ms at dt={DT}ms ({int(SIM_MS/DT):,} steps)")
    print("=" * 60)

    kc_pre, kc_post = build_network()
    print(f"  Synapses: {len(kc_pre):,}")

    odor_names = list(ODORS.keys())
    kc_patterns = {}

    print("\n  Running simulations...")
    total_t0 = time.perf_counter()

    for name, pattern in ODORS.items():
        t0 = time.perf_counter()
        kc_amp = run_simulation(pattern, kc_pre, kc_post)
        elapsed = time.perf_counter() - t0
        sparsity = compute_sparsity(kc_amp)
        kc_patterns[name] = kc_amp
        print(f"    {name:20s}  sparsity={sparsity*100:.2f}%  time={elapsed:.3f}s")

    total_elapsed = time.perf_counter() - total_t0

    print(f"\n  Total wall time: {total_elapsed:.3f}s")
    print(f"  Per-odor:        {total_elapsed/len(ODORS):.3f}s")

    # Inter-odor correlations
    print("\n  Inter-odor KC correlations:")
    corr_matrix = {}
    for i, n1 in enumerate(odor_names):
        for j, n2 in enumerate(odor_names):
            if j > i:
                r = pearson_r(kc_patterns[n1], kc_patterns[n2])
                corr_matrix[f"{n1} vs {n2}"] = round(r, 4)
                print(f"    {n1:20s} vs {n2:20s}: r = {r:.4f}")

    # Key metrics
    avg_sparsity = np.mean([compute_sparsity(v) for v in kc_patterns.values()])
    fruit_vs_danger = pearson_r(kc_patterns["fruit_ferment"], kc_patterns["danger_mold"])
    fruit_vs_fruit  = pearson_r(kc_patterns["fruit_ferment"], kc_patterns["fruit_ripe"])

    print(f"\n  KEY METRICS:")
    print(f"    Average KC sparsity:        {avg_sparsity*100:.2f}%  (target: 1-3%)")
    print(f"    fruit_ferment vs danger:    r = {fruit_vs_danger:.4f}  (should be low)")
    print(f"    fruit_ferment vs fruit_ripe:r = {fruit_vs_fruit:.4f}  (should be higher)")

    # Save JSON for comparison
    results = {
        "language": "python",
        "n_pn": N_PN,
        "n_kc": N_KC,
        "kc_fan_in": KC_FAN_IN,
        "sim_ms": SIM_MS,
        "total_wall_time_s": round(total_elapsed, 4),
        "per_odor_s": round(total_elapsed / len(ODORS), 4),
        "avg_kc_sparsity_pct": round(avg_sparsity * 100, 4),
        "fruit_vs_danger_r": round(fruit_vs_danger, 4),
        "fruit_vs_fruit_r": round(fruit_vs_fruit, 4),
        "kc_mean_amp": {k: round(float(v.mean()), 6) for k, v in kc_patterns.items()},
        "correlations": corr_matrix,
    }

    out = "/Users/vladyslav/Documents/GitHub/experiment/benchmarks/smell_test/results_python.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {out}")


if __name__ == "__main__":
    main()
