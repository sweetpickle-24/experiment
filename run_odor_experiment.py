#!/usr/bin/env python3
"""
Standalone odor discrimination experiment.
Tests wave-based olfactory system with 5 odors and tracks discrimination.
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hive.main import FlyBrainSystem


def print_separator(char="=", length=70):
    """Print separator line."""
    print(char * length)


def run_odor_experiment(duration_ms=500, isi_ms=1000, repetitions=3):
    """
    Run comprehensive odor discrimination experiment.
    
    Args:
        duration_ms: Duration of each odor presentation (ms)
        isi_ms: Inter-stimulus interval (ms)
        repetitions: Number of times to present each odor
    """
    print_separator()
    print(" WAVE-BASED OLFACTORY DISCRIMINATION EXPERIMENT")
    print_separator()
    print()
    
    # Initialize system
    print("Initializing fly brain system...")
    system = FlyBrainSystem("hive/config.yaml")
    print()
    
    # Start experiment
    system.start_experiment(
        "Odor Discrimination",
        "Testing wave-based olfactory processing with 5 odors"
    )
    
    # Get odors
    odor_names = ["food", "danger", "neutral", "mate", "random_control"]
    odors = {name: system.odor_library[name] for name in odor_names}
    
    print(f"Testing {len(odors)} odors:")
    for name in odor_names:
        odor = odors[name]
        print(f"  - {name}: amplitude={odor.baseline_amplitude:.2f}, band={odor.frequency_bias}")
    print()
    
    print_separator("-")
    print(" PRESENTING ODORS")
    print_separator("-")
    print()
    
    # Calculate step counts
    dt = system.config['oscillator']['dt']
    duration_steps = int(duration_ms / dt)
    isi_steps = int(isi_ms / dt)
    
    # Present each odor multiple times
    for rep in range(repetitions):
        print(f"\n[Repetition {rep + 1}/{repetitions}]")
        
        for odor_name in odor_names:
            odor = odors[odor_name]
            
            print(f"\n  Presenting: {odor_name}")
            onset_time = system.current_time
            
            # Set odor
            system.olfactory.set_odor(odor, duration_ms, onset_time)
            
            # Start tracking
            system.odor_tracker.start_tracking(odor_name, onset_time, duration_ms)
            
            # Run simulation during odor presentation
            for step in range(duration_steps):
                system.step()
                
                # Print progress every 100ms
                if step % int(100 / dt) == 0 and step > 0:
                    elapsed = step * dt
                    coherence = system.odor_tracker.current_response.pn_phase_coherence[-1] if system.odor_tracker.current_response and system.odor_tracker.current_response.pn_phase_coherence else 0.0
                    print(f"    t={elapsed:.0f}ms | PN coherence: {coherence:.3f}")
            
            # Clear odor
            system.olfactory.clear_odor()
            
            # Wait ISI (keep tracking for response window)
            for step in range(isi_steps):
                system.step()
            
            # Get response
            response = system.odor_tracker.get_response(odor_name)
            if response:
                print(f"    Peak amplitude: {response.pn_peak_amplitude:.3f}")
                print(f"    Response latency: {response.pn_response_latency:.1f}ms")
                if response.attractor_formed:
                    print(f"    Attractor formed! Strength: {response.memory_strength:.3f}")
    
    print()
    print_separator("-")
    print(" RESULTS SUMMARY")
    print_separator("-")
    print()
    
    # Print summary for each odor
    for odor_name in odor_names:
        system.odor_tracker.print_summary(odor_name)
    
    # Compute discrimination matrix
    print()
    print_separator("-")
    print(" DISCRIMINATION MATRIX")
    print_separator("-")
    print()
    
    discrimination = system.odor_tracker.compute_discrimination_matrix(odor_names)
    
    # Print matrix
    print(f"{'':15s}", end="")
    for name in odor_names:
        print(f"{name[:10]:12s}", end="")
    print()
    
    for odor1 in odor_names:
        print(f"{odor1[:15]:15s}", end="")
        for odor2 in odor_names:
            similarity = discrimination.get((odor1, odor2), 0.0)
            print(f"{similarity:12.3f}", end="")
        print()
    
    print()
    print_separator("-")
    print(" ANALYSIS")
    print_separator("-")
    print()
    
    # Analyze discrimination
    # Within-odor similarity (diagonal)
    within_similarities = []
    for odor_name in odor_names:
        sim = discrimination.get((odor_name, odor_name), 0.0)
        within_similarities.append(sim)
    
    # Between-odor similarity (off-diagonal)
    between_similarities = []
    for i, odor1 in enumerate(odor_names):
        for j, odor2 in enumerate(odor_names):
            if i < j:  # Upper triangle only
                sim = discrimination.get((odor1, odor2), 0.0)
                between_similarities.append(sim)
    
    print(f"Within-odor similarity (same odor): {np.mean(within_similarities):.3f} ± {np.std(within_similarities):.3f}")
    print(f"Between-odor similarity (different): {np.mean(between_similarities):.3f} ± {np.std(between_similarities):.3f}")
    print()
    
    # Check discrimination success
    discrimination_index = np.mean(within_similarities) - np.mean(between_similarities)
    print(f"Discrimination index: {discrimination_index:.3f}")
    
    if discrimination_index > 0.3:
        print("✓ EXCELLENT discrimination! Odors are clearly separated.")
    elif discrimination_index > 0.15:
        print("✓ Good discrimination. Odors are distinguishable.")
    elif discrimination_index > 0.05:
        print("⚠ Weak discrimination. Patterns are somewhat similar.")
    else:
        print("✗ Poor discrimination. Odors not reliably distinguished.")
    
    print()
    
    # Specific comparisons
    print("Key comparisons:")
    comparisons = [
        ("food", "danger", "Expected: low similarity (different contexts)"),
        ("food", "mate", "Expected: low similarity (different modalities)"),
        ("danger", "neutral", "Expected: medium similarity"),
    ]
    
    for odor1, odor2, explanation in comparisons:
        sim = discrimination.get((odor1, odor2), 0.0)
        print(f"  {odor1} vs {odor2}: {sim:.3f} ({explanation})")
    
    print()
    print_separator()
    print(" EXPERIMENT COMPLETE")
    print_separator()
    print()
    print(f"Total simulation time: {system.current_time:.0f} ms ({system.current_time/1000:.1f} s)")
    print(f"Total steps: {system.step_count}")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run odor discrimination experiment")
    parser.add_argument("--duration", type=int, default=500, help="Odor presentation duration (ms)")
    parser.add_argument("--isi", type=int, default=1000, help="Inter-stimulus interval (ms)")
    parser.add_argument("--repetitions", type=int, default=3, help="Number of repetitions per odor")
    
    args = parser.parse_args()
    
    run_odor_experiment(
        duration_ms=args.duration,
        isi_ms=args.isi,
        repetitions=args.repetitions
    )
