#!/usr/bin/env python3
"""
Standalone experiment runner for Wave-Based Fly Brain Consciousness.
Runs simulation without frontend, with comprehensive logging for analysis.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import sys
import time
import json
from pathlib import Path
from datetime import datetime
from hive.main import FlyBrainSystem

# Create logs directory
LOGS_DIR = Path("experiment_logs")
LOGS_DIR.mkdir(exist_ok=True)

# Create timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOGS_DIR / f"experiment_{timestamp}.jsonl"
summary_file = LOGS_DIR / f"summary_{timestamp}.txt"


def log_event(event_type: str, data: dict):
    """Log event to JSONL file for later analysis."""
    event = {
        "timestamp": time.time(),
        "time_ms": data.get('time_ms', 0),
        "type": event_type,
        "data": data
    }
    with open(log_file, 'a') as f:
        f.write(json.dumps(event) + '\n')


def print_and_log(message: str):
    """Print to console and write to summary file."""
    print(message)
    with open(summary_file, 'a') as f:
        f.write(message + '\n')


def analyze_snapshot(system, step_count: int):
    """Analyze and log current system state."""
    time_ms = system.current_time
    
    # Basic metrics
    coherence = system.oscillator.get_phase_coherence()
    energy = system.oscillator.get_energy()
    active_neurons = int((system.oscillator.amplitude > 0.1).sum())
    
    # Hive statistics
    active_hives = list(system.hive_detector.active_hives.values())
    hive_count = len(active_hives)
    avg_hive_size = sum(len(h.member_ids) for h in active_hives) / hive_count if hive_count > 0 else 0
    avg_coherence = sum(h.coherence for h in active_hives) / hive_count if hive_count > 0 else 0
    
    # Pattern statistics
    pattern_count = len(system.thought_detector.patterns)
    pattern_types = {}
    for p in system.thought_detector.patterns.values():
        pattern_types[p.pattern_type] = pattern_types.get(p.pattern_type, 0) + 1
    
    # Memory statistics
    memory_count = len(system.memory.phase_memory.patterns)
    
    # Consciousness state
    consciousness = system.consciousness_manager.current_state.name
    
    # Visual stimulus
    current_stimulus = getattr(system, 'current_stimulus', 'none')
    
    # Anomalies
    recent_anomalies = list(system.recent_anomalies)[-10:] if hasattr(system, 'recent_anomalies') else []
    anomaly_count = len(recent_anomalies)
    
    # Log detailed data
    log_event('snapshot', {
        'step': step_count,
        'time_ms': time_ms,
        'metrics': {
            'coherence': float(coherence),
            'energy': float(energy),
            'active_neurons': active_neurons,
            'consciousness': consciousness
        },
        'hives': {
            'count': hive_count,
            'avg_size': float(avg_hive_size),
            'avg_coherence': float(avg_coherence)
        },
        'patterns': {
            'count': pattern_count,
            'types': pattern_types
        },
        'memory': {
            'count': memory_count
        },
        'visual': {
            'stimulus': current_stimulus
        },
        'anomalies': {
            'count': anomaly_count,
            'recent': [
                {
                    'type': a.type,
                    'subtype': a.subtype,
                    'severity': float(a.severity),
                    'description': a.description
                }
                for a in recent_anomalies
            ]
        }
    })
    
    return {
        'coherence': coherence,
        'energy': energy,
        'hive_count': hive_count,
        'pattern_count': pattern_count,
        'memory_count': memory_count,
        'consciousness': consciousness,
        'stimulus': current_stimulus
    }


def run_experiment(duration_ms: float = 5000.0, report_interval: float = 100.0):
    """Run simulation experiment with logging."""
    
    print_and_log("="*80)
    print_and_log("WAVE-BASED FLY BRAIN CONSCIOUSNESS - STANDALONE EXPERIMENT")
    print_and_log("="*80)
    print_and_log(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_and_log(f"Duration: {duration_ms}ms ({duration_ms/1000:.1f}s)")
    print_and_log(f"Log file: {log_file}")
    print_and_log(f"Summary file: {summary_file}")
    print_and_log("="*80)
    print_and_log("")
    
    # Initialize system
    print_and_log("Initializing fly brain system...")
    system = FlyBrainSystem("hive/config.yaml")
    
    print_and_log("")
    print_and_log("="*80)
    print_and_log("RUNNING SIMULATION")
    print_and_log("="*80)
    print_and_log("")
    
    # Calculate steps
    dt = system.config['oscillator']['dt']
    target_steps = int(duration_ms / dt)
    report_steps = int(report_interval / dt)
    
    # Track interesting events
    hive_births = 0
    hive_deaths = 0
    pattern_discoveries = 0
    memory_formations = 0
    consciousness_transitions = []
    
    # Run simulation
    start_wall_time = time.time()
    
    for step in range(target_steps):
        system.step()
        
        # Periodic reporting
        if (step + 1) % report_steps == 0 or step == 0:
            stats = analyze_snapshot(system, step + 1)
            
            elapsed_wall = time.time() - start_wall_time
            sim_time = system.current_time
            speedup = sim_time / (elapsed_wall * 1000) if elapsed_wall > 0 else 0
            
            print_and_log(f"[Step {step+1:6d} | t={sim_time:7.1f}ms | {elapsed_wall:.1f}s elapsed | {speedup:.2f}x realtime]")
            print_and_log(f"  Consciousness: {stats['consciousness']}")
            print_and_log(f"  Coherence: {stats['coherence']:.3f} | Energy: {stats['energy']:.1f}")
            print_and_log(f"  Active: {stats['hive_count']} hives | {stats['pattern_count']} patterns | {stats['memory_count']} memories")
            print_and_log(f"  Stimulus: {stats['stimulus']}")
            print_and_log("")
            
            # Track events
            new_hive_count = len(system.hive_detector.active_hives)
            if new_hive_count > stats['hive_count']:
                hive_births += new_hive_count - stats['hive_count']
            
            if len(system.consciousness_manager.state_history) > len(consciousness_transitions):
                new_transitions = system.consciousness_manager.state_history[len(consciousness_transitions):]
                for trans in new_transitions:
                    consciousness_transitions.append(trans)
                    print_and_log(f"  🧠 CONSCIOUSNESS TRANSITION: {trans['from']} → {trans['to']}")
                    log_event('consciousness_transition', trans)
    
    # Final summary
    end_wall_time = time.time()
    total_wall_time = end_wall_time - start_wall_time
    
    print_and_log("")
    print_and_log("="*80)
    print_and_log("EXPERIMENT COMPLETE")
    print_and_log("="*80)
    print_and_log(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_and_log(f"Total simulation time: {system.current_time:.1f}ms")
    print_and_log(f"Total wall time: {total_wall_time:.1f}s")
    print_and_log(f"Average speedup: {system.current_time / (total_wall_time * 1000):.2f}x realtime")
    print_and_log("")
    
    # Final statistics
    final_stats = analyze_snapshot(system, target_steps)
    
    print_and_log("FINAL STATISTICS:")
    print_and_log(f"  Total hives formed: {len(system.hive_registry.hives)}")
    print_and_log(f"  Active hives: {final_stats['hive_count']}")
    print_and_log(f"  Total patterns discovered: {final_stats['pattern_count']}")
    print_and_log(f"  Memories formed: {final_stats['memory_count']}")
    print_and_log(f"  Consciousness transitions: {len(consciousness_transitions)}")
    print_and_log(f"  Final consciousness state: {final_stats['consciousness']}")
    print_and_log(f"  Final global coherence: {final_stats['coherence']:.3f}")
    print_and_log(f"  Final energy: {final_stats['energy']:.1f}")
    print_and_log("")
    
    # Pattern type breakdown
    pattern_types = {}
    for p in system.thought_detector.patterns.values():
        pattern_types[p.pattern_type] = pattern_types.get(p.pattern_type, 0) + 1
    
    if pattern_types:
        print_and_log("PATTERN TYPES:")
        for ptype, count in sorted(pattern_types.items(), key=lambda x: -x[1]):
            print_and_log(f"  {ptype}: {count}")
        print_and_log("")
    
    # Consciousness state time
    if consciousness_transitions:
        print_and_log("CONSCIOUSNESS STATE DURATIONS:")
        for trans in consciousness_transitions:
            print_and_log(f"  {trans['from']}: {trans['duration_in_prev_state']:.1f}ms")
        print_and_log("")
    
    # Evolution stats
    if hasattr(system, 'evolution'):
        evo_stats = system.evolution.get_statistics()
        print_and_log("EVOLUTION:")
        print_and_log(f"  Generation: {evo_stats['generation']}")
        print_and_log(f"  Fitness: {evo_stats['current_fitness']:.3f}")
        print_and_log(f"  Total mutations: {evo_stats['total_mutations']}")
        print_and_log(f"  Kept mutations: {evo_stats['kept_mutations']}")
        print_and_log("")
    
    print_and_log("="*80)
    print_and_log(f"📊 Full log data saved to: {log_file}")
    print_and_log(f"📄 Human-readable summary: {summary_file}")
    print_and_log("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run fly brain consciousness experiment')
    parser.add_argument('--duration', type=float, default=5000.0,
                       help='Simulation duration in milliseconds (default: 5000ms = 5s)')
    parser.add_argument('--report-interval', type=float, default=100.0,
                       help='Reporting interval in milliseconds (default: 100ms)')
    
    args = parser.parse_args()
    
    try:
        run_experiment(duration_ms=args.duration, report_interval=args.report_interval)
    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
