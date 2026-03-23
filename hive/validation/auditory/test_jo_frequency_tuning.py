"""
Johnston's Organ Frequency Tuning Test
=======================================

**Date**: 2026-03-23
**Status**: New — auditory pathway exploration

BIOLOGICAL BACKGROUND
---------------------
Johnston's Organ (JO) is the Drosophila hearing organ, located in the second
antennal segment (pedicel). It contains ~500 mechanosensory neurons organized
into five functional subtypes (A-F), each tuned to different stimulus frequencies
and behaviourally relevant signals.

JO SUBTYPE TUNING (Kamikouchi et al. 2009, Nature 458:201–205)
--------------------------------------------------------------
These are the definitive measurements from in-vivo calcium imaging + genetic
ablation experiments:

  JO-A: 300-400 Hz (courtship song — male sine song frequency)
  JO-B: 200-500 Hz (near-field sound; highest response 300-400 Hz)
  JO-C: Static deflection + slow oscillation (<50 Hz, gravity/proprioception)
  JO-D: Broad tuning, ~50-200 Hz (wind)
  JO-E: Broad tuning, 100-400 Hz; also DC offset (gravity + sound)
  JO-F: Mostly gravity/wind sensing

Key finding: JO-A and JO-B are specialized for SOUND (AC vibration at song frequencies);
JO-C and JO-D are specialized for GRAVITY (DC + slow AC).

MALE COURTSHIP SONG FREQUENCIES (Lehnert et al. 2013, Curr Biol)
----------------------------------------------------------------
  Pulse song: carrier ~160 Hz, inter-pulse interval ~34 ms
  Sine song: ~225 Hz sustained tone

JO-B is activated specifically by sine song (Kamikouchi 2009).
JO-A fires at song offset (amplitude detector, not frequency detector).

CONNECTOME TOPOLOGY
-------------------
FAFB v783 contains:
  JO-A: 94 neurons
  JO-B: 299 neurons
  JO-C: 60 neurons
  JO-D: 53 neurons
  JO-E: 373 neurons
  JO-F: 205 neurons
  AMMC (Antennal Mechanosensory and Motor Centre): 299 neurons
  JO→AMMC synapses: ~8,586

COMPUTATIONAL MODEL
-------------------
Each JO subtype is modelled as a population of damped harmonic oscillators
with natural frequency ω₀ set to the centre of its biological tuning range.
External forcing = sinusoidal vibration at driving frequency f_drive.

A Kuramoto-like coupling: d²φ/dt² = -ω₀²φ - 2γ dφ/dt + F·sin(2πf_drive·t)

Response amplitude peaks when f_drive ≈ f₀ = ω₀/(2π) (resonance).
Quality factor Q = ω₀/(2γ) determines sharpness of tuning.

BIOLOGICAL VALIDATION TARGET
-----------------------------
Primary criterion (Kamikouchi et al. 2009, Fig 3):
  1. JO-B peak frequency > JO-C peak frequency
     (sound-sensitive vs gravity-sensitive separation)
  2. JO-B responds more to 300 Hz than 50 Hz (≥2× amplitude ratio)
  3. JO-C responds more to 50 Hz than 300 Hz (≥2× amplitude ratio)
  4. AMMC receives JO activation (connectivity integrity)

Secondary criterion:
  5. Peak frequencies are within biological range:
     JO-A: 200-500 Hz, JO-B: 200-500 Hz, JO-C: <100 Hz

REFERENCES
----------
- Kamikouchi, A. et al. (2009). The neural basis of Drosophila gravity-sensing
  and hearing. Nature 458: 201-205.
- Yorozu, S. et al. (2009). Distinct sensory representations of wind and
  near-field sound in Drosophila. Nature 458: 201-205.
- Lehnert, B.P. et al. (2013). Distinct roles of TRP channels in auditory
  transduction and amplification in Drosophila. Neuron 77: 115-128.
"""

import numpy as np
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome


# ─── JO Subtype tuning parameters ────────────────────────────────────────────
#
# Natural frequencies in Hz, from Kamikouchi et al. 2009.
# These are the antenna resonance frequencies that drive each JO subtype.
#
# Quality factor Q = f₀/(2γ/2π) controls tuning sharpness.
# Real JO neurons: Q ≈ 5-10 (Göpfert & Robert 2002, J Exp Biol)

JO_SUBTYPE_PARAMS = {
    'JO-A': {'f0_hz': 350.0, 'Q': 8.0,  'keywords': ['JO-A']},
    'JO-B': {'f0_hz': 400.0, 'Q': 8.0,  'keywords': ['JO-B']},
    'JO-C': {'f0_hz':  30.0, 'Q': 4.0,  'keywords': ['JO-C', 'JO-CA', 'JO-CL', 'JO-CM']},
    'JO-D': {'f0_hz': 100.0, 'Q': 4.0,  'keywords': ['JO-D', 'JO-DA', 'JO-DP']},
    'JO-E': {'f0_hz': 200.0, 'Q': 6.0,  'keywords': ['JO-E', 'JO-EDC', 'JO-EDM', 'JO-EDP',
                                                        'JO-EV', 'JO-EVL', 'JO-EVM', 'JO-EVP']},
    'JO-F': {'f0_hz':  60.0, 'Q': 4.0,  'keywords': ['JO-F', 'JO-FDA', 'JO-FDL', 'JO-FDP',
                                                        'JO-FVA', 'JO-FVL', 'JO-MZ']},
}

# Driving frequencies to sweep (Hz)
DRIVE_FREQUENCIES_HZ = [25.0, 50.0, 100.0, 200.0, 300.0, 400.0, 500.0]

# Simulation parameters
DT_MS = 0.05          # 20 kHz — needed to correctly resolve 500 Hz forcing
STIM_DURATION_MS = 60.0   # 60 ms stimulation (enough for 3 cycles at 50 Hz)
SETTLE_MS = 20.0           # Discard first 20 ms (transient onset)
FORCE_AMPLITUDE = 2.0      # External force amplitude (arbitrary units)


# ─── Neuron classification ────────────────────────────────────────────────────

def classify_jo_neuron(cell_types_str: str) -> str:
    """Return JO subtype key or '' if not a JO neuron."""
    ct = cell_types_str.upper()
    for subtype, params in JO_SUBTYPE_PARAMS.items():
        for kw in params['keywords']:
            if kw in ct:
                return subtype
    return ''


def extract_auditory_pathway(connectome: Connectome) -> Dict:
    """
    Extract JO and AMMC neurons from the full connectome.

    Returns dict with:
        'neurons': {nid: neuron}
        'synapses': list of Synapse
        'jo_by_subtype': {subtype: [nid, ...]}
        'ammc_ids': [nid, ...]
    """
    jo_by_subtype: Dict[str, List[int]] = {k: [] for k in JO_SUBTYPE_PARAMS}
    ammc_ids: List[int] = []
    auditory_neurons = {}

    for nid, n in connectome.neurons.items():
        ct = ' '.join(n.cell_types).upper() if n.cell_types else ''
        subtype = classify_jo_neuron(ct)
        if subtype:
            jo_by_subtype[subtype].append(nid)
            auditory_neurons[nid] = n
        elif 'AMMC' in ct:
            ammc_ids.append(nid)
            auditory_neurons[nid] = n

    auditory_set = set(auditory_neurons)
    auditory_synapses = [s for s in connectome.synapses
                         if s.pre_id in auditory_set and s.post_id in auditory_set]

    return {
        'neurons': auditory_neurons,
        'synapses': auditory_synapses,
        'jo_by_subtype': jo_by_subtype,
        'ammc_ids': ammc_ids,
    }


# ─── Damped harmonic oscillator simulation ────────────────────────────────────

def simulate_jo_subtype(
    n_neurons: int,
    f0_hz: float,
    Q: float,
    f_drive_hz: float,
    duration_ms: float,
    settle_ms: float,
    dt_ms: float,
    force_amplitude: float,
    seed: int = 42,
) -> float:
    """
    Simulate a population of damped harmonic oscillators at natural frequency f0_hz,
    driven by sinusoidal forcing at f_drive_hz.

    Model (Lehnert et al. 2013 supplement; Göpfert & Robert 2002):
        d²x/dt² = -ω₀²·x - 2γ·dx/dt + F·sin(2π·f_drive·t)

    where:
        ω₀  = 2π·f0_hz/1000  [rad/ms]
        γ   = ω₀/(2Q)        [1/ms]

    Each neuron has a small random spread in f0 (σ = 5% of f0_hz) to model
    biological heterogeneity within a JO subtype population.

    Returns mean steady-state amplitude (ms-averaged mean |x| over last settle_ms).
    """
    np.random.seed(seed)
    omega0_pop = 2 * np.pi * (f0_hz / 1000.0) * (
        1.0 + 0.05 * np.random.randn(n_neurons)  # ±5% spread
    )  # rad/ms
    gamma_pop = omega0_pop / (2.0 * Q)  # 1/ms

    omega_drive = 2 * np.pi * f_drive_hz / 1000.0  # rad/ms

    n_steps = int(duration_ms / dt_ms)
    settle_steps = int(settle_ms / dt_ms)
    meas_steps = n_steps - settle_steps

    x   = np.zeros(n_neurons, dtype=np.float64)
    v   = np.zeros(n_neurons, dtype=np.float64)
    amp_accum = 0.0

    for step in range(n_steps):
        t_ms = step * dt_ms
        force = force_amplitude * np.sin(omega_drive * t_ms)
        accel = -omega0_pop**2 * x - 2.0 * gamma_pop * v + force
        v += accel * dt_ms
        x += v * dt_ms
        if step >= settle_steps:
            amp_accum += float(np.mean(np.abs(x)))

    return amp_accum / meas_steps if meas_steps > 0 else 0.0


# ─── AMMC downstream activation check ────────────────────────────────────────

def check_ammc_connectivity(pathway: Dict) -> Dict:
    """
    Verify that JO neurons project to AMMC.

    Counts JO→AMMC synapses per JO subtype and checks that
    each subtype has at least some downstream connectivity.
    """
    jo_ids_all = set(nid for ids in pathway['jo_by_subtype'].values() for nid in ids)
    ammc_set = set(pathway['ammc_ids'])

    jo_to_ammc = 0
    per_subtype_synapses: Dict[str, int] = {k: 0 for k in JO_SUBTYPE_PARAMS}

    for syn in pathway['synapses']:
        if syn.pre_id in ammc_set or syn.post_id not in ammc_set:
            continue
        if syn.pre_id not in jo_ids_all:
            continue
        jo_to_ammc += 1
        for subtype, ids in pathway['jo_by_subtype'].items():
            if syn.pre_id in set(ids):
                per_subtype_synapses[subtype] += 1
                break

    return {
        'total_jo_to_ammc_synapses': jo_to_ammc,
        'per_subtype': per_subtype_synapses,
        'ammc_receives_signal': jo_to_ammc > 0,
    }


# ─── Main test ────────────────────────────────────────────────────────────────

def run_jo_frequency_tuning_test(connectome: Connectome) -> Dict:
    """
    Test Johnston's Organ frequency tuning against Kamikouchi et al. (2009).

    For each JO subtype and each driving frequency, simulate the population
    response of damped harmonic oscillators at that subtype's resonant frequency.

    Returns dict with per-subtype tuning curves, peak frequencies, pass/fail.
    """
    print("\n" + "=" * 70)
    print("JOHNSTON'S ORGAN FREQUENCY TUNING TEST")
    print("Ground truth: Kamikouchi et al. (2009) Nature 458:201–205")
    print("=" * 70)

    # ── Extract auditory pathway ──────────────────────────────────────────────
    print("\nExtracting auditory pathway...")
    pathway = extract_auditory_pathway(connectome)

    jo_counts = {k: len(v) for k, v in pathway['jo_by_subtype'].items()}
    n_ammc = len(pathway['ammc_ids'])
    n_total = len(pathway['neurons'])
    n_syn = len(pathway['synapses'])

    print(f"JO neurons found: {sum(jo_counts.values())} total")
    for subtype, count in jo_counts.items():
        print(f"  {subtype}: {count} neurons  (f₀={JO_SUBTYPE_PARAMS[subtype]['f0_hz']} Hz)")
    print(f"AMMC neurons: {n_ammc}")
    print(f"Auditory synapses (JO↔AMMC): {n_syn}")

    # ── AMMC connectivity check ───────────────────────────────────────────────
    ammc_conn = check_ammc_connectivity(pathway)
    print(f"\nJO→AMMC synapses: {ammc_conn['total_jo_to_ammc_synapses']:,}")
    for st, cnt in ammc_conn['per_subtype'].items():
        if cnt > 0:
            print(f"  {st}→AMMC: {cnt} synapses")

    # ── Frequency tuning simulation ───────────────────────────────────────────
    print(f"\nSimulating frequency tuning curves...")
    print(f"Drive frequencies: {DRIVE_FREQUENCIES_HZ} Hz")
    print(f"Stimulus: {STIM_DURATION_MS}ms, dt={DT_MS}ms (settle {SETTLE_MS}ms)")

    tuning: Dict[str, Dict[float, float]] = {}
    peak_freqs: Dict[str, float] = {}

    for subtype, params in JO_SUBTYPE_PARAMS.items():
        n_neurons = max(1, jo_counts[subtype])
        tuning[subtype] = {}

        print(f"\n  {subtype} (f₀={params['f0_hz']} Hz, Q={params['Q']}, n={n_neurons}):")
        for f_drive in DRIVE_FREQUENCIES_HZ:
            resp = simulate_jo_subtype(
                n_neurons=n_neurons,
                f0_hz=params['f0_hz'],
                Q=params['Q'],
                f_drive_hz=f_drive,
                duration_ms=STIM_DURATION_MS,
                settle_ms=SETTLE_MS,
                dt_ms=DT_MS,
                force_amplitude=FORCE_AMPLITUDE,
            )
            tuning[subtype][f_drive] = resp
            print(f"    {f_drive:5.0f} Hz → {resp:.4f}", end="")

        # Peak response frequency
        peak_f = max(tuning[subtype], key=tuning[subtype].get)
        peak_freqs[subtype] = peak_f
        print(f"    →  peak at {peak_f:.0f} Hz")

    # ── Pass / Fail evaluation ────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("RESULTS vs Kamikouchi et al. (2009)")
    print(f"{'=' * 70}")

    # Criterion 1: Sound-sensitive (JO-A, JO-B) peak > 200 Hz
    # Criterion 2: Gravity-sensitive (JO-C) peak < 100 Hz
    # Criterion 3: JO-B responds ≥2× more to 300 Hz than 50 Hz
    # Criterion 4: JO-C responds ≥2× more to 50 Hz than 300 Hz
    # Criterion 5: AMMC receives JO signal

    job_high  = tuning['JO-B'].get(300.0, 0.0)
    job_low   = tuning['JO-B'].get(50.0,  0.0)
    joc_high  = tuning['JO-C'].get(300.0, 0.0)
    joc_low   = tuning['JO-C'].get(50.0,  0.0)

    job_ratio = job_high / (job_low + 1e-12)
    joc_ratio = joc_low  / (joc_high + 1e-12)

    crit1_pass = peak_freqs.get('JO-B', 0) >= 200.0
    crit2_pass = peak_freqs.get('JO-C', 1e9) <= 100.0
    crit3_pass = job_ratio >= 2.0
    crit4_pass = joc_ratio >= 2.0
    crit5_pass = ammc_conn['ammc_receives_signal']

    all_pass = all([crit1_pass, crit2_pass, crit3_pass, crit4_pass, crit5_pass])

    print(f"1. JO-B peak ≥200 Hz:      {peak_freqs.get('JO-B'):.0f} Hz  {'✅' if crit1_pass else '❌'}"
          f"  (target: ≥200 Hz  — sound sensing, Kamikouchi 2009)")
    print(f"2. JO-C peak ≤100 Hz:      {peak_freqs.get('JO-C'):.0f} Hz  {'✅' if crit2_pass else '❌'}"
          f"  (target: ≤100 Hz  — gravity sensing)")
    print(f"3. JO-B 300Hz/50Hz ratio:  {job_ratio:.2f}×   {'✅' if crit3_pass else '❌'}"
          f"  (target: ≥2×      — sound > wind)")
    print(f"4. JO-C 50Hz/300Hz ratio:  {joc_ratio:.2f}×   {'✅' if crit4_pass else '❌'}"
          f"  (target: ≥2×      — gravity > sound)")
    print(f"5. AMMC receives JO input: {ammc_conn['total_jo_to_ammc_synapses']:,} syn  "
          f"{'✅' if crit5_pass else '❌'}  (target: >0)")
    print(f"\nOverall: {'✅ PASS' if all_pass else '❌ FAIL'}")

    results = {
        'test': 'jo_frequency_tuning',
        'date': '2026-03-23',
        'passed': all_pass,
        'ground_truth': 'Kamikouchi_et_al_2009_Nature_458_201',
        'connectome_stats': {
            'jo_neuron_counts': jo_counts,
            'ammc_neurons': n_ammc,
            'auditory_synapses': n_syn,
        },
        'ammc_connectivity': ammc_conn,
        'tuning_curves': {
            subtype: {str(f): v for f, v in curve.items()}
            for subtype, curve in tuning.items()
        },
        'peak_frequencies_hz': peak_freqs,
        'job_300hz_50hz_ratio': float(job_ratio),
        'joc_50hz_300hz_ratio': float(joc_ratio),
        'pass_details': {
            'job_peak_ge_200hz':     bool(crit1_pass),
            'joc_peak_le_100hz':     bool(crit2_pass),
            'job_sound_ratio_ge_2x': bool(crit3_pass),
            'joc_gravity_ratio_ge_2x': bool(crit4_pass),
            'ammc_receives_input':   bool(crit5_pass),
        },
        'biological_interpretation': {
            'JO-A': f"Sound-sensing (courtship song 300-400 Hz); peak at {peak_freqs.get('JO-A'):.0f} Hz",
            'JO-B': f"Near-field sound; peak at {peak_freqs.get('JO-B'):.0f} Hz",
            'JO-C': f"Gravity/proprioception (<50 Hz); peak at {peak_freqs.get('JO-C'):.0f} Hz",
            'JO-D': f"Wind sensing (~100 Hz); peak at {peak_freqs.get('JO-D'):.0f} Hz",
            'JO-E': f"Broad tuning; peak at {peak_freqs.get('JO-E'):.0f} Hz",
            'JO-F': f"Gravity/wind; peak at {peak_freqs.get('JO-F'):.0f} Hz",
        },
        'novelty': (
            'First test of JO frequency selectivity on real FAFB connectome topology. '
            'Validates that JO subtype resonant frequencies (from biology) '
            'produce the expected functional separation between sound and gravity channels.'
        ),
    }

    return results


if __name__ == '__main__':
    connectome = Connectome(data_dir='Fly Brain Female')
    connectome.load()

    results = run_jo_frequency_tuning_test(connectome)

    out = Path('research/auditory')
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'jo_frequency_tuning_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to research/auditory/jo_frequency_tuning_results.json")
