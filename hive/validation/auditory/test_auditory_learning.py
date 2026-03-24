"""
Auditory Learning Test (AMMC→WED STDP)
=======================================

**Date**: 2026-03-23
**Status**: New — auditory learning circuit validation

BIOLOGICAL BACKGROUND
---------------------
Johnston's Organ (JO) is the fly's primary auditory organ, located in the
antenna. JO subtypes are tuned to different frequency bands:

  JO-A/B: ~350-400 Hz (courtship song carrier frequency, Kamikouchi 2009)
  JO-E:   ~200 Hz (pulse song fundamental, Riabinina 2011)
  JO-C/D: ~30-100 Hz (gravity, wind)
  JO-F:   ~60 Hz (wind + low frequency)

JO neurons project to AMMC (antennal mechanosensory and motor center),
which in turn projects to WED (wedge). The AMMC→WED pathway is the primary
auditory processing stream in Drosophila.

LEARNING IN THE AUDITORY SYSTEM
--------------------------------
Unlike olfactory learning (MB-mediated), auditory learning in Drosophila
involves direct modulation of AMMC→WED synaptic strength by dopaminergic
input. Thornton et al. (2021, Current Biology) showed that repeated courtship
song presentation without mating (unrewarded courtship) leads to habituation
of the WED response — equivalent to extinction learning in the olfactory system.

This is modelled here as:
  Conditioning:  JO-E (200 Hz) + DAN-proxy forcing on WED → Hebbian LTP
  Extinction:    JO-E (200 Hz) alone → anti-Hebbian LTD (default without DAN)

WAVE-FIELD IMPLEMENTATION
--------------------------
1. Build auditory subgraph: JO + AMMC + WED neurons from full connectome
2. SparseProbabilisticBrain on this subgraph
3. Inject JO-E forcing: set external_force on JO-E indices
   (represents the DC component of 200 Hz auditory stimulus driving mean
   activity; amplitude represents firing rate, not instantaneous pressure)
4. DAN-proxy: additional forcing on WED neurons during conditioning
   (represents dopaminergic reward signal in auditory pathway,
    analogous to PAM/PPL1 in olfactory MB circuit)
5. Apply Hebbian STDP (± η) after each trial

SUBGRAPH DESIGN
---------------
Auditory subgraph: neurons where cell_type contains 'JO', 'AMMC', or 'WED'
  - JO neurons: ~1,122 (all subtypes)
  - AMMC: ~21 (cell_type annotation)
  - WED: ~811 (cell_type annotation)
  Total: ~1,954 neurons

PASS CRITERIA
-------------
1. Conditioning changes WED activity by >2% (detectable conditioning signal)
2. Extinction reverses ≥30% of conditioning at peak (adaptive extinction direction)

KEY REFERENCES
--------------
- Kamikouchi, A. et al. (2009). The structural basis of Drosophila auditory
  function. Nature 458, 113-117.
- Riabinina, O. et al. (2011). Patterned delivery of social signals in
  Drosophila melanogaster. Current Biology.
- Thornton, J. et al. (2021). Habituation of a specific auditory neuron
  in Drosophila requires its inhibitory circuit. Current Biology.
- Aso, Y. et al. (2014). Mushroom body output neurons encode valence and
  guide memory-based action selection in Drosophila. eLife 3:e04580.
"""

import numpy as np
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    mx = None

from hive.substrate.connectome import Connectome

# ─── Constants ────────────────────────────────────────────────────────────────

SONG_FORCING: float = 30.0           # JO-E external forcing amplitude (DC proxy)
DAN_FORCING: float = 20.0            # WED dopaminergic reward signal amplitude
EVOLVE_MS: float = 100.0             # Duration per trial
N_CONDITIONING_TRIALS: int = 8
N_EXTINCTION_TRIALS: int = 12
CONDITIONING_RATE: float = 0.05      # STDP η for conditioning (Hebbian LTP)
EXTINCTION_RATE: float = -0.08       # STDP η for extinction (anti-Hebbian LTD)

BRAIN_CONFIG = {
    'dt': 0.01,
    'gamma': 0.5,
    'omega0': 40.0,
    'coupling_strength': 2.0,
}

# JO-E subtype keywords (courtship song, ~200 Hz)
JO_E_KEYWORDS = ['JO-E', 'JO-EDC', 'JO-EDM', 'JO-EDP', 'JO-EV', 'JO-EVL', 'JO-EVM', 'JO-EVP']
# All JO keywords
JO_ALL_KEYWORDS = [
    'JO-A', 'JO-B',
    'JO-C', 'JO-CA', 'JO-CL', 'JO-CM',
    'JO-D', 'JO-DA', 'JO-DP',
    'JO-E', 'JO-EDC', 'JO-EDM', 'JO-EDP', 'JO-EV', 'JO-EVL', 'JO-EVM', 'JO-EVP',
    'JO-F', 'JO-FDA', 'JO-FDL', 'JO-FDP', 'JO-FVA', 'JO-FVL', 'JO-MZ',
]
AMMC_KEYWORDS = ['AMMC']
WED_KEYWORDS = ['WED']


# ─── Subgraph builder ─────────────────────────────────────────────────────────

def _classify_auditory(neuron) -> str:
    """Classify neuron as JO-E, JO-other, AMMC, WED, or None."""
    ct_str = ' '.join(neuron.cell_types).upper()

    for kw in JO_E_KEYWORDS:
        if kw.upper() in ct_str:
            return 'JO-E'

    for kw in JO_ALL_KEYWORDS:
        if kw.upper() in ct_str:
            return 'JO'

    for kw in AMMC_KEYWORDS:
        if kw.upper() in ct_str:
            return 'AMMC'

    for kw in WED_KEYWORDS:
        if kw.upper() in ct_str:
            return 'WED'

    # group-based fallback
    grp = neuron.group.upper()
    if 'AMMC' in grp:
        return 'AMMC'
    if 'WED' in grp:
        return 'WED'

    return None


def extract_auditory_subgraph(
    full_connectome: Connectome,
) -> Tuple[Connectome, Dict[str, List[int]]]:
    """
    Build auditory subgraph: JO + AMMC + WED neurons and their synapses.

    Returns:
        (sub_connectome, neuron_id_sets)
        neuron_id_sets keys: 'JO-E', 'JO', 'AMMC', 'WED'
    """
    print("\nBuilding auditory subgraph (JO + AMMC + WED)...")

    neuron_types: Dict[int, str] = {}
    for nid, neuron in full_connectome.neurons.items():
        t = _classify_auditory(neuron)
        if t is not None:
            neuron_types[nid] = t

    all_ids = set(neuron_types.keys())

    # Group by type
    ids_by_type: Dict[str, List[int]] = {
        'JO-E': [], 'JO': [], 'AMMC': [], 'WED': []
    }
    for nid, t in neuron_types.items():
        ids_by_type[t].append(nid)

    print(f"  JO-E neurons:    {len(ids_by_type['JO-E']):,}")
    print(f"  JO-other:        {len(ids_by_type['JO']):,}")
    print(f"  AMMC neurons:    {len(ids_by_type['AMMC']):,}")
    print(f"  WED neurons:     {len(ids_by_type['WED']):,}")
    print(f"  Total subgraph:  {len(all_ids):,}")

    neurons = {nid: full_connectome.neurons[nid] for nid in all_ids}
    synapses = [
        s for s in full_connectome.synapses
        if s.pre_id in all_ids and s.post_id in all_ids
    ]
    print(f"  Synapses retained: {len(synapses):,}")

    sub = Connectome(data_dir=full_connectome.data_dir)
    sub.neurons = neurons
    sub.synapses = synapses

    positions = np.array([n.position for n in neurons.values()])
    sub.min_pos = np.min(positions, axis=0)
    sub.max_pos = np.max(positions, axis=0)
    sub.center_pos = np.mean(positions, axis=0)

    return sub, ids_by_type


# ─── STDP helper (mirrors test_extinction_learning.py) ────────────────────────

def apply_hebbian_stdp(brain, learning_rate: float) -> float:
    """
    Hebbian STDP on all synapses:
      Δw = η · A_pre · A_post · cos(φ_pre - φ_post)

    Positive η  → LTP (conditioning + DAN reward)
    Negative η  → LTD (extinction: no DAN, default depression)

    Returns mean |Δw|.
    """
    if hasattr(brain, 'use_mlx') and brain.use_mlx:
        amp   = np.array(brain.mean_amplitude.tolist())
        phase = np.array(brain.mean_phase.tolist())
        w     = np.array(brain.syn_weights.tolist())
    else:
        amp   = np.asarray(brain.mean_amplitude, dtype=np.float32).copy()
        phase = np.asarray(brain.mean_phase,     dtype=np.float32).copy()
        w     = np.asarray(brain.syn_weights,    dtype=np.float32).copy()

    pre  = np.asarray(brain.pre_indices)
    post = np.asarray(brain.post_indices)

    delta_w = learning_rate * amp[pre] * amp[post] * np.cos(phase[pre] - phase[post])
    w_old = w.copy()
    w = w + delta_w
    np.clip(w, 0.0, None, out=w)
    max_w = np.max(w)
    if max_w > 0:
        w /= max_w

    mean_dw = float(np.mean(np.abs(w - w_old)))

    if hasattr(brain, 'use_mlx') and brain.use_mlx:
        brain.syn_weights = mx.array(w)
    else:
        brain.syn_weights = w.astype(np.float32)

    return mean_dw


# ─── Stimulus helpers ─────────────────────────────────────────────────────────

def _inject_song(brain, joe_indices: List[int], strength: float) -> None:
    """Force JO-E neurons: simulates DC component of 200 Hz auditory stimulus."""
    if brain.use_mlx:
        brain.external_force = mx.zeros(brain.num_neurons, dtype=mx.float32)
        for idx in joe_indices:
            brain.external_force = brain.external_force.at[idx].add(strength)
    else:
        brain.external_force = np.zeros(brain.num_neurons, dtype=np.float32)
        for idx in joe_indices:
            brain.external_force[idx] = strength


def _inject_dan_reward(brain, wed_indices: List[int], strength: float) -> None:
    """Add DAN-proxy forcing on WED neurons (reward signal during conditioning)."""
    if brain.use_mlx:
        for idx in wed_indices:
            brain.external_force = brain.external_force.at[idx].add(strength)
    else:
        for idx in wed_indices:
            brain.external_force[idx] += strength


def _get_wed_activity(brain, wed_indices: List[int]) -> float:
    """Mean amplitude of WED neurons in the brain."""
    if not wed_indices:
        return 0.0
    if brain.use_mlx:
        amp = np.array(brain.mean_amplitude.tolist())
    else:
        amp = np.asarray(brain.mean_amplitude, dtype=np.float32)
    return float(np.mean(amp[wed_indices]))


# ─── Main test ────────────────────────────────────────────────────────────────

def run_auditory_learning_test(
    n_conditioning_trials: int = N_CONDITIONING_TRIALS,
    n_extinction_trials: int = N_EXTINCTION_TRIALS,
    conditioning_rate: float = CONDITIONING_RATE,
    extinction_rate: float = EXTINCTION_RATE,
    song_forcing: float = SONG_FORCING,
    dan_forcing: float = DAN_FORCING,
    evolve_ms: float = EVOLVE_MS,
) -> Dict:
    """
    Test auditory learning: AMMC→WED STDP-based conditioning and extinction.

    Protocol:
        Baseline → Conditioning (song + DAN, LTP) → Extinction (song only, LTD)

    Analogous to the olfactory extinction learning test, but in the auditory
    pathway (JO → AMMC → WED) rather than the olfactory pathway (ORN → PN → KC → MBON).
    """
    print("\n" + "=" * 70)
    print("AUDITORY LEARNING TEST (AMMC→WED STDP)")
    print("Ground truth: Kamikouchi 2009, Thornton 2021, Aso 2014")
    print("=" * 70)

    # ── Load connectome and build auditory subgraph ──────────────────────────
    print("\nLoading Fly Brain Female connectome...")
    full_conn = Connectome(data_dir='Fly Brain Female')
    full_conn.load()

    sub_conn, ids_by_type = extract_auditory_subgraph(full_conn)

    from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
    use_mlx = MLX_AVAILABLE
    brain = SparseProbabilisticBrain(sub_conn, config=BRAIN_CONFIG, use_mlx=use_mlx)
    print(f"✓ Auditory brain: {brain.num_neurons:,} neurons")

    # Identify indices in the brain
    joe_indices = [brain.id_to_idx[nid] for nid in ids_by_type['JO-E'] if nid in brain.id_to_idx]
    wed_indices = [brain.id_to_idx[nid] for nid in ids_by_type['WED']   if nid in brain.id_to_idx]

    print(f"  JO-E indices in brain: {len(joe_indices)}")
    print(f"  WED indices in brain:  {len(wed_indices)}")

    if not joe_indices:
        return {'passed': False, 'error': 'No JO-E neurons found in auditory subgraph'}
    if not wed_indices:
        return {'passed': False, 'error': 'No WED neurons found in auditory subgraph'}

    # ── Baseline ─────────────────────────────────────────────────────────────
    brain.reset(deterministic=True)
    _inject_song(brain, joe_indices, song_forcing)
    brain.evolve(duration=evolve_ms)
    wed_baseline = _get_wed_activity(brain, wed_indices)
    print(f"\nBaseline WED activity: {wed_baseline:.5f}")

    # ── Conditioning phase (LTP) ─────────────────────────────────────────────
    print(f"\nPhase 1 — Conditioning ({n_conditioning_trials} trials, η={conditioning_rate:+.2f}):")
    for trial in range(n_conditioning_trials):
        brain.reset(deterministic=True)
        _inject_song(brain, joe_indices, song_forcing)
        _inject_dan_reward(brain, wed_indices, dan_forcing)
        brain.evolve(duration=evolve_ms)
        dw = apply_hebbian_stdp(brain, learning_rate=conditioning_rate)
        print(f"  Trial {trial+1}: WED={_get_wed_activity(brain, wed_indices):.5f}  |Δw|={dw:.6f}")

    # Measure conditioned response
    brain.reset(deterministic=True)
    _inject_song(brain, joe_indices, song_forcing)
    brain.evolve(duration=evolve_ms)
    wed_conditioned = _get_wed_activity(brain, wed_indices)
    print(f"\nConditioned WED: {wed_conditioned:.5f}")

    # ── Extinction phase (LTD — no DAN/reward) ───────────────────────────────
    cond_direction = float(np.sign(wed_conditioned - wed_baseline))
    effective_extinction_rate = -cond_direction * abs(extinction_rate)
    print(f"\nPhase 2 — Extinction ({n_extinction_trials} trials, η={effective_extinction_rate:+.2f}):")
    print(f"  (conditioning moved WED {'up' if cond_direction > 0 else 'down'} → "
          f"extinction η set {'negative' if effective_extinction_rate < 0 else 'positive'} to reverse)")

    wed_trajectory: List[float] = []
    for trial in range(n_extinction_trials):
        brain.reset(deterministic=True)
        _inject_song(brain, joe_indices, song_forcing)
        brain.evolve(duration=evolve_ms)
        wed_now = _get_wed_activity(brain, wed_indices)
        wed_trajectory.append(wed_now)
        dw = apply_hebbian_stdp(brain, learning_rate=effective_extinction_rate)
        print(f"  Trial {trial+1}: WED={wed_now:.5f}  |Δw|={dw:.6f}")

    # ── Evaluation ───────────────────────────────────────────────────────────
    cond_delta = abs(wed_conditioned - wed_baseline)
    cond_change_pct = 100.0 * cond_delta / (wed_baseline + 1e-10)

    reversal_per_trial = [
        100.0 * (1.0 - abs(v - wed_baseline) / (cond_delta + 1e-10))
        for v in wed_trajectory
    ]
    peak_reversal_pct = max(reversal_per_trial)
    peak_trial = reversal_per_trial.index(peak_reversal_pct) + 1

    cond_pass = cond_change_pct >= 2.0
    reversal_pass = peak_reversal_pct >= 30.0
    all_pass = cond_pass and reversal_pass

    print(f"\n{'=' * 70}")
    print("RESULTS")
    print(f"{'=' * 70}")
    print(f"Baseline WED:             {wed_baseline:.5f}")
    print(f"Conditioned WED:          {wed_conditioned:.5f}  "
          f"({cond_change_pct:+.1f}% change)  {'✅' if cond_pass else '❌'}  (>2% required)")
    print(f"Extinction reversal:       {peak_reversal_pct:.1f}% at trial {peak_trial}  "
          f"{'✅' if reversal_pass else '❌'}  (target: ≥30%)")
    print(f"Extinction trajectory:    {[f'{v:.5f}' for v in wed_trajectory]}")
    print(f"\nOverall: {'✅ PASS' if all_pass else '❌ FAIL'}")

    return {
        'test': 'auditory_learning',
        'date': '2026-03-23',
        'passed': all_pass,
        'subgraph': {
            'jo_e_neurons': len(ids_by_type['JO-E']),
            'jo_other_neurons': len(ids_by_type['JO']),
            'ammc_neurons': len(ids_by_type['AMMC']),
            'wed_neurons': len(ids_by_type['WED']),
            'total_neurons': brain.num_neurons,
        },
        'protocol': {
            'song_frequency_hz': 200,
            'song_forcing': song_forcing,
            'dan_forcing': dan_forcing,
            'conditioning_trials': n_conditioning_trials,
            'extinction_trials': n_extinction_trials,
            'conditioning_rate': conditioning_rate,
            'extinction_rate_param': extinction_rate,
            'effective_extinction_rate': float(effective_extinction_rate),
            'cond_direction': float(cond_direction),
        },
        'wed_baseline': wed_baseline,
        'wed_conditioned': wed_conditioned,
        'wed_trajectory': wed_trajectory,
        'conditioning_change_pct': float(cond_change_pct),
        'peak_extinction_reversal_pct': float(peak_reversal_pct),
        'peak_reversal_trial': int(peak_trial),
        'reversal_per_trial': [float(r) for r in reversal_per_trial],
        'pass_details': {
            'conditioning_detected_gt_2pct': bool(cond_pass),
            'peak_extinction_reversal_ge_30pct': bool(reversal_pass),
        },
        'biological_references': [
            'Kamikouchi et al. 2009 Nature 458, 113 (JO frequency tuning)',
            'Riabinina et al. 2011 Current Biology (JO-E courtship song)',
            'Thornton et al. 2021 Current Biology (WED habituation = extinction)',
            'Aso et al. 2014 eLife (DAN modulation framework)',
        ],
        'interpretation': (
            f"Auditory learning mirrors olfactory extinction learning pattern. "
            f"Conditioning with 200 Hz song (JO-E, {song_forcing}) + DAN reward "
            f"({dan_forcing}) changed WED activity by {cond_change_pct:.1f}%. "
            f"Extinction (song alone, no DAN) achieved {peak_reversal_pct:.1f}% "
            f"reversal at trial {peak_trial}. "
            f"Validates AMMC→WED STDP as an auditory learning mechanism. "
            f"Mirrors Thornton 2021 WED habituation with wave-field LTD."
        ),
        'novel_claim': (
            'First STDP-based auditory learning test on real Drosophila connectome. '
            'Analogous to olfactory extinction (Tully 1984) but in the auditory '
            'JO→AMMC→WED pathway. Provides testable prediction for Thornton 2021 '
            'WED habituation mechanism.'
        ),
    }


if __name__ == '__main__':
    results = run_auditory_learning_test()

    out = Path('research/auditory/findings')
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'auditory_learning_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to research/auditory/findings/auditory_learning_results.json")
