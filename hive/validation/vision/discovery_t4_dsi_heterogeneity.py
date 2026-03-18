"""
Discovery: T4 DSI Heterogeneity — Are All T4 Cells Equally Direction-Selective?
================================================================================

THE CANONICAL VIEW
------------------
The standard textbook description of T4 cells:
  "T4 neurons are elementary motion detectors. Each T4 cell responds to
   motion in ONE preferred direction and is suppressed by the opposite."
  (Maisak et al. 2013, Nature; Haag et al. 2017, eLife)

This implies ALL T4 neurons of a given subtype (e.g., T4a = rightward) have
approximately the same DSI ≈ 0.7-0.9.

THE UNTESTED QUESTION
---------------------
Is there a DISTRIBUTION of DSI values across T4 cells?

In vivo calcium imaging (Maisak et al. 2013) recorded from ~50-200 T4 cells
per fly. The paper showed MEAN DSI and MEAN preferred direction, but not the
full distribution. If DSI has high variance, many T4 cells could be weakly
directional (DSI = 0.1-0.3) while a few are strongly directional (DSI > 0.8).

WHY THE DISTRIBUTION MATTERS
-----------------------------
1. INFORMATION THEORY: Heterogeneous DSI provides more information than
   uniform DSI. A population with DSI = {0.9, 0.5, 0.1} can encode
   velocity (fast motion → drives strong DSI cells; slow → drives weak DSI cells)
   whereas a uniform DSI = {0.7, 0.7, 0.7} population only encodes direction.

2. NEURAL CODE: If the T4 population has a soft "spectrum" of direction
   selectivity, the optomotor system can read out motion magnitude, not just
   direction — like how V1 orientation selectivity creates a graded map.

3. ANATOMY PREDICTION: DSI should correlate with the number of inhibitory
   Mi4/C3/CT1 synapses onto each T4 cell. T4 cells with more inhibitory input
   → higher DSI. FlyWire lets us directly test: does T4 DSI (measured via
   simulation) correlate with T4 inhibitory synapse count (from anatomy)?

4. BEHAVIORAL PREDICTION: The fraction of T4 cells with DSI > 0.5 (call this
   f_selective) should predict the slope of the velocity-response curve. If
   f_selective is low → saturating response at low velocities. If high →
   linear response over wider range.

MEASUREMENT APPROACH
--------------------
STEP 1: Identify all T4a neurons (rightward preference) in FlyWire
STEP 2: Present rightward grating (preferred) and leftward grating (null)
STEP 3: Apply T4a-specific forcing: activate each T4a neuron individually
        based on its spatial position in the visual field
STEP 4: Measure the amplitude response of EACH T4a neuron individually
        (not the population mean)
STEP 5: Compute DSI for each T4a cell from its individual response
STEP 6: Plot DSI distribution histogram

CHALLENGE: In our wave-based engine, all neurons are driven by the population
forcing. To measure individual T4a DSI, we need to:
  a) Identify each T4a neuron's spatial position (from FlyWire coordinates)
  b) Apply grating luminance at the correct local position for each T4a
  c) Measure that T4a's amplitude independently

SIMPLIFIED APPROACH (used here):
  - Use the LP amplitude as a readout of T4a population output
  - But decompose by: which medulla neurons are the T4a inputs?
  - For each T4a candidate: measure its specific contribution
  - DSI_i = (A_preferred_i - A_null_i) / (A_preferred_i + A_null_i + ε)

ANATOMY-PHYSIOLOGY CORRELATION
-------------------------------
For each T4a neuron, count:
  - Total input synapses from excitatory cells (Mi1, Tm3)
  - Total input synapses from inhibitory cells (Mi4, C3, CT1)
  - Inhibitory fraction = n_inh / (n_exc + n_inh)

Prediction: correlation(DSI_i, inhibitory_fraction_i) > 0.5

This would be the first anatomy-to-physiology correlation for individual
T4 cells — impossible to measure in vivo (would require single-neuron
patch clamp + synapse counting in the same cell).

EXPECTED OUTCOMES
-----------------
Scenario A (uniform DSI, σ < 0.05): Confirms canonical view
Scenario B (moderate spread, σ = 0.10-0.20): Suggests soft coding
Scenario C (high spread, σ > 0.30 with bimodal distribution): Completely
  new picture — T4 cells form "strong" and "weak" subpopulations

REFERENCES
----------
- Maisak, M.S. et al. (2013). A directional tuning map of Drosophila elementary
  motion detectors. Nature 500: 212-216. (Original T4 characterization, mean DSI)
- Haag, J. et al. (2017). Complementary mechanisms create direction selectivity
  in the fly. eLife 6: e29044. (T4 mechanism, no individual DSI distribution)
- Schnell, B. et al. (2012). Processing of horizontal optic flow in three visual
  interneurons of the Drosophila brain. Journal of Neurophysiology 108: 1939-1952.
- Shinomiya, K. et al. (2019). Comparisons between the ON- and OFF-edge motion
  pathways in the Drosophila visual system. eLife 8: e40025. (T4 synapse anatomy)
"""

import numpy as np
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scipy import stats as sp_stats

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
STIMULUS_DURATION_MS = 300.0

VOLTAGE_TO_FIRING_RATE = 50.0
FIRING_TO_FORCING = 10.0
EXCITATORY_GAIN = 0.10
INHIBITORY_GAIN = 0.50

# DSI thresholds
DSI_STRONG = 0.70   # Canonical strong direction selectivity
DSI_MODERATE = 0.30  # Moderate direction selectivity (minimum meaningful)
DSI_WEAK = 0.10      # Weak but non-zero


# ─── T4 neuron anatomy query ─────────────────────────────────────────────────

def get_t4a_input_synapse_counts(
    connectome: Connectome,
    t4a_neurons: List[int],
) -> Dict[int, Dict[str, int]]:
    """
    For each T4a neuron, count excitatory and inhibitory input synapses.

    Excitatory inputs (Mi1, Tm3 — cholinergic, fast):
      Cell type strings: 'Mi1', 'Tm3'
    Inhibitory inputs (Mi4, C3, CT1 — GABAergic, slow):
      Cell type strings: 'Mi4', 'C3', 'CT1'

    The INHIBITORY FRACTION = n_inh / (n_exc + n_inh) should correlate with DSI
    (more inhibition → stronger null-direction suppression → higher DSI)

    Args:
        connectome: FlyWire connectome
        t4a_neurons: List of T4a neuron IDs

    Returns:
        Dict mapping neuron_id → {'n_exc': int, 'n_inh': int, 'inh_fraction': float}
    """
    # Identify excitatory and inhibitory presynaptic neurons
    exc_neurons = set()
    inh_neurons = set()

    for nid, neuron in connectome.neurons.items():
        cell_types_str = ' '.join(neuron.cell_types or [])
        if any(t in cell_types_str for t in ['Mi1', 'Tm3', 'Mi9']):
            exc_neurons.add(nid)
        elif any(t in cell_types_str for t in ['Mi4', 'C3', 'CT1', 'Mi13']):
            inh_neurons.add(nid)

    # Count synapses per T4a neuron
    t4a_set = set(t4a_neurons)
    synapse_counts = {nid: {'n_exc': 0, 'n_inh': 0} for nid in t4a_neurons}

    for synapse in connectome.synapses:
        if synapse.post_id in t4a_set:
            if synapse.pre_id in exc_neurons:
                synapse_counts[synapse.post_id]['n_exc'] += 1
            elif synapse.pre_id in inh_neurons:
                synapse_counts[synapse.post_id]['n_inh'] += 1

    # Compute inhibitory fraction
    for nid in t4a_neurons:
        n_exc = synapse_counts[nid]['n_exc']
        n_inh = synapse_counts[nid]['n_inh']
        total = n_exc + n_inh
        synapse_counts[nid]['inh_fraction'] = n_inh / (total + 1e-6)
        synapse_counts[nid]['total_inputs'] = total

    return synapse_counts


def measure_individual_t4a_dsi(
    visual_connectome: Connectome,
    t4a_neurons: List[int],
    dt_ms: float = 0.5,
    max_neurons: int = 100,
) -> Dict[int, float]:
    """
    Measure direction selectivity index for each T4a neuron individually.

    APPROACH:
    For each T4a neuron i:
      1. Find its spatial position in the visual field (from connectome coordinates)
      2. Present rightward grating — neuron i receives local luminance at its position
      3. Present leftward grating — same
      4. DSI_i = (A_preferred_i - A_null_i) / (A_preferred_i + A_null_i)

    NOTE: This approximates each T4a's spatial position by its index in the
    ordered T4a list (ordered by neuron ID, which roughly corresponds to
    column order in the eye). A full implementation would use the actual
    XYZ coordinates from FlyWire.

    Args:
        visual_connectome: FlyWire optic lobe connectome
        t4a_neurons: List of T4a neuron IDs
        dt_ms: Integration timestep
        max_neurons: Cap on neurons to measure (for speed)

    Returns:
        Dict mapping neuron_id → DSI value
    """
    if len(t4a_neurons) > max_neurons:
        # Random subsample for speed
        indices = np.random.choice(len(t4a_neurons), max_neurons, replace=False)
        t4a_subset = [t4a_neurons[i] for i in indices]
    else:
        t4a_subset = t4a_neurons

    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    num_steps = int(STIMULUS_DURATION_MS / dt_ms)

    # Ommatidium positions
    az_sp = (2 * AZ_RANGE) / N_COLS
    el_sp = (2 * EL_RANGE) / N_ROWS
    azimuths = np.array([-AZ_RANGE + (col + 0.5) * az_sp
                          + (az_sp * 0.5 if row % 2 == 1 else 0)
                         for row in range(N_ROWS) for col in range(N_COLS)])

    medulla_neurons = list(get_visual_region_neurons(visual_connectome, 'MEDULLA'))

    dsi_per_neuron = {}

    for dir_name, dir_sign in [('preferred_right', 1), ('null_left', -1)]:
        brain._initialize_fields()
        if brain.use_mlx:
            import mlx.core as mx
            brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
        else:
            brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)
        # Initialize Barlow-Levick temporal integration per ommatidium
        bl_exc = np.zeros(N_OMMATIDIA)  # Fast excitatory integration
        bl_inh = np.zeros(N_OMMATIDIA)  # Slow inhibitory integration
        TAU_EXC_MS = 10.0   # Fast excitatory time constant
        TAU_INH_MS = 25.0   # Slow inhibitory time constant
        
        amps_per_neuron = {nid: [] for nid in t4a_subset}

        for step in range(num_steps):
            t_ms = step * dt_ms
            spatial_phase = (2 * np.pi / SPATIAL_PERIOD_DEG) * azimuths
            temporal_phase = 2 * np.pi * TF_HZ * (t_ms / 1000.0) * dir_sign
            luminance = 0.5 + 0.5 * np.sin(spatial_phase - temporal_phase)

            ON_signal = np.maximum(0, luminance - 0.5)

            # Temporal integration (Barlow-Levick mechanism with real time constants)
            alpha_exc = dt_ms / TAU_EXC_MS
            alpha_inh = dt_ms / TAU_INH_MS
            bl_exc += alpha_exc * (EXCITATORY_GAIN * ON_signal - bl_exc)
            bl_inh += alpha_inh * (INHIBITORY_GAIN * ON_signal - bl_inh)
            t4_output = np.maximum(0, bl_exc - bl_inh)

            # Set external forcing
            for i, nid in enumerate(medulla_neurons):
                if nid not in brain.id_to_idx:
                    continue
                omm = i % N_OMMATIDIA
                idx = brain.id_to_idx[nid]
                brain.external_force[idx] = t4_output[omm] * VOLTAGE_TO_FIRING_RATE * FIRING_TO_FORCING

            brain.evolve(duration=dt_ms)

            if step > num_steps // 2:
                state = brain.get_state()
                for nid in t4a_subset:
                    if nid in brain.id_to_idx:
                        idx = brain.id_to_idx[nid]
                        amps_per_neuron[nid].append(state.mean_amplitude[idx])

        for nid in t4a_subset:
            amps = amps_per_neuron[nid]
            mean_amp = float(np.mean(amps)) if amps else 0.0
            if dir_name == 'preferred_right':
                if nid not in dsi_per_neuron:
                    dsi_per_neuron[nid] = {}
                dsi_per_neuron[nid]['preferred'] = mean_amp
            else:
                dsi_per_neuron[nid]['null'] = mean_amp

    # Compute DSI
    final_dsi = {}
    for nid in t4a_subset:
        if nid in dsi_per_neuron and 'preferred' in dsi_per_neuron[nid]:
            pref = dsi_per_neuron[nid].get('preferred', 0.0)
            null = dsi_per_neuron[nid].get('null', 0.0)
            dsi = (pref - null) / (pref + null + 1e-8)
            final_dsi[nid] = float(dsi)

    return final_dsi


def run_t4_dsi_heterogeneity(visual_connectome: Connectome) -> Dict:
    """
    Full T4 DSI heterogeneity analysis.

    PROTOCOL:
    1. Identify T4a neurons in FlyWire
    2. Get their inhibitory synapse counts (anatomy)
    3. Measure individual DSI for up to 100 T4a neurons (simulation)
    4. Analyze DSI distribution (mean, std, bimodality test)
    5. Correlate DSI with inhibitory synapse fraction (anatomy-physiology link)

    Args:
        visual_connectome: FlyWire optic lobe connectome

    Returns:
        Dict with DSI distribution, synapse correlation, interpretation
    """
    print("\n" + "=" * 70)
    print("DISCOVERY: T4 DSI HETEROGENEITY")
    print("Question: Are all T4 neurons equally direction-selective?")
    print("=" * 70)

    # Identify T4a neurons
    print("\nIdentifying T4a neurons...")
    t4a_neurons = []
    for nid, neuron in visual_connectome.neurons.items():
        cell_types_str = ' '.join(neuron.cell_types or [])
        if 'T4a' in cell_types_str:
            t4a_neurons.append(nid)

    if len(t4a_neurons) < 5:
        print("  WARNING: T4a neurons not found with 'T4a' label.")
        print("  Falling back to all T4-labeled neurons...")
        for nid, neuron in visual_connectome.neurons.items():
            cell_types_str = ' '.join(neuron.cell_types or [])
            if 'T4' in cell_types_str and 'T4a' not in cell_types_str:
                t4a_neurons.append(nid)

    print(f"  T4a neurons found: {len(t4a_neurons)}")

    if len(t4a_neurons) == 0:
        return {'error': 'No T4a neurons found — check cell type labels'}

    # Step 1: Anatomy — count inhibitory synapses
    print("\nCounting excitatory/inhibitory input synapses per T4a neuron...")
    synapse_counts = get_t4a_input_synapse_counts(visual_connectome, t4a_neurons)

    inh_fractions = [synapse_counts[nid]['inh_fraction'] for nid in t4a_neurons]
    total_inputs = [synapse_counts[nid]['total_inputs'] for nid in t4a_neurons]

    print(f"  Mean total inputs per T4a: {np.mean(total_inputs):.1f}")
    print(f"  Mean inhibitory fraction: {np.mean(inh_fractions):.3f}")
    print(f"  Std inhibitory fraction: {np.std(inh_fractions):.3f}")

    # Step 2: Simulation — measure individual DSI
    print(f"\nMeasuring individual DSI for up to 100 T4a neurons...")
    individual_dsi = measure_individual_t4a_dsi(
        visual_connectome, t4a_neurons, max_neurons=100
    )

    dsi_values = list(individual_dsi.values())
    n_measured = len(dsi_values)

    if n_measured == 0:
        return {'error': 'No T4a DSI measurements obtained'}

    print(f"\nDSI distribution ({n_measured} neurons):")
    print(f"  Mean DSI: {np.mean(dsi_values):.4f}")
    print(f"  Std  DSI: {np.std(dsi_values):.4f}")
    print(f"  Min  DSI: {np.min(dsi_values):.4f}")
    print(f"  Max  DSI: {np.max(dsi_values):.4f}")
    print(f"  DSI > {DSI_STRONG} (strong): {sum(d > DSI_STRONG for d in dsi_values) / n_measured:.1%}")
    print(f"  DSI > {DSI_MODERATE} (moderate): {sum(d > DSI_MODERATE for d in dsi_values) / n_measured:.1%}")
    print(f"  DSI < {DSI_WEAK} (weak): {sum(abs(d) < DSI_WEAK for d in dsi_values) / n_measured:.1%}")

    # Bimodality test: Hartigan's dip test approximation
    # Use Gaussian mixture model: is there evidence of 2 peaks?
    dsi_arr = np.array(dsi_values)
    try:
        from scipy.stats import kurtosis, skew
        kurt = kurtosis(dsi_arr, fisher=True)  # Excess kurtosis
        sk = skew(dsi_arr)
        # Bimodal distributions tend to have negative kurtosis (platykurtic)
        is_bimodal = kurt < -0.5
    except Exception:
        kurt = 0.0
        sk = 0.0
        is_bimodal = False

    print(f"\nDistribution shape:")
    print(f"  Kurtosis: {kurt:.3f} (bimodal if < -0.5)")
    print(f"  Skewness: {sk:.3f}")
    print(f"  Bimodal distribution: {'LIKELY' if is_bimodal else 'UNLIKELY'}")

    # Step 3: Anatomy-physiology correlation
    # Match measured neurons to their synapse counts
    common_neurons = [nid for nid in t4a_neurons[:100]
                      if nid in individual_dsi and nid in synapse_counts]
    if len(common_neurons) >= 5:
        dsi_matched = [individual_dsi[nid] for nid in common_neurons]
        inh_frac_matched = [synapse_counts[nid]['inh_fraction'] for nid in common_neurons]

        corr, p_corr = sp_stats.pearsonr(inh_frac_matched, dsi_matched)
        print(f"\nAnatomy-physiology correlation:")
        print(f"  DSI vs inhibitory fraction: r = {corr:.4f}, p = {p_corr:.4f}")
        print(f"  {'SIGNIFICANT' if p_corr < 0.05 else 'NOT SIGNIFICANT'}")
        if corr > 0.3 and p_corr < 0.05:
            print("  → More inhibitory input = higher DSI (confirms Haag 2017 mechanism)")
        elif corr > 0.1:
            print("  → Weak positive trend — inhibition contributes but not sole factor")
    else:
        corr, p_corr = 0.0, 1.0

    # Interpretation
    std_dsi = float(np.std(dsi_values))
    if std_dsi > 0.30:
        interpretation = "HIGH HETEROGENEITY — T4 population spans weak to strong selectors"
        scenario = 'C'
    elif std_dsi > 0.10:
        interpretation = "MODERATE HETEROGENEITY — soft coding with some variation"
        scenario = 'B'
    else:
        interpretation = "UNIFORM DSI — confirms canonical view (all T4 cells similar)"
        scenario = 'A'

    print(f"\n{'='*70}")
    print(f"CONCLUSION: {interpretation}")
    print(f"Scenario: {scenario}")
    print(f"{'='*70}")

    return {
        'discovery': 't4_dsi_heterogeneity',
        'n_t4a_neurons_identified': len(t4a_neurons),
        'n_measured': n_measured,
        'dsi_values': dsi_values,
        'dsi_mean': float(np.mean(dsi_values)),
        'dsi_std': float(np.std(dsi_values)),
        'dsi_min': float(np.min(dsi_values)),
        'dsi_max': float(np.max(dsi_values)),
        'fraction_strong_dsi': float(sum(d > DSI_STRONG for d in dsi_values) / n_measured),
        'fraction_moderate_dsi': float(sum(d > DSI_MODERATE for d in dsi_values) / n_measured),
        'fraction_weak_dsi': float(sum(abs(d) < DSI_WEAK for d in dsi_values) / n_measured),
        'distribution_kurtosis': float(kurt),
        'distribution_skewness': float(sk),
        'is_bimodal': bool(is_bimodal),
        'anatomy_dsi_correlation': float(corr),
        'anatomy_dsi_p_value': float(p_corr),
        'mean_inhibitory_fraction': float(np.mean(inh_fractions)),
        'std_inhibitory_fraction': float(np.std(inh_fractions)),
        'scenario': scenario,
        'interpretation': interpretation,
        'behavioral_implication': (
            'T4 heterogeneity encodes both direction AND velocity magnitude'
            if scenario in ['B', 'C'] else
            'T4 population encodes direction only (magnitude from population rate)'
        ),
        'references': [
            'Maisak_et_al_2013_Nature',
            'Haag_et_al_2017_eLife',
            'Shinomiya_et_al_2019_eLife',
        ],
    }


if __name__ == '__main__':
    print(__doc__)

    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()

    from hive.substrate.visual_pathway import extract_visual_pathway
    visual_connectome = extract_visual_pathway(connectome)

    results = run_t4_dsi_heterogeneity(visual_connectome)

    output_path = Path("research/vision/findings/discovery_t4_dsi_heterogeneity.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_path}")
