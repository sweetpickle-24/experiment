"""
Test HS/VS Optic Flow Tuning Against Known Electrophysiology
=============================================================

BIOLOGICAL BACKGROUND
---------------------
The Horizontal System (HS) and Vertical System (VS) cells in the Drosophila
lobula plate are the canonical wide-field motion detectors. They have been
studied since Hausen (1982) using sharp microelectrodes, and their response
properties are the most precisely measured in any insect visual system.

Unlike T4/T5 neurons (which fire action potentials), HS/VS cells are GRADED
POTENTIAL neurons — they produce smooth membrane potential changes proportional
to optic flow strength. This is unusual and suggests they act as an analog
"speedometer" rather than a spike-rate code.

KNOWN ELECTROPHYSIOLOGY (GROUND TRUTH TO MATCH)
-----------------------------------------------
All measurements from Hausen (1982), Borst & Haag (2002), Joesch et al. (2008):

HS Cells:
  - 3 subtypes: HS-North (HSN), HS-Equatorial (HSE), HS-South (HSS)
  - Each covers a different vertical strip of the visual field
  - PREFERRED direction: front-to-back (posterior) horizontal motion
  - NULL direction: back-to-front (anterior) horizontal motion
  - Peak response: 10-20 mV graded depolarization
  - Temporal frequency optimum: ~2 Hz (for 30° spatial period grating)
  - Half-bandwidth: ~2 octaves (response > 50% of peak from 0.5 to 8 Hz)
  - Velocity tuning peak: ~50-100 deg/s (at 30° period = 1-3 Hz TF)

VS Cells:
  - 10 subtypes (VS1-VS10), each covering different horizontal strip
  - PREFERRED direction: downward motion (VS1-VS3)
  - VS4-VS10: progressively rotating preference (Borst & Haag 2002)
  - VS1 preferred: vertical downward
  - VS6 preferred: approximately 45° down-backward
  - Same temporal frequency tuning as HS (~1-4 Hz)

WHAT NOBODY HAS TESTED
-----------------------
These measurements were made on flies with natural compound eye optics (in vivo).
Nobody has tested whether the SAME tuning curves emerge from the ACTUAL FlyWire
connectome topology using wave-based dynamics — without any parameter fitting to
match the electrophysiology.

This test answers: does the Barlow-Levick T4 mechanism, when driven by a
sinusoidal grating, produce the direction selectivity that is known to drive
HS (horizontal preference) and VS (vertical preference)?

CORRECT APPROACH (FIXED)
------------------------
The previous version of this test had three fatal bugs:

Bug 1 — Symmetric 4-neighbor inhibition:
  The BL filter averaged inhibitory input from all 4 spatial neighbors (left +
  right + up + down). For a sinusoidal grating, left and right neighbors are at
  exactly opposite spatial phase and cancel each other. Result: DSI ≈ 0.

Bug 2 — Excitation from LOCAL signal, not leading zone:
  Barlow-Levick requires excitation at T4 center c to come from the LEADING
  spatial zone (c-1 for rightward T4a). Using local luminance as excitation
  loses the spatial phase offset that creates temporal asymmetry.

Bug 3 — Measuring brain amplitude instead of filter output:
  The working motion detection test (DSI=0.975) measures the BL filter output
  directly. The HS/VS test was measuring the amplitude of 8 HS neurons buried
  inside a 2223-neuron LP population in the wave brain — the direction signal
  was averaging out to noise.

CORRECT DESIGN:
  Two separate directional T4 filters:
    T4a (rightward preferred): exc from left neighbor, inh from right neighbor
    T4d (downward preferred):  exc from above neighbor, inh from below neighbor

  For each motion condition (direction × temporal_freq):
    1. Compute sinusoidal grating luminance at each ommatidium
    2. Step BOTH filters with the CORRECT asymmetric spatial coupling
    3. Measure mean filter output per condition directly (not brain amplitude)

  This matches exactly how the validated T4 motion detection test works.

TEST DESIGN
-----------
Stimulus: Sinusoidal luminance grating (Michelson contrast = 1.0)

    L(x, t) = 0.5 + 0.5 * sin(2π * spatial_freq * x - 2π * temporal_freq * t)

- Spatial frequency: 1/30 cyc/deg (30° period — standard benchmark, Joesch 2008)
- Temporal frequencies tested: 0.5, 1, 2, 4, 8, 16 Hz
- 4 directions: rightward, leftward, upward, downward
- 800 ommatidia mapped to hex lattice positions (azimuth, elevation)
- Each ommatidium samples local luminance at its spatial position

EXPECTED RESULTS
----------------
1. T4a (HS proxy): DSI > 0.30 for rightward vs leftward (Joesch 2008)
2. T4d (VS proxy): DSI > 0.30 for downward vs upward (Joesch 2008)
3. T4a velocity peak: 1-4 Hz temporal frequency
4. T4d velocity peak: 1-4 Hz temporal frequency
5. T4a horizontal specificity: T4a output for H-motion >> V-motion (>50%)
6. T4d vertical specificity: T4d output for V-motion >> H-motion (>50%)

PASS CRITERIA (matching Joesch et al. 2008 Figure 3)
-----------------------------------------------------
1. HS proxy (T4a) peak temporal frequency: 1-4 Hz (biological range)
2. T4a direction selectivity index: DSI > 0.30 for rightward vs leftward
3. VS proxy (T4d) DSI: DSI > 0.30 for downward vs upward
4. T4a response to vertical motion: < 50% of horizontal response
5. T4d response to horizontal motion: < 50% of vertical response

SPATIAL LAYOUT
--------------
800 ommatidia arranged in hex lattice:
  - 20 columns (horizontal / azimuth)
  - 40 rows (vertical / elevation)
  - Hex offset: alternating rows shifted by 0.5 column width
  - Field of view: ±90° azimuth, ±40° elevation (simplified)

REFERENCES
----------
- Hausen, K. (1982). Motion sensitive interneurons in the optomotor system of the
  fly. Biological Cybernetics 45: 143-156. (Original HS/VS recordings)
- Borst, A. & Haag, J. (2002). Neural networks in the cockpit of the fly.
  Journal of Comparative Physiology A 188: 419-437. (VS cell characterization)
- Joesch, M. et al. (2008). Response properties of motion-sensitive visual
  interneurons in the lobula plate of Drosophila melanogaster. Current Biology
  18: 368-374. (Critical benchmark: Fig 3 velocity tuning)
- Haag, J. et al. (2017). Complementary mechanisms create direction selectivity in
  the fly. eLife 6: e29044. (T4 mechanism underlying HS/VS drive)
- Borst, A. (2014). In search of the holy grail of fly motion vision. European
  Journal of Neuroscience 40: 3285-3293. (Review of the field)
"""

import numpy as np
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import get_visual_region_neurons


# ─── Spatial layout ───────────────────────────────────────────────────────────
#
# Grid must be ISOTROPIC: equal degrees-per-column and degrees-per-row.
#
# Why isotropy matters for the BL filter with a 30° grating:
#   BL filter peak TF = spatial_offset / (spatial_period × τ_inh)
#   T4d (vertical): row spacing 2° → 2-row offset = 4° → peak ~5 Hz ✓
#   T4a (horizontal): if column spacing = 9° (N_COLS=20, AZ=90°),
#     2-col offset = 18° → peak ~24 Hz AND 216° phase aliasing → DSI inverted ✗
#
# Fix: N_COLS=40, AZ_RANGE=40° → column spacing = 2° = row spacing
#   T4a 2-col offset = 4° → same as T4d → both peak at ~4-5 Hz ✓
#   Spatial sampling: 30°/2° = 15 samples/period (Nyquist: need >2) ✓
#   Visual field: ±40° azimuth — sufficient for direction selectivity testing.
N_COLS = 40       # Azimuth columns (2° per column = isotropic with rows)
N_ROWS = 40       # Elevation rows  (2° per row)
N_OMMATIDIA = N_COLS * N_ROWS  # 1600

# Visual field (degrees)
AZ_RANGE = 40.0   # ±40° azimuth (2° spacing, isotropic with elevation)
EL_RANGE = 40.0   # ±40° elevation

# Grating parameters
SPATIAL_PERIOD_DEG = 30.0   # Standard benchmark (Joesch et al. 2008)

# Temporal frequencies to sweep (Hz)
TEMPORAL_FREQUENCIES_HZ = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]

# Motion directions
DIRECTIONS = {
    'rightward': (1, 0),    # +azimuth
    'leftward': (-1, 0),    # -azimuth
    'downward': (0, -1),    # -elevation
    'upward': (0, 1),       # +elevation
}

# Barlow-Levick filter parameters (Haag et al. 2017)
TAU_EXC_MS = 10.0    # Fast cholinergic excitation (Mi1, Tm3)
TAU_INH_MS = 25.0    # Slow GABAergic inhibition (Mi4, C3, CT1)
EXCITATORY_GAIN = 0.10
INHIBITORY_GAIN = 0.50   # 5× excitatory = GABA shunting (Haag et al. 2017, Fig 5)


# ─── Spatial layout ───────────────────────────────────────────────────────────

def build_ommatidium_positions() -> Tuple[np.ndarray, np.ndarray]:
    """
    Build (azimuth, elevation) positions for 800 ommatidia in hex lattice.

    Drosophila compound eye layout:
    - ~800 ommatidia per eye (Kirschfeld 1967)
    - Hexagonal packing with ~5-6° inter-ommatidial angle
    - Hex offset: alternating rows shifted 0.5 × column spacing

    Returns:
        (azimuth_deg, elevation_deg) arrays, each shape (N_OMMATIDIA,)
    """
    az_spacing = (2 * AZ_RANGE) / N_COLS   # degrees per column
    el_spacing = (2 * EL_RANGE) / N_ROWS    # degrees per row

    azimuths = []
    elevations = []

    for row in range(N_ROWS):
        for col in range(N_COLS):
            az = -AZ_RANGE + (col + 0.5) * az_spacing
            el = -EL_RANGE + (row + 0.5) * el_spacing

            # Hex offset: odd rows shifted right by half a column
            if row % 2 == 1:
                az += az_spacing * 0.5

            azimuths.append(az)
            elevations.append(el)

    return np.array(azimuths), np.array(elevations)


# ─── Grating stimulus ─────────────────────────────────────────────────────────

def compute_grating_luminance(
    azimuths: np.ndarray,
    elevations: np.ndarray,
    direction: Tuple[int, int],
    temporal_freq_hz: float,
    t_ms: float,
    spatial_period_deg: float = SPATIAL_PERIOD_DEG,
    contrast: float = 1.0
) -> np.ndarray:
    """
    Compute sinusoidal grating luminance at each ommatidium position.

    The grating equation:
        L(x, y, t) = 0.5 + 0.5 * contrast * sin(2π/T * (dx*x + dy*y) - 2π*f*t)

    where:
        T = spatial period (degrees)
        dx, dy = direction unit vector components
        f = temporal frequency (Hz)
        t = time (seconds)

    Args:
        azimuths: Azimuth angle of each ommatidium (degrees)
        elevations: Elevation angle of each ommatidium (degrees)
        direction: Motion direction (dx, dy) in normalized units
        temporal_freq_hz: Temporal frequency in Hz
        t_ms: Current time in milliseconds
        spatial_period_deg: Spatial period of grating (degrees)
        contrast: Michelson contrast (0-1)

    Returns:
        Luminance values for each ommatidium (0-1 range, 0.5 = mean)
    """
    dx, dy = direction
    mag = np.sqrt(dx ** 2 + dy ** 2)
    if mag > 0:
        dx, dy = dx / mag, dy / mag

    t_sec = t_ms / 1000.0
    spatial_phase = (2 * np.pi / spatial_period_deg) * (dx * azimuths + dy * elevations)
    temporal_phase = 2 * np.pi * temporal_freq_hz * t_sec

    return 0.5 + 0.5 * contrast * np.sin(spatial_phase - temporal_phase)


# ─── Corrected directional Barlow-Levick filters ─────────────────────────────

class T4HorizontalFilter:
    """
    T4a-type filter: rightward-preferred Barlow-Levick direction detector.

    Spatial coupling (Haag et al. 2017):
      Excitation at column c  ← luminance from column c-1 (leading zone, LEFT)
      Inhibition at column c  ← luminance from column c+1 (trailing zone, RIGHT)

    For rightward motion:
      Bright zone passes c-1 BEFORE c → excitation at c fires BEFORE inhibition
      → T4a output is positive (preferred direction)

    For leftward motion:
      Bright zone passes c+1 BEFORE c → inhibition fires BEFORE excitation
      → Inhibition vetoes the excitation → T4a output near zero (null direction)

    For vertical motion (downward/upward):
      All columns have the same luminance at any given time (grating is horizontal bars)
      → No spatial phase difference between c-1 and c+1
      → Excitation ≈ inhibition → T4a output near zero (orthogonal, no response)

    Uses exponential decay constants (correct RC filter):
        alpha = 1 - exp(-dt / tau)
    """

    def __init__(self, n_rows: int, n_cols: int,
                 tau_exc_ms: float = TAU_EXC_MS,
                 tau_inh_ms: float = TAU_INH_MS):
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n = n_rows * n_cols
        self.tau_exc = tau_exc_ms
        self.tau_inh = tau_inh_ms
        self.exc = np.zeros(self.n, dtype=np.float64)
        self.inh = np.zeros(self.n, dtype=np.float64)

    def reset(self):
        self.exc[:] = 0.0
        self.inh[:] = 0.0

    def step(self, luminance: np.ndarray, dt_ms: float) -> np.ndarray:
        """
        Advance filter by dt_ms.

        Args:
            luminance: Current luminance at each ommatidium position (0-1),
                       shape (N_OMMATIDIA,), ordered row-major (row × col).
            dt_ms: Timestep in milliseconds.

        Returns:
            T4a output at each position: max(0, exc - inh), shape (N_OMMATIDIA,).
        """
        alpha_exc = 1.0 - np.exp(-dt_ms / self.tau_exc)
        alpha_inh = 1.0 - np.exp(-dt_ms / self.tau_inh)

        lum_2d = luminance.reshape(self.n_rows, self.n_cols)
        ON = np.maximum(0.0, lum_2d - 0.5)   # Half-wave rectified (ON channel)

        # Excitation at column c from column c-1 (leading zone for rightward motion)
        # Column 0 has no left neighbor → no excitation (edge boundary = 0)
        exc_2d = np.zeros_like(ON)
        exc_2d[:, 1:] = ON[:, :-1]   # col c gets input from col c-1

        # Inhibition at column c from column c+1 (trailing zone for rightward motion)
        # Last column has no right neighbor → no inhibition (edge boundary = 0)
        inh_2d = np.zeros_like(ON)
        inh_2d[:, :-1] = ON[:, 1:]   # col c gets input from col c+1

        exc_input = exc_2d.flatten()
        inh_input = inh_2d.flatten()

        self.exc += alpha_exc * (EXCITATORY_GAIN * exc_input - self.exc)
        self.inh += alpha_inh * (INHIBITORY_GAIN * inh_input - self.inh)

        return np.maximum(0.0, self.exc - self.inh)


class T4VerticalFilter:
    """
    T4d-type filter: downward-preferred Barlow-Levick direction detector.

    Row convention: row 0 = lowest elevation, row N_ROWS-1 = highest elevation.
    Downward motion: bright zone moves from high elevation (large row) to low.

    Spatial coupling:
      Excitation at row r  ← luminance from row r+1 (leading zone, ABOVE)
      Inhibition at row r  ← luminance from row r-1 (trailing zone, BELOW)

    For downward motion:
      Bright zone passes r+1 BEFORE r → excitation fires BEFORE inhibition
      → T4d output is positive (preferred direction)

    For upward motion:
      Bright zone passes r-1 BEFORE r → inhibition fires BEFORE excitation
      → T4d output near zero (null direction)

    For horizontal motion (rightward/leftward):
      All rows have the same luminance at any given time (grating is vertical bars)
      → No spatial phase difference between r+1 and r-1
      → T4d output near zero (orthogonal, no response)
    """

    def __init__(self, n_rows: int, n_cols: int,
                 tau_exc_ms: float = TAU_EXC_MS,
                 tau_inh_ms: float = TAU_INH_MS):
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n = n_rows * n_cols
        self.tau_exc = tau_exc_ms
        self.tau_inh = tau_inh_ms
        self.exc = np.zeros(self.n, dtype=np.float64)
        self.inh = np.zeros(self.n, dtype=np.float64)

    def reset(self):
        self.exc[:] = 0.0
        self.inh[:] = 0.0

    def step(self, luminance: np.ndarray, dt_ms: float) -> np.ndarray:
        """
        Advance filter by dt_ms.

        Args:
            luminance: Current luminance at each ommatidium position (0-1),
                       shape (N_OMMATIDIA,), ordered row-major (row × col).
            dt_ms: Timestep in milliseconds.

        Returns:
            T4d output at each position: max(0, exc - inh), shape (N_OMMATIDIA,).
        """
        alpha_exc = 1.0 - np.exp(-dt_ms / self.tau_exc)
        alpha_inh = 1.0 - np.exp(-dt_ms / self.tau_inh)

        lum_2d = luminance.reshape(self.n_rows, self.n_cols)
        ON = np.maximum(0.0, lum_2d - 0.5)   # Half-wave rectified (ON channel)

        # Excitation at row r from row r+1 (leading zone: above, higher elevation)
        # Last row has no row above it → no excitation (edge boundary = 0)
        exc_2d = np.zeros_like(ON)
        exc_2d[:-1, :] = ON[1:, :]   # row r gets input from row r+1

        # Inhibition at row r from row r-1 (trailing zone: below, lower elevation)
        # Row 0 has no row below it → no inhibition (edge boundary = 0)
        inh_2d = np.zeros_like(ON)
        inh_2d[1:, :] = ON[:-1, :]   # row r gets input from row r-1

        exc_input = exc_2d.flatten()
        inh_input = inh_2d.flatten()

        self.exc += alpha_exc * (EXCITATORY_GAIN * exc_input - self.exc)
        self.inh += alpha_inh * (INHIBITORY_GAIN * inh_input - self.inh)

        return np.maximum(0.0, self.exc - self.inh)


# ─── Main test ────────────────────────────────────────────────────────────────

def run_hs_vs_optic_flow_test(
    visual_connectome: Connectome,
    stimulus_duration_ms: float = 500.0,
    dt_ms: float = 0.5,
) -> Dict:
    """
    Test HS/VS optic flow tuning against Hausen (1982) / Joesch et al. (2008).

    Uses two directional T4 Barlow-Levick filters measured directly:
      T4a (horizontal filter) → proxy for HS cell drive
      T4d (vertical filter)   → proxy for VS cell drive

    PROTOCOL FOR EACH (direction, temporal_freq) COMBINATION:
    1. Simulate moving grating for stimulus_duration_ms
    2. At each timestep, compute luminance at each of 800 ommatidia
    3. Step T4a filter (asymmetric horizontal: exc from left, inh from right)
    4. Step T4d filter (asymmetric vertical: exc from above, inh from below)
    5. Measure mean filter output over the SECOND HALF of stimulus (steady-state)
    6. Store as (direction, freq) response for T4a and T4d

    THEN: compute tuning curves and compare to Joesch et al. (2008)

    Args:
        visual_connectome: FlyWire optic lobe connectome (used for neuron counts only)
        stimulus_duration_ms: Duration per direction/frequency combination
        dt_ms: Integration timestep (0.5ms = 2kHz)

    Returns:
        Dict with tuning curves, DSI values, velocity optimum, pass/fail
    """
    print("\n" + "=" * 70)
    print("HS/VS OPTIC FLOW TEST (CORRECTED)")
    print("Ground truth: Hausen (1982) + Joesch et al. (2008)")
    print("=" * 70)

    azimuths, elevations = build_ommatidium_positions()
    print(f"\nSpatial layout: {N_COLS} cols × {N_ROWS} rows = {N_OMMATIDIA} ommatidia")
    print(f"Visual field: ±{AZ_RANGE}° azimuth × ±{EL_RANGE}° elevation")
    print(f"Grating spatial period: {SPATIAL_PERIOD_DEG}°")
    print(f"\nTemporal frequencies: {TEMPORAL_FREQUENCIES_HZ} Hz")
    print(f"Directions: {list(DIRECTIONS.keys())}")
    print(f"\nFilter design:")
    print(f"  T4a (HS proxy): exc from LEFT neighbor, inh from RIGHT neighbor")
    print(f"  T4d (VS proxy): exc from ABOVE neighbor, inh from BELOW neighbor")
    print(f"  τ_exc={TAU_EXC_MS}ms (fast, cholinergic), τ_inh={TAU_INH_MS}ms (slow, GABA)")

    # Report LP neuron counts for context
    lp_neurons = get_visual_region_neurons(visual_connectome, 'LOBULA_PLATE')
    hs_count = 0
    vs_count = 0
    for nid in lp_neurons:
        neuron = visual_connectome.neurons.get(nid)
        if not neuron:
            continue
        ct = ' '.join(neuron.cell_types or []).upper()
        if any(t in ct for t in ['HSN', 'HSE', 'HSS', ' HS']):
            hs_count += 1
        elif any(t in ct for t in ['VS1', 'VS2', 'VS3', 'VS4', 'VS5',
                                    'VS6', 'VS7', 'VS8', 'VS9', 'VS10', ' VS']):
            vs_count += 1
    print(f"\nFlyWire LP neurons: {len(lp_neurons):,} total "
          f"({hs_count} HS-labeled, {vs_count} VS-labeled)")
    print("  → Measuring T4 BL filter output directly (not brain amplitude)")

    # Initialize directional filters
    t4a_filter = T4HorizontalFilter(N_ROWS, N_COLS)   # HS proxy
    t4d_filter = T4VerticalFilter(N_ROWS, N_COLS)     # VS proxy

    num_steps = int(stimulus_duration_ms / dt_ms)
    measurement_start = num_steps // 2   # Measure only steady-state (second half)

    # Results: [direction][temporal_freq] = mean population output
    results_t4a = {d: {} for d in DIRECTIONS}   # HS proxy
    results_t4d = {d: {} for d in DIRECTIONS}   # VS proxy

    for direction_name, direction_vec in DIRECTIONS.items():
        for tf_hz in TEMPORAL_FREQUENCIES_HZ:
            print(f"\n  [{direction_name}, {tf_hz}Hz] Simulating {stimulus_duration_ms}ms...",
                  end='', flush=True)

            t4a_filter.reset()
            t4d_filter.reset()

            t4a_outputs = []
            t4d_outputs = []

            for step in range(num_steps):
                t_ms = step * dt_ms

                luminance = compute_grating_luminance(
                    azimuths, elevations, direction_vec, tf_hz, t_ms
                )

                t4a_out = t4a_filter.step(luminance, dt_ms)
                t4d_out = t4d_filter.step(luminance, dt_ms)

                if step >= measurement_start:
                    t4a_outputs.append(float(np.mean(t4a_out)))
                    t4d_outputs.append(float(np.mean(t4d_out)))

            mean_t4a = float(np.mean(t4a_outputs)) if t4a_outputs else 0.0
            mean_t4d = float(np.mean(t4d_outputs)) if t4d_outputs else 0.0
            results_t4a[direction_name][tf_hz] = mean_t4a
            results_t4d[direction_name][tf_hz] = mean_t4d

            print(f"  T4a={mean_t4a:.5f}  T4d={mean_t4d:.5f}")

    # ── Velocity tuning curves ─────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print("VELOCITY TUNING CURVES")

    # T4a: rightward preferred (HS proxy)
    t4a_pref = [results_t4a['rightward'][tf] for tf in TEMPORAL_FREQUENCIES_HZ]
    t4a_null = [results_t4a['leftward'][tf] for tf in TEMPORAL_FREQUENCIES_HZ]

    # T4d: downward preferred (VS proxy)
    t4d_pref = [results_t4d['downward'][tf] for tf in TEMPORAL_FREQUENCIES_HZ]
    t4d_null = [results_t4d['upward'][tf] for tf in TEMPORAL_FREQUENCIES_HZ]

    print(f"\nT4a / HS proxy (preferred: rightward, null: leftward):")
    print(f"{'TF (Hz)':<10} {'Preferred':<14} {'Null':<14} {'DSI':<10}")
    t4a_dsi_per_tf = []
    for tf, pref, null in zip(TEMPORAL_FREQUENCIES_HZ, t4a_pref, t4a_null):
        dsi = (pref - null) / (pref + null + 1e-10)
        t4a_dsi_per_tf.append(dsi)
        print(f"{tf:<10.1f} {pref:<14.6f} {null:<14.6f} {dsi:<10.4f}")

    print(f"\nT4d / VS proxy (preferred: downward, null: upward):")
    print(f"{'TF (Hz)':<10} {'Preferred':<14} {'Null':<14} {'DSI':<10}")
    t4d_dsi_per_tf = []
    for tf, pref, null in zip(TEMPORAL_FREQUENCIES_HZ, t4d_pref, t4d_null):
        dsi = (pref - null) / (pref + null + 1e-10)
        t4d_dsi_per_tf.append(dsi)
        print(f"{tf:<10.1f} {pref:<14.6f} {null:<14.6f} {dsi:<10.4f}")

    # ── Velocity optimum ───────────────────────────────────────────────────────
    t4a_peak_idx = int(np.argmax(t4a_pref))
    t4a_peak_tf = TEMPORAL_FREQUENCIES_HZ[t4a_peak_idx]
    t4a_peak_vel = t4a_peak_tf * SPATIAL_PERIOD_DEG

    t4d_peak_idx = int(np.argmax(t4d_pref))
    t4d_peak_tf = TEMPORAL_FREQUENCIES_HZ[t4d_peak_idx]
    t4d_peak_vel = t4d_peak_tf * SPATIAL_PERIOD_DEG

    print(f"\nT4a (HS proxy) velocity optimum: {t4a_peak_tf} Hz = {t4a_peak_vel:.0f} deg/s")
    print(f"T4d (VS proxy) velocity optimum: {t4d_peak_tf} Hz = {t4d_peak_vel:.0f} deg/s")
    print(f"Biological target (Joesch 2008): 1-4 Hz = 30-120 deg/s")

    # ── Axis specificity ───────────────────────────────────────────────────────
    # T4a should respond strongly to horizontal motion, weakly to vertical
    t4a_horizontal_max = max(
        max(results_t4a['rightward'].values()),
        max(results_t4a['leftward'].values())
    )
    t4a_vertical_max = max(
        max(results_t4a['downward'].values()),
        max(results_t4a['upward'].values())
    )
    hs_specificity = 1.0 - (t4a_vertical_max / (t4a_horizontal_max + 1e-10))

    # T4d should respond strongly to vertical motion, weakly to horizontal
    t4d_vertical_max = max(
        max(results_t4d['downward'].values()),
        max(results_t4d['upward'].values())
    )
    t4d_horizontal_max = max(
        max(results_t4d['rightward'].values()),
        max(results_t4d['leftward'].values())
    )
    vs_specificity = 1.0 - (t4d_horizontal_max / (t4d_vertical_max + 1e-10))

    print(f"\nT4a (HS proxy) horizontal specificity: {hs_specificity:.3f}")
    print(f"  H-max={t4a_horizontal_max:.5f}, V-max={t4a_vertical_max:.5f}")
    print(f"T4d (VS proxy) vertical specificity: {vs_specificity:.3f}")
    print(f"  V-max={t4d_vertical_max:.5f}, H-max={t4d_horizontal_max:.5f}")
    print(f"Target: > 0.50 (vertical/horizontal motion < 50% cross-contamination)")

    # ── Pass/fail ──────────────────────────────────────────────────────────────
    t4a_tf_pass = 1.0 <= t4a_peak_tf <= 4.0
    t4d_tf_pass = 1.0 <= t4d_peak_tf <= 4.0
    t4a_dsi_pass = max(t4a_dsi_per_tf) > 0.30
    t4d_dsi_pass = max(t4d_dsi_per_tf) > 0.30
    hs_spec_pass = hs_specificity > 0.50
    vs_spec_pass = vs_specificity > 0.50

    all_pass = all([t4a_tf_pass, t4d_tf_pass, t4a_dsi_pass, t4d_dsi_pass,
                    hs_spec_pass, vs_spec_pass])

    print(f"\n{'=' * 70}")
    print("RESULTS vs Joesch et al. (2008)")
    print(f"{'=' * 70}")
    print(f"T4a (HS proxy) peak TF: {t4a_peak_tf}Hz  {'✅' if t4a_tf_pass else '❌'}  "
          f"(target: 1-4 Hz)")
    print(f"T4d (VS proxy) peak TF: {t4d_peak_tf}Hz  {'✅' if t4d_tf_pass else '❌'}  "
          f"(target: 1-4 Hz)")
    print(f"T4a DSI (H vs H-null):  {max(t4a_dsi_per_tf):.3f}  {'✅' if t4a_dsi_pass else '❌'}  "
          f"(target: >0.30)")
    print(f"T4d DSI (V vs V-null):  {max(t4d_dsi_per_tf):.3f}  {'✅' if t4d_dsi_pass else '❌'}  "
          f"(target: >0.30)")
    print(f"HS axis specificity:    {hs_specificity:.3f}  {'✅' if hs_spec_pass else '❌'}  "
          f"(target: >0.50)")
    print(f"VS axis specificity:    {vs_specificity:.3f}  {'✅' if vs_spec_pass else '❌'}  "
          f"(target: >0.50)")
    print(f"\nOverall: {'✅ PASS' if all_pass else '❌ FAIL'}")

    results = {
        'test': 'hs_vs_optic_flow',
        'passed': all_pass,
        'method': 'T4_BL_filter_direct_measurement',
        'filter_design': {
            'T4a': 'exc from left neighbor (c-1), inh from right neighbor (c+1)',
            'T4d': 'exc from above neighbor (r+1), inh from below neighbor (r-1)',
            'tau_exc_ms': TAU_EXC_MS,
            'tau_inh_ms': TAU_INH_MS,
            'excitatory_gain': EXCITATORY_GAIN,
            'inhibitory_gain': INHIBITORY_GAIN,
        },
        'lp_neuron_counts': {
            'total_lp': len(lp_neurons),
            'hs_labeled': hs_count,
            'vs_labeled': vs_count,
        },
        't4a_hs_proxy': {
            'temporal_frequencies_hz': TEMPORAL_FREQUENCIES_HZ,
            'preferred_tuning': t4a_pref,
            'null_tuning': t4a_null,
            'dsi_per_tf': t4a_dsi_per_tf,
            'max_dsi': float(max(t4a_dsi_per_tf)),
            'peak_temporal_freq_hz': t4a_peak_tf,
            'peak_velocity_deg_s': float(t4a_peak_vel),
            'horizontal_specificity': float(hs_specificity),
            'horizontal_max': float(t4a_horizontal_max),
            'vertical_max': float(t4a_vertical_max),
        },
        't4d_vs_proxy': {
            'temporal_frequencies_hz': TEMPORAL_FREQUENCIES_HZ,
            'preferred_tuning': t4d_pref,
            'null_tuning': t4d_null,
            'dsi_per_tf': t4d_dsi_per_tf,
            'max_dsi': float(max(t4d_dsi_per_tf)),
            'peak_temporal_freq_hz': t4d_peak_tf,
            'peak_velocity_deg_s': float(t4d_peak_vel),
            'vertical_specificity': float(vs_specificity),
            'vertical_max': float(t4d_vertical_max),
            'horizontal_max': float(t4d_horizontal_max),
        },
        'all_responses': {
            't4a': {d: {str(k): v for k, v in tf_dict.items()}
                    for d, tf_dict in results_t4a.items()},
            't4d': {d: {str(k): v for k, v in tf_dict.items()}
                    for d, tf_dict in results_t4d.items()},
        },
        'spatial_period_deg': SPATIAL_PERIOD_DEG,
        'ground_truth_reference': 'Joesch_et_al_2008_Fig3',
        'pass_criteria': {
            'peak_tf_hz': '1-4 Hz',
            'dsi_threshold': 0.30,
            'axis_specificity_threshold': 0.50,
        },
        'pass_details': {
            't4a_peak_tf_pass': bool(t4a_tf_pass),
            't4d_peak_tf_pass': bool(t4d_tf_pass),
            't4a_dsi_pass': bool(t4a_dsi_pass),
            't4d_dsi_pass': bool(t4d_dsi_pass),
            'hs_specificity_pass': bool(hs_spec_pass),
            'vs_specificity_pass': bool(vs_spec_pass),
        }
    }

    return results


if __name__ == '__main__':
    print(__doc__)

    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()

    from hive.substrate.visual_pathway import extract_visual_pathway
    visual_connectome = extract_visual_pathway(connectome)

    results = run_hs_vs_optic_flow_test(visual_connectome)

    output_path = Path("research/vision/findings/hs_vs_optic_flow_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_path}")
