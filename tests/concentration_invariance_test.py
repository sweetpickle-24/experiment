#!/usr/bin/env python3
"""
Concentration Invariance Test for Olfactory System

Tests whether Kenyon Cell identity (which KCs are active) remains constant
across different odor concentrations. This is a key biological principle:
same odor should activate same KCs regardless of concentration strength.

This addresses a critical validation gap mentioned in the manuscript.

Author: [Your Name]
Date: March 13, 2026
"""

import argparse
import numpy as np
import json
import time
from pathlib import Path

# Import simulation components
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import (
    assert_reproducible_backend, log_path, results_path, set_seed, write_results,
)

from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.data.door_client import DoorClient

# Three odorants that resolve against the DoOR matrix.
#
# The third entry was 'isoamyl acetate', which is the same molecule as
# isopentyl_acetate but is not a key in the matrix. Before 2026-09-03 that miss
# returned a zero vector, and a zero pattern correlates with itself at exactly
# 1.0 at every concentration, so this odorant contributed a perfect score at
# all ten concentration pairs without simulating anything. It is now named as
# the matrix names it. See ODOR_AUDIT.md.
TEST_ODORS = [
    'benzaldehyde',        # aromatic aldehyde
    '2-heptanone',         # aliphatic methyl ketone
    'isopentyl_acetate',   # branched acetate ester (a.k.a. isoamyl acetate)
]

DEFAULT_SEED = 42

def compute_pattern_correlation(pattern1, pattern2, threshold=0.01):
    """
    Compute correlation between two KC activity patterns.
    
    Uses binary threshold to define "active" neurons, then computes
    correlation of binary patterns and continuous patterns.
    
    Returns:
        binary_corr: Correlation of thresholded (0/1) patterns
        continuous_corr: Correlation of raw amplitude values
        jaccard: Jaccard similarity of active neuron sets
    """
    # Binary patterns
    active1 = (pattern1 > threshold).astype(float)
    active2 = (pattern2 > threshold).astype(float)
    
    # Binary correlation
    if np.std(active1) > 0 and np.std(active2) > 0:
        binary_corr = np.corrcoef(active1, active2)[0, 1]
    else:
        binary_corr = 1.0 if np.allclose(active1, active2) else 0.0
    
    # Continuous correlation
    if np.std(pattern1) > 0 and np.std(pattern2) > 0:
        continuous_corr = np.corrcoef(pattern1, pattern2)[0, 1]
    else:
        continuous_corr = 1.0 if np.allclose(pattern1, pattern2) else 0.0
    
    # Jaccard similarity (intersection over union of active neurons)
    intersection = np.sum(np.logical_and(active1, active2))
    union = np.sum(np.logical_or(active1, active2))
    jaccard = intersection / union if union > 0 else 1.0
    
    return {
        'binary_correlation': float(binary_corr),
        'continuous_correlation': float(continuous_corr),
        'jaccard_similarity': float(jaccard)
    }


def test_single_odor_concentrations(brain, odor_name, glomerular_pattern, 
                                    concentrations, duration_ms=100.0):
    """
    Test one odor at multiple concentrations.
    
    Args:
        brain: SparseProbabilisticBrain instance
        odor_name: Name of the odor
        glomerular_pattern: 20-channel base pattern
        concentrations: List of concentration multipliers (e.g., [0.1, 0.5, 1.0, 5.0, 10.0])
        duration_ms: Simulation duration in milliseconds
        
    Returns:
        results: Dict with KC patterns for each concentration
    """
    print(f"\n{'='*60}")
    print(f"Testing odor: {odor_name}")
    print(f"Concentrations: {concentrations}")
    print(f"{'='*60}")
    
    results = {
        'odor': odor_name,
        'concentrations': {},
        'correlations': {}
    }
    
    # Test each concentration
    for conc in concentrations:
        print(f"\n  Concentration: {conc}× baseline...")
        
        # Reset brain state to deterministic initial conditions
        brain.reset(deterministic=True)
        
        # Inject odor with LOGARITHMIC concentration scaling
        # This prevents saturation at high concentrations
        base_strength = 50.0
        # Use log scaling: log10(1 + 10*conc) maps 0.1→1.0, 1.0→11, 10.0→101
        scaled_strength = base_strength * np.log10(1 + 10 * conc)
        brain.inject_odor(glomerular_pattern, strength=scaled_strength)
        
        # Simulate
        start = time.time()
        brain.evolve(duration=duration_ms)
        elapsed = time.time() - start
        
        # Extract KC activity WITH normalization (mimics APL feedback)
        kc_activity = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
        
        # Compute sparsity
        threshold = 0.01
        active_kcs = np.sum(kc_activity > threshold)
        total_kcs = len(kc_activity)
        sparsity = active_kcs / total_kcs
        
        print(f"    Simulation time: {elapsed:.2f}s")
        print(f"    Active KCs: {active_kcs}/{total_kcs} ({sparsity*100:.2f}%)")
        print(f"    Mean amplitude: {np.mean(kc_activity):.4f}")
        print(f"    Max amplitude: {np.max(kc_activity):.4f}")
        
        # Store results
        results['concentrations'][conc] = {
            'kc_pattern': kc_activity.tolist() if hasattr(kc_activity, 'tolist') else list(kc_activity),
            'active_count': int(active_kcs),
            'sparsity': float(sparsity),
            'mean_amplitude': float(np.mean(kc_activity)),
            'max_amplitude': float(np.max(kc_activity)),
            'simulation_time_sec': float(elapsed)
        }
    
    # Compute cross-concentration correlations
    conc_list = sorted(concentrations)
    print(f"\n  Computing pattern correlations...")
    
    for i, conc1 in enumerate(conc_list):
        for conc2 in conc_list[i+1:]:
            pattern1 = np.array(results['concentrations'][conc1]['kc_pattern'])
            pattern2 = np.array(results['concentrations'][conc2]['kc_pattern'])
            
            corr = compute_pattern_correlation(pattern1, pattern2)
            
            key = f"{conc1}x_vs_{conc2}x"
            results['correlations'][key] = corr
            
            print(f"    {key}:")
            print(f"      Binary correlation: {corr['binary_correlation']:.4f}")
            print(f"      Jaccard similarity: {corr['jaccard_similarity']:.4f}")
    
    return results


def analyze_concentration_invariance(all_results):
    """
    Analyze overall concentration invariance across all odors.
    
    Biological expectation: Correlations >0.7 indicate good concentration invariance.
    """
    print(f"\n{'='*60}")
    print("CONCENTRATION INVARIANCE ANALYSIS")
    print(f"{'='*60}\n")
    
    # Collect all pairwise correlations
    all_binary_corrs = []
    all_jaccard_sims = []
    
    for odor_name, odor_results in all_results.items():
        print(f"Odor: {odor_name}")
        
        for comparison, corr_data in odor_results['correlations'].items():
            binary_corr = corr_data['binary_correlation']
            jaccard_sim = corr_data['jaccard_similarity']
            
            all_binary_corrs.append(binary_corr)
            all_jaccard_sims.append(jaccard_sim)
            
            print(f"  {comparison}: binary={binary_corr:.3f}, jaccard={jaccard_sim:.3f}")
        print()
    
    # Summary statistics
    print(f"{'='*60}")
    print("SUMMARY STATISTICS")
    print(f"{'='*60}\n")
    
    print(f"Binary Correlation (thresholded KC patterns):")
    print(f"  Mean: {np.mean(all_binary_corrs):.4f}")
    print(f"  Std:  {np.std(all_binary_corrs):.4f}")
    print(f"  Min:  {np.min(all_binary_corrs):.4f}")
    print(f"  Max:  {np.max(all_binary_corrs):.4f}")
    print()
    
    print(f"Jaccard Similarity (active KC overlap):")
    print(f"  Mean: {np.mean(all_jaccard_sims):.4f}")
    print(f"  Std:  {np.std(all_jaccard_sims):.4f}")
    print(f"  Min:  {np.min(all_jaccard_sims):.4f}")
    print(f"  Max:  {np.max(all_jaccard_sims):.4f}")
    print()
    
    # Interpretation
    mean_binary = np.mean(all_binary_corrs)
    mean_jaccard = np.mean(all_jaccard_sims)
    
    print(f"BIOLOGICAL VALIDATION:")
    if mean_binary > 0.7 and mean_jaccard > 0.6:
        print(f"  ✅ STRONG concentration invariance (mean correlation={mean_binary:.3f})")
        print(f"     Same odor activates consistent KC patterns across concentrations.")
        print(f"     Matches biological expectation.")
    elif mean_binary > 0.5 and mean_jaccard > 0.4:
        print(f"  ⚠️  MODERATE concentration invariance (mean correlation={mean_binary:.3f})")
        print(f"     Some variability but generally consistent patterns.")
    else:
        print(f"  ❌ WEAK concentration invariance (mean correlation={mean_binary:.3f})")
        print(f"     High variability suggests concentration-dependent KC recruitment.")
        print(f"     May need parameter tuning or circuit refinement.")
    
    print()
    
    return {
        'binary_correlation': {
            'mean': float(np.mean(all_binary_corrs)),
            'std': float(np.std(all_binary_corrs)),
            'min': float(np.min(all_binary_corrs)),
            'max': float(np.max(all_binary_corrs))
        },
        'jaccard_similarity': {
            'mean': float(np.mean(all_jaccard_sims)),
            'std': float(np.std(all_jaccard_sims)),
            'min': float(np.min(all_jaccard_sims)),
            'max': float(np.max(all_jaccard_sims))
        },
        'validation': 'strong' if mean_binary > 0.7 else 'moderate' if mean_binary > 0.5 else 'weak'
    }


def main(use_mlx=False, seed=DEFAULT_SEED,
         output_name='concentration_invariance_results.json',
         allow_mlx_result=False, projection='sklearn_pca',
         glomerular_mapping='position'):
    """
    Main concentration invariance test.

    Tests 3 representative odors at 5 concentration levels:
    0.1×, 0.5×, 1.0×, 5.0×, 10.0× (covering 100-fold range)

    Args:
        use_mlx          : GPU backend. Defaults to False. Deterministic as of
                           2026-09-03 (segmented reduction replaced the
                           order-dependent scatter-add), but CPU remains the
                           reporting default.
        seed             : RNG seed recorded in the output.
        output_name      : filename under results/final/.
        allow_mlx_result : permit writing a result from the MLX backend. Off by
                           default so a reported number cannot come from a
                           non-reproducible run by accident.
        projection       : receptor->glomerular projection ('sklearn_pca' or
                           'uncentered_svd'), recorded in the output.
        glomerular_mapping : channel->PN assignment ('position' or 'index'),
                           recorded in the output.
    """
    print("="*60)
    print("CONCENTRATION INVARIANCE TEST")
    print("Wave-Based Olfactory Simulation")
    print("="*60)
    print()

    set_seed(seed)
    print(f"Seed: {seed}")
    
    # Configuration
    test_odors = list(TEST_ODORS)

    concentrations = [0.1, 0.5, 1.0, 5.0, 10.0]  # 100-fold range
    
    duration_ms = 100.0  # 100 ms simulation per trial
    
    print(f"Test Configuration:")
    print(f"  Odors: {test_odors}")
    print(f"  Concentrations: {concentrations} (100-fold range)")
    print(f"  Simulation duration: {duration_ms} ms per trial")
    print(f"  Total trials: {len(test_odors) * len(concentrations)} = {len(test_odors)} odors × {len(concentrations)} concentrations")
    print()
    
    # Load connectome
    print("Loading connectome...")
    full_connectome = Connectome(data_dir="Fly Brain Female")
    full_connectome.load()
    print(f"  Loaded {len(full_connectome.neurons)} total neurons")
    
    # Extract olfactory pathway
    print("Extracting olfactory pathway...")
    connectome = extract_olfactory_pathway(full_connectome)
    print(f"  Extracted {len(connectome.neurons)} olfactory neurons")
    print(f"  Synapses: {len(connectome.synapses)}")
    print()
    
    # Initialize brain
    print("Initializing brain simulator...")
    # NOTE (2026-09-03): previously dt=0.01, gamma=0.5, omega0=40.0,
    # coupling_strength=2.0 — all four were silently discarded by the engine,
    # which ran at dt=0.1 ms, gamma=0.1. Left empty to preserve that behaviour.
    config = {}
    brain = SparseProbabilisticBrain(
        connectome=connectome,
        config=config,
        use_mlx=use_mlx,
        glomerular_mapping=glomerular_mapping,
    )
    memory_mb = (brain.num_neurons * 5 * 4) / (1024 * 1024)  # 5 fields × 4 bytes
    print(f"  Memory usage: {memory_mb:.1f} MB")
    print(f"  Backend: {'MLX (GPU)' if brain.use_mlx else 'NumPy (CPU)'}")
    if not allow_mlx_result:
        # This run's number is reported, so the backend must be reproducible.
        assert_reproducible_backend(brain)
    print()
    
    # Load DOoR database for odor patterns
    print("Loading DOoR database...")
    door_client = DoorClient(projection=projection)
    print(f"  Loaded {len(door_client.odorant_names)} odorants")
    print()
    
    # Run concentration tests
    all_results = {}
    
    for odor_name in test_odors:
        # Resolve and fetch. An unresolvable name raises rather than becoming a
        # zero vector; there is no synthetic substitute, because a fabricated
        # pattern silently entering a reported mean is the defect this test was
        # inflated by.
        glomerular_pattern = door_client.get_glomerular_pattern(odor_name)

        # Test this odor at multiple concentrations
        results = test_single_odor_concentrations(
            brain=brain,
            odor_name=odor_name,
            glomerular_pattern=glomerular_pattern,
            concentrations=concentrations,
            duration_ms=duration_ms
        )
        
        all_results[odor_name] = results
    
    # Analyze overall invariance
    summary = analyze_concentration_invariance(all_results)
    
    # Save results
    output_data = {
        'test_configuration': {
            'odors': test_odors,
            'concentrations': concentrations,
            'duration_ms': duration_ms,
            'binary_threshold': 0.01,
            'kc_target_sparsity': 0.06,
            'brain_parameters': {
                'num_neurons': brain.num_neurons,
                'dt': float(brain.dt),
                'use_mlx': brain.use_mlx
            }
        },
        'odor_results': all_results,
        'summary': summary,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    output_file = write_results(
        output_name, output_data,
        brain=brain, door_client=door_client,
        duration_ms=duration_ms, seed=seed,
        test='concentration_invariance',
        n_pairwise_comparisons=len(test_odors) * (
            len(concentrations) * (len(concentrations) - 1) // 2
        ),
    )
    
    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}\n")
    
    # Print citation-ready summary
    print("CITATION-READY SUMMARY:")
    print("-" * 60)
    print(f"We tested concentration invariance across 3 odors at 5 concentration")
    print(f"levels (0.1× to 10×, 100-fold range). KC pattern correlation was")
    print(f"{summary['binary_correlation']['mean']:.3f} ± {summary['binary_correlation']['std']:.3f}")
    print(f"(mean ± SD, n={len(test_odors) * len(concentrations)} trials), with Jaccard similarity")
    print(f"{summary['jaccard_similarity']['mean']:.3f} ± {summary['jaccard_similarity']['std']:.3f}.")
    
    if summary['validation'] == 'strong':
        print(f"This demonstrates strong concentration invariance, consistent with")
        print(f"biological observations (Turner et al., 2008; Ito et al., 2008).")
    elif summary['validation'] == 'moderate':
        print(f"This demonstrates moderate concentration invariance, with some")
        print(f"concentration-dependent variability as observed in biological systems.")
    else:
        print(f"Results show concentration-dependent KC recruitment, suggesting")
        print(f"potential parameter tuning needed for full biological fidelity.")
    
    print("-" * 60)
    print()
    
    print("✅ Concentration invariance test complete!")
    print()
    
    return all_results, summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--use-mlx', action='store_true',
                        help='run on the MLX GPU backend (not reproducible)')
    parser.add_argument('--allow-mlx-result', action='store_true',
                        help='permit writing a result file from an MLX run')
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    parser.add_argument('--output', default='concentration_invariance_results.json',
                        help='filename under results/final/')
    parser.add_argument('--projection', default='sklearn_pca',
                        choices=['sklearn_pca', 'uncentered_svd'],
                        help='receptor->glomerular projection to use')
    parser.add_argument('--glomerular-mapping', default='position',
                        choices=['position', 'index'],
                        help='channel->PN assignment to use')
    args = parser.parse_args()

    results, summary = main(
        use_mlx=args.use_mlx,
        seed=args.seed,
        output_name=args.output,
        allow_mlx_result=args.allow_mlx_result,
        projection=args.projection,
        glomerular_mapping=args.glomerular_mapping,
    )
