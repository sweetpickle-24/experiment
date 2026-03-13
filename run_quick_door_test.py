"""
Quick DOoR test with minimal memory usage.

Tests just 3 odors instead of full validation to verify the system works
without loading massive datasets.
"""

import numpy as np
from pathlib import Path

# Import modules
from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.probabilistic_wave import ProbabilisticWaveBrain
from hive.data.door_client import DoorClient
from hive.data.published_patterns import PublishedPatternLibrary
from hive.metrics.pattern_similarity import composite_similarity

print("\n" + "="*70)
print("QUICK DOOR TEST - Minimal Memory Usage")
print("="*70)

# 1. Load connectome
print("\n1. Loading connectome...")
connectome = Connectome()
connectome.load()

# 2. Extract olfactory pathway
print("\n2. Extracting olfactory pathway...")
olfactory = extract_olfactory_pathway(connectome)
print(f"  Olfactory neurons: {len(olfactory.neurons):,}")
print(f"  Olfactory synapses: {len(olfactory.synapses):,}")

# 3. Initialize probabilistic brain (coarse grid for memory efficiency)
print("\n3. Initializing probabilistic brain (100μm grid)...")
brain = ProbabilisticWaveBrain(
    connectome=olfactory,
    grid_spacing=100.0,  # Coarse grid: 100μm instead of 50μm
    use_mlx=True
)

# 4. Load DOoR
print("\n4. Loading DOoR database...")
door = DoorClient()

# 5. Load patterns
print("\n5. Loading published patterns...")
patterns = PublishedPatternLibrary()

# 6. Test 3 odors
print("\n6. Testing 3 odors...")
test_odors = ['ethyl_acetate', 'acetic_acid', 'CO2']

results = []
for odor in test_odors:
    if odor not in door.odorant_names:
        print(f"  ⚠ {odor} not in DOoR, skipping")
        continue
    
    print(f"\n  Testing {odor}...")
    
    # Get pattern
    glom = door.get_glomerular_pattern(odor)
    print(f"    Glom pattern: {glom.shape}, norm={np.linalg.norm(glom):.3f}")
    
    # Simulate
    brain.reset()
    brain.inject_odor(glom)
    brain.evolve(duration=100.0)  # Short: 100ms
    
    activity = brain.get_region_activity('PN')
    print(f"    Activity: {activity.shape}, mean={np.mean(activity):.3f}")
    
    # Compare to published if available
    pub = patterns.get_pattern(odor, 'PN')
    if pub:
        # Resize to match
        if len(activity) != len(pub.pattern):
            activity = activity[:len(pub.pattern)]
        
        metrics = composite_similarity(activity, pub.pattern)
        print(f"    Correlation: {metrics['spatial_correlation']:.3f}")
        print(f"    Cosine: {metrics['cosine_similarity']:.3f}")
        results.append((odor, metrics))

# Summary
print("\n" + "="*70)
print("QUICK TEST SUMMARY")
print("="*70)
print(f"\nTested: {len(results)} odors")
for odor, metrics in results:
    print(f"  {odor}: corr={metrics['spatial_correlation']:.3f}, cos={metrics['cosine_similarity']:.3f}")

print("\n✓ Quick test complete!")
print("="*70)
