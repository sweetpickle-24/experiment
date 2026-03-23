"""
Smell Test — Julia Implementation

Exact same sparse wave oscillator as the Python reference.
Pure Julia (no packages). Uses @threads for parallel scatter accumulation.

Run:  julia smell_test.jl
"""

using LinearAlgebra, Statistics, JSON3, Printf, Random
using Base.Threads: @threads

# ─── Network constants ────────────────────────────────────────────────────────
const N_PN       = 2198
const N_KC       = 5279
const N_CHANNELS = 20
const KC_FAN_IN  = 7
const SIM_MS     = 300.0f0
const DT         = 0.1f0
const SEED       = 42

# ─── Physics constants ────────────────────────────────────────────────────────
const GAMMA       = 0.1f0
const SIGMA_NOISE = 0.1f0
const OMEGA0      = Float32(2π * 10.0 / 1000.0)
const EXT_STR     = 50.0f0
const VAR_CORR    = exp(-0.1f0 / 2.0f0)

# ─── Channel frequencies ──────────────────────────────────────────────────────
const CHANNEL_FREQ = Float32[
    20, 18, 22,  8, 12, 16,
    14,  6, 10,  5,  9, 12,
     7,  6,  5,  5, 11, 13,
     7,  4
]
const CHANNEL_OMEGA = Float32.(2π .* CHANNEL_FREQ ./ 1000.0)

# ─── Odor patterns ───────────────────────────────────────────────────────────
function _norm(v::Vector{Float64})
    n = norm(v)
    return Float32.(v ./ n)
end

const ODORS = Dict{String,Vector{Float32}}(
    "fruit_ferment"  => _norm([0.85,0.20,0.70,0.10,0.15,0.05,
                                0.65,0.25,0.40,0.00,0.00,0.00,
                                0.00,0.05,0.00,0.00,0.15,0.10,
                                0.00,0.05]),
    "fruit_ripe"     => _norm([0.90,0.45,0.35,0.15,0.20,0.30,
                                0.25,0.05,0.20,0.00,0.00,0.10,
                                0.00,0.00,0.00,0.00,0.10,0.20,
                                0.00,0.05]),
    "danger_mold"    => _norm([0.00,0.00,0.05,0.00,0.00,0.00,
                                0.00,0.20,0.60,0.70,0.00,0.05,
                                0.90,0.85,0.00,0.00,0.05,0.00,
                                0.75,0.00]),
    "social_female"  => _norm([0.00,0.05,0.00,0.30,0.10,0.00,
                                0.00,0.00,0.00,0.20,0.10,0.10,
                                0.00,0.00,0.90,0.05,0.05,0.00,
                                0.00,0.05]),
    "clean_air"      => _norm([0.02,0.02,0.02,0.02,0.02,0.02,
                                0.02,0.05,0.02,0.00,0.00,0.02,
                                0.00,0.00,0.00,0.00,0.05,0.05,
                                0.00,0.90]),
)

# ─── Build network ────────────────────────────────────────────────────────────
function build_network(seed::Int=SEED)
    rng = MersenneTwister(seed)
    pre  = Int32[]
    post = Int32[]
    pn_pool = collect(Int32, 0:N_PN-1)
    for kc in 0:N_KC-1
        pns = sample_without_replacement(rng, pn_pool, KC_FAN_IN)
        for pn in pns
            push!(pre,  pn)
            push!(post, kc)
        end
    end
    return pre, post
end

function sample_without_replacement(rng, pool, k)
    n = length(pool)
    idx = randperm(rng, n)[1:k]
    return pool[idx]
end

# ─── Single simulation step ───────────────────────────────────────────────────
function step!(phase::Vector{Float32}, vel::Vector{Float32},
               amp::Vector{Float32}, var_ph::Vector{Float32},
               pre::Vector{Int32}, post::Vector{Int32},
               weights::Vector{Float32}, ext_force::Vector{Float32},
               N::Int)

    # Coupling (PN → KC): serial scatter accumulate
    coupling = zeros(Float32, N)
    @inbounds for s in eachindex(pre)
        pi = pre[s]  + 1   # 1-indexed PN
        ki = post[s] + N_PN + 1  # 1-indexed KC in full array
        dp = phase[pi] - phase[ki]
        coupling[ki] += weights[s] * sin(dp) * amp[pi] * VAR_CORR
    end

    # Oscillator update (all neurons)
    @inbounds for i in 1:N
        a = -2f0 * GAMMA * vel[i] - OMEGA0^2 * phase[i] + coupling[i] + ext_force[i]
        vel[i]   += a * DT
        phase[i] += vel[i] * DT
        phase[i]  = atan(sin(phase[i]), cos(phase[i]))
        var_ph[i] = clamp(var_ph[i] * (1f0 - 2f0*GAMMA*DT) + SIGMA_NOISE^2*DT, 0.01f0, 10.0f0)
        amp_drive = abs(vel[i]) * 0.1f0
        amp[i] = clamp(amp[i] * (1f0 - GAMMA*DT) + amp_drive*DT, 0.001f0, 10.0f0)
    end
end

# ─── Run simulation ───────────────────────────────────────────────────────────
function run_simulation(odor_pattern::Vector{Float32},
                        pre::Vector{Int32}, post::Vector{Int32};
                        seed::Int=SEED)
    N = N_PN + N_KC
    rng = MersenneTwister(seed)

    phase  = Float32.(rand(rng, N) .* 2π .- π)
    vel    = zeros(Float32, N)
    amp    = fill(0.1f0, N)
    var_ph = fill(0.1f0, N)

    pns_per_ch = div(N_PN, N_CHANNELS)
    weights = fill(1.0f0 / KC_FAN_IN, length(pre))

    num_steps = Int(SIM_MS / DT)
    ext_base = zeros(Float32, N)
    for ch in 1:N_CHANNELS
        s = (ch-1) * pns_per_ch + 1
        e = s + pns_per_ch - 1
        for i in s:e
            ext_base[i] = odor_pattern[ch] * EXT_STR
        end
    end

    ext_force = zeros(Float32, N)

    for step in 0:num_steps-1
        t = step * DT
        # Build sinusoidal forcing for this timestep
        @inbounds for ch in 1:N_CHANNELS
            s = (ch-1)*pns_per_ch + 1
            e = s + pns_per_ch - 1
            f = ext_base[s] * sin(CHANNEL_OMEGA[ch] * t)
            for i in s:e
                ext_force[i] = f
            end
        end

        step!(phase, vel, amp, var_ph, pre, post, weights, ext_force, N)
    end

    return amp[N_PN+1:end]   # KC amplitudes
end

# ─── Metrics ─────────────────────────────────────────────────────────────────
function compute_sparsity(kc_amp::Vector{Float32})
    thr = mean(kc_amp) + std(kc_amp)
    return count(x -> x > thr, kc_amp) / length(kc_amp)
end

function pearson_r(a::Vector{Float32}, b::Vector{Float32})
    am = a .- mean(a); bm = b .- mean(b)
    d = sqrt(sum(am.^2) * sum(bm.^2))
    return d > 1e-10 ? dot(am, bm) / d : 0.0
end

# ─── Main ─────────────────────────────────────────────────────────────────────
function main()
    println("=" ^ 60)
    println("  SMELL TEST — Julia")
    println("  Network: $N_PN PNs + $N_KC KCs, $KC_FAN_IN PN/KC")
    println("  Simulation: $(Int(SIM_MS))ms at dt=$(DT)ms ($(Int(SIM_MS/DT)) steps)")
    println("  Threads: $(Threads.nthreads())")
    println("=" ^ 60)

    pre, post = build_network()
    println("  Synapses: $(length(pre))")

    odor_names = collect(keys(ODORS))
    kc_patterns = Dict{String,Vector{Float32}}()

    println("\n  Running simulations...")
    total_t0 = time()

    for name in odor_names
        pattern = ODORS[name]
        t0 = time()
        kc_amp = run_simulation(pattern, pre, post)
        elapsed = time() - t0
        sp = compute_sparsity(kc_amp)
        kc_patterns[name] = kc_amp
        @printf("    %-20s  sparsity=%.2f%%  time=%.3fs\n", name, sp*100, elapsed)
    end

    total_elapsed = time() - total_t0
    @printf("\n  Total wall time: %.3fs\n", total_elapsed)
    @printf("  Per-odor:        %.3fs\n", total_elapsed / length(ODORS))

    println("\n  Inter-odor KC correlations:")
    corr_dict = Dict{String,Float64}()
    for (i, n1) in enumerate(odor_names)
        for (j, n2) in enumerate(odor_names)
            if j > i
                r = pearson_r(kc_patterns[n1], kc_patterns[n2])
                key = "$n1 vs $n2"
                corr_dict[key] = round(r; digits=4)
                @printf("    %-20s vs %-20s: r = %.4f\n", n1, n2, r)
            end
        end
    end

    avg_sp = mean(compute_sparsity(v) for v in values(kc_patterns))
    fruit_vs_danger = pearson_r(kc_patterns["fruit_ferment"], kc_patterns["danger_mold"])
    fruit_vs_fruit  = pearson_r(kc_patterns["fruit_ferment"], kc_patterns["fruit_ripe"])

    println("\n  KEY METRICS:")
    @printf("    Average KC sparsity:         %.2f%%  (target: 1-3%%)\n", avg_sp*100)
    @printf("    fruit_ferment vs danger:     r = %.4f  (should be low)\n", fruit_vs_danger)
    @printf("    fruit_ferment vs fruit_ripe: r = %.4f  (should be higher)\n", fruit_vs_fruit)

    results = Dict(
        "language"            => "julia",
        "n_pn"                => N_PN,
        "n_kc"                => N_KC,
        "kc_fan_in"           => KC_FAN_IN,
        "sim_ms"              => SIM_MS,
        "total_wall_time_s"   => round(total_elapsed; digits=4),
        "per_odor_s"          => round(total_elapsed/length(ODORS); digits=4),
        "avg_kc_sparsity_pct" => round(avg_sp*100; digits=4),
        "fruit_vs_danger_r"   => round(fruit_vs_danger; digits=4),
        "fruit_vs_fruit_r"    => round(fruit_vs_fruit; digits=4),
        "kc_mean_amp"         => Dict(k => round(mean(v); digits=6) for (k,v) in kc_patterns),
        "correlations"        => corr_dict,
    )

    out = "/Users/vladyslav/Documents/GitHub/experiment/benchmarks/smell_test/results_julia.json"
    open(out, "w") do f
        JSON3.write(f, results)
    end
    println("\n  Results saved: $out")
end

main()
