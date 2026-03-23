//! Smell Test — Rust Metal GPU Implementation
//!
//! Same physics as Rust CPU version, but 2 MSL compute shaders run every step:
//!
//!   Shader 1: compute_coupling   — N_KC threads, each gathers 7 PN inputs
//!   Shader 2: oscillator_update  — N threads, runs wave physics + ext_force
//!
//! Strategy: encode ALL 3000 steps into ONE command buffer (no CPU-GPU sync
//! per step). The `t` parameter changes each step — passed as a 4-byte
//! constant via setBytes inside each compute pass. Metal guarantees ordering
//! of sequential compute passes within the same command buffer.
//!
//! Compile: SDKROOT=... cargo build --release (see ../.cargo/config.toml)

use std::time::Instant;
use std::f32::consts::PI;
use std::collections::HashMap;
use metal::*;
use serde_json::json;

// ─── Constants ───────────────────────────────────────────────────────────────
const N_PN: usize  = 2198;
const N_KC: usize  = 5279;
const N: usize     = N_PN + N_KC;
const N_CHANNELS: usize = 20;
const KC_FAN_IN: usize  = 7;
const SIM_MS: f32  = 300.0;
const DT: f32      = 0.1;
const SEED: u64    = 42;
const EXT_STR: f32 = 50.0;

const CHANNEL_FREQ: [f32; N_CHANNELS] = [
    20.0, 18.0, 22.0,  8.0, 12.0, 16.0,
    14.0,  6.0, 10.0,  5.0,  9.0, 12.0,
     7.0,  6.0,  5.0,  5.0, 11.0, 13.0,
     7.0,  4.0,
];

// ─── MSL Shader Source ───────────────────────────────────────────────────────
const MSL_SOURCE: &str = r#"
#include <metal_stdlib>
using namespace metal;

constant uint   N_PN_C      = 2198;
constant uint   N_KC_C      = 5279;
constant uint   KC_FAN_IN_C = 7;
constant float  GAMMA_C     = 0.1f;
constant float  OMEGA0_C    = 0.06283185f;   // 2*pi*10/1000
constant float  DT_C        = 0.1f;
constant float  SIGMA_C     = 0.1f;
constant float  VAR_CORR_C  = 0.95122942f;  // exp(-0.05)

// ── Kernel 1: compute_coupling ───────────────────────────────────────────────
// Each KC thread gathers its KC_FAN_IN PN inputs and writes coupling[kc+N_PN].
// Synapses are in KC order: KC 0 owns indices 0..6, KC 1 owns 7..13, etc.
// No atomic scatter needed.
kernel void compute_coupling(
    device const float* phase    [[ buffer(0) ]],
    device const float* amp      [[ buffer(1) ]],
    device const uint*  pre      [[ buffer(2) ]],   // (N_KC*KC_FAN_IN,) PN indices 0-based
    device const float* weights  [[ buffer(3) ]],
    device float*       coupling [[ buffer(4) ]],   // (N,) output
    uint kc [[ thread_position_in_grid ]])
{
    if (kc >= N_KC_C) return;
    uint ki   = kc + N_PN_C;
    uint base = kc * KC_FAN_IN_C;
    float sum = 0.0f;
    for (uint i = 0; i < KC_FAN_IN_C; i++) {
        uint pi   = pre[base + i];
        float dp  = phase[pi] - phase[ki];
        sum += weights[base + i] * sin(dp) * amp[pi] * VAR_CORR_C;
    }
    coupling[ki] = sum;
}

// ── Kernel 2: oscillator_update ──────────────────────────────────────────────
// Each thread handles one neuron (0-based id in 0..N).
// Computes ext_force for PNs from per-PN precomputed strength/omega.
kernel void oscillator_update(
    device float*       phase       [[ buffer(0) ]],
    device float*       vel         [[ buffer(1) ]],
    device float*       amp         [[ buffer(2) ]],
    device float*       var_ph      [[ buffer(3) ]],
    device const float* coupling    [[ buffer(4) ]],
    device const float* pn_strength [[ buffer(5) ]],   // (N_PN,)
    device const float* pn_omega    [[ buffer(6) ]],   // (N_PN,)
    constant float&     t           [[ buffer(7) ]],
    uint id [[ thread_position_in_grid ]])
{
    if (id >= N_PN_C + N_KC_C) return;

    float ef = (id < N_PN_C)
        ? pn_strength[id] * sin(pn_omega[id] * t)
        : 0.0f;

    float a = -2.0f * GAMMA_C * vel[id]
              - OMEGA0_C * OMEGA0_C * phase[id]
              + coupling[id] + ef;

    vel[id]   += a * DT_C;
    phase[id] += vel[id] * DT_C;
    phase[id]  = atan2(sin(phase[id]), cos(phase[id]));

    float vp = var_ph[id] * (1.0f - 2.0f * GAMMA_C * DT_C)
               + SIGMA_C * SIGMA_C * DT_C;
    var_ph[id] = clamp(vp, 0.01f, 10.0f);

    float ad = fabs(vel[id]) * 0.1f;
    amp[id] = clamp(amp[id] * (1.0f - GAMMA_C * DT_C) + ad * DT_C, 0.001f, 10.0f);
}
"#;

// ─── Simple deterministic PRNG ────────────────────────────────────────────────
struct Rng(u64);
impl Rng {
    fn new(seed: u64) -> Self { Rng(seed ^ 0x1234567890ABCDEF) }
    fn next_u64(&mut self) -> u64 {
        self.0 ^= self.0 << 13; self.0 ^= self.0 >> 7; self.0 ^= self.0 << 17; self.0
    }
    fn next_f32(&mut self) -> f32 { (self.next_u64() >> 11) as f32 / (1u64 << 53) as f32 }
    fn next_phase(&mut self) -> f32 { self.next_f32() * 2.0 * PI - PI }
    fn sample_k(&mut self, n: usize, k: usize) -> Vec<usize> {
        let mut pool: Vec<usize> = (0..n).collect();
        for i in 0..k { let j = i + (self.next_u64() as usize) % (n - i); pool.swap(i, j); }
        pool[..k].to_vec()
    }
}

// ─── Odor library ─────────────────────────────────────────────────────────────
fn norm_pattern(v: &[f32]) -> Vec<f32> {
    let n: f32 = v.iter().map(|x| x*x).sum::<f32>().sqrt();
    v.iter().map(|x| x/n).collect()
}
fn odor_library() -> Vec<(&'static str, Vec<f32>)> { vec![
    ("fruit_ferment",  norm_pattern(&[0.85,0.20,0.70,0.10,0.15,0.05,0.65,0.25,0.40,0.00,0.00,0.00,0.00,0.05,0.00,0.00,0.15,0.10,0.00,0.05])),
    ("fruit_ripe",     norm_pattern(&[0.90,0.45,0.35,0.15,0.20,0.30,0.25,0.05,0.20,0.00,0.00,0.10,0.00,0.00,0.00,0.00,0.10,0.20,0.00,0.05])),
    ("danger_mold",    norm_pattern(&[0.00,0.00,0.05,0.00,0.00,0.00,0.00,0.20,0.60,0.70,0.00,0.05,0.90,0.85,0.00,0.00,0.05,0.00,0.75,0.00])),
    ("social_female",  norm_pattern(&[0.00,0.05,0.00,0.30,0.10,0.00,0.00,0.00,0.00,0.20,0.10,0.10,0.00,0.00,0.90,0.05,0.05,0.00,0.00,0.05])),
    ("clean_air",      norm_pattern(&[0.02,0.02,0.02,0.02,0.02,0.02,0.02,0.05,0.02,0.00,0.00,0.02,0.00,0.00,0.00,0.00,0.05,0.05,0.00,0.90])),
]}

// ─── Build network ─────────────────────────────────────────────────────────────
fn build_network(seed: u64) -> (Vec<u32>, Vec<u32>) {
    let mut rng = Rng::new(seed);
    let mut pre = Vec::with_capacity(N_KC * KC_FAN_IN);
    let mut post = Vec::with_capacity(N_KC * KC_FAN_IN);
    for kc in 0..N_KC {
        for pn in rng.sample_k(N_PN, KC_FAN_IN) {
            pre.push(pn as u32);
            post.push(kc as u32);
        }
    }
    (pre, post)
}

// ─── GPU buffer helpers ───────────────────────────────────────────────────────
fn new_buffer_f32(device: &Device, data: &[f32]) -> Buffer {
    device.new_buffer_with_data(
        data.as_ptr() as *const _,
        (data.len() * 4) as u64,
        MTLResourceOptions::StorageModeShared,
    )
}

fn new_buffer_u32(device: &Device, data: &[u32]) -> Buffer {
    device.new_buffer_with_data(
        data.as_ptr() as *const _,
        (data.len() * 4) as u64,
        MTLResourceOptions::StorageModeShared,
    )
}

// ─── Encode one compute pass ───────────────────────────────────────────────────
fn encode_pass(
    cmd_buf: &CommandBufferRef,
    pipeline: &ComputePipelineState,
    bufs: &[(&Buffer, u64)],        // (buffer, offset) pairs
    bytes: Option<(&[u8], u64)>,    // optional raw bytes constant at last binding
    threads: u64,
) {
    let encoder = cmd_buf.new_compute_command_encoder();
    encoder.set_compute_pipeline_state(pipeline);
    for (i, (buf, offset)) in bufs.iter().enumerate() {
        encoder.set_buffer(i as u64, Some(*buf), *offset);
    }
    if let Some((bytes_data, binding)) = bytes {
        encoder.set_bytes(binding, bytes_data.len() as u64, bytes_data.as_ptr() as *const _);
    }
    let tg_size  = MTLSize { width: 256, height: 1, depth: 1 };
    let grid_size = MTLSize { width: threads, height: 1, depth: 1 };
    encoder.dispatch_threads(grid_size, tg_size);
    encoder.end_encoding();
}

// ─── Run simulation ────────────────────────────────────────────────────────────
fn run_simulation(
    device: &Device,
    queue: &CommandQueue,
    coupling_pipeline: &ComputePipelineState,
    oscillator_pipeline: &ComputePipelineState,
    odor: &[f32],
    pre_g: &Buffer,
    weights_g: &Buffer,
    seed: u64,
) -> Vec<f32> {
    let mut rng = Rng::new(seed);

    // State buffers (Shared — CPU visible for init + final readback)
    let mut phase_data  = (0..N).map(|_| rng.next_phase()).collect::<Vec<f32>>();
    let mut vel_data    = vec![0f32; N];
    let amp_data        = vec![0.1f32; N];
    let var_ph_data     = vec![0.1f32; N];
    let coupling_data   = vec![0f32; N];   // PNs stay 0; KCs overwritten each step

    let phase_buf  = new_buffer_f32(device, &phase_data);
    let vel_buf    = new_buffer_f32(device, &vel_data);
    let amp_buf    = new_buffer_f32(device, &amp_data);
    let var_ph_buf = new_buffer_f32(device, &var_ph_data);
    let coupling_buf = new_buffer_f32(device, &coupling_data);

    // Per-PN forcing (precomputed on CPU, uploaded once)
    let pns_per_ch = N_PN / N_CHANNELS;
    let omega = CHANNEL_FREQ.map(|f| 2.0 * PI * f / 1000.0);
    let mut pn_strength = vec![0f32; N_PN];
    let mut pn_omega    = vec![0f32; N_PN];
    for ch in 0..N_CHANNELS {
        let s = ch * pns_per_ch;
        let e = s + pns_per_ch;
        for i in s..e {
            pn_strength[i] = odor[ch] * EXT_STR;
            pn_omega[i]    = omega[ch];
        }
    }
    let pn_strength_buf = new_buffer_f32(device, &pn_strength);
    let pn_omega_buf    = new_buffer_f32(device, &pn_omega);

    let num_steps = (SIM_MS / DT) as usize;

    // Encode ALL steps into one command buffer — no CPU-GPU sync per step.
    // Metal guarantees sequential execution of compute passes within a buffer.
    let cmd_buf = queue.new_command_buffer();

    for step in 0..num_steps {
        let t: f32 = step as f32 * DT;
        let t_bytes: [u8; 4] = t.to_ne_bytes();

        // Pass 1: compute_coupling (N_KC threads)
        encode_pass(
            cmd_buf,
            coupling_pipeline,
            &[
                (&phase_buf,   0),
                (&amp_buf,     0),
                (pre_g,        0),
                (weights_g,    0),
                (&coupling_buf, 0),
            ],
            None,
            N_KC as u64,
        );

        // Pass 2: oscillator_update (N threads)
        encode_pass(
            cmd_buf,
            oscillator_pipeline,
            &[
                (&phase_buf,       0),
                (&vel_buf,         0),
                (&amp_buf,         0),
                (&var_ph_buf,      0),
                (&coupling_buf,    0),
                (&pn_strength_buf, 0),
                (&pn_omega_buf,    0),
            ],
            Some((&t_bytes, 7)),   // t as constant at binding 7
            N as u64,
        );
    }

    // Submit and wait (single GPU round-trip for all 3000 steps)
    cmd_buf.commit();
    cmd_buf.wait_until_completed();

    // Readback KC amplitudes from Shared buffer
    let amp_ptr = amp_buf.contents() as *const f32;
    let amp_slice = unsafe { std::slice::from_raw_parts(amp_ptr, N) };
    amp_slice[N_PN..].to_vec()
}

// ─── Metrics ──────────────────────────────────────────────────────────────────
fn sparsity(kc: &[f32]) -> f32 {
    let mean: f32 = kc.iter().sum::<f32>() / kc.len() as f32;
    let std:  f32 = (kc.iter().map(|x| (x-mean).powi(2)).sum::<f32>() / kc.len() as f32).sqrt();
    kc.iter().filter(|&&x| x > mean + std).count() as f32 / kc.len() as f32
}
fn pearson(a: &[f32], b: &[f32]) -> f32 {
    let ma: f32 = a.iter().sum::<f32>() / a.len() as f32;
    let mb: f32 = b.iter().sum::<f32>() / b.len() as f32;
    let am: Vec<f32> = a.iter().map(|x| x-ma).collect();
    let bm: Vec<f32> = b.iter().map(|x| x-mb).collect();
    let dot: f32 = am.iter().zip(&bm).map(|(x,y)| x*y).sum();
    let da: f32  = am.iter().map(|x| x*x).sum::<f32>().sqrt();
    let db: f32  = bm.iter().map(|x| x*x).sum::<f32>().sqrt();
    if da*db > 1e-10 { dot/(da*db) } else { 0.0 }
}

// ─── Main ─────────────────────────────────────────────────────────────────────
fn main() {
    println!("{}", "=".repeat(60));
    println!("  SMELL TEST — Rust Metal GPU");

    let device = Device::system_default().expect("No Metal device");
    println!("  Device: {}", device.name());
    println!("  Network: {} PNs + {} KCs, {} PN/KC", N_PN, N_KC, KC_FAN_IN);
    println!("  Simulation: {}ms at dt={}ms ({} steps)", SIM_MS as u32, DT, (SIM_MS/DT) as u32);
    println!("{}", "=".repeat(60));

    // Compile MSL shaders at startup
    let compile_opts = metal::CompileOptions::new();
    let library = device.new_library_with_source(MSL_SOURCE, &compile_opts)
        .expect("MSL compile failed");

    let coupling_fn  = library.get_function("compute_coupling",   None).unwrap();
    let osc_fn       = library.get_function("oscillator_update",  None).unwrap();

    let coupling_pipeline  = device.new_compute_pipeline_state_with_function(&coupling_fn).unwrap();
    let oscillator_pipeline = device.new_compute_pipeline_state_with_function(&osc_fn).unwrap();
    let queue = device.new_command_queue();

    // Build network on CPU, upload synapse arrays to GPU
    let (pre_cpu, _post_cpu) = build_network(SEED);
    println!("  Synapses: {}", pre_cpu.len());

    let weights_cpu = vec![1.0f32 / KC_FAN_IN as f32; pre_cpu.len()];
    let pre_g     = new_buffer_u32(&device, &pre_cpu);
    let weights_g = new_buffer_f32(&device, &weights_cpu);

    let odors = odor_library();

    // Warmup: avoid counting first-run Metal pipeline JIT in timings
    println!("\n  Warming up GPU pipelines...");
    let _ = run_simulation(&device, &queue, &coupling_pipeline, &oscillator_pipeline,
                           &odors[0].1, &pre_g, &weights_g, SEED);
    println!("  Warmup complete.");

    let mut kc_patterns: HashMap<&str, Vec<f32>> = HashMap::new();
    println!("\n  Running simulations (GPU)...");
    let total_t0 = Instant::now();

    for (name, odor) in &odors {
        let t0 = Instant::now();
        let kc_amp = run_simulation(&device, &queue, &coupling_pipeline, &oscillator_pipeline,
                                    odor, &pre_g, &weights_g, SEED);
        let elapsed = t0.elapsed().as_secs_f64();
        let sp = sparsity(&kc_amp);
        let rt = elapsed / (SIM_MS as f64 / 1000.0);
        if rt < 1.0 {
            println!("    {:<20}  sparsity={:.2}%  time={:.3}s  ({:.1}x faster than realtime)",
                     name, sp*100.0, elapsed, 1.0/rt);
        } else {
            println!("    {:<20}  sparsity={:.2}%  time={:.3}s  ({:.1}x slower than realtime)",
                     name, sp*100.0, elapsed, rt);
        }
        kc_patterns.insert(name, kc_amp);
    }

    let total_elapsed = total_t0.elapsed().as_secs_f64();
    let per_odor = total_elapsed / odors.len() as f64;
    let rt_avg = per_odor / (SIM_MS as f64 / 1000.0);

    println!("\n  Total wall time: {:.3}s", total_elapsed);
    println!("  Per-odor:        {:.3}s", per_odor);
    if rt_avg < 1.0 {
        println!("  Real-time:       {:.1}x FASTER than real life", 1.0/rt_avg);
    } else {
        println!("  Real-time:       {:.1}x SLOWER than real life", rt_avg);
    }

    println!("\n  Inter-odor KC correlations:");
    let mut corr_map = serde_json::Map::new();
    for (i, (n1,_)) in odors.iter().enumerate() {
        for (j, (n2,_)) in odors.iter().enumerate() {
            if j > i {
                let r = pearson(&kc_patterns[n1], &kc_patterns[n2]);
                println!("    {:<20} vs {:<20}: r = {:.4}", n1, n2, r);
                corr_map.insert(format!("{} vs {}", n1, n2), json!(format!("{:.4}", r)));
            }
        }
    }

    let avg_sp: f32 = kc_patterns.values().map(|v| sparsity(v)).sum::<f32>() / kc_patterns.len() as f32;
    let fvd = pearson(&kc_patterns["fruit_ferment"], &kc_patterns["danger_mold"]);
    let fvf = pearson(&kc_patterns["fruit_ferment"], &kc_patterns["fruit_ripe"]);

    println!("\n  KEY METRICS:");
    println!("    Average KC sparsity:         {:.2}%", avg_sp*100.0);
    println!("    fruit_ferment vs danger:     r = {:.4}", fvd);
    println!("    fruit_ferment vs fruit_ripe: r = {:.4}", fvf);

    let mean_amps: serde_json::Map<String,serde_json::Value> = kc_patterns.iter()
        .map(|(k,v)| { let m = v.iter().sum::<f32>()/v.len() as f32; (k.to_string(), json!(format!("{:.6}",m))) })
        .collect();

    let results = json!({
        "language": "rust_metal_gpu",
        "device": device.name().to_string(),
        "n_pn": N_PN, "n_kc": N_KC, "kc_fan_in": KC_FAN_IN, "sim_ms": SIM_MS,
        "total_wall_time_s": format!("{:.4}", total_elapsed),
        "per_odor_s": format!("{:.4}", per_odor),
        "realtime_ratio": format!("{:.4}", rt_avg),
        "avg_kc_sparsity_pct": format!("{:.4}", avg_sp*100.0),
        "fruit_vs_danger_r": format!("{:.4}", fvd),
        "fruit_vs_fruit_r": format!("{:.4}", fvf),
        "kc_mean_amp": mean_amps,
        "correlations": corr_map,
    });

    let out = "/Users/vladyslav/Documents/GitHub/experiment/benchmarks/smell_test/results_rust_gpu.json";
    std::fs::write(out, serde_json::to_string_pretty(&results).unwrap()).unwrap();
    println!("\n  Results saved: {}", out);
}
