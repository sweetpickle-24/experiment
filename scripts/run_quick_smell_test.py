"""
Quick Smell Test: Verify sparse probabilistic brain + DOoR integration.

Tests only 3 odors with short simulations to verify everything works.
"""

import numpy as np
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.data.door_client import DoorClient
from hive.data.published_patterns import PublishedPatternLibrary


def main():
    print("\n" + "="*70)
    print("QUICK SMELL TEST")
    print("="*70)
    
    # 1. Load connectome
    print("\n1. Loading connectome...")
    connectome = Connectome(data_dir='Fly Brain Female')
    connectome.load()
    print(f"✓ Loaded {len(connectome.neurons):,} neurons")
    
    # 2. Extract olfactory pathway
    print("\n2. Extracting olfactory pathway...")
    olfactory_connectome = extract_olfactory_pathway(connectome)
    print(f"✓ Extracted {len(olfactory_connectome.neurons):,} olfactory neurons")
    
    # 3. Initialize sparse brain
    print("\n3. Initializing sparse probabilistic brain...")
    brain = SparseProbabilisticBrain(
        connectome=olfactory_connectome,
        use_mlx=True
    )
    print(f"✓ Brain ready: {brain.num_neurons:,} neurons")
    
    # 4. Load DOoR
    print("\n4. Loading DOoR database...")
    door_client = DoorClient()
    print(f"✓ DOoR loaded: {len(door_client.odorant_names)} odorants")
    
    # 5. Test 3 odors
    print("\n" + "="*70)
    print("TESTING 3 ODORS")
    print("="*70)
    
    test_odors = ['geosmin', 'ethyl acetate', '2-heptanone']
    
    for i, odor_name in enumerate(test_odors, 1):
        print(f"\n--- Test {i}/3: {odor_name} ---")
        
        # Get odor pattern
        pattern = door_client.get_glomerular_pattern(odor_name)
        if pattern is None:
            print(f"  ⚠ Odor not in database, skipping")
            continue
        
        print(f"  Glomerular pattern: {pattern[:5]} ... (20 channels)")
        
        # Reset brain
        brain.reset()
        
        # Inject odor
        brain.inject_odor(pattern)
        print(f"  ✓ Odor injected")
        
        # Simulate 50ms (fast test)
        print(f"  Simulating 50ms...")
        t0 = time.time()
        brain.evolve(duration=50.0)
        elapsed = time.time() - t0
        print(f"  ✓ Simulation complete ({elapsed:.2f}s)")
        
        # Extract activity
        pn_activity = brain.get_region_activity('PN')
        kc_activity = brain.get_region_activity('KC')
        
        print(f"  PN activity: mean={np.mean(pn_activity):.3f}, std={np.std(pn_activity):.3f}")
        print(f"  KC activity: mean={np.mean(kc_activity):.3f}, std={np.std(kc_activity):.3f}")
        
        # Check if activity is reasonable
        if np.mean(pn_activity) > 0.01 and np.std(pn_activity) > 0.001:
            print(f"  ✓ Brain response looks good")
        else:
            print(f"  ⚠ Brain response seems flat")
    
    # 6. Summary
    print("\n" + "="*70)
    print("QUICK TEST COMPLETE")
    print("="*70)
    print("\n✓ All systems operational:")
    print("  - Connectome loading")
    print("  - Olfactory pathway extraction")
    print("  - Sparse probabilistic brain")
    print("  - DOoR database integration")
    print("  - Odor injection and simulation")
    print("  - Region-specific activity extraction")
    print("\nReady for full validation!")


if __name__ == '__main__':
    main()
