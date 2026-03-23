"""
Smell Test — Julia Metal.jl GPU Implementation

Same physics as smell_test.jl but on the M4 Pro GPU via Metal.jl.

Two GPU kernels per step (no atomic scatter needed — synapses are built
in KC order, so coupling is a simple segmented reduce):

  Kernel 1: compute_coupling!  — N_KC threads, each sums its 7 PN inputs
  Kernel 2: oscillator_update! — N threads, runs wave physics + ext_force

No CPU-GPU round trip per step: state stays on GPU for all 3000 steps.
Final mx.synchronize() + Array() to pull KC amplitudes back to CPU.

Run:  julia smell_test_gpu.jl
"""

using Metal, Random, Statistics, Printf, JSON3, LinearAlgebra

# ─── Constants ────────────────────────────────────────────────────────────────
const N_PN       = 2198
const N_KC       = 5279
const N          = N_PN + N_KC
const N_CHANNELS = 20
const KC_FAN_IN  = 7
const SIM_MS     = 300.0f0
const DT         = 0.1f0
const SEED       = 42
const GAMMA      = 0.1f0
const SIGMA_NOISE = 0.1f0
const OMEGA0     = Float32(2π * 10.0 / 1000.0)
const VAR_CORR   = exp(-0.1f0 / 2.0f0)
const EXT_STR    = 50.0f0

const CHANNEL_OMEGA = Float32.(2π .* [
    20, 18, 22,  8, 12, 16,
    14,  6, 10,  5,  9, 12,
     7,  6,  5,  5, 11, 13,
     7,  4] ./ 1000.0)

function _norm(v)
    n = norm(v)
    Float32.(v ./ n)
end

const ODORS = Dict{String,Vector{Float32}}(
    "fruit_ferment"  => _norm([0.85,0.20,0.70,0.10,0.15,0.05,
                                0.65,0.25,0.40,0.00,0.00,0.00,
                                0.00,0.05,0.00,0.00,0.15,0.10,0.00,0.05]),
    "fruit_ripe"     => _norm([0.90,0.45,0.35,0.15,0.20,0.30,
                                0.25,0.05,0.20,0.00,0.00,0.10,
                                0.00,0.00,0.00,0.00,0.10,0.20,0.00,0.05]),
    "danger_mold"    => _norm([0.00,0.00,0.05,0.00,0.00,0.00,
                                0.00,0.20,0.60,0.70,0.00,0.05,
                                0.90,0.85,0.00,0.00,0.05,0.00,0.75,0.00]),
    "social_female"  => _norm([0.00,0.05,0.00,0.30,0.10,0.00,
                                0.00,0.00,0.00,0.20,0.10,0.10,
                                0.00,0.00,0.90,0.05,0.05,0.00,0.00,0.05]),
    "clean_air"      => _norm([0.02,0.02,0.02,0.02,0.02,0.02,
                                0.02,0.05,0.02,0.00,0.00,0.02,
                                0.00,0.00,0.00,0.00,0.05,0.05,0.00,0.90]),
)

# ─── Network ──────────────────────────────────────────────────────────────────
function build_network(seed::Int = SEED)
    rng = MersenneTwister(seed)
    pre  = Int32[]
    post = Int32[]
    pn_pool = collect(Int32, 1:N_PN)   # 1-based Julia indices
    for kc in 1:N_KC
        idxs = randperm(rng, N_PN)[1:KC_FAN_IN]
        for i in idxs
            push!(pre,  pn_pool[i])
            push!(post, Int32(kc))
        end
    end
    return pre, post
end

# ─── GPU Kernels ──────────────────────────────────────────────────────────────

"""
Kernel 1: compute_coupling!
Each thread handles one KC (1-based id = kc index in 1..N_KC).
Gathers KC_FAN_IN PN inputs (synapses in KC order) and writes coupling[kc + N_PN].
"""
function compute_coupling_kernel!(
        coupling::MtlDeviceArray{Float32,1},
        phase::MtlDeviceArray{Float32,1},
        amp::MtlDeviceArray{Float32,1},
        pre::MtlDeviceArray{Int32,1},
        weights::MtlDeviceArray{Float32,1})
    kc = thread_position_in_grid_1d()
    kc > N_KC && return
    ki = kc + N_PN   # KC position in full N array (1-based)
    base = (kc - 1) * KC_FAN_IN  # 0-based synapse offset
    s = 0.0f0
    for i in 1:KC_FAN_IN
        pi = pre[base + i]   # 1-based PN index
        dp = phase[pi] - phase[ki]
        s += weights[base + i] * sin(dp) * amp[pi] * VAR_CORR
    end
    coupling[ki] = s
    return
end

"""
Kernel 2: oscillator_update!
Each thread handles one neuron (id = 1..N).
Runs full oscillator step + ext_force for PNs.
"""
function oscillator_update_kernel!(
        phase::MtlDeviceArray{Float32,1},
        vel::MtlDeviceArray{Float32,1},
        amp::MtlDeviceArray{Float32,1},
        var_ph::MtlDeviceArray{Float32,1},
        coupling::MtlDeviceArray{Float32,1},
        pn_strength::MtlDeviceArray{Float32,1},
        pn_omega::MtlDeviceArray{Float32,1},
        t::Float32)
    id = thread_position_in_grid_1d()
    id > N && return

    # External force: non-zero only for PNs
    ef = id <= N_PN ? pn_strength[id] * sin(pn_omega[id] * t) : 0.0f0

    a = -2.0f0 * GAMMA * vel[id] - OMEGA0 * OMEGA0 * phase[id] + coupling[id] + ef
    vel[id]   += a * DT
    phase[id] += vel[id] * DT
    phase[id]  = atan(sin(phase[id]), cos(phase[id]))

    vp = var_ph[id] * (1.0f0 - 2.0f0 * GAMMA * DT) + SIGMA_NOISE * SIGMA_NOISE * DT
    var_ph[id] = min(max(vp, 0.01f0), 10.0f0)

    ad = abs(vel[id]) * 0.1f0
    amp[id] = min(max(amp[id] * (1.0f0 - GAMMA * DT) + ad * DT, 0.001f0), 10.0f0)
    return
end

# ─── Simulation ───────────────────────────────────────────────────────────────
function run_simulation_gpu(odor_pattern::Vector{Float32},
                             pre_cpu::Vector{Int32},
                             post_cpu::Vector{Int32};
                             seed::Int = SEED)
    rng = MersenneTwister(seed)

    # Initial state on GPU
    phase  = MtlArray(Float32.(rand(rng, N) .* 2π .- π))
    vel    = MtlArray(zeros(Float32, N))
    amp    = MtlArray(fill(0.1f0, N))
    var_ph = MtlArray(fill(0.1f0, N))

    # Coupling workspace (PNs section stays 0)
    coupling = MtlArray(zeros(Float32, N))

    # Synapse arrays on GPU (1-based PN indices)
    pre_g  = MtlArray(pre_cpu)
    weights = MtlArray(fill(1.0f0 / KC_FAN_IN, length(pre_cpu)))

    # Per-PN forcing arrays (N_PN,)
    pns_per_ch = div(N_PN, N_CHANNELS)
    pn_omega_cpu    = zeros(Float32, N_PN)
    pn_strength_cpu = zeros(Float32, N_PN)
    for ch in 1:N_CHANNELS
        s = (ch-1)*pns_per_ch + 1
        e = s + pns_per_ch - 1
        pn_omega_cpu[s:e]    .= CHANNEL_OMEGA[ch]
        pn_strength_cpu[s:e] .= odor_pattern[ch] * EXT_STR
    end
    pn_omega    = MtlArray(pn_omega_cpu)
    pn_strength = MtlArray(pn_strength_cpu)

    # Thread grid config
    threads_kc  = min(N_KC, 1024)
    groups_kc   = cld(N_KC, threads_kc)
    threads_n   = min(N, 1024)
    groups_n    = cld(N, threads_n)

    num_steps = Int(SIM_MS / DT)

    for step in 0:num_steps-1
        t = Float32(step * DT)

        # Kernel 1: coupling (N_KC threads)
        @metal threads=threads_kc groups=groups_kc compute_coupling_kernel!(
            coupling, phase, amp, pre_g, weights)

        # Kernel 2: oscillator update (N threads)
        @metal threads=threads_n groups=groups_n oscillator_update_kernel!(
            phase, vel, amp, var_ph, coupling, pn_strength, pn_omega, t)
    end

    # Sync GPU and return KC amplitudes
    Metal.synchronize()
    return Array(amp)[N_PN+1:end]
end

# ─── Metrics ─────────────────────────────────────────────────────────────────
function compute_sparsity(kc::Vector{Float32})
    thr = mean(kc) + std(kc)
    count(x -> x > thr, kc) / length(kc)
end

function pearson_r(a::Vector{Float32}, b::Vector{Float32})
    am = a .- mean(a); bm = b .- mean(b)
    d = sqrt(sum(am.^2) * sum(bm.^2))
    d > 1e-10 ? dot(am, bm) / d : 0.0f0
end

# ─── Main ─────────────────────────────────────────────────────────────────────
function main()
    println("=" ^ 60)
    println("  SMELL TEST — Julia Metal.jl GPU")
    println("  Device: ", Metal.device())
    println("  Network: $N_PN PNs + $N_KC KCs, $KC_FAN_IN PN/KC")
    println("  Simulation: $(Int(SIM_MS))ms at dt=$(DT)ms ($(Int(SIM_MS/DT)) steps)")
    println("=" ^ 60)

    pre_cpu, post_cpu = build_network()
    println("  Synapses: $(length(pre_cpu))")

    # Warmup: force kernel compilation before timing
    println("\n  Warming up GPU kernels...")
    _ = run_simulation_gpu(first(values(ODORS)), pre_cpu, post_cpu)
    println("  Warmup complete.")

    odor_names = collect(keys(ODORS))
    kc_patterns = Dict{String,Vector{Float32}}()

    println("\n  Running simulations (GPU)...")
    total_t0 = time()

    for name in odor_names
        pattern = ODORS[name]
        t0 = time()
        kc_amp = run_simulation_gpu(pattern, pre_cpu, post_cpu)
        elapsed = time() - t0
        sp = compute_sparsity(kc_amp)
        kc_patterns[name] = kc_amp
        rt = elapsed / (SIM_MS / 1000.0)
        if rt < 1.0
            @printf("    %-20s  sparsity=%.2f%%  time=%.3fs  (%.1fx faster than realtime)\n",
                    name, sp*100, elapsed, 1/rt)
        else
            @printf("    %-20s  sparsity=%.2f%%  time=%.3fs  (%.1fx slower than realtime)\n",
                    name, sp*100, elapsed, rt)
        end
    end

    total_elapsed = time() - total_t0
    per_odor = total_elapsed / length(ODORS)
    rt_avg = per_odor / (SIM_MS / 1000.0)

    @printf("\n  Total wall time: %.3fs\n", total_elapsed)
    @printf("  Per-odor:        %.3fs\n", per_odor)
    if rt_avg < 1.0
        @printf("  Real-time:       %.1fx FASTER than real life\n", 1/rt_avg)
    else
        @printf("  Real-time:       %.1fx SLOWER than real life\n", rt_avg)
    end

    println("\n  Inter-odor KC correlations:")
    corr_dict = Dict{String,Float64}()
    for (i, n1) in enumerate(odor_names)
        for (j, n2) in enumerate(odor_names)
            if j > i
                r = pearson_r(kc_patterns[n1], kc_patterns[n2])
                corr_dict["$n1 vs $n2"] = round(r; digits=4)
                @printf("    %-20s vs %-20s: r = %.4f\n", n1, n2, r)
            end
        end
    end

    avg_sp = mean(compute_sparsity(v) for v in values(kc_patterns))
    fvd = pearson_r(kc_patterns["fruit_ferment"], kc_patterns["danger_mold"])
    fvf = pearson_r(kc_patterns["fruit_ferment"], kc_patterns["fruit_ripe"])

    println("\n  KEY METRICS:")
    @printf("    Average KC sparsity:         %.2f%%\n", avg_sp*100)
    @printf("    fruit_ferment vs danger:     r = %.4f\n", fvd)
    @printf("    fruit_ferment vs fruit_ripe: r = %.4f\n", fvf)
    @printf("    Real-time factor:            %.2fx %s\n",
            rt_avg < 1 ? 1/rt_avg : rt_avg, rt_avg < 1 ? "(FASTER)" : "(slower)")

    results = Dict(
        "language"           => "julia_metal_gpu",
        "device"             => string(Metal.device()),
        "n_pn" => N_PN, "n_kc" => N_KC, "kc_fan_in" => KC_FAN_IN, "sim_ms" => SIM_MS,
        "total_wall_time_s"  => round(total_elapsed; digits=4),
        "per_odor_s"         => round(per_odor; digits=4),
        "realtime_ratio"     => round(rt_avg; digits=4),
        "avg_kc_sparsity_pct"=> round(avg_sp*100; digits=4),
        "fruit_vs_danger_r"  => round(fvd; digits=4),
        "fruit_vs_fruit_r"   => round(fvf; digits=4),
        "kc_mean_amp" => Dict(k => round(mean(v); digits=6) for (k,v) in kc_patterns),
        "correlations"       => corr_dict,
    )

    out = "/Users/vladyslav/Documents/GitHub/experiment/benchmarks/smell_test/results_julia_gpu.json"
    open(out, "w") do f; JSON3.write(f, results); end
    println("\n  Results saved: $out")
end

main()
