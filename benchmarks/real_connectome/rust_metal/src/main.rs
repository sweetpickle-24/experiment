/// Rust Metal GPU benchmark — real olfactory connectome
/// 10,906 neurons | 446,388 synapses | 1000 steps (100ms bio)

use metal::*;
use std::fs;
use std::time::Instant;
use std::path::PathBuf;

// ── Physics constants loaded from JSON ───────────────────────────────────────
struct Meta {
    n_neurons: usize,
    n_synapses: usize,
    n_kc: usize,
    dt: f32,
    gamma: f32,
    omega0: f32,
    sigma: f32,
    var_correction: f32,
    n_steps: usize,
}

fn load_meta(base: &PathBuf) -> Meta {
    let txt = fs::read_to_string(base.join("network_meta.json")).unwrap();
    let v: serde_json::Value = serde_json::from_str(&txt).unwrap();
    Meta {
        n_neurons:      v["n_neurons"].as_u64().unwrap() as usize,
        n_synapses:     v["n_synapses"].as_u64().unwrap() as usize,
        n_kc:           v["n_kc"].as_u64().unwrap() as usize,
        dt:             v["dt"].as_f64().unwrap() as f32,
        gamma:          v["gamma"].as_f64().unwrap() as f32,
        omega0:         v["omega0"].as_f64().unwrap() as f32,
        sigma:          v["sigma_noise"].as_f64().unwrap() as f32,
        var_correction: v["var_correction"].as_f64().unwrap() as f32,
        n_steps:        v["n_steps"].as_u64().unwrap() as usize,
    }
}

fn load_f32(base: &PathBuf, name: &str) -> Vec<f32> {
    let bytes = fs::read(base.join(name)).unwrap();
    let n = bytes.len() / 4;
    let mut v = vec![0f32; n];
    unsafe { std::ptr::copy_nonoverlapping(bytes.as_ptr(), v.as_mut_ptr() as *mut u8, bytes.len()); }
    v
}

fn load_i32(base: &PathBuf, name: &str) -> Vec<i32> {
    let bytes = fs::read(base.join(name)).unwrap();
    let n = bytes.len() / 4;
    let mut v = vec![0i32; n];
    unsafe { std::ptr::copy_nonoverlapping(bytes.as_ptr(), v.as_mut_ptr() as *mut u8, bytes.len()); }
    v
}

// ── MSL shader ───────────────────────────────────────────────────────────────
// Float atomics (atomic<float>) require Metal 3.0+ and are not available on
// this GPU compiler. We implement float atomic-add via int CAS loop instead.
// integer atomics (atomic_int) are universally supported.
const SHADER: &str = r#"
#include <metal_stdlib>
#include <metal_atomic>
using namespace metal;

// Float atomic add via int CAS — works on all Metal versions
inline void atomic_add_float(device atomic_int* addr, float val) {
    int old_int = atomic_load_explicit(addr, memory_order_relaxed);
    int new_int;
    do {
        new_int = as_type<int>(as_type<float>(old_int) + val);
    } while (!atomic_compare_exchange_weak_explicit(
                 addr, &old_int, new_int,
                 memory_order_relaxed, memory_order_relaxed));
}

// Kernel 1: one thread per synapse — CAS-atomic accumulate to post neuron
kernel void compute_coupling(
    device const float*  phase    [[ buffer(0) ]],
    device const float*  amp      [[ buffer(1) ]],
    device const int*    pre      [[ buffer(2) ]],
    device const int*    post_idx [[ buffer(3) ]],
    device const float*  wgt      [[ buffer(4) ]],
    device atomic_int*   coupling [[ buffer(5) ]],
    constant float&      varc     [[ buffer(6) ]],
    uint sid [[ thread_position_in_grid ]])
{
    int pi = pre[sid];
    int pj = post_idx[sid];
    float dp = phase[pi] - phase[pj];
    float contribution = wgt[sid] * sin(dp) * amp[pi] * varc;
    atomic_add_float(&coupling[pj], contribution);
}

// Kernel 2: one thread per neuron — load coupling, integrate physics, zero buffer
kernel void oscillator_update(
    device float*       phase    [[ buffer(0) ]],
    device float*       vel      [[ buffer(1) ]],
    device float*       amp      [[ buffer(2) ]],
    device float*       varp     [[ buffer(3) ]],
    device atomic_int*  coupling [[ buffer(4) ]],
    device const float* ext      [[ buffer(5) ]],
    constant float&     omega0   [[ buffer(6) ]],
    constant float&     gamma    [[ buffer(7) ]],
    constant float&     sigma    [[ buffer(8) ]],
    constant float&     dt       [[ buffer(9) ]],
    uint id [[ thread_position_in_grid ]])
{
    // Read coupling (stored as int bit-pattern of float)
    int cf_int = atomic_load_explicit(&coupling[id], memory_order_relaxed);
    float cf   = as_type<float>(cf_int);

    float v   = vel[id];
    float ph  = phase[id];
    float a   = amp[id];
    float vp  = varp[id];

    float accel = -2.0f * gamma * v - omega0 * omega0 * ph + cf + ext[id];
    float v2    = v + accel * dt;
    float ph2   = ph + v2 * dt;
    ph2         = atan2(sin(ph2), cos(ph2));

    float vp2   = vp * (1.0f - 2.0f * gamma * dt) + sigma * sigma * dt;
    vp2         = clamp(vp2, 0.01f, 10.0f);

    float ad    = fabs(v2) * 0.1f;
    float a2    = a * (1.0f - gamma * dt) + ad * dt;
    a2          = clamp(a2, 0.001f, 10.0f);

    phase[id]   = ph2;
    vel[id]     = v2;
    amp[id]     = a2;
    varp[id]    = vp2;

    // Zero coupling buffer for next step (store int 0 = float 0.0)
    atomic_store_explicit(&coupling[id], 0, memory_order_relaxed);
}
"#;

// ── GPU buffer helper ─────────────────────────────────────────────────────────
fn make_buf<T>(device: &Device, data: &[T]) -> Buffer {
    let bytes = std::mem::size_of_val(data);
    device.new_buffer_with_data(
        data.as_ptr() as *const _,
        bytes as u64,
        MTLResourceOptions::StorageModeShared,
    )
}

fn make_zeros(device: &Device, n: usize) -> Buffer {
    let bytes = (n * 4) as u64;
    device.new_buffer(bytes, MTLResourceOptions::StorageModeShared)
}

fn buf_as_slice<T>(buf: &Buffer, n: usize) -> &[T] {
    unsafe { std::slice::from_raw_parts(buf.contents() as *const T, n) }
}

fn main() {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();

    let m = load_meta(&base);
    println!("Rust Metal GPU — real fly olfactory connectome");
    println!("  {} neurons | {} synapses | {} steps",
             m.n_neurons, m.n_synapses, m.n_steps);

    // ── load data ────────────────────────────────────────────────────────────
    let pre_cpu   = load_i32(&base, "pre_indices.bin");
    let post_cpu  = load_i32(&base, "post_indices.bin");
    let wgt_cpu   = load_f32(&base, "syn_weights.bin");
    let kc_cpu    = load_i32(&base, "kc_indices.bin");
    let phase0    = load_f32(&base, "init_phase.bin");
    let amp0      = load_f32(&base, "init_amp.bin");
    let ext_cpu   = load_f32(&base, "ext_force.bin");

    // ── Metal setup ──────────────────────────────────────────────────────────
    let device = Device::system_default().expect("No Metal device");
    println!("  GPU: {}", device.name());

    let lib = device.new_library_with_source(SHADER, &CompileOptions::new()).unwrap();
    let kern_coupling = lib.get_function("compute_coupling", None).unwrap();
    let kern_update   = lib.get_function("oscillator_update", None).unwrap();
    let pso_coupling  = device.new_compute_pipeline_state_with_function(&kern_coupling).unwrap();
    let pso_update    = device.new_compute_pipeline_state_with_function(&kern_update).unwrap();

    let queue = device.new_command_queue();

    // ── GPU buffers (read-only / constant) ───────────────────────────────────
    let b_pre    = make_buf(&device, &pre_cpu);
    let b_post   = make_buf(&device, &post_cpu);
    let b_wgt    = make_buf(&device, &wgt_cpu);
    let b_ext    = make_buf(&device, &ext_cpu);
    let b_varc   = make_buf(&device, &[m.var_correction]);
    let b_omega0 = make_buf(&device, &[m.omega0]);
    let b_gamma  = make_buf(&device, &[m.gamma]);
    let b_sigma  = make_buf(&device, &[m.sigma]);
    let b_dt     = make_buf(&device, &[m.dt]);

    // ── state buffers ─────────────────────────────────────────────────────────
    let reset_state = |b_phase: &Buffer, b_vel: &Buffer, b_amp: &Buffer, b_varp: &Buffer, b_coupling: &Buffer| {
        let phase_ptr = b_phase.contents() as *mut f32;
        let amp_ptr   = b_amp.contents()   as *mut f32;
        let vel_ptr   = b_vel.contents()   as *mut f32;
        let varp_ptr  = b_varp.contents()  as *mut f32;
        let coup_ptr  = b_coupling.contents() as *mut f32;
        unsafe {
            for i in 0..m.n_neurons {
                *phase_ptr.add(i)   = phase0[i];
                *amp_ptr.add(i)     = amp0[i];
                *vel_ptr.add(i)     = 0.0;
                *varp_ptr.add(i)    = 0.1;
                *coup_ptr.add(i)    = 0.0;
            }
        }
    };

    let b_phase    = make_buf(&device, &phase0);
    let b_vel      = make_zeros(&device, m.n_neurons);
    let b_amp      = make_buf(&device, &amp0);
    let b_varp     = {
        let init = vec![0.1f32; m.n_neurons];
        make_buf(&device, &init)
    };
    let b_coupling = make_zeros(&device, m.n_neurons);  // i32 buffer (used as atomic_int in MSL)

    // thread sizes
    let ts_syn  = pso_coupling.max_total_threads_per_threadgroup().min(1024) as u64;
    let gs_syn  = (m.n_synapses as u64).div_ceil(ts_syn);
    let ts_neur = pso_update.max_total_threads_per_threadgroup().min(1024) as u64;
    let gs_neur = (m.n_neurons as u64).div_ceil(ts_neur);

    let encode_step = |cb: &CommandBufferRef| {
        // coupling pass
        let enc = cb.new_compute_command_encoder();
        enc.set_compute_pipeline_state(&pso_coupling);
        enc.set_buffer(0, Some(&b_phase),    0);
        enc.set_buffer(1, Some(&b_amp),      0);
        enc.set_buffer(2, Some(&b_pre),      0);
        enc.set_buffer(3, Some(&b_post),     0);
        enc.set_buffer(4, Some(&b_wgt),      0);
        enc.set_buffer(5, Some(&b_coupling), 0);
        enc.set_buffer(6, Some(&b_varc),     0);
        enc.dispatch_thread_groups(
            MTLSize::new(gs_syn, 1, 1),
            MTLSize::new(ts_syn, 1, 1),
        );
        enc.end_encoding();

        // update pass
        let enc = cb.new_compute_command_encoder();
        enc.set_compute_pipeline_state(&pso_update);
        enc.set_buffer(0, Some(&b_phase),    0);
        enc.set_buffer(1, Some(&b_vel),      0);
        enc.set_buffer(2, Some(&b_amp),      0);
        enc.set_buffer(3, Some(&b_varp),     0);
        enc.set_buffer(4, Some(&b_coupling), 0);
        enc.set_buffer(5, Some(&b_ext),      0);
        enc.set_buffer(6, Some(&b_omega0),   0);
        enc.set_buffer(7, Some(&b_gamma),    0);
        enc.set_buffer(8, Some(&b_sigma),    0);
        enc.set_buffer(9, Some(&b_dt),       0);
        enc.dispatch_thread_groups(
            MTLSize::new(gs_neur, 1, 1),
            MTLSize::new(ts_neur, 1, 1),
        );
        enc.end_encoding();
    };

    // ── warm-up ──────────────────────────────────────────────────────────────
    println!("Warming up GPU …");
    for _ in 0..10 {
        let cb = queue.new_command_buffer();
        encode_step(cb);
        cb.commit();
        cb.wait_until_completed();
    }
    reset_state(&b_phase, &b_vel, &b_amp, &b_varp, &b_coupling);
    println!("  GPU warm-up done");

    // ── timed run (batch 100 steps per command buffer) ────────────────────────
    let t_start = Instant::now();

    for batch_start in (0..m.n_steps).step_by(100) {
        let cb = queue.new_command_buffer();
        let steps_this_batch = (m.n_steps - batch_start).min(100);
        for _ in 0..steps_this_batch {
            encode_step(cb);
        }
        cb.commit();
        cb.wait_until_completed();
    }

    let wall = t_start.elapsed().as_secs_f64();

    // ── KC sparsity ───────────────────────────────────────────────────────────
    let amp_final: &[f32] = buf_as_slice(&b_amp, m.n_neurons);
    let active = kc_cpu.iter().filter(|&&i| amp_final[i as usize] > 0.01).count();
    let sparsity = active as f64 / m.n_kc as f64 * 100.0;

    let bio_ms      = m.n_steps as f64 * m.dt as f64;
    let rt_factor   = bio_ms / 1000.0 / wall;
    let ms_per_step = wall / m.n_steps as f64 * 1000.0;

    println!("\n{}", "=".repeat(55));
    println!("  Wall time       : {:.3} s",     wall);
    println!("  Bio time        : {:.0} ms",    bio_ms);
    println!("  Real-time factor: {:.3}×  ({})",
             rt_factor, if rt_factor > 1.0 { "faster than RT" } else { "slower than RT" });
    println!("  ms per step     : {:.3} ms",    ms_per_step);
    println!("  KC sparsity     : {:.2}%  ({}/{})", sparsity, active, m.n_kc);
    println!("{}", "=".repeat(55));

    // ── write results ────────────────────────────────────────────────────────
    let out = format!(
        r#"{{
  "backend": "rust_metal_gpu",
  "n_neurons": {n},
  "n_synapses": {s},
  "n_steps": {ns},
  "wall_time_s": {wt:.6},
  "bio_time_ms": {bio:.1},
  "rt_factor": {rt:.6},
  "ms_per_step": {mps:.6},
  "kc_sparsity_pct": {sp:.4},
  "active_kc": {ak},
  "total_kc": {tk}
}}"#,
        n   = m.n_neurons,
        s   = m.n_synapses,
        ns  = m.n_steps,
        wt  = wall,
        bio = bio_ms,
        rt  = rt_factor,
        mps = ms_per_step,
        sp  = sparsity,
        ak  = active,
        tk  = m.n_kc,
    );
    let out_path = base.join("results_rust_metal.json");
    fs::write(&out_path, out).unwrap();
    println!("  Results → results_rust_metal.json");
}
