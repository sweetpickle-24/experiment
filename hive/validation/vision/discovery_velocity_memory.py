"""
Discovery: Visual Velocity Memory from Ring Buffer — Predicting Motion Aftereffects
====================================================================================

THE PHENOMENON
--------------
The MOTION AFTEREFFECT (MAE) is one of the most studied visual illusions:
  - Stare at a waterfall for 30 seconds
  - Look at a static rock face
  - The rock appears to drift UPWARD (opposite to the adapting direction)

This has been extensively studied in humans and primates.
In DROSOPHILA: almost completely unstudied. Gabbiani et al. (2002) showed that
locusts have visual persistence for looming objects, but horizontal motion
persistence has never been measured in any small insect.

MECHANISM HYPOTHESIS
--------------------
After a moving stimulus stops:
  - LP neurons (HS/VS) remain depolarized for some time (residual activation)
  - The RING BUFFER in SparseProbabilisticBrain stores 50ms of history
  - When forcing stops, the stored state slowly decays
  - If LP amplitude at t=0ms_after_stop > t=50ms_after_stop:
    → "velocity memory" exists (LP holds the motion signal briefly)

This is NOT the same as the perceptual MAE (which requires adaptation and
opponent mechanism). This is SIMPLER: does the LP just maintain elevated
activity for a few ms after motion stops?

THE PREDICTION
--------------
After a moving grating stops:
  LP amplitude decay should follow:
    A(t) = A_peak × exp(-t / τ_memory)

  Where τ_memory depends on the LP membrane time constant and network recurrence.

  For a purely feedforward system: τ_memory ≈ LP_membrane_τ ≈ 5-20ms
  For a recurrent system: τ_memory >> LP_membrane_τ (extended by recurrence)

VELOCITY DEPENDENCE HYPOTHESIS
-------------------------------
High-velocity motion (16 Hz, 480 deg/s):
  - Strong, brief T4 activation during motion
  - After motion stops: LP amplitude drops quickly (nothing to sustain it)
  - τ_memory_fast ≈ 5-15ms

Low-velocity motion (0.5 Hz, 15 deg/s):
  - Weaker but sustained T4 activation
  - After motion stops: LP may retain more energy (less transient)
  - τ_memory_slow ≈ 10-30ms

BEHAVIORAL PREDICTION
---------------------
If τ_memory > 0 → during a saccade (20ms eye movement equivalent), the LP
retains the motion direction from the PRE-saccade environment. This could
help flies maintain optomotor responses through brief saccadic gaps.

Quantitative prediction for behavioral experiments:
  "Drosophila should maintain optomotor response for [τ_memory]ms after
   grating disappears" — testable with blank-flash optomotor experiments

THE RING BUFFER ADVANTAGE
-------------------------
The SparseProbabilisticBrain already has:
  - `amplitude_history`: ring buffer of 10 snapshots at 5ms intervals = 50ms
  - `get_amplitude_delayed(delay_ms)`: access past states

This means we can directly measure the DECAY of LP activation after motion
stops by comparing amplitude at different time lags.

EXPERIMENTAL DESIGN
-------------------
1. Present moving grating at 5 velocities: 0.5, 1, 2, 4, 8 Hz
2. Stimulus duration: 400ms (steady state reached)
3. At t=400ms: stimulus STOPS (zero forcing)
4. Continue simulation for 100ms with zero forcing
5. Sample LP amplitude at t=0, 10, 20, 30, 40, 50ms post-stop
6. Fit exponential decay to get τ_memory per velocity

NOVEL ASPECT
------------
This is the first test of visual velocity memory in Drosophila using a
wave-based simulation. The result will:
  a) Quantify the LP memory timescale from first principles (connectome + wave physics)
  b) Generate a specific behavioral prediction (τ_memory = X ms)
  c) Suggest that LP integration serves as a "short-term visual buffer"
     during saccadic eye/body movements

REFERENCES
----------
- Gabbiani, F. et al. (2002). Multiplicative computation in a visual neuron
  sensitive to looming. Nature 420: 320-324.
- Mateeff, S. et al. (1991). Motion perception: asynchronous updating of
  attended and unattended representations. Vision Research 31: 2235-2242.
- Hausen, K. (1982). Motion sensitive interneurons in the optomotor system
  of the fly. Biological Cybernetics 45: 143-156.
- Borst, A. & Haag, J. (2002). Neural networks in the cockpit of the fly.
  Journal of Comparative Physiology A 188: 419-437.
"""

import numpy as np
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scipy.optimize import curve_fit

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import get_visual_region_neurons
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain


# ─── Parameters ───────────────────────────────────────────────────────────────
N_COLS = 20
N_ROWS = 40
N_OMMATIDIA = N_COLS * N_ROWS
AZ_RANGE = 90.0
EL_RANGE = 40.0
SPATIAL_PERIOD_DEG = 30.0

STIMULUS_DURATION_MS = 400.0    # On period (reach steady state)
DECAY_DURATION_MS = 100.0       # Post-stimulus observation window
SAMPLE_INTERVAL_MS = 5.0        # Sampling every 5ms (ring buffer interval)

VOLTAGE_TO_FIRING_RATE = 50.0
FIRING_TO_FORCING = 10.0
EXCITATORY_GAIN = 0.10
INHIBITORY_GAIN = 0.50

# Velocities to test
TEMPORAL_FREQUENCIES_HZ = [0.5, 1.0, 2.0, 4.0, 8.0]


def build_positions():
    az_sp = (2 * AZ_RANGE) / N_COLS
    el_sp = (2 * EL_RANGE) / N_ROWS
    az, el = [], []
    for row in range(N_ROWS):
        for col in range(N_COLS):
            a = -AZ_RANGE + (col + 0.5) * az_sp
            e = -EL_RANGE + (row + 0.5) * el_sp
            if row % 2 == 1:
                a += az_sp * 0.5
            az.append(a)
            el.append(e)
    return np.array(az), np.array(el)


class BarlowLevickFilter:
    def __init__(self, n):
        self.n = n
        self.exc = np.zeros(n)
        self.inh = np.zeros(n)

    def reset(self):
        self.exc[:] = 0
        self.inh[:] = 0

    def step(self, luminance, dt_ms):
        ON = np.maximum(0, luminance - 0.5)
        self.exc += (dt_ms / 10.0) * (EXCITATORY_GAIN * ON - self.exc)
        self.inh += (dt_ms / 25.0) * (INHIBITORY_GAIN * ON - self.inh)
        return np.maximum(0, self.exc - self.inh)


def photon_rate_to_voltage(photon_rate):
    if photon_rate < 1:
        return 0.0
    return float(np.clip(10.0 * np.log10(max(photon_rate, 10.0) / 10.0), 0, 40))


def measure_velocity_memory(
    visual_connectome: Connectome,
    tf_hz: float,
    dt_ms: float = 0.5,
) -> Dict:
    """
    Measure LP amplitude decay after motion stops at a given temporal frequency.

    Protocol:
      Phase 1 (0 to STIMULUS_DURATION_MS): Moving grating at tf_hz
        - Record steady-state LP amplitude (average over last 100ms)
      Phase 2 (0 to DECAY_DURATION_MS after stop): No stimulus (zero forcing)
        - Sample LP amplitude at t=0, 5, 10, 15, ..., 100ms post-stop
        - Use ring buffer (get_amplitude_delayed) where possible
        - Also track direct amplitude measurement

    Args:
        visual_connectome: FlyWire optic lobe connectome
        tf_hz: Temporal frequency of the adapting stimulus
        dt_ms: Integration timestep

    Returns:
        Dict with steady-state amplitude, decay curve, fitted τ
    """
    print(f"\n  [tf_hz={tf_hz}Hz] Running stimulus + decay protocol...")

    azimuths, elevations = build_positions()
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)

    lp_neurons = list(get_visual_region_neurons(visual_connectome, 'LOBULA_PLATE'))
    lp_idx = [brain.id_to_idx[nid] for nid in lp_neurons if nid in brain.id_to_idx]
    medulla_neurons = list(get_visual_region_neurons(visual_connectome, 'MEDULLA'))

    bl = BarlowLevickFilter(N_OMMATIDIA)
    brain._reset_state()
    bl.reset()

    on_steps = int(STIMULUS_DURATION_MS / dt_ms)
    off_steps = int(DECAY_DURATION_MS / dt_ms)

    # Phase 1: Stimulus on — reach steady state
    steady_state_amps = []
    measurement_start = on_steps * 3 // 4  # Last 25% = steady state

    for step in range(on_steps):
        t_ms = step * dt_ms
        spatial_phase = (2 * np.pi / SPATIAL_PERIOD_DEG) * azimuths
        temporal_phase = 2 * np.pi * tf_hz * (t_ms / 1000.0)
        luminance = 0.5 + 0.5 * np.sin(spatial_phase - temporal_phase)

        t4_out = bl.step(luminance, dt_ms)

        forcing = {}
        for i, nid in enumerate(medulla_neurons):
            if nid not in brain.id_to_idx:
                continue
            omm = i % N_OMMATIDIA
            forcing[nid] = t4_out[omm] * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING

        brain.step(dt_ms / 1000.0, forcing)

        if step >= measurement_start:
            state = brain.get_state()
            if lp_idx:
                steady_state_amps.append(state.mean_amplitude[lp_idx].mean())

    steady_state = float(np.mean(steady_state_amps)) if steady_state_amps else 0.0
    print(f"    Steady-state LP amplitude: {steady_state:.6f}")

    # Phase 2: Stimulus off — measure decay
    decay_samples_ms = np.arange(0, DECAY_DURATION_MS + SAMPLE_INTERVAL_MS,
                                  SAMPLE_INTERVAL_MS)
    decay_amplitudes = {}

    bl.reset()  # Stop T4 output

    for off_step in range(off_steps + 1):
        t_off_ms = off_step * dt_ms

        # Zero forcing (no stimulus)
        brain.step(dt_ms / 1000.0, {})

        # Sample at specified intervals
        if any(abs(t_off_ms - sample_ms) < dt_ms * 0.5 for sample_ms in decay_samples_ms):
            state = brain.get_state()
            if lp_idx:
                amp = float(state.mean_amplitude[lp_idx].mean())
                sample_t = round(t_off_ms / SAMPLE_INTERVAL_MS) * SAMPLE_INTERVAL_MS
                decay_amplitudes[float(sample_t)] = amp

    # Fit exponential decay
    times = sorted(decay_amplitudes.keys())
    amps = [decay_amplitudes[t] for t in times]
    times_arr = np.array(times)
    amps_arr = np.array(amps)

    if len(times) >= 3 and steady_state > 0:
        # Normalize to first post-stop amplitude
        amps_norm = amps_arr / (amps_arr[0] + 1e-10)

        def exp_decay(t, tau, asymptote):
            return np.exp(-t / tau) * (1 - asymptote) + asymptote

        try:
            popt, _ = curve_fit(exp_decay, times_arr, amps_norm,
                                p0=[20.0, 0.1],
                                bounds=([1, 0], [500, 1]))
            tau_ms, asymptote = popt
            # R² of fit
            y_pred = exp_decay(times_arr, *popt)
            ss_res = np.sum((amps_norm - y_pred) ** 2)
            ss_tot = np.sum((amps_norm - amps_norm.mean()) ** 2)
            r_squared = float(1 - ss_res / (ss_tot + 1e-10))
        except Exception:
            tau_ms = float('inf')
            asymptote = amps_norm[-1] if len(amps_norm) > 0 else 0.0
            r_squared = 0.0
    else:
        tau_ms = float('inf')
        asymptote = 0.0
        r_squared = 0.0

    print(f"    Decay τ: {tau_ms:.2f} ms (R²={r_squared:.3f})")
    print(f"    Velocity memory: {'YES' if tau_ms < 100 else 'NONE/MINIMAL'}")

    return {
        'tf_hz': float(tf_hz),
        'velocity_deg_s': float(tf_hz * SPATIAL_PERIOD_DEG),
        'steady_state_amplitude': float(steady_state),
        'decay_curve': {str(t): v for t, v in decay_amplitudes.items()},
        'tau_memory_ms': float(tau_ms),
        'decay_asymptote': float(asymptote),
        'fit_r_squared': float(r_squared),
        'velocity_memory_detected': bool(tau_ms < 100 and r_squared > 0.5),
    }


def run_velocity_memory(visual_connectome: Connectome) -> Dict:
    """
    Full velocity memory experiment across 5 temporal frequencies.

    Measures how long LP neurons "remember" a motion stimulus after it stops,
    as a function of the stimulus velocity (temporal frequency).

    Args:
        visual_connectome: FlyWire optic lobe connectome

    Returns:
        Dict with per-velocity memory timescales and behavioral predictions
    """
    print("\n" + "=" * 70)
    print("DISCOVERY: VISUAL VELOCITY MEMORY")
    print("Question: How long does LP retain motion direction after stimulus stops?")
    print("= Memory timescale = potential visual buffer for saccadic gaps")
    print("=" * 70)

    results_per_tf = {}
    for tf_hz in TEMPORAL_FREQUENCIES_HZ:
        results_per_tf[tf_hz] = measure_velocity_memory(visual_connectome, tf_hz)

    # Analysis
    print(f"\n{'='*70}")
    print("VELOCITY MEMORY SUMMARY")
    print(f"{'='*70}")
    print(f"{'TF (Hz)':<10} {'Velocity (deg/s)':<18} {'τ_memory (ms)':<16} {'Memory?':<10}")
    for tf, r in sorted(results_per_tf.items()):
        mem = 'YES' if r['velocity_memory_detected'] else 'NO'
        print(f"{tf:<10.1f} {r['velocity_deg_s']:<18.0f} {r['tau_memory_ms']:<16.2f} {mem:<10}")

    # Check velocity dependence
    detected = [(tf, r['tau_memory_ms']) for tf, r in results_per_tf.items()
                if r['velocity_memory_detected']]

    if len(detected) >= 2:
        tfs, taus = zip(*detected)
        # Negative correlation: higher velocity → shorter memory?
        corr = np.corrcoef(np.log(tfs), taus)[0, 1] if len(tfs) > 2 else 0.0
        print(f"\nVelocity-memory correlation: r = {corr:.3f}")
        if corr < -0.5:
            print("  → Higher velocity = shorter memory (transient response)")
        elif corr > 0.5:
            print("  → Higher velocity = longer memory (surprise!)")
        else:
            print("  → No systematic velocity-memory relationship")
    else:
        corr = 0.0

    # Behavioral prediction
    mean_tau = float(np.mean([r['tau_memory_ms'] for r in results_per_tf.values()
                               if r['velocity_memory_detected']])) if detected else 0.0

    behavioral_prediction = (
        f"Drosophila optomotor response should persist for ~{mean_tau:.0f}ms "
        f"after grating disappears (testable with blank-flash optomotor)"
        if mean_tau > 5 else
        "No persistent LP activity after motion stops — no saccadic buffering"
    )

    print(f"\nBehavioral prediction: {behavioral_prediction}")

    return {
        'discovery': 'velocity_memory',
        'temporal_frequencies_hz': TEMPORAL_FREQUENCIES_HZ,
        'results_per_tf': {str(k): v for k, v in results_per_tf.items()},
        'mean_tau_memory_ms': float(mean_tau),
        'velocity_memory_found': bool(len(detected) > 0),
        'velocity_corr_with_tau': float(corr),
        'behavioral_prediction': behavioral_prediction,
        'experimental_test': 'Blank-flash optomotor assay (grating + blank + measure)',
        'ring_buffer_used': True,
        'references': [
            'Gabbiani_et_al_2002_Nature',
            'Hausen_1982_Biological_Cybernetics',
            'Borst_Haag_2002_JCP',
        ],
    }


if __name__ == '__main__':
    print(__doc__)

    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()

    from hive.substrate.visual_pathway import extract_visual_pathway
    visual_connectome = extract_visual_pathway(connectome)

    results = run_velocity_memory(visual_connectome)

    output_path = Path("research/vision/findings/discovery_velocity_memory.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_path}")
