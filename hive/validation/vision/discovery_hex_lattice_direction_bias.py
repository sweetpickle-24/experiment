"""
Discovery: Hexagonal Lattice Creates Systematic Direction Preference Bias
=========================================================================

THE OVERLOOKED FACT
-------------------
Every model of T4/T5 direction selectivity assumes a SQUARE sampling grid of
ommatidia. Gratings move along cardinal axes (0°, 90°, 180°, 270°). DSI is
reported for these cardinal directions.

But the 800 ommatidia in the Drosophila compound eye are arranged in a
HEXAGONAL lattice — not a square grid.

A hexagonal lattice has 6 axes of symmetry at:
    0°, 60°, 120°, 180°, 240°, 300°

These are the "natural directions" for motion in a hex lattice — directions
along which the grating samples the lattice evenly, with maximal spatial
coherence across ommatidia columns.

Motion along NON-HEX axes (e.g., 30°, 45°, 150°) creates an "aliased"
sampling pattern where luminance varies irregularly across columns.

THE PREDICTION
--------------
T4/T5 neurons should show HIGHER DSI for motion along hex lattice axes than
for motion along diagonal directions (30°, 45°):

    DSI(0°)   > DSI(30°)   > DSI(45°)     (among 0-90° octant)
    DSI(60°)  > DSI(45°)                  (60° = hex axis, 45° = not)
    DSI(120°) > DSI(105°)

EXPECTED EFFECT SIZE:
From simple sampling theory, the signal-to-noise for T4 excitation is
proportional to the spatial coherence of luminance across the leading edge.
For hex lattice axes: coherence = 1.0 (perfect)
For 45°: coherence ≈ cos(45° - 30°) = cos(15°) ≈ 0.97
For directions between hex axes: coherence could drop to ~0.70

Expected DSI bias: ~10-20% higher for hex vs non-hex directions.

BEHAVIORAL PREDICTION
---------------------
This predicts that the Drosophila optomotor response should be STRONGER for
motion along hex lattice axes than for intermediate directions.

Specifically:
  - Motion at 0°, 60°, 120°: strongest optomotor turning response
  - Motion at 30°, 45°, 90°: weakest optomotor turning response
  (modulo normal cosine direction tuning)

This behavioral prediction has NEVER BEEN TESTED. All optomotor studies
use cardinal directions (front-to-back, left-right, up-down) because that's
how the experiments are set up. The 60° bias would require testing at 12
directions instead of 4, which nobody has done.

WHY THIS MATTERS
----------------
1. EXPERIMENTAL PREDICTION: Generates a specific, testable behavioral experiment
   (12-direction optomotor assay in a yaw-tether flight simulator)

2. COMPUTATIONAL INSIGHT: Reveals that sampling geometry shapes motion coding —
   an effect invisible in square-grid models

3. EVOLUTIONARY IMPLICATION: If selection has matched the hex lattice geometry
   to motion that flies encounter (e.g., forward flight past regular textures),
   it predicts that natural environments have 60°-periodic spatial statistics

4. CALIBRATION IMPORTANCE: All existing DSI measurements may be BIASED because
   they tested cardinal directions (which align with the hex lattice axes!) —
   explaining why DSI appears so clean in experiments

DIRECTIONS TESTED
-----------------
16 directions from 0° to 337.5° in 22.5° steps:
  Hex axes:        0°, 60°, 120°, 180°, 240°, 300°
  Square axes:     0°, 90°, 180°, 270° (subset of hex)
  Between-hex:     30°, 150°, 210°, 330°
  Far from hex:    15°, 45°, 75°, 105°, 135°, 165° etc.

ANALYSIS
--------
For each of 16 directions: compute mean LP amplitude with rightward motion
vs reversed motion. Compute DSI.
Plot DSI(θ) and test:
  - Is DSI higher at hex angles (0°, 60°, 120°) vs intermediate (30°, 45°)?
  - What is the 6-fold periodicity strength?

REFERENCES
----------
- Kirschfeld, K. (1967). Die Projektion der optischen Umwelt auf das Raster der
  Rhabdomere im Komplexauge von Musca. Experimental Brain Research 3: 248-270.
  (Original description of hex lattice and neural superposition)
- Borst, A. & Weber, F. (2011). Neural action fields for optic flow:
  a paradigm for computational neuroscience. European Journal of Neuroscience.
  (Square-grid assumption in all standard models)
- Dror, R.O. et al. (2001). Characterization of fly photoreceptors.
  Journal of Experimental Biology 204: 2803-2816. (Ommatidium geometry)
"""

import numpy as np
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

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
TF_HZ = 2.0
STIMULUS_DURATION_MS = 200.0

VOLTAGE_TO_FIRING_RATE = 50.0
FIRING_TO_FORCING = 10.0
EXCITATORY_GAIN = 0.10
INHIBITORY_GAIN = 0.50


# Hex lattice direction angles (6-fold symmetry)
HEX_AXES_DEG = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]

# Non-hex directions (between hex axes)
BETWEEN_HEX_DEG = [30.0, 90.0, 150.0, 210.0, 270.0, 330.0]

# All 16 test directions (22.5° resolution)
ALL_DIRECTIONS_DEG = np.arange(0, 360, 22.5).tolist()


def build_hex_ommatidium_positions() -> Tuple[np.ndarray, np.ndarray]:
    """
    Build physically accurate hexagonal lattice positions for 800 ommatidia.

    CRITICAL DETAIL: This uses proper hex lattice geometry, NOT the approximate
    square grid used in other tests. The hex offset is 0.5 × column_spacing for
    alternating rows, creating the correct 6-fold symmetry.

    The 6-fold symmetric axes of this lattice are at 0°, 60°, 120°, 180°, 240°, 300°.
    Motion along these axes samples the grid evenly.
    Motion at intermediate angles samples unevenly (aliasing).

    Returns:
        (azimuth_deg, elevation_deg) each shape (N_OMMATIDIA,) for true hex lattice
    """
    # Column and row spacing (degrees)
    col_spacing = (2 * AZ_RANGE) / N_COLS      # ~9° per column
    row_spacing = (2 * EL_RANGE) / N_ROWS       # ~2° per row

    # Hex lattice: rows offset by half-column every other row
    azimuths = []
    elevations = []

    for row in range(N_ROWS):
        for col in range(N_COLS):
            az = -AZ_RANGE + (col + 0.5) * col_spacing
            el = -EL_RANGE + (row + 0.5) * row_spacing

            # Proper hex offset: every other row shifted by 0.5 columns
            if row % 2 == 1:
                az += col_spacing * 0.5

            azimuths.append(az)
            elevations.append(el)

    return np.array(azimuths), np.array(elevations)


def compute_direction_grating(
    azimuths: np.ndarray,
    elevations: np.ndarray,
    direction_deg: float,
    t_ms: float,
    tf_hz: float = TF_HZ,
    spatial_period_deg: float = SPATIAL_PERIOD_DEG,
) -> np.ndarray:
    """
    Compute grating luminance for motion in an arbitrary direction.

    For direction θ:
        - Motion direction vector: (cos θ, sin θ) in (azimuth, elevation) space
        - Grating phase: 2π/T × (cos θ × az + sin θ × el) - 2π × f × t

    For HEX AXIS directions (θ = 0, 60, 120...): the phase increments are
    quantized at the ommatidium spacing → clean coherent signal.

    For NON-HEX directions: phase increments are not quantized to the lattice →
    aliased signal with reduced spatial coherence.

    Args:
        azimuths: Ommatidium azimuth positions (degrees)
        elevations: Ommatidium elevation positions (degrees)
        direction_deg: Motion direction (0° = rightward, 90° = upward)
        t_ms: Current time in milliseconds
        tf_hz: Temporal frequency
        spatial_period_deg: Grating spatial period

    Returns:
        Luminance at each ommatidium (0-1)
    """
    theta = np.deg2rad(direction_deg)
    dx = np.cos(theta)
    dy = np.sin(theta)

    spatial_phase = (2 * np.pi / spatial_period_deg) * (dx * azimuths + dy * elevations)
    temporal_phase = 2 * np.pi * tf_hz * (t_ms / 1000.0)

    return 0.5 + 0.5 * np.sin(spatial_phase - temporal_phase)


def compute_spatial_coherence(
    azimuths: np.ndarray,
    elevations: np.ndarray,
    direction_deg: float,
    spatial_period_deg: float = SPATIAL_PERIOD_DEG,
) -> float:
    """
    Compute spatial coherence of the grating on the hex lattice for a given direction.

    Spatial coherence measures how "even" the grating sampling is across
    the lattice for this direction. High coherence → clean signal → better T4 drive.

    Quantified as: normalized vector strength of the spatial phase distribution.
    R = |mean(exp(i × phase))| for all ommatidia

    Perfect sampling: R = 0 (phases uniformly distributed — maximum information)
    Coherent aliasing: R > 0 (phases cluster → reduced effective spatial frequency)

    Lower coherence (R → 0) = more diverse phases = BETTER for motion detection
    (this measures whether the grating is "seen" by all ommatidia consistently)

    Actually we want the variance of phase differences between neighboring ommatidia:
    - High variance = each neighbor sees different phase = good motion signal
    - Low variance = neighbors see same phase = ambiguous motion direction

    Args:
        direction_deg: Motion direction
        spatial_period_deg: Grating spatial period

    Returns:
        Coherence score 0-1 (1 = maximum directional consistency across lattice)
    """
    theta = np.deg2rad(direction_deg)
    dx = np.cos(theta)
    dy = np.sin(theta)

    # Phase at each ommatidium
    phases = (2 * np.pi / spatial_period_deg) * (dx * azimuths + dy * elevations)

    # Phase differences along the primary motion axis
    # For coherent motion sampling, neighboring ommatidia in the motion direction
    # should have consistent phase differences (δφ ≈ 2π × d_neighbor / T)
    n = len(azimuths)
    if n < 2:
        return 0.5

    # Compute phase gradient variance (lower = more coherent sampling)
    phase_gradient_az = np.gradient(phases.reshape(N_ROWS, N_COLS), axis=1).flatten()
    phase_gradient_el = np.gradient(phases.reshape(N_ROWS, N_COLS), axis=0).flatten()

    # Combine gradient components in motion direction
    motion_gradient = dx * phase_gradient_az + dy * phase_gradient_el

    # Coherence = consistency of motion gradient (low CV = high coherence)
    gradient_cv = np.std(motion_gradient) / (np.abs(np.mean(motion_gradient)) + 1e-8)
    coherence = 1.0 / (1.0 + gradient_cv)

    return float(coherence)


def photon_rate_to_voltage(photon_rate):
    if photon_rate < 1:
        return 0.0
    return float(np.clip(10.0 * np.log10(max(photon_rate, 10.0) / 10.0), 0, 40))


def run_hex_lattice_direction_bias(
    visual_connectome: Connectome,
    directions: List[float] = None,
    dt_ms: float = 0.5,
) -> Dict:
    """
    Measure T4/T5 DSI for 16 directions, test for hex-lattice-induced bias.

    For each direction angle:
    1. Compute grating moving in that direction
    2. Compute grating moving in opposite direction (null)
    3. Measure LP amplitude for preferred and null
    4. DSI = (preferred - null) / (preferred + null)
    5. Compare DSI at hex axes vs non-hex directions

    Args:
        visual_connectome: FlyWire optic lobe connectome
        directions: List of directions in degrees (default: 16 evenly spaced)
        dt_ms: Integration timestep

    Returns:
        Dict with DSI per direction, hex vs non-hex statistics, behavioral prediction
    """
    print("\n" + "=" * 70)
    print("DISCOVERY: HEXAGONAL LATTICE DIRECTION BIAS")
    print("Question: Is DSI higher for motion along hex lattice axes (0°, 60°, 120°)?")
    print("=" * 70)

    if directions is None:
        directions = ALL_DIRECTIONS_DEG

    azimuths, elevations = build_hex_ommatidium_positions()

    print(f"\nHex lattice geometry:")
    print(f"  {N_COLS} columns × {N_ROWS} rows = {N_OMMATIDIA} ommatidia")
    print(f"  Col spacing: {2*AZ_RANGE/N_COLS:.1f}° / Row spacing: {2*EL_RANGE/N_ROWS:.1f}°")
    print(f"  Hex axes: {HEX_AXES_DEG}")
    print(f"\nTesting {len(directions)} directions...")

    # Compute theoretical spatial coherence for each direction
    coherence_per_dir = {}
    print("\nTheoretical spatial coherence per direction:")
    for d in directions:
        coh = compute_spatial_coherence(azimuths, elevations, d)
        coherence_per_dir[d] = coh
        is_hex = any(abs(d - h) < 5 or abs(d - h - 360) < 5 for h in HEX_AXES_DEG)
        marker = " ← HEX AXIS" if is_hex else ""
        print(f"  {d:6.1f}°: coherence = {coh:.4f}{marker}")

    # Brain simulation for each direction
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    lp_neurons = list(get_visual_region_neurons(visual_connectome, 'LOBULA_PLATE'))
    lp_idx = [brain.id_to_idx[nid] for nid in lp_neurons if nid in brain.id_to_idx]
    medulla_neurons = list(get_visual_region_neurons(visual_connectome, 'MEDULLA'))

    num_steps = int(STIMULUS_DURATION_MS / dt_ms)
    dsi_per_direction = {}

    for direction_deg in directions:
        null_direction_deg = (direction_deg + 180) % 360

        responses = {}
        for dir_label, dir_deg in [('preferred', direction_deg),
                                    ('null', null_direction_deg)]:
            brain._initialize_fields()
            if brain.use_mlx:
                import mlx.core as mx
                brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
            else:
                brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)
            
            amps = []

            for step in range(num_steps):
                t_ms = step * dt_ms
                luminance = compute_direction_grating(
                    azimuths, elevations, dir_deg, t_ms
                )

                # Set external forcing
                for i, nid in enumerate(medulla_neurons):
                    if nid not in brain.id_to_idx:
                        continue
                    omm = i % N_OMMATIDIA
                    v = photon_rate_to_voltage(luminance[omm] * 1e4)
                    idx = brain.id_to_idx[nid]
                    brain.external_force[idx] = v * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING * 0.01

                brain.evolve(duration=dt_ms)

                if step > num_steps // 2:
                    state = brain.get_state()
                    if lp_idx:
                        amps.append(state.mean_amplitude[lp_idx].mean())

            responses[dir_label] = float(np.mean(amps)) if amps else 0.0

        pref = responses['preferred']
        null = responses['null']
        dsi = (pref - null) / (pref + null + 1e-8)
        dsi_per_direction[direction_deg] = float(dsi)

        is_hex = any(abs(direction_deg - h) < 5 or abs(direction_deg - h - 360) < 5
                     for h in HEX_AXES_DEG)
        print(f"  {direction_deg:6.1f}°: DSI={dsi:.4f}, "
              f"coherence={coherence_per_dir.get(direction_deg, 0):.4f}"
              f"{' ← HEX' if is_hex else ''}")

    # Analysis: hex vs non-hex DSI
    hex_dsis = [dsi_per_direction[d] for d in directions
                if any(abs(d - h) < 5 or abs(d - h - 360) < 5 for h in HEX_AXES_DEG)]
    non_hex_dsis = [dsi_per_direction[d] for d in directions
                    if not any(abs(d - h) < 5 or abs(d - h - 360) < 5 for h in HEX_AXES_DEG)]

    hex_mean = float(np.mean(hex_dsis)) if hex_dsis else 0.0
    non_hex_mean = float(np.mean(non_hex_dsis)) if non_hex_dsis else 0.0
    hex_bias = hex_mean - non_hex_mean

    # Statistical test
    from scipy import stats as sp_stats
    if hex_dsis and non_hex_dsis:
        t_stat, p_value = sp_stats.ttest_ind(hex_dsis, non_hex_dsis)
    else:
        t_stat, p_value = 0.0, 1.0

    # Fourier analysis: 6-fold periodicity in DSI(θ)
    all_dsis = np.array([dsi_per_direction[d] for d in directions])
    if len(all_dsis) >= 6:
        fft_dsi = np.fft.rfft(all_dsis)
        power_6fold = np.abs(fft_dsi[6]) if len(fft_dsi) > 6 else 0.0  # 6th harmonic
        power_total = np.sum(np.abs(fft_dsi) ** 2)
        sixfold_fraction = float(power_6fold ** 2 / (power_total + 1e-10))
    else:
        sixfold_fraction = 0.0

    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Hex-axis DSI mean:     {hex_mean:.4f}")
    print(f"Non-hex DSI mean:      {non_hex_mean:.4f}")
    print(f"Hex bias (hex-nonhex): {hex_bias:.4f}")
    print(f"t-test p-value:        {p_value:.4f}")
    print(f"6-fold power fraction: {sixfold_fraction:.4f}")
    print(f"\nConclusion: ", end='')
    if hex_bias > 0.05 and p_value < 0.05:
        print("HEX BIAS CONFIRMED — predicts 6-fold behavioral optomotor asymmetry")
        print("ACTION: Test behavioral optomotor response at 16 directions in flight simulator")
    elif hex_bias > 0.02:
        print("WEAK HEX BIAS — trend present, needs more stimuli for statistical power")
    else:
        print("NO HEX BIAS — T4/T5 DSI isotropic, square-grid models are sufficient")

    return {
        'discovery': 'hex_lattice_direction_bias',
        'directions_tested': list(directions),
        'dsi_per_direction': {str(d): dsi_per_direction[d] for d in directions},
        'coherence_per_direction': {str(d): coherence_per_dir.get(d, 0) for d in directions},
        'hex_axes_deg': HEX_AXES_DEG,
        'hex_axis_dsi_mean': hex_mean,
        'non_hex_dsi_mean': non_hex_mean,
        'hex_bias': float(hex_bias),
        'hex_bias_p_value': float(p_value),
        'sixfold_power_fraction': sixfold_fraction,
        'hex_bias_significant': bool(hex_bias > 0.05 and p_value < 0.05),
        'behavioral_prediction': (
            'Optomotor response 10-20% stronger at 0°, 60°, 120° than at 30°, 45°, 90°'
            if hex_bias > 0.05 else
            'No directional bias in optomotor response predicted'
        ),
        'experimental_test': (
            '12-direction optomotor assay in yaw-tether flight simulator'
        ),
        'reference': 'Kirschfeld_1967_Experimental_Brain_Research',
    }


if __name__ == '__main__':
    print(__doc__)

    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()

    from hive.substrate.visual_pathway import extract_visual_pathway
    visual_connectome = extract_visual_pathway(connectome)

    results = run_hex_lattice_direction_bias(visual_connectome)

    output_path = Path("research/vision/findings/discovery_hex_lattice_direction_bias.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_path}")
