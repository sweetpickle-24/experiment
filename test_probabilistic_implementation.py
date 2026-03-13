"""
Quick test script to verify probabilistic wave implementation.

Tests each component independently before running full validation.
"""

import sys
import numpy as np


def test_imports():
    """Test that all modules can be imported."""
    print("\n" + "="*70)
    print("TEST 1: Module Imports")
    print("="*70)
    
    try:
        from hive.engine.probabilistic_wave import ProbabilisticWaveBrain
        print("✓ probabilistic_wave")
    except Exception as e:
        print(f"✗ probabilistic_wave: {e}")
        return False
    
    try:
        from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
        print("✓ olfactory_subgraph")
    except Exception as e:
        print(f"✗ olfactory_subgraph: {e}")
        return False
    
    try:
        from hive.data.door_client import DoorClient
        print("✓ door_client")
    except Exception as e:
        print(f"✗ door_client: {e}")
        return False
    
    try:
        from hive.data.published_patterns import PublishedPatternLibrary
        print("✓ published_patterns")
    except Exception as e:
        print(f"✗ published_patterns: {e}")
        return False
    
    try:
        from hive.metrics.pattern_similarity import composite_similarity
        print("✓ pattern_similarity")
    except Exception as e:
        print(f"✗ pattern_similarity: {e}")
        return False
    
    try:
        from hive.inverse.smell_optimizer import SmellOptimizer
        print("✓ smell_optimizer")
    except Exception as e:
        print(f"✗ smell_optimizer: {e}")
        return False
    
    print("\n✓ All imports successful!")
    return True


def test_door_client():
    """Test DOoR client functionality."""
    print("\n" + "="*70)
    print("TEST 2: DOoR Client")
    print("="*70)
    
    try:
        from hive.data.door_client import DoorClient
        
        client = DoorClient(data_dir='data')
        print(f"✓ Client initialized")
        print(f"  Odorants: {len(client.odorant_names)}")
        print(f"  Receptors: {len(client.receptor_names)}")
        
        # Test odorant query
        response = client.get_odorant_response('ethyl_acetate')
        print(f"✓ Odorant response: shape={response.shape}")
        
        # Test glomerular mapping
        glom = client.get_glomerular_pattern('ethyl_acetate')
        print(f"✓ Glomerular pattern: shape={glom.shape}, norm={np.linalg.norm(glom):.3f}")
        
        # Test similarity search
        similar = client.find_similar_odorants(glom, top_k=3)
        print(f"✓ Similar odorants: {[s[0] for s in similar]}")
        
        return True
    
    except Exception as e:
        print(f"✗ DOoR client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_library():
    """Test published pattern library."""
    print("\n" + "="*70)
    print("TEST 3: Published Pattern Library")
    print("="*70)
    
    try:
        from hive.data.published_patterns import PublishedPatternLibrary
        
        library = PublishedPatternLibrary(data_dir='data')
        print(f"✓ Library initialized")
        print(f"  Total patterns: {len(library.patterns)}")
        print(f"  Odors: {library.get_all_odors()}")
        print(f"  Regions: {library.get_all_regions()}")
        
        # Test pattern retrieval
        pattern = library.get_pattern('ethyl_acetate', 'PN')
        if pattern:
            print(f"✓ Pattern retrieved: {pattern.odor_name} ({pattern.region})")
            print(f"  Shape: {pattern.pattern.shape}")
            print(f"  Source: {pattern.source_paper}")
        
        return True
    
    except Exception as e:
        print(f"✗ Pattern library test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_similarity_metrics():
    """Test similarity metrics."""
    print("\n" + "="*70)
    print("TEST 4: Similarity Metrics")
    print("="*70)
    
    try:
        from hive.metrics.pattern_similarity import (
            spatial_correlation, cosine_similarity, 
            wasserstein_distance, composite_similarity
        )
        
        # Test patterns
        p1 = np.random.lognormal(0, 0.5, 100)
        p1 /= np.linalg.norm(p1)
        
        p2 = p1 + np.random.normal(0, 0.1, 100)
        p2 /= np.linalg.norm(p2)
        
        # Test metrics
        corr = spatial_correlation(p1, p2)
        print(f"✓ Spatial correlation: {corr:.3f}")
        
        cos = cosine_similarity(p1, p2)
        print(f"✓ Cosine similarity: {cos:.3f}")
        
        wass = wasserstein_distance(p1, p2)
        print(f"✓ Wasserstein distance: {wass:.3f}")
        
        comp = composite_similarity(p1, p2)
        print(f"✓ Composite score: {comp['composite_score']:.3f}")
        
        return True
    
    except Exception as e:
        print(f"✗ Similarity metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_probabilistic_brain_minimal():
    """Test probabilistic brain with minimal connectome."""
    print("\n" + "="*70)
    print("TEST 5: Probabilistic Brain (Minimal)")
    print("="*70)
    
    try:
        from hive.engine.probabilistic_wave import ProbabilisticWaveBrain
        from hive.substrate.connectome import Connectome, Neuron, Synapse
        import numpy as np
        
        # Create tiny synthetic connectome
        print("Creating synthetic connectome...")
        connectome = Connectome()
        
        # Add 100 neurons
        for i in range(100):
            connectome.neurons[i] = Neuron(
                root_id=i,
                position=np.random.uniform(0, 100, 3),
                group='AL',
                nt_type='GLUT',
                nt_scores={'GLUT': 1.0},
                cell_types=['PN']
            )
        
        # Add 500 random synapses
        for i in range(500):
            pre = np.random.randint(0, 100)
            post = np.random.randint(0, 100)
            if pre != post:
                connectome.synapses.append(Synapse(
                    pre_id=pre,
                    post_id=post,
                    weight=np.random.randint(1, 10),
                    nt_type='GLUT',
                    neuropil='AL'
                ))
        
        print(f"✓ Synthetic connectome: {len(connectome.neurons)} neurons, {len(connectome.synapses)} synapses")
        
        # Initialize brain
        print("Initializing probabilistic brain...")
        brain = ProbabilisticWaveBrain(
            connectome=connectome,
            grid_spacing=50.0,
            use_mlx=True
        )
        print(f"✓ Brain initialized: {brain.grid_shape} grid")
        
        # Test simulation
        print("Testing simulation...")
        glom_pattern = np.random.uniform(0, 1, 20)
        glom_pattern /= np.linalg.norm(glom_pattern)
        
        brain.reset()
        brain.inject_odor(glom_pattern)
        brain.evolve(duration=50.0)  # 50ms
        
        activity = brain.get_region_activity('PN')
        print(f"✓ Simulation complete: activity shape={activity.shape}")
        
        return True
    
    except Exception as e:
        print(f"✗ Probabilistic brain test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print(" "*20 + "PROBABILISTIC WAVE IMPLEMENTATION")
    print(" "*30 + "QUICK TEST SUITE")
    print("="*80)
    
    tests = [
        ("Imports", test_imports),
        ("DOoR Client", test_door_client),
        ("Pattern Library", test_pattern_library),
        ("Similarity Metrics", test_similarity_metrics),
        ("Probabilistic Brain", test_probabilistic_brain_minimal),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            success = test_fn()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED! Ready to run full validation.")
        print("\nNext step: python run_door_validation.py")
    else:
        print("\n✗ SOME TESTS FAILED. Fix errors before running full validation.")
        return 1
    
    print("="*80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
