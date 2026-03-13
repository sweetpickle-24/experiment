"""
Find Digital Smell: What patterns produce what brain responses?

This discovers the mapping: glomerular_pattern → brain_activity
"""

import numpy as np
import time
import sys
import json

sys.path.insert(0, '/Users/vladyslav/Documents/GitHub/experiment')

from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.data.door_client import DoorClient


def compute_digital_smell_signature(brain, glom_pattern, odor_name):
    """
    Compute the full digital smell signature.
    
    Returns:
        dict with glomerular input, PN/KC/MBON responses, and metadata
    """
    # Reset
    brain.reset()
    
    # Inject
    brain.inject_odor(glom_pattern)
    
    # Simulate
    brain.evolve(duration=100.0)  # 100ms
    
    # Extract all region activities
    pn_activity = brain.get_region_activity('PN')
    kc_activity = brain.get_region_activity('KC')
    mbon_activity = brain.get_region_activity('MBON')
    
    # Compute statistics
    signature = {
        'odor_name': odor_name,
        'glomerular_pattern': glom_pattern.tolist(),
        'glomerular_stats': {
            'mean': float(np.mean(glom_pattern)),
            'std': float(np.std(glom_pattern)),
            'max': float(np.max(glom_pattern)),
            'sparsity': float(np.sum(glom_pattern > 0.1) / len(glom_pattern))
        },
        'pn_response': {
            'pattern': pn_activity.tolist() if len(pn_activity) <= 50 else pn_activity[:50].tolist(),
            'mean': float(np.mean(pn_activity)),
            'std': float(np.std(pn_activity)),
            'max': float(np.max(pn_activity)),
            'active_count': int(np.sum(pn_activity > 0.02))
        },
        'kc_response': {
            'mean': float(np.mean(kc_activity)),
            'std': float(np.std(kc_activity)),
            'max': float(np.max(kc_activity)),
            'sparsity': float(np.sum(kc_activity > 0.01) / len(kc_activity)),
            'active_count': int(np.sum(kc_activity > 0.01))
        },
        'mbon_response': {
            'mean': float(np.mean(mbon_activity)),
            'std': float(np.std(mbon_activity)),
            'max': float(np.max(mbon_activity))
        }
    }
    
    return signature


def main():
    print("\n" + "="*70)
    print("DIGITAL SMELL DISCOVERY")
    print("="*70)
    
    # Load system
    print("\n1. Loading olfactory brain...")
    connectome = Connectome(data_dir='Fly Brain Female')
    connectome.load()
    olfactory_connectome = extract_olfactory_pathway(connectome)
    
    brain = SparseProbabilisticBrain(
        connectome=olfactory_connectome,
        use_mlx=True
    )
    print(f"✓ Brain ready: {brain.num_neurons:,} neurons")
    
    # Load DOoR
    print("\n2. Loading DOoR database...")
    door_client = DoorClient()
    print(f"✓ {len(door_client.odorant_names)} odorants available")
    
    # Test 10 diverse odors
    print("\n" + "="*70)
    print("TESTING 10 ODORS")
    print("="*70)
    
    test_odors = [
        'geosmin',           # Earthy
        'ethyl_acetate',     # Fruity ester
        '2-heptanone',       # Ketone
        'acetic_acid',       # Vinegar
        '1-octanol',         # Alcohol
        'benzaldehyde',      # Almond
        'propionic_acid',    # Cheese
        'limonene',          # Citrus
        'eugenol',           # Clove
        'CO2'                # Carbon dioxide
    ]
    
    digital_smells = []
    
    for i, odor_name in enumerate(test_odors, 1):
        print(f"\n{'='*70}")
        print(f"ODOR {i}/10: {odor_name}")
        print('='*70)
        
        # Get glomerular pattern
        pattern = door_client.get_glomerular_pattern(odor_name)
        if pattern is None:
            print(f"⚠ Not in database, skipping")
            continue
        
        # Compute signature
        print(f"Computing digital smell signature...")
        t0 = time.time()
        signature = compute_digital_smell_signature(brain, pattern, odor_name)
        elapsed = time.time() - t0
        
        digital_smells.append(signature)
        
        # Display
        print(f"\n✓ Complete ({elapsed:.2f}s)")
        print(f"\nGLOMERULAR INPUT (20 channels):")
        print(f"  Pattern: {pattern[:5]} ... {pattern[-3:]}")
        print(f"  Mean: {signature['glomerular_stats']['mean']:.3f}")
        print(f"  Sparsity: {signature['glomerular_stats']['sparsity']:.1%} active")
        
        print(f"\nPN RESPONSE:")
        print(f"  Mean: {signature['pn_response']['mean']:.3f}")
        print(f"  Std:  {signature['pn_response']['std']:.3f}")
        print(f"  Active neurons: {signature['pn_response']['active_count']}")
        
        print(f"\nKC RESPONSE (Mushroom Body):")
        print(f"  Mean: {signature['kc_response']['mean']:.3f}")
        print(f"  Sparsity: {signature['kc_response']['sparsity']:.1%}")
        print(f"  Active KCs: {signature['kc_response']['active_count']}/5279")
        
        print(f"\nMBON RESPONSE (Output):")
        print(f"  Mean: {signature['mbon_response']['mean']:.3f}")
        print(f"  Max:  {signature['mbon_response']['max']:.3f}")
    
    # Save database
    print("\n" + "="*70)
    print("DIGITAL SMELL DATABASE")
    print("="*70)
    
    output_file = 'digital_smell_database.json'
    with open(output_file, 'w') as f:
        json.dump(digital_smells, f, indent=2)
    
    print(f"\n✓ Saved {len(digital_smells)} digital smells to {output_file}")
    
    # Summary
    print("\n" + "="*70)
    print("WHAT IS A DIGITAL SMELL?")
    print("="*70)
    print("\nA digital smell is:")
    print("  1. GLOMERULAR PATTERN: 20 receptor activation values [0-1]")
    print("  2. PN RESPONSE: Projection neuron activity pattern")
    print("  3. KC SPARSIFICATION: Sparse mushroom body code (~2% active)")
    print("  4. MBON OUTPUT: Final behavioral output signal")
    print("\nKey insight:")
    print("  - Input: Dense glomerular code (20 channels)")
    print("  - Processing: PN amplification → KC sparsification")
    print("  - Output: Sparse, discriminable neural patterns")
    print("\nEach odor has a unique 'digital fingerprint' in this space.")
    
    # Show most/least sparse
    if digital_smells:
        kc_sparsities = [(s['odor_name'], s['kc_response']['sparsity']) for s in digital_smells]
        kc_sparsities.sort(key=lambda x: x[1])
        
        print(f"\nMost sparse KC response: {kc_sparsities[0][0]} ({kc_sparsities[0][1]:.1%})")
        print(f"Least sparse KC response: {kc_sparsities[-1][0]} ({kc_sparsities[-1][1]:.1%})")


if __name__ == '__main__':
    main()
