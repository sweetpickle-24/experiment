"""
Test script to verify the wave-based fly brain system works.
Runs a minimal simulation and checks basic functionality.
"""

import sys
import numpy as np
from pathlib import Path

# Add hive to path
sys.path.insert(0, str(Path(__file__).parent / 'hive'))

def test_substrate():
    """Test substrate loading."""
    print("\n" + "="*60)
    print("TEST 1: Substrate Loading")
    print("="*60)
    
    from substrate import Connectome, SpatialIndex
    
    connectome = Connectome("Fly Brain Female")
    connectome.load()
    
    assert len(connectome.neurons) > 100000, "Should have ~139K neurons"
    assert len(connectome.synapses) > 1000000, "Should have millions of synapses"
    
    spatial_index = SpatialIndex(connectome)
    
    # Test nearest neighbor query
    first_id = list(connectome.neurons.keys())[0]
    neighbors = spatial_index.find_nearest(first_id, k=10)
    assert len(neighbors) == 10, "Should find 10 neighbors"
    
    print("✓ Substrate loading works")
    return connectome, spatial_index


def test_oscillator_engine(connectome):
    """Test oscillator dynamics."""
    print("\n" + "="*60)
    print("TEST 2: Oscillator Engine")
    print("="*60)
    
    import yaml
    from engine import OscillatorEngine
    
    with open('hive/config.yaml') as f:
        config = yaml.safe_load(f)
    
    num_neurons = len(connectome.neurons)
    oscillator = OscillatorEngine(num_neurons, config)
    
    # Set random frequencies
    freqs = np.random.uniform(0.01, 0.1, num_neurons)  # rad/ms
    oscillator.set_frequencies(freqs)
    
    # Run for 100 steps
    for i in range(100):
        oscillator.step()
    
    assert oscillator.time > 0, "Time should advance"
    assert oscillator.get_energy() > 0, "Should have energy"
    
    coherence = oscillator.get_phase_coherence()
    print(f"  Global coherence after 100 steps: {coherence:.3f}")
    
    print("✓ Oscillator engine works")
    return oscillator


def test_hive_detection(connectome, spatial_index, oscillator):
    """Test hive formation."""
    print("\n" + "="*60)
    print("TEST 3: Hive Detection")
    print("="*60)
    
    import yaml
    from hives import HiveDetector
    
    with open('hive/config.yaml') as f:
        config = yaml.safe_load(f)
    
    hive_detector = HiveDetector(connectome, spatial_index, oscillator, config)
    
    # Detect hives
    new_hives = hive_detector.detect_hives(oscillator.time)
    
    print(f"  Detected {len(new_hives)} new hives")
    print(f"  Free neurons: {len(hive_detector.free_neurons)}")
    
    print("✓ Hive detection works")
    return hive_detector


def test_consciousness(oscillator):
    """Test consciousness states."""
    print("\n" + "="*60)
    print("TEST 4: Consciousness States")
    print("="*60)
    
    import yaml
    from consciousness.states import ConsciousnessStateManager, ConsciousnessState
    from consciousness.global_field import GlobalFieldComputer
    
    with open('hive/config.yaml') as f:
        config = yaml.safe_load(f)
    
    state_manager = ConsciousnessStateManager(config)
    field_computer = GlobalFieldComputer(oscillator)
    
    # Compute metrics
    metrics = field_computer.compute_metrics()
    
    print(f"  Global coherence: {metrics['global_coherence']:.3f}")
    print(f"  Dominant frequency: {metrics['dominant_frequency']:.2f} Hz")
    print(f"  Phase topology: {metrics['phase_topology']}")
    print(f"  Current state: {state_manager.current_state.value}")
    
    # Force state transition
    state_manager.force_state(ConsciousnessState.SHOCK, oscillator.time)
    assert state_manager.current_state == ConsciousnessState.SHOCK
    
    print("✓ Consciousness states work")


def test_full_integration():
    """Test full system integration."""
    print("\n" + "="*60)
    print("TEST 5: Full System Integration")
    print("="*60)
    
    from main import FlyBrainSystem
    
    # Create system (will load everything)
    system = FlyBrainSystem("hive/config.yaml")
    
    # Run brief simulation
    print("\n  Running 100ms simulation...")
    for i in range(200):  # 200 steps = 100ms at 0.5ms/step
        system.step()
        
        if (i + 1) % 50 == 0:
            coherence = system.oscillator.get_phase_coherence()
            hives = len(system.hive_detector.active_hives)
            print(f"    Step {i+1}: coherence={coherence:.3f}, hives={hives}")
    
    # Get final state
    state = system.get_state_snapshot()
    
    print(f"\n  Final metrics:")
    print(f"    Time: {state['time']:.1f} ms")
    print(f"    Global coherence: {state['global_coherence']:.3f}")
    print(f"    Energy: {state['energy']:.1f}")
    print(f"    Active hives: {len(state['hives'])}")
    
    print("✓ Full system integration works")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "FLY BRAIN SYSTEM TESTS" + " "*21 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        # Test 1: Substrate
        connectome, spatial_index = test_substrate()
        
        # Test 2: Oscillator
        oscillator = test_oscillator_engine(connectome)
        
        # Test 3: Hives
        hive_detector = test_hive_detection(connectome, spatial_index, oscillator)
        
        # Test 4: Consciousness
        test_consciousness(oscillator)
        
        # Test 5: Full integration
        test_full_integration()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        print("\nThe wave-based fly brain is functional!")
        print("Ready for experiments.")
        
    except Exception as e:
        print(f"\n\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
