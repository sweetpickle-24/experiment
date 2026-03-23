//! Smell Test — Rust Implementation
//!
//! Exact same sparse wave oscillator as the Python reference.
//! Uses rayon for parallel iteration where safe, serial scatter accumulate
//! for the coupling step (scatter patterns don't parallelize with safe Rust easily).
//!
//! Compile & run:  cargo run --release

use std::time::Instant;
use std::f32::consts::PI;
use std::collections::HashMap;
use rayon::prelude::*;
use serde_json::json;

// ─── Network constants ───────────────────────────────────────────────────────
const N_PN: usize = 2198;
const N_KC: usize = 5279;
const N: usize = N_PN + N_KC;
const N_CHANNELS: usize = 20;
const KC_FAN_IN: usize = 7;
const SIM_MS: f32 = 300.0;
const DT: f32 = 0.1;
const SEED: u64 = 42;

// ─── Physics constants ────────────────────────────────────────────────────────
const GAMMA: f32 = 0.1;
const SIGMA_NOISE: f32 = 0.1;
const OMEGA0: f32 = 2.0 * PI * 10.0 / 1000.0;
const EXT_STR: f32 = 50.0;

// ─── Channel frequencies ──────────────────────────────────────────────────────
const CHANNEL_FREQ: [f32; N_CHANNELS] = [
    20.0, 18.0, 22.0,  8.0, 12.0, 16.0,
    14.0,  6.0, 10.0,  5.0,  9.0, 12.0,
     7.0,  6.0,  5.0,  5.0, 11.0, 13.0,
     7.0,  4.0,
];

fn channel_omega() -> [f32; N_CHANNELS] {
    let mut o = [0f32; N_CHANNELS];
    for (i, f) in CHANNEL_FREQ.iter().enumerate() {
        o[i] = 2.0 * PI * f / 1000.0;
    }
    o
}

// ─── Simple deterministic PRNG (xorshift64) ───────────────────────────────────
struct Rng(u64);

impl Rng {
    fn new(seed: u64) -> Self { Rng(seed ^ 0x1234567890ABCDEF) }

    fn next_u64(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }

    fn next_f32(&mut self) -> f32 {
        (self.next_u64() >> 11) as f32 / (1u64 << 53) as f32
    }

    // Float in [-pi, pi]
    fn next_phase(&mut self) -> f32 {
        self.next_f32() * 2.0 * PI - PI
    }

    // Sample k distinct indices from [0, n)
    fn sample_without_replacement(&mut self, n: usize, k: usize) -> Vec<usize> {
        let mut pool: Vec<usize> = (0..n).collect();
        for i in 0..k {
            let j = i + (self.next_u64() as usize) % (n - i);
            pool.swap(i, j);
        }
        pool[..k].to_vec()
    }
}

// ─── Odor library ─────────────────────────────────────────────────────────────
fn norm_pattern(v: &[f32]) -> Vec<f32> {
    let n: f32 = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    v.iter().map(|x| x / n).collect()
}

fn odor_library() -> Vec<(&'static str, Vec<f32>)> {
    vec![
        ("fruit_ferment", norm_pattern(&[
            0.85, 0.20, 0.70, 0.10, 0.15, 0.05,
            0.65, 0.25, 0.40, 0.00, 0.00, 0.00,
            0.00, 0.05, 0.00, 0.00, 0.15, 0.10,
            0.00, 0.05])),
        ("fruit_ripe", norm_pattern(&[
            0.90, 0.45, 0.35, 0.15, 0.20, 0.30,
            0.25, 0.05, 0.20, 0.00, 0.00, 0.10,
            0.00, 0.00, 0.00, 0.00, 0.10, 0.20,
            0.00, 0.05])),
        ("danger_mold", norm_pattern(&[
            0.00, 0.00, 0.05, 0.00, 0.00, 0.00,
            0.00, 0.20, 0.60, 0.70, 0.00, 0.05,
            0.90, 0.85, 0.00, 0.00, 0.05, 0.00,
            0.75, 0.00])),
        ("social_female", norm_pattern(&[
            0.00, 0.05, 0.00, 0.30, 0.10, 0.00,
            0.00, 0.00, 0.00, 0.20, 0.10, 0.10,
            0.00, 0.00, 0.90, 0.05, 0.05, 0.00,
            0.00, 0.05])),
        ("clean_air", norm_pattern(&[
            0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
            0.02, 0.05, 0.02, 0.00, 0.00, 0.02,
            0.00, 0.00, 0.00, 0.00, 0.05, 0.05,
            0.00, 0.90])),
    ]
}

// ─── Build network ─────────────────────────────────────────────────────────────
fn build_network(seed: u64) -> (Vec<u32>, Vec<u32>) {
    let mut rng = Rng::new(seed);
    let mut pre: Vec<u32> = Vec::with_capacity(N_KC * KC_FAN_IN);
    let mut post: Vec<u32> = Vec::with_capacity(N_KC * KC_FAN_IN);

    for kc in 0..N_KC {
        let pns = rng.sample_without_replacement(N_PN, KC_FAN_IN);
        for pn in pns {
            pre.push(pn as u32);
            post.push(kc as u32);
        }
    }
    (pre, post)
}

// ─── Run simulation ────────────────────────────────────────────────────────────
fn run_simulation(odor: &[f32], pre: &[u32], post: &[u32], seed: u64) -> Vec<f32> {
    let var_corr = (-0.1f32 / 2.0).exp();
    let omega = channel_omega();
    let weight = 1.0f32 / KC_FAN_IN as f32;
    let pns_per_ch = N_PN / N_CHANNELS;

    let mut rng = Rng::new(seed);

    let mut phase  = vec![0f32; N];
    let mut vel    = vec![0f32; N];
    let mut amp    = vec![0.1f32; N];
    let mut var_ph = vec![0.1f32; N];

    for p in phase.iter_mut() { *p = rng.next_phase(); }

    // Precompute per-PN base forcing amplitude
    let mut ext_base = vec![0f32; N];
    for ch in 0..N_CHANNELS {
        let s = ch * pns_per_ch;
        let e = s + pns_per_ch;
        let a = odor[ch] * EXT_STR;
        for i in s..e { ext_base[i] = a; }
    }

    let num_steps = (SIM_MS / DT) as usize;

    for step in 0..num_steps {
        let t = step as f32 * DT;

        // Build ext_force (sinusoidal per channel)
        let mut ext_force = vec![0f32; N];
        for ch in 0..N_CHANNELS {
            let s = ch * pns_per_ch;
            let e = s + pns_per_ch;
            let f = ext_base[s] * (omega[ch] * t).sin();
            for i in s..e { ext_force[i] = f; }
        }

        // Coupling: PN → KC scatter accumulate (serial — safe, no data races)
        let mut coupling = vec![0f32; N];
        for idx in 0..pre.len() {
            let pi = pre[idx] as usize;
            let ki = post[idx] as usize + N_PN;
            let dp = phase[pi] - phase[ki];
            coupling[ki] += weight * dp.sin() * amp[pi] * var_corr;
        }

        // Oscillator update — parallelised with rayon
        let iter = phase.par_iter_mut()
            .zip(vel.par_iter_mut())
            .zip(amp.par_iter_mut())
            .zip(var_ph.par_iter_mut())
            .zip(coupling.par_iter())
            .zip(ext_force.par_iter());

        iter.for_each(|(((((ph, v), a), vp), c), ef)| {
            let acc = -2.0 * GAMMA * *v - OMEGA0 * OMEGA0 * *ph + *c + *ef;
            *v  += acc * DT;
            *ph += *v * DT;
            *ph  = ph.sin().atan2(ph.cos());
            *vp  = (*vp * (1.0 - 2.0 * GAMMA * DT) + SIGMA_NOISE * SIGMA_NOISE * DT)
                    .clamp(0.01, 10.0);
            let amp_drive = v.abs() * 0.1;
            *a = (*a * (1.0 - GAMMA * DT) + amp_drive * DT).clamp(0.001, 10.0);
        });
    }

    amp[N_PN..].to_vec()
}

// ─── Metrics ──────────────────────────────────────────────────────────────────
fn compute_sparsity(kc: &[f32]) -> f32 {
    let mean: f32 = kc.iter().sum::<f32>() / kc.len() as f32;
    let var: f32  = kc.iter().map(|x| (x - mean).powi(2)).sum::<f32>() / kc.len() as f32;
    let std = var.sqrt();
    let thr = mean + std;
    kc.iter().filter(|&&x| x > thr).count() as f32 / kc.len() as f32
}

fn pearson_r(a: &[f32], b: &[f32]) -> f32 {
    let ma: f32 = a.iter().sum::<f32>() / a.len() as f32;
    let mb: f32 = b.iter().sum::<f32>() / b.len() as f32;
    let am: Vec<f32> = a.iter().map(|x| x - ma).collect();
    let bm: Vec<f32> = b.iter().map(|x| x - mb).collect();
    let dot: f32     = am.iter().zip(bm.iter()).map(|(x, y)| x * y).sum();
    let da: f32      = am.iter().map(|x| x * x).sum::<f32>().sqrt();
    let db: f32      = bm.iter().map(|x| x * x).sum::<f32>().sqrt();
    if da * db > 1e-10 { dot / (da * db) } else { 0.0 }
}

// ─── Main ─────────────────────────────────────────────────────────────────────
fn main() {
    println!("{}", "=".repeat(60));
    println!("  SMELL TEST — Rust");
    println!("  Network: {} PNs + {} KCs, {} PN/KC", N_PN, N_KC, KC_FAN_IN);
    println!("  Simulation: {}ms at dt={}ms ({} steps)", SIM_MS as u32,
             DT, (SIM_MS / DT) as u32);
    println!("  rayon threads: {}", rayon::current_num_threads());
    println!("{}", "=".repeat(60));

    let (pre, post) = build_network(SEED);
    println!("  Synapses: {}", pre.len());

    let odors = odor_library();
    let mut kc_patterns: HashMap<&str, Vec<f32>> = HashMap::new();
    let mut timings: HashMap<&str, f64> = HashMap::new();

    println!("\n  Running simulations...");
    let total_t0 = Instant::now();

    for (name, pattern) in &odors {
        let t0 = Instant::now();
        let kc_amp = run_simulation(pattern, &pre, &post, SEED);
        let elapsed = t0.elapsed().as_secs_f64();
        let sp = compute_sparsity(&kc_amp);
        println!("    {:<20}  sparsity={:.2}%  time={:.3}s", name, sp * 100.0, elapsed);
        kc_patterns.insert(name, kc_amp);
        timings.insert(name, elapsed);
    }

    let total_elapsed = total_t0.elapsed().as_secs_f64();
    println!("\n  Total wall time: {:.3}s", total_elapsed);
    println!("  Per-odor:        {:.3}s", total_elapsed / odors.len() as f64);

    println!("\n  Inter-odor KC correlations:");
    let mut corr_map = serde_json::Map::new();
    for (i, (n1, _)) in odors.iter().enumerate() {
        for (j, (n2, _)) in odors.iter().enumerate() {
            if j > i {
                let r = pearson_r(&kc_patterns[n1], &kc_patterns[n2]);
                let key = format!("{} vs {}", n1, n2);
                println!("    {:<20} vs {:<20}: r = {:.4}", n1, n2, r);
                corr_map.insert(key, json!(format!("{:.4}", r)));
            }
        }
    }

    let avg_sp: f32 = kc_patterns.values().map(|v| compute_sparsity(v)).sum::<f32>()
        / kc_patterns.len() as f32;
    let fruit_danger = pearson_r(&kc_patterns["fruit_ferment"], &kc_patterns["danger_mold"]);
    let fruit_fruit  = pearson_r(&kc_patterns["fruit_ferment"], &kc_patterns["fruit_ripe"]);

    println!("\n  KEY METRICS:");
    println!("    Average KC sparsity:         {:.2}%  (target: 1-3%)", avg_sp * 100.0);
    println!("    fruit_ferment vs danger:     r = {:.4}  (should be low)", fruit_danger);
    println!("    fruit_ferment vs fruit_ripe: r = {:.4}  (should be higher)", fruit_fruit);

    let mean_amps: serde_json::Map<String, serde_json::Value> = kc_patterns.iter()
        .map(|(k, v)| {
            let m = v.iter().sum::<f32>() / v.len() as f32;
            (k.to_string(), json!(format!("{:.6}", m)))
        })
        .collect();

    let results = json!({
        "language": "rust",
        "n_pn": N_PN,
        "n_kc": N_KC,
        "kc_fan_in": KC_FAN_IN,
        "sim_ms": SIM_MS,
        "total_wall_time_s": format!("{:.4}", total_elapsed),
        "per_odor_s": format!("{:.4}", total_elapsed / odors.len() as f64),
        "avg_kc_sparsity_pct": format!("{:.4}", avg_sp * 100.0),
        "fruit_vs_danger_r": format!("{:.4}", fruit_danger),
        "fruit_vs_fruit_r": format!("{:.4}", fruit_fruit),
        "kc_mean_amp": mean_amps,
        "correlations": corr_map,
    });

    let out = "/Users/vladyslav/Documents/GitHub/experiment/benchmarks/smell_test/results_rust.json";
    std::fs::write(out, serde_json::to_string_pretty(&results).unwrap()).unwrap();
    println!("\n  Results saved: {}", out);
}
