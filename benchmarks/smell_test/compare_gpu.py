"""
GPU Smell Test — Full Comparison: CPU vs GPU, Python vs Julia vs Rust
"""

import json, os

BASE = os.path.dirname(__file__)

def load(tag):
    p = os.path.join(BASE, f"results_{tag}.json")
    with open(p) as f: return json.load(f)

def to_f(v): return float(v) if isinstance(v, (int, float)) else float(str(v))

def main():
    py_cpu  = load("python")
    jl_cpu  = load("julia")
    rs_cpu  = load("rust")
    py_gpu  = load("python_gpu")
    jl_gpu  = load("julia_gpu")
    rs_gpu  = load("rust_gpu")

    all6 = [
        ("Python CPU",  py_cpu,  "cpu"),
        ("Julia  CPU",  jl_cpu,  "cpu"),
        ("Rust   CPU",  rs_cpu,  "cpu"),
        ("Python MLX",  py_gpu,  "gpu"),
        ("Julia Metal", jl_gpu,  "gpu"),
        ("Rust Metal",  rs_gpu,  "gpu"),
    ]

    sim_ms = 300.0   # ms of biology per run

    print("\n" + "="*76)
    print("  SMELL TEST — FULL COMPARISON: CPU vs GPU")
    print("  Sparse wave oscillator: 2198 PNs + 5279 KCs, 300ms at dt=0.1ms")
    print("="*76)

    # ── Performance ─────────────────────────────────────────────────────────
    print(f"\n{'PERFORMANCE':}")
    print(f"  {'Implementation':<16} {'Per-odor (s)':>13} {'vs Py-CPU':>10} {'vs Real-time':>14}")
    print(f"  {'-'*14} {'-'*13} {'-'*10} {'-'*14}")
    py_cpu_t = to_f(py_cpu["per_odor_s"])
    for label, r, kind in all6:
        t  = to_f(r["per_odor_s"])
        sp = py_cpu_t / t
        rt = t / (sim_ms / 1000.0)
        rt_str = f"{1/rt:.1f}x faster" if rt < 1.0 else f"{rt:.1f}x slower"
        tag = "🟢 GPU" if kind == "gpu" else "   CPU"
        print(f"  {tag} {label:<14} {t:>13.3f} {sp:>9.1f}x {rt_str:>14}")

    # ── Real-time boundary ────────────────────────────────────────────────────
    print(f"\n  REAL-TIME BOUNDARY (1.0 = real-time speed):")
    for label, r, kind in all6:
        rt = to_f(r["per_odor_s"]) / (sim_ms / 1000.0)
        bar_len = max(1, min(40, int(40 / rt))) if rt >= 1 else min(40, int(40 / rt * 10))
        marker = "REAL-TIME" if abs(rt - 1.0) < 0.2 else ("FASTER ✅" if rt < 1.0 else "slower ❌")
        if rt < 1.0:
            print(f"  {'GPU' if kind=='gpu' else 'CPU'} {label:<14}  {1/rt:5.1f}x faster  {marker}")
        else:
            print(f"  {'GPU' if kind=='gpu' else 'CPU'} {label:<14}  {rt:5.1f}x slower  {marker}")

    # ── Biological accuracy (GPU vs CPU consistency) ──────────────────────────
    print(f"\n{'BIOLOGICAL ACCURACY (correlations should match CPU baseline):':}")
    print(f"  {'Implementation':<16} {'KC Sparsity':>12} {'fruit vs danger':>16} {'fruit vs fruit':>15}")
    print(f"  {'-'*14} {'-'*12} {'-'*16} {'-'*15}")
    for label, r, kind in all6:
        sp  = to_f(r["avg_kc_sparsity_pct"])
        fd  = to_f(r["fruit_vs_danger_r"])
        ff  = to_f(r["fruit_vs_fruit_r"])
        tag = "🟢 GPU" if kind == "gpu" else "   CPU"
        print(f"  {tag} {label:<14} {sp:>11.2f}% {fd:>16.4f} {ff:>15.4f}")

    # ── Speedup summary ────────────────────────────────────────────────────────
    py_gpu_t = to_f(py_gpu["per_odor_s"])
    jl_gpu_t = to_f(jl_gpu["per_odor_s"])
    rs_gpu_t = to_f(rs_gpu["per_odor_s"])
    jl_cpu_t = to_f(jl_cpu["per_odor_s"])
    rs_cpu_t = to_f(rs_cpu["per_odor_s"])

    print(f"\n{'GPU SPEEDUP OVER CPU (same language):':}")
    print(f"  Python:  {py_cpu_t:.3f}s → {py_gpu_t:.3f}s  ({py_cpu_t/py_gpu_t:.1f}× speedup)")
    print(f"  Julia:   {jl_cpu_t:.3f}s → {jl_gpu_t:.3f}s  ({jl_cpu_t/jl_gpu_t:.1f}× speedup)")
    print(f"  Rust:    {rs_cpu_t:.3f}s → {rs_gpu_t:.3f}s  ({rs_cpu_t/rs_gpu_t:.1f}× speedup)")

    print(f"\n{'REAL-TIME SUMMARY:':}")
    print(f"  Python CPU:   {py_cpu_t/(sim_ms/1000):.1f}× SLOWER than real life")
    print(f"  Julia  CPU:   {jl_cpu_t/(sim_ms/1000):.1f}× SLOWER than real life")
    print(f"  Rust   CPU:   {rs_cpu_t/(sim_ms/1000):.1f}× SLOWER than real life")
    print(f"  Python MLX:   {py_gpu_t/(sim_ms/1000):.2f}× {'FASTER' if py_gpu_t < sim_ms/1000 else 'SLOWER'} than real life")
    print(f"  Julia Metal:  {jl_gpu_t/(sim_ms/1000):.2f}× {'FASTER' if jl_gpu_t < sim_ms/1000 else 'SLOWER'} than real life")
    print(f"  Rust Metal:   {rs_gpu_t/(sim_ms/1000):.2f}× {'FASTER' if rs_gpu_t < sim_ms/1000 else 'SLOWER'} than real life  ← WINNER")

    print(f"\n{'WINNER — Rust Metal is ' + f'{py_cpu_t/rs_gpu_t:.0f}× faster than Python CPU':}")
    print("="*76 + "\n")


if __name__ == "__main__":
    main()
