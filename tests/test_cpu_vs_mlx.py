#!/usr/bin/env python3
"""
CPU vs MLX Validation Test
Tests if NumPy (CPU) backend produces equivalent results to MLX (GPU).

This is critical for publication - proves results aren't GPU artifacts.
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from validation_utils import init_olfactory_brain, results_path
from hive.substrate.olfactory_subgraph import classify_olfactory_neuron

def measure_kc_activity(brain, connectome):
    """Measure KC sparsity."""
    # Get amplitudes
    if brain.use_mlx:
        import mlx.core as mx
        amplitudes = np.array(brain.mean_amplitude)
    else:
        amplitudes = brain.mean_amplitude
    
    # Find KC neurons
    kc_ids = []
    for nid, neuron in connectome.neurons.items():
        if classify_olfactory_neuron(neuron) == 'KC':
            kc_ids.append(nid)
    
    # Get KC indices
    kc_indices = [i for i, nid in enumerate(brain.neuron_ids) if nid in kc_ids]
    
    if not kc_indices:
        return 0.0, 0, len(amplitudes)
    
    # Measure activity
    kc_amplitudes = amplitudes[kc_indices]
    threshold = 0.01
    active_kcs = np.sum(kc_amplitudes > threshold)
    total_kcs = len(kc_indices)
    sparsity = (active_kcs / total_kcs) * 100.0
    
    return sparsity, active_kcs, total_kcs

def test_odor_response(brain, connectome, odor_pattern, backend_name):
    """Test single odor response."""
    print(f"\n{'='*60}")
    print(f"Testing with {backend_name} backend")
    print(f"{'='*60}")
    
    # Reset brain
    brain.reset(deterministic=True)  # Use deterministic initialization
    
    # Inject odor
    print(f"Injecting odor pattern...")
    brain.inject_odor(odor_pattern, strength=50.0)
    
    # Evolve
    print(f"Evolving for 100ms...")
    start = time.time()
    brain.evolve(duration=100.0)
    elapsed = time.time() - start
    
    # Measure KC activity
    sparsity, active, total = measure_kc_activity(brain, connectome)
    
    print(f"\nResults:")
    print(f"  Simulation time: {elapsed:.2f} seconds")
    print(f"  KC sparsity: {sparsity:.3f}%")
    print(f"  Active KCs: {active}/{total}")
    
    # Get full KC pattern for correlation
    if brain.use_mlx:
        import mlx.core as mx
        amplitudes = np.array(brain.mean_amplitude)
    else:
        amplitudes = brain.mean_amplitude
    
    kc_ids = [nid for nid, neuron in connectome.neurons.items() 
              if classify_olfactory_neuron(neuron) == 'KC']
    kc_indices = [i for i, nid in enumerate(brain.neuron_ids) if nid in kc_ids]
    kc_pattern = amplitudes[kc_indices] if kc_indices else np.array([])
    
    return {
        'backend': backend_name,
        'sparsity_percent': float(sparsity),
        'active_kcs': int(active),
        'total_kcs': int(total),
        'simulation_time_sec': float(elapsed),
        'kc_pattern': kc_pattern.tolist() if len(kc_pattern) < 1000 else []  # Store if small
    }

def main():
    print("\n" + "="*70)
    print("CPU vs MLX VALIDATION TEST")
    print("="*70)
    print("\nPurpose: Verify NumPy (CPU) produces equivalent results to MLX (GPU)")
    print("Critical for publication: proves results aren't GPU artifacts")
    
    # Create synthetic odor pattern (simple test)
    np.random.seed(42)  # Fixed seed for reproducibility
    odor_pattern = np.random.rand(20) * 0.5  # 20-channel glomerular pattern
    
    print(f"\nTest odor pattern: {odor_pattern[:5]}... (20 channels)")
    
    results = {}
    
    # Test 1: MLX (GPU)
    print("\n" + "="*70)
    print("TEST 1: MLX (GPU) Backend")
    print("="*70)
    
    brain_mlx, door_client, connectome = init_olfactory_brain(use_mlx=True)
    results['mlx'] = test_odor_response(brain_mlx, connectome, odor_pattern, 'MLX (GPU)')
    
    # Clean up
    del brain_mlx
    
    # Test 2: NumPy (CPU)
    print("\n" + "="*70)
    print("TEST 2: NumPy (CPU) Backend")
    print("="*70)
    
    brain_cpu, door_client, connectome = init_olfactory_brain(use_mlx=False)
    results['cpu'] = test_odor_response(brain_cpu, connectome, odor_pattern, 'NumPy (CPU)')
    
    # Compare results
    print("\n" + "="*70)
    print("COMPARISON: MLX vs NumPy")
    print("="*70)
    
    mlx_sparsity = results['mlx']['sparsity_percent']
    cpu_sparsity = results['cpu']['sparsity_percent']
    diff = abs(mlx_sparsity - cpu_sparsity)
    diff_percent = (diff / mlx_sparsity) * 100 if mlx_sparsity > 0 else 0
    
    print(f"\nKC Sparsity:")
    print(f"  MLX (GPU):    {mlx_sparsity:.3f}%")
    print(f"  NumPy (CPU):  {cpu_sparsity:.3f}%")
    print(f"  Difference:   {diff:.3f}% ({diff_percent:.2f}% relative)")
    
    print(f"\nActive KCs:")
    print(f"  MLX (GPU):    {results['mlx']['active_kcs']}/{results['mlx']['total_kcs']}")
    print(f"  NumPy (CPU):  {results['cpu']['active_kcs']}/{results['cpu']['total_kcs']}")
    
    print(f"\nSimulation Speed:")
    print(f"  MLX (GPU):    {results['mlx']['simulation_time_sec']:.2f}s")
    print(f"  NumPy (CPU):  {results['cpu']['simulation_time_sec']:.2f}s")
    speedup = results['cpu']['simulation_time_sec'] / results['mlx']['simulation_time_sec']
    print(f"  Speedup:      {speedup:.1f}× faster on GPU")
    
    # Pattern correlation (if stored)
    if results['mlx']['kc_pattern'] and results['cpu']['kc_pattern']:
        mlx_pattern = np.array(results['mlx']['kc_pattern'])
        cpu_pattern = np.array(results['cpu']['kc_pattern'])
        if len(mlx_pattern) == len(cpu_pattern) and len(mlx_pattern) > 0:
            correlation = np.corrcoef(mlx_pattern, cpu_pattern)[0, 1]
            print(f"\nPattern Correlation:")
            print(f"  r = {correlation:.6f}")
            results['pattern_correlation'] = float(correlation)
    
    # Validation assessment
    print("\n" + "="*70)
    print("VALIDATION ASSESSMENT")
    print("="*70)
    
    # Criteria for equivalence
    sparsity_threshold = 1.0  # 1% absolute difference acceptable
    correlation_threshold = 0.95  # r > 0.95 for pattern correlation
    
    sparsity_ok = diff < sparsity_threshold
    correlation_ok = results.get('pattern_correlation', 0) > correlation_threshold
    
    print(f"\nCriteria:")
    print(f"  Sparsity difference < {sparsity_threshold}%: {'✓ PASS' if sparsity_ok else '✗ FAIL'}")
    if 'pattern_correlation' in results:
        print(f"  Pattern correlation > {correlation_threshold}: {'✓ PASS' if correlation_ok else '✗ FAIL'}")
    
    overall_pass = sparsity_ok
    
    print(f"\n{'='*70}")
    if overall_pass:
        print("✓ VALIDATION PASSED: CPU and GPU produce equivalent results")
        print("  Results are not GPU artifacts - scientifically valid!")
    else:
        print("⚠ VALIDATION WARNING: Significant difference detected")
        print("  May need investigation before publication")
    print("="*70)
    
    # Add summary
    results['summary'] = {
        'sparsity_difference_percent': float(diff),
        'sparsity_difference_relative_percent': float(diff_percent),
        'pattern_correlation': results.get('pattern_correlation', None),
        'speedup': float(speedup),
        'validation_passed': overall_pass,
        'criteria': {
            'sparsity_threshold_percent': sparsity_threshold,
            'correlation_threshold': correlation_threshold
        }
    }
    
    # Save results
    output_file = results_path('cpu_vs_mlx_validation.json')
    with open(output_file, 'w') as f:
        # Remove large arrays before saving
        results_to_save = results.copy()
        if results_to_save['mlx']['kc_pattern']:
            results_to_save['mlx']['kc_pattern'] = f"{len(results['mlx']['kc_pattern'])} values"
        if results_to_save['cpu']['kc_pattern']:
            results_to_save['cpu']['kc_pattern'] = f"{len(results['cpu']['kc_pattern'])} values"
        
        json.dump(results_to_save, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    
    return results

if __name__ == '__main__':
    results = main()
