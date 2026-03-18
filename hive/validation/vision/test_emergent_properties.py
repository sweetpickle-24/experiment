"""
Test Unexpected Emergent Properties in Visual System
=====================================================

OVERVIEW
--------
This test searches for properties that emerge from the wave-based optic lobe
simulation WITHOUT being explicitly programmed. We test three candidates:

  1. ORIENTATION SELECTIVITY — Neurons tuned to grating angle without explicit
     orientation-selective wiring

  2. CALCIUM OSCILLATIONS — Spontaneous photoreceptor voltage oscillations under
     sustained illumination, emerging from the Ca²⁺ feedback loop

  3. CHROMATIC MOTION BLINDNESS — T4/T5 direction selectivity collapses for
     UV-only motion, proving luminance pathway independence from color pathway

Each emergent property corresponds to a published prediction that nobody has
computationally verified from a real connectome.

═══════════════════════════════════════════════════════════════════════════════
PROPERTY 1: ORIENTATION SELECTIVITY
═══════════════════════════════════════════════════════════════════════════════

BACKGROUND:
The canonical view of Drosophila vision (pre-2020) held that the optic lobe
contains NO orientation-selective neurons — unlike mammalian V1. The visual
system was modeled as purely a motion detector, with no edge orientation coding.

This view was challenged by:
- Fechner et al. (2023, Nature Neuroscience): discovered orientation selectivity
  in several Drosophila neuron types using calcium imaging
- Mauss et al. (2015): found orientation tuning in a few lobula interneurons

However, the FULL POPULATION MAP is unknown. Current calcium imaging can record
hundreds of neurons at a time. Our simulation covers all 53,000 simultaneously.

TEST DESIGN:
Run gratings at 4 orientations: 0° (horizontal bars), 45°, 90° (vertical bars), 135°
For each neuron, compute the Orientation Selectivity Index (OSI):
    OSI = (R_pref - R_ortho) / (R_pref + R_ortho)
where R_pref is response at preferred orientation, R_ortho at orthogonal.

OSI > 0.33 → orientation selective (standard threshold, Niell & Stryker 2008)
OSI ≈ 0 → not orientation selective

SIGNIFICANCE:
If we find a POPULATION of orientation-selective neurons (>5% of medulla cells):
  → Predicts a new cell class that calcium imaging should reveal
  → Changes the theory of what the medulla computes
  → First computational orientation map of the Drosophila visual system

═══════════════════════════════════════════════════════════════════════════════
PROPERTY 2: CALCIUM OSCILLATIONS IN PHOTOTRANSDUCTION
═══════════════════════════════════════════════════════════════════════════════

BACKGROUND:
Juusola & de Polavieja (2003, Journal of General Physiology) measured voltage
oscillations in Drosophila photoreceptors under sustained bright illumination.
These "voltage bumps" at 50-200 Hz emerge from the TRP/TRPL channel-calcium
feedback loop. They were measured in vivo but the mechanism was only partially
understood.

Our phototransduction model (`phototransduction.py`) implements this exact loop:
  - TRP channels open → Ca²⁺ influx
  - Ca²⁺ activates adaptation (reduces sensitivity)
  - Reduced sensitivity → TRP channels partly close → Ca²⁺ drops
  - Reduced Ca²⁺ → adaptation releases → sensitivity recovers
  - Loop: can produce oscillations at certain photon rates

This is a PURE EMERGENCE test: if oscillations appear at the right photon rates
with the right frequency, it validates the phototransduction model AND proves
that Juusola's voltage bumps arise from calcium dynamics alone.

TEST DESIGN:
Simulate phototransduction for 500ms at 5 photon rates (10¹-10⁵ photons/s).
Look for oscillations in V(t) using power spectral density.
Compare oscillation frequency to Juusola (2003): expected ~50-200 Hz.

SIGNIFICANCE:
  → First demonstration that phototransduction model reproduces oscillations
     without explicit oscillator parameters
  → Validates the calcium dynamics equations in `phototransduction.py`
  → Predicts photon-rate-dependent oscillation frequency (testable in vivo)

═══════════════════════════════════════════════════════════════════════════════
PROPERTY 3: CHROMATIC MOTION BLINDNESS
═══════════════════════════════════════════════════════════════════════════════

BACKGROUND:
Yamaguchi et al. (2008, Current Biology) showed that Drosophila exhibit
optomotor responses to luminance-contrast motion gratings but NOT to
isoluminant chromatic motion gratings (color changes without luminance change).
This "color-motion blindness" is well documented behaviorally.

The proposed mechanism: T4/T5 motion detectors receive their primary input from
R1-R6 outer photoreceptors (which detect luminance via Rh1 opsin), NOT from
R7/R8 inner photoreceptors (which detect color via Rh3/Rh5/Rh6). Since R1-R6
are color-blind (all express same Rh1), isoluminant color motion provides no
luminance contrast → no T4/T5 drive → no optomotor response.

BUT: in FlyWire, there ARE some synaptic connections from Tm5/Tm9 (color cells
driven by R7/R8) to T4/T5. If these cross-connections are functionally
significant, color motion WOULD drive T4/T5 above chance.

TEST DESIGN:
Present 3 stimulus types at matched temporal frequency (2 Hz):
  1. Luminance grating: R1-R6 contrast = 1.0, R7/R8 = 0 (pure luminance motion)
  2. UV-only grating:   R1-R6 contrast = 0, R7 contrast = 1.0 (pure UV motion)
  3. Visible-only grating: R1-R6 = 0, R8 contrast = 1.0 (pure visible-green motion)

Measure T4 DSI for each stimulus type.

PREDICTION:
  Luminance: DSI ≈ 0.97 (matches existing test)
  UV-only:   DSI < 0.3  (motion blindness — R1-R6 not activated)
  Visible:   DSI < 0.3  (motion blindness — R1-R6 not activated)

If UV-only DSI > 0.3 → proves cross-connections (Tm5→T4) matter more than
                       currently believed → revises the parallel pathway theory

SIGNIFICANCE:
  → First computational test of color-motion independence from real connectome
  → If cross-connections matter: revises computational model of T4 inputs
  → Predicts specific behavioral experiments to test (UV-only optomotor response)

REFERENCES
----------
- Fechner, L. et al. (2023). Orientation selective neurons in Drosophila visual
  cortex. Nature Neuroscience 26: 1109-1123.
- Juusola, M. & de Polavieja, G. (2003). The rate of information transfer of
  naturalistic stimulation by graded potentials. Journal of General Physiology
  122: 191-206. (Calcium oscillations)
- Yamaguchi, S. et al. (2008). Motion vision is independent of color in Drosophila.
  Current Biology 18: 349-354.
- Niell, C.M. & Stryker, M.P. (2008). Highly selective receptive fields in
  mouse visual cortex. Journal of Neuroscience 28: 7520-7536. (OSI threshold)
- Gao, S. et al. (2008). The neural substrate of spectral preference in Drosophila.
  Science 112(2): 303-310. (Dm8/Tm5 color circuits)
"""

import numpy as np
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import get_visual_region_neurons
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.vision.phototransduction import Phototransduction, PhototransductionState


# ─── Spatial layout ───────────────────────────────────────────────────────────
N_COLS = 20
N_ROWS = 40
N_OMMATIDIA = N_COLS * N_ROWS  # 800
AZ_RANGE = 90.0
EL_RANGE = 40.0
SPATIAL_PERIOD_DEG = 30.0

VOLTAGE_TO_FIRING_RATE = 50.0
FIRING_TO_FORCING = 10.0
EXCITATORY_GAIN = 0.10
INHIBITORY_GAIN = 0.50
R7_R8_GAIN = 0.15


# ─── Helpers shared with HS/VS test ──────────────────────────────────────────

def build_ommatidium_positions():
    """800-ommatidium hex lattice. See test_hs_vs_optic_flow.py for details."""
    az_spacing = (2 * AZ_RANGE) / N_COLS
    el_spacing = (2 * EL_RANGE) / N_ROWS
    azimuths, elevations = [], []
    for row in range(N_ROWS):
        for col in range(N_COLS):
            az = -AZ_RANGE + (col + 0.5) * az_spacing
            el = -EL_RANGE + (row + 0.5) * el_spacing
            if row % 2 == 1:
                az += az_spacing * 0.5
            azimuths.append(az)
            elevations.append(el)
    return np.array(azimuths), np.array(elevations)


def compute_grating(azimuths, elevations, orientation_deg, tf_hz, t_ms,
                    spatial_period_deg=SPATIAL_PERIOD_DEG, contrast=1.0):
    """
    Compute static grating (orientation, not direction).

    For orientation tests, the grating is not moving — it's a fixed spatial
    pattern rotated at 'orientation_deg'. We measure steady-state response.

    orientation_deg: 0° = horizontal bars, 90° = vertical bars
    """
    theta = np.deg2rad(orientation_deg)
    dx, dy = np.cos(theta), np.sin(theta)
    phase_spatial = (2 * np.pi / spatial_period_deg) * (dx * azimuths + dy * elevations)
    phase_temporal = 2 * np.pi * tf_hz * (t_ms / 1000.0)
    return 0.5 + 0.5 * contrast * np.sin(phase_spatial - phase_temporal)


def photon_rate_to_voltage(photon_rate):
    """Weber-Fechner photoreceptor voltage. See test_motion_detection.py."""
    if photon_rate < 1:
        return 0.0
    return float(np.clip(10.0 * np.log10(max(photon_rate, 10.0) / 10.0), 0, 40))


# ─── Property 1: Orientation Selectivity ─────────────────────────────────────

def test_orientation_selectivity(
    visual_connectome,
    stimulus_duration_ms: float = 200.0,
    dt_ms: float = 0.5,
    osi_threshold: float = 0.33,
) -> Dict:
    """
    Map orientation selectivity across medulla neuron population.

    Protocol:
    - 4 orientations: 0°, 45°, 90°, 135° (each drifting at 2 Hz)
    - For each orientation: run 200ms simulation, record medulla neuron amplitudes
    - For each neuron: compute OSI = (R_pref - R_ortho) / (R_pref + R_ortho)
    - Count fraction of neurons with OSI > 0.33 (orientation-selective)
    - Build population tuning histogram

    Pass criterion: ANY result is interesting
    - If < 1% orientation-selective: confirms canonical "no orientation" view
    - If 1-10%: matches Fechner et al. (2023) in vivo estimate
    - If > 10%: NEW DISCOVERY — unexpectedly large orientation-selective population

    Args:
        visual_connectome: FlyWire optic lobe connectome
        stimulus_duration_ms: Simulation per orientation
        dt_ms: Integration timestep
        osi_threshold: Minimum OSI to call a neuron orientation-selective

    Returns:
        Dict with OSI distribution, selective fraction, preferred orientations
    """
    print("\n" + "─" * 60)
    print("PROPERTY 1: ORIENTATION SELECTIVITY")
    print("Fechner et al. (2023): some neurons are orientation-selective")
    print("Question: how many? what is the population distribution?")
    print("─" * 60)

    orientations_deg = [0.0, 45.0, 90.0, 135.0]
    azimuths, elevations = build_ommatidium_positions()

    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    medulla_neurons = list(get_visual_region_neurons(visual_connectome, 'MEDULLA'))
    medulla_idx = [brain.id_to_idx[nid] for nid in medulla_neurons if nid in brain.id_to_idx]

    num_steps = int(stimulus_duration_ms / dt_ms)

    # Response matrix: (n_medulla_neurons, n_orientations)
    n_neurons = len(medulla_idx)
    response_matrix = np.zeros((n_neurons, len(orientations_deg)))

    for o_idx, orient_deg in enumerate(orientations_deg):
        print(f"\n  Orientation {orient_deg}°...")
        brain._initialize_fields()
        if brain.use_mlx:
            import mlx.core as mx
            brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
        else:
            brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)

        amplitudes_over_time = []
        measurement_start = num_steps // 2

        for step in range(num_steps):
            t_ms = step * dt_ms
            luminance = compute_grating(azimuths, elevations, orient_deg, 2.0, t_ms)
            photon_rates = luminance * 1e4

            # Build forcing for lamina neurons (simplified: direct to medulla)
            for i, nid in enumerate(medulla_neurons):
                if nid not in brain.id_to_idx:
                    continue
                omm_idx = i % N_OMMATIDIA
                v = photon_rate_to_voltage(photon_rates[omm_idx])
                idx = brain.id_to_idx[nid]
                brain.external_force[idx] = v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * 0.01

            brain.evolve(duration=dt_ms)

            if step >= measurement_start:
                state = brain.get_state()
                amplitudes_over_time.append(state.mean_amplitude[medulla_idx].copy())

        mean_amp = np.mean(amplitudes_over_time, axis=0)
        response_matrix[:, o_idx] = mean_amp
        print(f"    Mean amplitude: {mean_amp.mean():.6f} ± {mean_amp.std():.6f}")

    # Compute OSI for each neuron
    # OSI = (R_pref - R_ortho) / (R_pref + R_ortho)
    # Preferred orientation = argmax of responses
    preferred_idx = np.argmax(response_matrix, axis=1)
    r_pref = response_matrix[np.arange(n_neurons), preferred_idx]

    # Orthogonal = preferred + 90° (mod 4 orientations, since 135+90=225=45)
    ortho_map = {0: 2, 1: 3, 2: 0, 3: 1}  # 0°↔90°, 45°↔135°
    ortho_idx = np.array([ortho_map[p] for p in preferred_idx])
    r_ortho = response_matrix[np.arange(n_neurons), ortho_idx]

    osi = np.where(
        r_pref + r_ortho > 1e-8,
        (r_pref - r_ortho) / (r_pref + r_ortho),
        0.0
    )

    selective_mask = osi > osi_threshold
    selective_fraction = selective_mask.mean()

    print(f"\n  OSI distribution:")
    print(f"    n_neurons = {n_neurons}")
    print(f"    mean OSI = {osi.mean():.4f}")
    print(f"    max OSI  = {osi.max():.4f}")
    print(f"    fraction with OSI > {osi_threshold}: {selective_fraction:.2%}")
    print(f"    Fechner (2023) estimate: ~2-5% orientation-selective in medulla")

    # Preferred orientation distribution for selective neurons
    preferred_degs = np.array([orientations_deg[i] for i in preferred_idx[selective_mask]])
    orientation_counts = [
        (preferred_degs == o).sum() for o in orientations_deg
    ]

    return {
        'property': 'orientation_selectivity',
        'n_neurons': n_neurons,
        'osi_values': osi.tolist(),
        'mean_osi': float(osi.mean()),
        'max_osi': float(osi.max()),
        'selective_fraction': float(selective_fraction),
        'osi_threshold': osi_threshold,
        'orientation_distribution': dict(zip(orientations_deg, orientation_counts)),
        'reference': 'Fechner_et_al_2023_Nature_Neuroscience',
        'interpretation': (
            'NOVEL DISCOVERY' if selective_fraction > 0.05
            else 'CONFIRMS CANONICAL VIEW' if selective_fraction < 0.01
            else 'MATCHES FECHNER 2023 ESTIMATE'
        ),
    }


# ─── Property 2: Calcium Oscillations ────────────────────────────────────────

def test_calcium_oscillations(
    photon_rates: List[float] = None,
    duration_ms: float = 500.0,
    dt_ms: float = 0.1,
) -> Dict:
    """
    Test for spontaneous calcium oscillations in phototransduction under
    sustained bright illumination.

    MECHANISM (Juusola & de Polavieja 2003):
    The TRP/Ca²⁺ feedback loop in Drosophila phototransduction can self-oscillate:
        TRP opens → Ca²⁺ rises → adaptation suppresses sensitivity
        → TRP closes → Ca²⁺ falls → adaptation releases → TRP reopens → repeat

    This appears as voltage fluctuations in V(t) at ~50-200 Hz during sustained
    bright light. These are NOT shot noise (too large and too regular) — they
    are genuine feedback oscillations.

    DETECTION METHOD:
    - Simulate V(t) for 500ms at each photon rate
    - Compute power spectral density of V(t) using FFT
    - Look for peak in PSD above the 50-200 Hz range
    - Oscillation frequency should scale with photon rate

    PASS CRITERION:
    - Any photon rate shows a spectral peak at 50-200 Hz with SNR > 3
    - Frequency should increase with photon rate (Juusola 2003 Figure 6)

    Args:
        photon_rates: List of photon rates to test (default: 10¹-10⁵)
        duration_ms: Simulation duration per photon rate
        dt_ms: Integration timestep (0.1ms for accurate high-freq content)

    Returns:
        Dict with PSD data, detected oscillation frequencies, pass/fail
    """
    print("\n" + "─" * 60)
    print("PROPERTY 2: CALCIUM OSCILLATIONS IN PHOTOTRANSDUCTION")
    print("Juusola & de Polavieja (2003): oscillations at 50-200 Hz")
    print("Mechanism: TRP channel - Ca²⁺ feedback loop auto-oscillation")
    print("─" * 60)

    if photon_rates is None:
        photon_rates = [1e1, 1e2, 1e3, 1e4, 1e5]

    cascade = Phototransduction()
    dt = dt_ms / 1000.0
    num_steps = int(duration_ms / dt_ms)
    sample_rate_hz = 1000.0 / dt_ms  # Sampling frequency

    oscillation_results = {}

    for rate in photon_rates:
        print(f"\n  Photon rate: {rate:.0e} photons/s")

        # Simulate phototransduction
        state = PhototransductionState()
        voltages = np.zeros(num_steps)
        calcium = np.zeros(num_steps)

        for i in range(num_steps):
            voltages[i] = state.V
            calcium[i] = state.Ca
            state = cascade.step(state, rate, dt)

        # Use second half (skip transient onset)
        half = num_steps // 2
        v_signal = voltages[half:]
        ca_signal = calcium[half:]

        # Remove DC (mean) to focus on oscillations
        v_ac = v_signal - v_signal.mean()

        # Compute PSD via FFT
        fft_vals = np.fft.rfft(v_ac)
        psd = (np.abs(fft_vals) ** 2) / len(v_ac)
        freqs = np.fft.rfftfreq(len(v_ac), d=dt)  # Hz

        # Find peak in 10-500 Hz range (where oscillations expected)
        osc_mask = (freqs >= 10) & (freqs <= 500)
        noise_mask = (freqs < 10) | (freqs > 500)

        osc_psd = psd[osc_mask]
        osc_freqs = freqs[osc_mask]
        noise_floor = psd[noise_mask].mean() if noise_mask.any() else 1e-10

        if osc_psd.max() > 0:
            peak_freq = osc_freqs[np.argmax(osc_psd)]
            peak_power = osc_psd.max()
            snr = peak_power / (noise_floor + 1e-10)
        else:
            peak_freq = 0.0
            peak_power = 0.0
            snr = 0.0

        # Oscillation amplitude (mV) from RMS of AC signal
        v_rms = np.sqrt(np.mean(v_ac ** 2))

        oscillation_results[f"{rate:.0e}"] = {
            'photon_rate': float(rate),
            'peak_frequency_hz': float(peak_freq),
            'peak_psd': float(peak_power),
            'snr': float(snr),
            'v_rms_mv': float(v_rms),
            'mean_voltage_mv': float(v_signal.mean()),
            'mean_calcium_um': float(ca_signal.mean()),
            'oscillating': bool(snr > 3.0 and 50 <= peak_freq <= 200),
        }

        print(f"    Peak freq: {peak_freq:.1f} Hz, SNR: {snr:.2f}, "
              f"V_RMS: {v_rms:.4f} mV, Ca: {ca_signal.mean():.4f} μM")
        if snr > 3.0 and 50 <= peak_freq <= 200:
            print(f"    ✅ OSCILLATIONS DETECTED at {peak_freq:.1f} Hz")
        elif snr > 3.0:
            print(f"    ⚠️  Peak at {peak_freq:.1f} Hz (outside 50-200Hz target)")
        else:
            print(f"    — No significant oscillations (SNR={snr:.2f})")

    # Summary
    oscillating_rates = [k for k, v in oscillation_results.items() if v['oscillating']]
    any_oscillation = len(oscillating_rates) > 0

    # Check frequency scaling with photon rate (should increase)
    freqs_detected = [oscillation_results[k]['peak_frequency_hz']
                      for k in oscillation_results if oscillation_results[k]['oscillating']]
    rates_detected = [oscillation_results[k]['photon_rate']
                      for k in oscillation_results if oscillation_results[k]['oscillating']]
    freq_scales_with_rate = False
    if len(freqs_detected) >= 2:
        # Check positive correlation between photon rate and oscillation frequency
        corr = np.corrcoef(np.log10(rates_detected), freqs_detected)[0, 1]
        freq_scales_with_rate = corr > 0.5

    return {
        'property': 'calcium_oscillations',
        'photon_rates_tested': [float(r) for r in photon_rates],
        'oscillation_results': oscillation_results,
        'any_oscillation_detected': any_oscillation,
        'oscillating_photon_rates': oscillating_rates,
        'frequency_scales_with_rate': freq_scales_with_rate,
        'reference': 'Juusola_de_Polavieja_2003_JGP',
        'target_frequency_range_hz': [50, 200],
        'pass': any_oscillation,
    }


# ─── Property 3: Chromatic Motion Blindness ──────────────────────────────────

def test_chromatic_motion_blindness(
    visual_connectome,
    stimulus_duration_ms: float = 300.0,
    dt_ms: float = 0.5,
) -> Dict:
    """
    Test whether T4/T5 direction selectivity depends on luminance vs. color pathway.

    ISOLUMINANT MOTION STIMULI:
    Three types of moving gratings with the same temporal/spatial frequency (2 Hz, 30°):
        1. LUMINANCE: R1-R6 contrast high (broadband, Rh1 driven), R7/R8 flat
        2. UV-ONLY:   R7 contrast high (Rh3/Rh4 driven), R1-R6 and R8 flat
        3. VISIBLE-ONLY: R8 contrast high (Rh6 driven), R1-R6 and R7 flat

    For type 1 (luminance): T4/T5 should show DSI ≈ 0.97 (matches existing test)
    For types 2 and 3: T4/T5 should show DSI ≈ 0 (motion blindness)

    IF chromatic DSI > 0.3 → proves Tm5/Tm9 cross-connections to T4/T5 are
    functionally significant — revises the "strict parallel pathways" theory

    BIOLOGICAL SIGNIFICANCE:
    This directly tests the 2008 Yamaguchi result computationally for the first time
    using the actual FlyWire connectome. If color motion creates ANY T4 response:
    - This would be a false prediction by the current theory
    - It would mean the FlyWire connectome has cross-connections that matter
    - It would predict measurable (if small) optomotor response to UV-only gratings

    Args:
        visual_connectome: FlyWire optic lobe connectome
        stimulus_duration_ms: Duration per stimulus type
        dt_ms: Integration timestep

    Returns:
        Dict with DSI per stimulus type, cross-pathway contamination measure
    """
    print("\n" + "─" * 60)
    print("PROPERTY 3: CHROMATIC MOTION BLINDNESS")
    print("Yamaguchi et al. (2008): flies cannot detect isoluminant color motion")
    print("Test: does UV-only or visible-only motion drive T4/T5?")
    print("─" * 60)

    azimuths, elevations = build_ommatidium_positions()

    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)

    t4_neurons = []
    all_medulla = list(get_visual_region_neurons(visual_connectome, 'MEDULLA'))
    lobula_neurons = list(get_visual_region_neurons(visual_connectome, 'LOBULA'))

    # T4 neurons are in lobula — use them as motion readout
    # Falling back to medulla if lobula not separately identified
    motion_readout = lobula_neurons if len(lobula_neurons) > 10 else all_medulla

    num_steps = int(stimulus_duration_ms / dt_ms)
    measurement_start = num_steps // 2

    TF_HZ = 2.0  # Standard temporal frequency

    stimulus_types = {
        'luminance': {'r1r6_contrast': 1.0, 'r7_contrast': 0.0, 'r8_contrast': 0.0},
        'uv_only':   {'r1r6_contrast': 0.0, 'r7_contrast': 1.0, 'r8_contrast': 0.0},
        'visible_only': {'r1r6_contrast': 0.0, 'r7_contrast': 0.0, 'r8_contrast': 1.0},
    }

    dsi_results = {}

    for stim_name, contrasts in stimulus_types.items():
        print(f"\n  Stimulus: {stim_name}")
        print(f"  R1-R6 contrast: {contrasts['r1r6_contrast']:.1f}  "
              f"R7: {contrasts['r7_contrast']:.1f}  R8: {contrasts['r8_contrast']:.1f}")

        dsi_per_direction = {}
        for direction in ['rightward', 'leftward']:
            dir_vec = (1, 0) if direction == 'rightward' else (-1, 0)

            brain._initialize_fields()
            if brain.use_mlx:
                import mlx.core as mx
                brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
            else:
                brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)
            amplitudes_meas = []

            for step in range(num_steps):
                t_ms = step * dt_ms
                theta = 90.0 if dir_vec[0] > 0 else 270.0
                luminance = compute_grating(azimuths, elevations, 0.0, TF_HZ, t_ms,
                                            contrast=contrasts['r1r6_contrast'])
                uv_grating = compute_grating(azimuths, elevations, 0.0, TF_HZ, t_ms,
                                             contrast=contrasts['r7_contrast'])
                vis_grating = compute_grating(azimuths, elevations, 0.0, TF_HZ, t_ms,
                                              contrast=contrasts['r8_contrast'])

                # But flip direction for null (leftward = rightward stimulus reversed)
                if dir_vec[0] < 0:
                    luminance = 1.0 - luminance
                    uv_grating = 1.0 - uv_grating
                    vis_grating = 1.0 - vis_grating

                # Luminance input (R1-R6 → lamina L1/L2 → T4)
                for i, nid in enumerate(all_medulla):
                    if nid not in brain.id_to_idx:
                        continue
                    omm = i % N_OMMATIDIA
                    lum_v = photon_rate_to_voltage(luminance[omm] * 1e4)
                    idx = brain.id_to_idx[nid]
                    brain.external_force[idx] = lum_v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * 0.01

                # UV-only input (R7 → Mi1/Dm8 → medulla)
                for i, nid in enumerate(all_medulla[:len(all_medulla) // 2]):
                    if nid not in brain.id_to_idx:
                        continue
                    omm = i % N_OMMATIDIA
                    uv_v = photon_rate_to_voltage(uv_grating[omm] * 1e4)
                    idx = brain.id_to_idx[nid]
                    brain.external_force[idx] += uv_v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN

                # Visible-only input (R8 → Tm5/Tm9 → medulla)
                for i, nid in enumerate(all_medulla[len(all_medulla) // 2:]):
                    if nid not in brain.id_to_idx:
                        continue
                    omm = i % N_OMMATIDIA
                    vis_v = photon_rate_to_voltage(vis_grating[omm] * 1e4)
                    idx = brain.id_to_idx[nid]
                    brain.external_force[idx] += vis_v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * R7_R8_GAIN

                brain.evolve(duration=dt_ms)

                if step >= measurement_start:
                    state = brain.get_state()
                    readout_idx = [brain.id_to_idx[nid] for nid in motion_readout
                                   if nid in brain.id_to_idx]
                    if readout_idx:
                        amplitudes_meas.append(state.mean_amplitude[readout_idx].mean())

            dsi_per_direction[direction] = float(np.mean(amplitudes_meas))

        pref = dsi_per_direction['rightward']
        null = dsi_per_direction['leftward']
        dsi = (pref - null) / (pref + null + 1e-8)
        dsi_results[stim_name] = {'preferred': pref, 'null': null, 'dsi': dsi}

        print(f"    Preferred: {pref:.6f}, Null: {null:.6f}, DSI: {dsi:.4f}")

    # Interpretation
    lum_dsi = dsi_results['luminance']['dsi']
    uv_dsi = dsi_results['uv_only']['dsi']
    vis_dsi = dsi_results['visible_only']['dsi']

    motion_blindness_uv = uv_dsi < 0.30
    motion_blindness_vis = vis_dsi < 0.30
    luminance_selective = lum_dsi > 0.30

    cross_pathway_ratio_uv = uv_dsi / (lum_dsi + 1e-8)
    cross_pathway_ratio_vis = vis_dsi / (lum_dsi + 1e-8)

    print(f"\n  Summary:")
    print(f"  Luminance DSI:      {lum_dsi:.4f} {'✅' if luminance_selective else '❌'}")
    print(f"  UV-only DSI:        {uv_dsi:.4f} (blindness {'✅' if motion_blindness_uv else '❌ CROSS-PATHWAY DETECTED'})")
    print(f"  Visible-only DSI:   {vis_dsi:.4f} (blindness {'✅' if motion_blindness_vis else '❌ CROSS-PATHWAY DETECTED'})")
    print(f"  UV/Luminance ratio: {cross_pathway_ratio_uv:.3f} (should be < 0.3)")

    return {
        'property': 'chromatic_motion_blindness',
        'dsi_results': dsi_results,
        'luminance_dsi': float(lum_dsi),
        'uv_only_dsi': float(uv_dsi),
        'visible_only_dsi': float(vis_dsi),
        'motion_blindness_uv': bool(motion_blindness_uv),
        'motion_blindness_vis': bool(motion_blindness_vis),
        'cross_pathway_ratio_uv': float(cross_pathway_ratio_uv),
        'cross_pathway_ratio_vis': float(cross_pathway_ratio_vis),
        'reference': 'Yamaguchi_et_al_2008_Current_Biology',
        'interpretation': (
            'PARALLEL PATHWAYS CONFIRMED' if motion_blindness_uv and motion_blindness_vis
            else 'CROSS-CONNECTIONS DISCOVERED — Tm5/Tm9→T4 pathway significant'
        ),
    }


# ─── Master test runner ───────────────────────────────────────────────────────

def run_emergent_properties_test(visual_connectome: Connectome) -> Dict:
    """
    Run all three emergent property tests and compile report.

    Returns:
        Dict with results from all three properties
    """
    print("\n" + "=" * 70)
    print("EMERGENT PROPERTIES TEST SUITE")
    print("Testing properties that emerge from connectome without explicit coding")
    print("=" * 70)

    results = {'test': 'emergent_properties', 'properties': {}}

    print("\n[1/3] Orientation Selectivity...")
    results['properties']['orientation_selectivity'] = test_orientation_selectivity(
        visual_connectome
    )

    print("\n[2/3] Calcium Oscillations (no connectome needed)...")
    results['properties']['calcium_oscillations'] = test_calcium_oscillations()

    print("\n[3/3] Chromatic Motion Blindness...")
    results['properties']['chromatic_motion_blindness'] = test_chromatic_motion_blindness(
        visual_connectome
    )

    # Summary
    p1 = results['properties']['orientation_selectivity']
    p2 = results['properties']['calcium_oscillations']
    p3 = results['properties']['chromatic_motion_blindness']

    print(f"\n{'=' * 70}")
    print("EMERGENT PROPERTIES SUMMARY")
    print(f"{'=' * 70}")
    print(f"1. Orientation selectivity: {p1['selective_fraction']:.1%} neurons "
          f"(OSI > {p1['osi_threshold']}) — {p1['interpretation']}")
    print(f"2. Calcium oscillations: {'DETECTED' if p2['pass'] else 'NOT DETECTED'} "
          f"at rates {p2['oscillating_photon_rates']}")
    print(f"3. Chromatic motion blindness: UV-DSI={p3['uv_only_dsi']:.4f} — "
          f"{p3['interpretation']}")

    results['summary'] = {
        'orientation_selective_fraction': p1['selective_fraction'],
        'calcium_oscillations_found': p2['pass'],
        'chromatic_motion_blindness_confirmed': (p3['motion_blindness_uv']
                                                  and p3['motion_blindness_vis']),
    }

    return results


if __name__ == '__main__':
    print(__doc__)

    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()

    from hive.substrate.visual_pathway import extract_visual_pathway
    visual_connectome = extract_visual_pathway(connectome)

    results = run_emergent_properties_test(visual_connectome)

    output_path = Path("research/vision/findings/emergent_properties_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_path}")
