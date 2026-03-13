"""
Full fly brain olfactory experiment with wave dynamics.

This is NOT a mock test. This loads the actual 139K-neuron connectome
and presents odors to the real olfactory pathway (5,670 PNs → 5,716 KCs → 3,530 LH).

Measures:
- PN phase space discrimination (from actual wave dynamics)
- MB/LH downstream activity
- Offset persistence in recurrent network
- Trial reproducibility with same odor
- Concentration invariance

Runtime estimate: ~10 minutes on M4 Mac (full brain, no GPU)
"""

import sys
import time
import json
import numpy as np
from pathlib import Path

sys.path.insert(0, '.')

# Force unbuffered output
sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', buffering=1)

from hive.main import FlyBrainSystem
from hive.interface.olfactory import create_odor_library

def print_banner(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print('='*70)

def save_results(results, filename="odor_brain_results.json"):
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved to {filename}")


def run_experiment():
    print_banner("FULL FLY BRAIN OLFACTORY EXPERIMENT")
    print("Loading 139K-neuron connectome with wave-based olfaction...")
    print("This will take ~1 minute to initialize...")
    
    t0 = time.time()
    system = FlyBrainSystem(config_path="hive/config.yaml")
    init_time = time.time() - t0
    print(f"✓ Brain initialized in {init_time:.1f}s")
    
    # Get odor library
    odor_library = system.odor_library
    
    # Experiment protocol
    print_banner("EXPERIMENT PROTOCOL")
    
    # Protocol 1: Different odors (discrimination test)
    odor_sequence = [
        ('fruit_ferment', 1.0),
        ('danger_mold', 1.0),
        ('social_female', 1.0),
        ('yeast', 1.0),
        ('clean_air', 0.5),
    ]
    
    # Protocol 2: Concentration series (invariance test)
    concentration_series = [
        ('fruit_ferment', 0.3),
        ('fruit_ferment', 0.7),
        ('fruit_ferment', 1.0),
    ]
    
    # Protocol 3: Repeated trials (reproducibility test)
    repeated_trials = [
        ('danger_mold', 1.0),
        ('danger_mold', 1.0),
        ('danger_mold', 1.0),
    ]
    
    all_trials = odor_sequence + concentration_series + repeated_trials
    
    stim_duration_ms = 200.0   # 200ms per odor (fly discriminates in ~100ms)
    gap_duration_ms = 100.0    # 100ms gap between odors
    post_offset_tracking_ms = 200.0  # Track persistence after offset
    
    total_sim_time = len(all_trials) * (stim_duration_ms + gap_duration_ms + post_offset_tracking_ms)
    n_steps = int(total_sim_time / system.config['oscillator']['dt'])
    
    print(f"\nTrials: {len(all_trials)}")
    print(f"Simulation time: {total_sim_time/1000:.2f} seconds")
    print(f"Integration steps: {n_steps:,}")
    print(f"Estimated runtime: ~{n_steps * 0.18 / 1000 / 60:.1f} minutes")
    
    print("\nOdors to present:")
    for i, (name, conc) in enumerate(all_trials, 1):
        print(f"  {i}. {name:20s} (conc={conc:.1f})")
    
    # Results storage
    results = {
        'metadata': {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'n_neurons': len(system.connectome.neurons),
            'n_pn': len(system.odor_tracker.pn_ids),
            'n_mb': len(system.odor_tracker.mb_ids),
            'n_lh': len(system.odor_tracker.lh_ids),
            'dt_ms': system.config['oscillator']['dt'],
            'total_sim_time_ms': total_sim_time,
            'init_time_sec': init_time,
        },
        'trials': [],
        'summary': {}
    }
    
    print_banner("STARTING SIMULATION")
    print("Press Ctrl+C to abort\n")
    
    current_time = 0.0
    trial_idx = 0
    step_count = 0
    
    last_progress_time = time.time()
    start_time = time.time()
    
    try:
        for trial_idx, (odor_name, concentration) in enumerate(all_trials):
            odor = odor_library[odor_name]
            
            # Phase 1: Odor presentation
            onset = current_time
            offset = onset + stim_duration_ms
            
            system.olfactory.set_odor(odor, stim_duration_ms, onset, concentration)
            system.odor_tracker.begin_trial(odor_name, odor.family, concentration, onset)
            
            print(f"\n[Trial {trial_idx+1}/{len(all_trials)}] {odor_name} (conc={concentration:.1f})")
            print(f"  Onset: {onset:.1f}ms, Duration: {stim_duration_ms:.1f}ms")
            
            # Simulate odor presentation window (WAVE-AWARE ADAPTIVE STEPPING!)
            trial_steps = int(stim_duration_ms / system.config['oscillator']['dt'])
            batch_size = 10  # Optimal batch size (16× faster than sequential)
            
            steps_completed = 0
            time_target = current_time + stim_duration_ms
            
            for batch_start in range(0, trial_steps, batch_size):
                batch_end = min(batch_start + batch_size, trial_steps)
                
                # Execute batch - adaptive dt may complete faster!
                for _ in range(batch_end - batch_start):
                    if system.current_time >= time_target:
                        break  # Already reached target time with adaptive steps!
                    
                    system.step()
                    step_count += 1
                    steps_completed += 1
                
                # Sync once per batch (not per step)
                from hive.gpu_utils import synchronize
                synchronize()
                
                current_time = system.current_time
                
                # Progress update every 2 seconds
                if time.time() - last_progress_time > 2.0:
                    elapsed = time.time() - start_time
                    progress = step_count / n_steps
                    eta = elapsed / progress - elapsed if progress > 0 else 0
                    # Show actual time progress, not just step count
                    time_progress = current_time / (trial_idx * 500 + stim_duration_ms + gap_duration_ms)
                    print(f"    Progress: {progress*100:.1f}% | Time: {current_time:.1f}ms | Elapsed: {elapsed:.0f}s | ETA: {eta:.0f}s", end='\r')
                    last_progress_time = time.time()
                
                # Break if we've reached target time (adaptive stepping!)
                if current_time >= time_target:
                    break
            
            system.odor_tracker.end_trial(offset)
            
            # Phase 2: Post-offset persistence tracking (WAVE-AWARE ADAPTIVE)
            system.olfactory.clear_odor()
            gap_duration_total = gap_duration_ms + post_offset_tracking_ms
            batch_size = 10  # Optimal batch size
            
            time_target = current_time + gap_duration_total
            gap_steps = int(gap_duration_total / system.config['oscillator']['dt'])
            
            for batch_start in range(0, gap_steps, batch_size):
                if current_time >= time_target:
                    break
                    
                batch_end = min(batch_start + batch_size, gap_steps)
                batch_len = batch_end - batch_start
                
                for _ in range(batch_len):
                    if current_time >= time_target:
                        break
                    system.step()
                    step_count += 1
                    current_time = system.current_time
                
                # Sync once per batch
                from hive.gpu_utils import synchronize
                synchronize()
            
            print(f"  ✓ Trial complete at {current_time:.1f}ms")
        
        print("\n\n✓ All trials complete")
        
        # Extract results from tracker
        print_banner("ANALYZING RESULTS")
        
        tracker_summary = system.odor_tracker.get_summary()
        results['summary'] = tracker_summary
        
        # Per-trial details
        for trial in system.odor_tracker.trials:
            results['trials'].append({
                'odor_name': trial.odor_name,
                'odor_family': trial.odor_family,
                'concentration': trial.concentration,
                'onset_time': trial.onset_time,
                'offset_time': trial.offset_time,
                'mean_pn_amplitude': float(np.mean(trial.pn_amplitudes)) if trial.pn_amplitudes else 0.0,
                'mean_pn_coherence': float(np.mean(trial.pn_coherence)) if trial.pn_coherence else 0.0,
                'mean_mb_amplitude': float(np.mean(trial.mb_amplitudes)) if trial.mb_amplitudes else 0.0,
                'mean_lh_amplitude': float(np.mean(trial.lh_amplitudes)) if trial.lh_amplitudes else 0.0,
                'persistence_steps': len(trial.pn_persistence),
                'mean_persistence_amplitude': float(np.mean(trial.pn_persistence)) if trial.pn_persistence else 0.0,
            })
        
        # Print discrimination matrix
        disc_matrix = tracker_summary.get('discrimination_matrix', {})
        if disc_matrix:
            print("\n📊 PN STATE DISCRIMINATION MATRIX (cosine similarity):")
            print("   (Computed from actual oscillator phase space, NOT raw input)\n")
            odor_names = sorted(disc_matrix.keys())
            print(f"{'':20s}", end="")
            for name in odor_names:
                print(f"{name[:10]:>12s}", end="")
            print()
            for a in odor_names:
                print(f"{a:20s}", end="")
                for b in odor_names:
                    val = disc_matrix.get(a, {}).get(b, 0.0)
                    print(f"{val:12.4f}", end="")
                print()
        
        # Print trial reproducibility
        repro = tracker_summary.get('trial_reproducibility', {})
        if repro:
            print("\n🔁 TRIAL-TO-TRIAL REPRODUCIBILITY:")
            for odor, sim in repro.items():
                if sim is not None:
                    status = "✓ STABLE" if sim > 0.85 else "⚠ UNSTABLE"
                    print(f"  {odor:20s}: {sim:.4f}  {status}")
        
        # Print offset persistence
        persist = tracker_summary.get('offset_persistence', {})
        if persist:
            print("\n⏱  OFFSET PERSISTENCE (memory trace):")
            for odor, trials in persist.items():
                if trials:
                    mean_persist_ms = np.mean([t['persistence_ms'] for t in trials])
                    print(f"  {odor:20s}: {mean_persist_ms:.1f}ms")
        
        # Print concentration invariance
        conc_inv = tracker_summary.get('concentration_invariance', {})
        if conc_inv:
            print("\n🎚  CONCENTRATION INVARIANCE:")
            for odor, data in conc_inv.items():
                sim = data.get('mean_cross_conc_similarity', 0.0)
                status = "✓ IDENTITY PRESERVED" if sim > 0.8 else "⚠ CONCENTRATION CONFUSED"
                print(f"  {odor:20s}: {sim:.4f}  {status}")
        
        # Timing
        total_runtime = time.time() - start_time
        results['metadata']['total_runtime_sec'] = total_runtime
        results['metadata']['slowdown_factor'] = total_runtime / (total_sim_time / 1000.0)
        
        print(f"\n⏱  TIMING:")
        print(f"  Total runtime: {total_runtime:.1f}s")
        print(f"  Simulation time: {total_sim_time/1000:.2f}s")
        print(f"  Slowdown factor: {results['metadata']['slowdown_factor']:.1f}×")
        
        # Save
        save_results(results)
        
        print_banner("EXPERIMENT COMPLETE")
        print(f"\nResults saved to: odor_brain_results.json")
        print(f"\nThis was the REAL fly brain processing odors with wave dynamics.")
        print(f"PNs ({len(system.odor_tracker.pn_ids)}) → MBs ({len(system.odor_tracker.mb_ids)}) → LH ({len(system.odor_tracker.lh_ids)})")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Experiment aborted by user")
        print(f"Completed {step_count}/{n_steps} steps ({step_count/n_steps*100:.1f}%)")
        save_results(results)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(run_experiment())
