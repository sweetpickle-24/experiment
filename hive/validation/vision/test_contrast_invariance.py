"""
Test Contrast Invariance in Visual System

Tests if wavelength representation is stable across intensity changes.

Setup:
- Same wavelength (e.g., 500nm green) at 10 intensities (1-100%)
- Measure medulla pattern correlation across intensities

Target: r > 0.70 (like concentration invariance in smell)

Mechanisms:
- Photoreceptor adaptation (calcium feedback in TRP channels)
- Lamina gain control (L1-L3 lateral inhibition)
- Medulla normalization
"""

import numpy as np
import sys
from pathlib import Path
from typing import Dict, List
from scipy.stats import pearsonr

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import get_visual_region_neurons
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.vision.spectral_stimuli import SpectralStimulusGenerator


def test_contrast_invariance_vision(
    visual_connectome: Connectome,
    test_wavelengths: List[float] = [450, 500, 600],
    num_intensities: int = 10,
    simulation_duration_ms: float = 100.0
) -> Dict:
    """
    Test contrast invariance across intensity changes.
    
    Args:
        visual_connectome: Optic lobe connectome
        test_wavelengths: Wavelengths to test (nm)
        num_intensities: Number of intensity levels
        simulation_duration_ms: Simulation duration
    
    Returns:
        Dictionary with contrast invariance results
    """
    print("\n" + "="*70)
    print("CONTRAST INVARIANCE TEST - VISION")
    print("="*70)
    
    # Initialize
    brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
    generator = SpectralStimulusGenerator()
    
    # Get medulla neurons
    medulla_neurons = get_visual_region_neurons(visual_connectome, 'MEDULLA')
    medulla_indices = [brain.id_to_idx[nid] for nid in medulla_neurons if nid in brain.id_to_idx]
    
    print(f"Medulla neurons: {len(medulla_neurons):,}")
    print(f"Test wavelengths: {test_wavelengths}")
    print(f"Intensity levels: {num_intensities}")
    
    results = {
        'metadata': {
            'test_wavelengths': test_wavelengths,
            'num_intensities': num_intensities,
            'medulla_neurons': len(medulla_neurons)
        },
        'wavelength_results': []
    }
    
    all_correlations = []
    
    for wavelength in test_wavelengths:
        print(f"\n{wavelength}nm:")
        
        # Generate intensity series
        intensity_series = generator.generate_intensity_series(
            wavelength,
            num_intensities=num_intensities,
            intensity_range=(0.1, 1.0)
        )
        
        # Simulate all intensities
        patterns = []
        intensities = []
        
        for stimulus in intensity_series:
            pattern = simulate_stimulus_vision(
                brain, stimulus, medulla_indices, simulation_duration_ms
            )
            patterns.append(pattern)
            intensities.append(stimulus.intensity)
        
        # Compute pairwise correlations
        correlations = []
        for i in range(len(patterns)):
            for j in range(i+1, len(patterns)):
                if np.std(patterns[i]) > 0 and np.std(patterns[j]) > 0:
                    corr, _ = pearsonr(patterns[i], patterns[j])
                    correlations.append(corr)
                    
                    intensity_ratio = intensities[j] / intensities[i]
                    if intensity_ratio >= 2.0:  # Log major intensity changes
                        print(f"  {intensities[i]:.2f}x vs {intensities[j]:.2f}x ({intensity_ratio:.1f}×): r={corr:.3f}")
        
        if len(correlations) > 0:
            mean_corr = np.mean(correlations)
            std_corr = np.std(correlations)
            min_corr = np.min(correlations)
            
            all_correlations.extend(correlations)
            
            wl_result = {
                'wavelength_nm': int(wavelength),
                'mean_correlation': float(mean_corr),
                'std_correlation': float(std_corr),
                'min_correlation': float(min_corr),
                'num_comparisons': len(correlations)
            }
            results['wavelength_results'].append(wl_result)
            
            print(f"  Mean correlation: {mean_corr:.3f} ± {std_corr:.3f}")
            print(f"  Min correlation: {min_corr:.3f}")
    
    # Overall statistics
    all_correlations = np.array(all_correlations)
    overall_mean = np.mean(all_correlations)
    overall_std = np.std(all_correlations)
    overall_min = np.min(all_correlations)
    
    results['summary'] = {
        'mean_correlation': float(overall_mean),
        'std_correlation': float(overall_std),
        'min_correlation': float(overall_min),
        'total_comparisons': len(all_correlations)
    }
    
    # Check against target (r > 0.70 like concentration invariance)
    target_correlation = 0.70
    passed = overall_mean >= target_correlation
    
    print("\n" + "="*70)
    print("CONTRAST INVARIANCE RESULTS")
    print("="*70)
    print(f"\nOverall mean correlation: {overall_mean:.3f} ± {overall_std:.3f}")
    print(f"Min correlation: {overall_min:.3f}")
    print(f"Target: r > {target_correlation}")
    
    if passed:
        print("\n✅ CONTRAST INVARIANCE TEST PASSED")
        print("Wavelength representation stable across intensity changes")
    else:
        print("\n⚠️ CONTRAST INVARIANCE TEST: WEAK")
        print(f"Correlation {overall_mean:.3f} below target {target_correlation}")
    
    results['test_passed'] = passed
    print("="*70)
    
    return results


def simulate_stimulus_vision(
    brain: SparseProbabilisticBrain,
    stimulus,
    medulla_indices: List[int],
    duration_ms: float
) -> np.ndarray:
    """Simulate stimulus and return medulla pattern."""
    brain._initialize_fields()
    
    from hive.validation.vision.test_sparse_coding import convert_photoreceptor_to_forcing
    lamina_neurons = list(brain.neuron_ids)[:800]
    forcing = convert_photoreceptor_to_forcing(stimulus.photoreceptor_pattern, lamina_neurons)
    
    num_steps = int(duration_ms / brain.dt)
    for _ in range(num_steps):
        brain.step(forcing)
    
    return brain.mean_amplitude[medulla_indices]


if __name__ == "__main__":
    print("Testing Contrast Invariance in Vision\n")
    
    # Load visual connectome
    visual_conn = Connectome(data_dir="data/vision/optic_lobe")
    visual_conn.load_json("data/vision/optic_lobe/flywire_optic_lobe.json")
    
    # Run test
    results = test_contrast_invariance_vision(
        visual_conn,
        test_wavelengths=[450, 500, 600],
        num_intensities=10
    )
    
    print("\n✓ Test complete")
