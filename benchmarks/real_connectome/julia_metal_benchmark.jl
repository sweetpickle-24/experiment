#!/usr/bin/env julia
# Julia Metal GPU benchmark — real olfactory connectome
# CSR-format coupling (no atomics): 1 thread per neuron, loops over incoming synapses
# 10,906 neurons | 446,388 synapses | 1000 steps (100ms bio)

using Metal, JSON3, Printf, Statistics

BASE = @__DIR__

meta = JSON3.read(read(joinpath(BASE, "network_meta.json"), String))
N      = Int32(meta["n_neurons"])
S      = Int32(meta["n_synapses"])
N_KC   = meta["n_kc"]
DT     = Float32(meta["dt"])
GAMMA  = Float32(meta["gamma"])
OMEGA0 = Float32(meta["omega0"])
SIGMA  = Float32(meta["sigma_noise"])
VARC   = Float32(meta["var_correction"])
NSTEPS = meta["n_steps"]

@printf("Julia Metal GPU — real fly olfactory connectome (CSR coupling)\n")
@printf("  %d neurons | %d synapses | %d steps\n", N, S, NSTEPS)

# ── load binary data ──────────────────────────────────────────────────────────
load_i32(f) = copy(reinterpret(Int32,  read(joinpath(BASE, f))))
load_f32(f) = copy(reinterpret(Float32, read(joinpath(BASE, f))))

kc_cpu    = load_i32("kc_indices.bin") .+ Int32(1)   # 1-based
phase0    = load_f32("init_phase.bin")
amp0      = load_f32("init_amp.bin")
ext_cpu   = load_f32("ext_force.bin")

# CSR arrays (already sorted by post neuron)
csr_pre_cpu  = load_i32("csr_pre.bin")  .+ Int32(1)   # 1-based
csr_wgt_cpu  = load_f32("csr_wgt.bin")
row_ptr_cpu  = load_i32("csr_row_ptr.bin")   # length N+1

@printf("  CSR row_ptr loaded: %d entries, max nnz/row = %d\n",
        length(row_ptr_cpu), maximum(diff(row_ptr_cpu)))

# Move to GPU
csr_pre_g  = MtlArray(csr_pre_cpu)
csr_wgt_g  = MtlArray(csr_wgt_cpu)
row_ptr_g  = MtlArray(row_ptr_cpu)
ext_g      = MtlArray(ext_cpu)

# ── Metal kernels ─────────────────────────────────────────────────────────────
# Kernel: 1 thread per neuron.
# Phase 1 (coupling): loops over CSR row to accumulate incoming synapse forces.
# Phase 2 (update): integrate wave physics.
# Combined to avoid a second kernel launch per step.

function wave_step_kernel!(
        phase   :: MtlDeviceArray{Float32,1},
        vel     :: MtlDeviceArray{Float32,1},
        amp     :: MtlDeviceArray{Float32,1},
        varp    :: MtlDeviceArray{Float32,1},
        csr_pre :: MtlDeviceArray{Int32,1},
        csr_wgt :: MtlDeviceArray{Float32,1},
        row_ptr :: MtlDeviceArray{Int32,1},
        ext     :: MtlDeviceArray{Float32,1},
        omega0  :: Float32,
        gamma   :: Float32,
        sigma   :: Float32,
        dt      :: Float32,
        varc    :: Float32)

    id = thread_position_in_grid_1d()
    id > length(phase) && return nothing

    # Accumulate coupling from incoming synapses (CSR row)
    row_start = row_ptr[id] + Int32(1)     # +1 because row_ptr is 0-based offsets stored as Int32
    row_end   = row_ptr[id + Int32(1)]     # exclusive (0-based length)

    cf = 0.0f0
    ph_j = phase[id]
    @inbounds for k in row_start:row_end
        pi = csr_pre[k]
        dp = phase[pi] - ph_j
        cf += csr_wgt[k] * sin(dp) * amp[pi] * varc
    end

    # Wave physics
    v   = vel[id]
    a   = amp[id]
    vp  = varp[id]

    accel = -2.0f0 * gamma * v - omega0 * omega0 * ph_j + cf + ext[id]
    v2    = v + accel * dt
    ph2   = ph_j + v2 * dt
    ph2   = atan(sin(ph2), cos(ph2))

    vp2   = vp * (1.0f0 - 2.0f0 * gamma * dt) + sigma * sigma * dt
    vp2   = clamp(vp2, 0.01f0, 10.0f0)

    ad    = abs(v2) * 0.1f0
    a2    = a * (1.0f0 - gamma * dt) + ad * dt
    a2    = clamp(a2, 0.001f0, 10.0f0)

    phase[id] = ph2
    vel[id]   = v2
    amp[id]   = a2
    varp[id]  = vp2

    return nothing
end

# thread config: 1 thread per neuron
TPIG = min(1024, nextpow(2, cld(Int(N), 256)))
NGRP = cld(Int(N), TPIG)

# ── state factory ─────────────────────────────────────────────────────────────
make_state() = (
    MtlArray(copy(phase0)),
    MtlArray(zeros(Float32, N)),
    MtlArray(copy(amp0)),
    MtlArray(fill(Float32(0.1), N)),
)

# ── warm-up (10 steps, forces JIT compilation) ────────────────────────────────
print("Warming up GPU …\n")
(phase, vel, amp, varp) = make_state()
for _ in 1:10
    @metal threads=TPIG groups=NGRP wave_step_kernel!(
        phase, vel, amp, varp,
        csr_pre_g, csr_wgt_g, row_ptr_g, ext_g,
        OMEGA0, GAMMA, SIGMA, DT, VARC)
end
Metal.synchronize()
println("  GPU warm-up done")

# ── timed run ─────────────────────────────────────────────────────────────────
(phase, vel, amp, varp) = make_state()
t_start = time_ns()

for s in 1:NSTEPS
    @metal threads=TPIG groups=NGRP wave_step_kernel!(
        phase, vel, amp, varp,
        csr_pre_g, csr_wgt_g, row_ptr_g, ext_g,
        OMEGA0, GAMMA, SIGMA, DT, VARC)
    if s % 100 == 0
        Metal.synchronize()
    end
end
Metal.synchronize()
wall = (time_ns() - t_start) / 1e9

# ── KC sparsity ───────────────────────────────────────────────────────────────
amp_cpu  = Array(amp)
active   = count(i -> amp_cpu[i] > 0.01f0, kc_cpu)
sparsity = active / N_KC * 100.0

bio_ms      = NSTEPS * DT
rt_factor   = bio_ms / 1000.0 / wall
ms_per_step = wall / NSTEPS * 1000.0

@printf("\n%s\n", "="^55)
@printf("  Wall time       : %.3f s\n",   wall)
@printf("  Bio time        : %.0f ms\n",  bio_ms)
@printf("  Real-time factor: %.3f×  (%s)\n", rt_factor, rt_factor>1 ? "faster than RT" : "slower than RT")
@printf("  ms per step     : %.3f ms\n",  ms_per_step)
@printf("  KC sparsity     : %.2f%%  (%d/%d)\n", sparsity, active, N_KC)
@printf("%s\n", "="^55)

results = Dict(
    "backend"         => "julia_metal_gpu",
    "n_neurons"       => Int(N),
    "n_synapses"      => Int(S),
    "n_steps"         => NSTEPS,
    "wall_time_s"     => wall,
    "bio_time_ms"     => Float64(bio_ms),
    "rt_factor"       => rt_factor,
    "ms_per_step"     => ms_per_step,
    "kc_sparsity_pct" => sparsity,
    "active_kc"       => active,
    "total_kc"        => N_KC,
)
open(joinpath(BASE, "results_julia_metal.json"), "w") do f
    JSON3.write(f, results)
end
println("  Results → results_julia_metal.json")
