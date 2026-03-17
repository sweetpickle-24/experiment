"""
Test Decorrelation in Visual System

Tests if similar wavelengths produce anticorrelated medulla patterns.

Setup:
- Input: Similar wavelengths (e.g., 450nm vs 480nm blue-cyan)
- Photoreceptor correlation: r = +0.75 (similar input)
- Expected: Medulla pattern correlation r < 0 (anticorrelated)

Mechanism: Same as olfaction
- Random lamina→medulla connectivity (expansion 5,000→40,000)
- High threshold sparse activation
- Competition → anticorrelation
"""

import numpy as np
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from scipy.stats import pearsonr

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import get_visual_region_neurons
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.vision.spectral_stimuli import SpectralStimulusGenerator


def test_decorrelation_vision(
    visual_connectome: Connectome,
    similarity_threshold: float = 30.0,
    simulation_duration_ms: float = 100.0
) -> Dict:
    """
    Test decorrelation between similar wavelengths.
    
    Args:
        visual_connectome: Optic lobe connectome
        similarity_threshold: Wavelength similarity (nm)
        simulation_duration_ms: Simulation duration
    
    Returns:
        Dictionary with decorrelation results
    """
    print("\n" + "="*70)
    print("DECORRELATION TEST - VISION")
    print("="*70)
    
    # Initialize
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    generator = SpectralStimulusGenerator()
    
    # Get medulla neurons (where decorrelation should occur)
    medulla_neurons = get_visual_region_neurons(visual_connectome, 'MEDULLA')
    medulla_indices = [brain.id_to_idx[nid] for nid in medulla_neurons if nid in brain.id_to_idx]
    
    print(f"Medulla neurons: {len(medulla_neurons):,}")
    print(f"Similarity threshold: ±{similarity_threshold} nm")
    
    # Test pairs of similar wavelengths
    test_wavelengths = [400, 450, 500, 550, 600]
    
    results = {
        'metadata': {
            'similarity_threshold_nm': similarity_threshold,
            'medulla_neurons': len(medulla_neurons),
            'test_wavelengths': test_wavelengths
        },
        'wavelength_pairs': []
    }
    
    print(f"\nTesting {len(test_wavelengths)} reference wavelengths...")
    
    all_input_correlations = []
    all_medulla_correlations = []
    
    for ref_wl in test_wavelengths:
        # Get similar wavelengths
        similar_wls = generator.get_similar_wavelengths(ref_wl, similarity_threshold)
        
        if len(similar_wls) == 0:
            continue
        
        print(f"\n{ref_wl}nm → similar: {[int(w) for w in similar_wls[:3]]}")
        
        # Generate stimuli
        ref_stimulus = generator.generate_pure_wavelengths()[
            list(generator.pure_wavelengths).index(ref_wl)
        ]
        
        for sim_wl in similar_wls[:3]:  # Test top 3 similar
            sim_stimulus = generator.generate_pure_wavelengths()[
                list(generator.pure_wavelengths).index(sim_wl)
            ]
            
            # Measure input correlation (photoreceptor patterns)
            input_corr, _ = pearsonr(
                ref_stimulus.photoreceptor_pattern.flatten(),
                sim_stimulus.photoreceptor_pattern.flatten()
            )
            
            # Simulate both stimuli
            ref_pattern = simulate_stimulus(brain, ref_stimulus, medulla_indices, simulation_duration_ms)
            sim_pattern = simulate_stimulus(brain, sim_stimulus, medulla_indices, simulation_duration_ms)
            
            # Measure medulla correlation
            medulla_corr, _ = pearsonr(ref_pattern, sim_pattern)
            
            all_input_correlations.append(input_corr)
            all_medulla_correlations.append(medulla_corr)
            
            pair_result = {
                'wavelength_1': int(ref_wl),
                'wavelength_2': int(sim_wl),
                'distance_nm': abs(ref_wl - sim_wl),
                'input_correlation': float(input_corr),
                'medulla_correlation': float(medulla_corr),
                'decorrelated': medulla_corr < 0
            }
            results['wavelength_pairs'].append(pair_result)
            
            print(f"  {ref_wl}nm vs {int(sim_wl)}nm: input r={input_corr:.3f} → medulla r={medulla_corr:.3f}")
    
    # Summary statistics
    all_input_correlations = np.array(all_input_correlations)
    all_medulla_correlations = np.array(all_medulla_correlations)
    
    mean_input_corr = np.mean(all_input_correlations)
    mean_medulla_corr = np.mean(all_medulla_correlations)
    
    num_decorrelated = np.sum(all_medulla_correlations < 0)
    pct_decorrelated = 100.0 * num_decorrelated / len(all_medulla_correlations)
    
    results['summary'] = {
        'mean_input_correlation': float(mean_input_corr),
        'mean_medulla_correlation': float(mean_medulla_corr),
        'num_pairs_tested': len(all_medulla_correlations),
        'num_decorrelated': int(num_decorrelated),
        'percent_decorrelated': float(pct_decorrelated),
        'decorrelation_strength': float(mean_input_corr - mean_medulla_corr)
    }
    
    # Check if decorrelation occurred
    # Target: mean medulla correlation < 0 (anticorrelated)
    target_correlation = 0.0
    passed = mean_medulla_corr < target_correlation
    
    print("\n" + "="*70)
    print("DECORRELATION RESULTS")
    print("="*70)
    print(f"\nMean input correlation: {mean_input_corr:.3f}")
    print(f"Mean medulla correlation: {mean_medulla_corr:.3f}")
    print(f"Decorrelation strength: {mean_input_corr - mean_medulla_corr:.3f}")
    print(f"\nPairs decorrelated: {num_decorrelated}/{len(all_medulla_correlations)} ({pct_decorrelated:.1f}%)")
    print(f"Target: r < {target_correlation}")
    
    if passed:
        print("\n✅ DECORRELATION TEST PASSED")
        print("Similar wavelengths produce anticorrelated medulla patterns")
    else:
        print("\n⚠️ DECORRELATION TEST: WEAK")
        print("Medulla patterns still positively correlated")
    
    results['test_passed'] = passed
    print("="*70)
    
    return results


def simulate_stimulus(
    brain: SparseProbabilisticBrain,
    stimulus,
    medulla_indices: List[int],
    duration_ms: float
) -> np.ndarray:
    """Simulate stimulus and return medulla activation pattern."""
    brain._initialize_fields()
    
    # Convert to forcing
    from hive.validation.vision.test_sparse_coding import convert_photoreceptor_to_forcing
    lamina_neurons = list(brain.neuron_ids)[:800]
    forcing = convert_photoreceptor_to_forcing(stimulus.photoreceptor_pattern, lamina_neurons)
    
    # Simulate
    num_steps = int(duration_ms / brain.dt)
    for _ in range(num_steps):
        brain.step(forcing)
    
    # Extract medulla pattern
    pattern = brain.mean_amplitude[medulla_indices]
    return pattern


if __name__ == "__main__":
    print("Testing Decorrelation in Vision\n")
    
    # Load visual connectome
    visual_conn = Connectome(data_dir="data/vision/optic_lobe")
    visual_conn.load_json("data/vision/optic_lobe/flywire_optic_lobe.json")
    
    # Run test
    results = test_decorrelation_vision(visual_conn, similarity_threshold=30.0)
    
    print("\n✓ Test complete")
