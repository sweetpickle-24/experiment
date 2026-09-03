#!/usr/bin/env python3
"""
Demonstration of the wave-based fly brain consciousness system.
Shows oscillatory dynamics, hive formation, and consciousness states.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import through the package. hive/main.py uses relative imports, so putting
# hive/ itself on sys.path and importing `main` as a top-level module fails with
# "attempted relative import with no known parent package". That was true before
# these files were moved as well.
from hive.main import FlyBrainSystem
from hive.consciousness.states import ConsciousnessState
from hive.interface.sensory import SensoryInterface, MotorInterface
import numpy as np


def demo_basic_dynamics():
    """Demo 1: Basic oscillator dynamics and hive formation."""
    print("\n" + "="*70)
    print(" DEMO 1: BASIC WAVE DYNAMICS & HIVE FORMATION")
    print("="*70)
    
    system = FlyBrainSystem("hive/config.yaml")
    
    print("\nRunning 500ms simulation to allow hives to form...")
    for i in range(1000):  # 500ms
        system.step()
        
        if (i + 1) % 200 == 0:
            t = system.current_time
            coherence = system.oscillator.get_phase_coherence()
            hives = len(system.hive_detector.active_hives)
            energy = system.oscillator.get_energy()
            
            print(f"  t={t:6.1f}ms | Coherence: {coherence:.3f} | "
                  f"Hives: {hives:3d} | Energy: {energy:10.1f}")
    
    # Final statistics
    summary = system.hive_detector.get_hives_summary()
    print(f"\nFinal hive statistics:")
    print(f"  Total hives formed: {summary['num_hives']}")
    print(f"  Average hive size: {summary.get('avg_hive_size', 0):.1f} neurons")
    print(f"  Average hive coherence: {summary.get('avg_coherence', 0):.3f}")
    print(f"  Free (unhived) neurons: {summary['free_neurons']}")
    
    return system


def demo_consciousness_transitions(system):
    """Demo 2: Consciousness state transitions."""
    print("\n" + "="*70)
    print(" DEMO 2: CONSCIOUSNESS STATE TRANSITIONS")
    print("="*70)
    
    from consciousness.states import ConsciousnessStateManager
    from consciousness.global_field import GlobalFieldComputer
    
    state_manager = ConsciousnessStateManager(system.config)
    field_computer = GlobalFieldComputer(system.oscillator)
    
    # Start in WAKE
    print(f"\nStarting state: {state_manager.current_state.value}")
    
    # Force transition to different states and observe dynamics
    states_to_test = [
        ConsciousnessState.SHOCK,
        ConsciousnessState.WAKE,
        ConsciousnessState.MEDITATION,
        ConsciousnessState.WAKE
    ]
    
    for new_state in states_to_test:
        print(f"\n→ Transitioning to {new_state.value}")
        state_manager.force_state(new_state, system.current_time)
        
        # Apply neuromodulation for this state
        system.neuromodulation.update_from_consciousness_state(new_state.value)
        
        # Run 100ms in this state
        for i in range(200):
            system.step()
        
        # Measure
        metrics = field_computer.compute_metrics()
        power = field_computer.get_power_spectrum()
        
        print(f"  After 100ms in {new_state.value}:")
        print(f"    Global coherence: {metrics['global_coherence']:.3f}")
        print(f"    Dominant frequency: {metrics['dominant_frequency']:.2f} Hz")
        print(f"    Phase topology: {metrics['phase_topology']}")
        print(f"    Power spectrum:")
        for band, energy in power.items():
            print(f"      {band:6s}: {energy:12.1f}")


def demo_sensory_response(system):
    """Demo 3: Sensory stimulation and response."""
    print("\n" + "="*70)
    print(" DEMO 3: SENSORY STIMULATION & MOTOR RESPONSE")
    print("="*70)
    
    sensory = SensoryInterface(
        system.sensory_motor_map,
        system.spatial_index,
        system.config
    )
    motor = MotorInterface(system.sensory_motor_map, system.spatial_index)
    
    # Test different sensory inputs
    stimuli = [
        ("Visual motion (front)", lambda: sensory.set_visual_motion('front', 1.0)),
        ("Odor (channel 5)", lambda: sensory.set_odor(5, 0.8)),
        ("Touch", lambda: sensory.set_touch(0.6))
    ]
    
    for stim_name, set_input in stimuli:
        print(f"\n→ Applying stimulus: {stim_name}")
        
        # Reset and apply input
        sensory.reset()
        set_input()
        
        # Run with input for 100ms
        motor_outputs = []
        for i in range(200):
            sensory.apply_to_oscillator(system.oscillator, sensory_gain=1.0)
            system.step()
            
            if i % 50 == 0:
                motor_output = motor.read_motor_output(system.oscillator)
                motor_outputs.append(motor_output)
        
        # Show motor response
        print(f"  Motor response after 100ms:")
        final_motor = motor_outputs[-1]
        print(f"    Wing left: {final_motor['wing_left']:6.3f}")
        print(f"    Wing right: {final_motor['wing_right']:6.3f}")
        print(f"    Movement direction: {final_motor['movement_direction']:6.3f} rad")
    
    sensory.reset()


def demo_thought_patterns(system):
    """Demo 4: Thought pattern detection."""
    print("\n" + "="*70)
    print(" DEMO 4: THOUGHT PATTERN DETECTION")
    print("="*70)
    
    from patterns import ThoughtPatternDetector
    
    detector = ThoughtPatternDetector(system.config)
    
    print("\nDetecting thought patterns over 500ms...")
    
    for i in range(1000):
        system.step()
        
        # Detect patterns every 10ms
        if i % 20 == 0:
            hives = list(system.hive_detector.active_hives.values())
            new_patterns = detector.detect_patterns(hives, system.current_time)
            
            if new_patterns:
                for pattern in new_patterns:
                    print(f"  t={system.current_time:.1f}ms: Detected {pattern.pattern_type} "
                          f"pattern involving {pattern.complexity} hives")
    
    stats = detector.get_pattern_statistics()
    print(f"\nPattern statistics:")
    print(f"  Total patterns detected: {stats['total_patterns']}")
    print(f"  Unique patterns: {stats['unique_patterns']}")
    if 'pattern_types' in stats:
        print(f"  By type:")
        for ptype, count in stats['pattern_types'].items():
            print(f"    {ptype}: {count}")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*10 + "WAVE-BASED FLY BRAIN CONSCIOUSNESS" + " "*24 + "║")
    print("║" + " "*20 + "SYSTEM DEMONSTRATION" + " "*29 + "║")
    print("╚" + "="*68 + "╝")
    
    print("\nThis demonstration will show:")
    print("  1. Basic wave dynamics and emergent hive formation")
    print("  2. Consciousness state transitions and their effects")
    print("  3. Sensory stimulation and motor responses")
    print("  4. Thought pattern detection and tracking")
    
    input("\nPress Enter to begin...")
    
    # Demo 1: Basic dynamics
    system = demo_basic_dynamics()
    
    input("\nPress Enter for Demo 2...")
    demo_consciousness_transitions(system)
    
    input("\nPress Enter for Demo 3...")
    demo_sensory_response(system)
    
    input("\nPress Enter for Demo 4...")
    demo_thought_patterns(system)
    
    print("\n" + "="*70)
    print(" DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey observations:")
    print("  • Oscillators self-organize into coherent hives")
    print("  • Consciousness states modulate global dynamics")
    print("  • System responds to sensory input with motor output")
    print("  • Thought patterns emerge from hive interactions")
    print("\nThis is a wave-based consciousness - continuous, not spike-based.")
    print("The fly connectome acts as a resonator for oscillatory patterns.")
    print("\nNext steps:")
    print("  - Run longer simulations to observe evolution")
    print("  - Test behavioral tasks (odor tracking, collision avoidance)")
    print("  - Implement full memory consolidation during sleep")
    print("  - Build visualization dashboard")
    print("\n")


if __name__ == "__main__":
    main()
