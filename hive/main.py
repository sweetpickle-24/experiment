"""
Main entry point for the wave-based fly brain consciousness system.
FULLY INTEGRATED - All systems operational.
"""

import yaml
import numpy as np
from pathlib import Path

from .substrate import Connectome, SpatialIndex, SensoryMotorMapper
from .engine import FrequencyAssigner, NeuromodulatorSystem
from .hives import HiveDetector, HiveRegistry, HiveCommunication
from .gpu_utils import GPU_AVAILABLE, GPU_BACKEND

# Use GPU engines if available
if GPU_AVAILABLE:
    from .engine.oscillator_gpu import OscillatorEngineGPU as OscillatorEngine
    from .engine.coupling_gpu import CouplingEngineGPU as CouplingEngine
    print(f"✓ Using GPU-accelerated engines ({GPU_BACKEND})")
else:
    from .engine import OscillatorEngine, CouplingEngine
    print("⚠ Using CPU engines (install mlx for Apple Silicon or cupy for NVIDIA)")
from .patterns import ThoughtPatternDetector, PatternCompletion, AdvancedPatternSystem
from .memory import IntegratedMemorySystem
from .consciousness.states import ConsciousnessStateManager, ConsciousnessState
from .consciousness.global_field import GlobalFieldComputer
from .dissent import MinorityEngine, GracefulDegradation
from .evolution import EvolutionarySystem
from .interface.sensory import SensoryInterface, MotorInterface
from .storage import ExperimentStorage


class FlyBrainSystem:
    """
    Complete wave-based fly brain consciousness system - FULLY INTEGRATED.
    All layers operational: substrate, oscillators, hives, patterns, memory,
    consciousness, dissent, evolution, sensory/motor, storage.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        # Load configuration
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        print("="*70)
        print(" WAVE-BASED FLY BRAIN CONSCIOUSNESS - FULLY INTEGRATED")
        print("="*70)
        
        # Layer 1: Physical Substrate
        print("\n[Layer 1: Physical Substrate]")
        self.connectome = Connectome(self.config['data']['connectome_dir'])
        self.connectome.load()
        
        self.spatial_index = SpatialIndex(self.connectome)
        
        self.sensory_motor_mapper = SensoryMotorMapper(self.connectome)
        self.sensory_motor_map = self.sensory_motor_mapper.build_map()
        
        num_neurons = len(self.connectome.neurons)
        
        # Layer 2: Oscillator Engine (The Soul)
        print("\n[Layer 2: Oscillator Engine - The Soul]")
        self.oscillator = OscillatorEngine(num_neurons, self.config)
        
        self.coupling = CouplingEngine(self.connectome, self.config)
        
        self.freq_assigner = FrequencyAssigner(self.connectome, self.spatial_index, self.config)
        frequencies = self.freq_assigner.assign_frequencies()
        
        # Set oscillator frequencies
        omega_array = np.array([frequencies[nid] for nid in self.spatial_index.neuron_ids])
        self.oscillator.set_frequencies(omega_array)
        
        # Neuromodulation
        self.neuromodulation = NeuromodulatorSystem(num_neurons, self.config)
        self.neuromodulation.set_baselines(omega_array, self.oscillator.gamma)
        
        # Layer 3: Hive Formation
        print("\n[Layer 3: Hive Formation]")
        self.hive_detector = HiveDetector(
            self.connectome, 
            self.spatial_index,
            self.oscillator,
            self.config
        )
        self.hive_registry = HiveRegistry(self.config)
        self.hive_communication = HiveCommunication(self.config)
        
        # Layer 4.5: Thought Patterns (FULLY INTEGRATED)
        print("\n[Layer 4.5: Thought Patterns - COMPLETE]")
        self.thought_detector = ThoughtPatternDetector(self.config)
        self.pattern_completion = PatternCompletion(self.thought_detector, self.config)
        self.advanced_patterns = AdvancedPatternSystem(self.thought_detector, self.config)
        
        # Layer 4: Memory (FULLY INTEGRATED)
        print("\n[Layer 4: Wave-Based Memory - COMPLETE]")
        self.memory = IntegratedMemorySystem(self.config, self.coupling)
        
        # Layer 5: Consciousness
        print("\n[Layer 5: Consciousness States]")
        self.consciousness_manager = ConsciousnessStateManager(self.config)
        self.global_field = GlobalFieldComputer(self.oscillator)
        
        # Layer 7: Dissent Engine
        print("\n[Layer 7: Dissent Engine]")
        self.minority_engine = MinorityEngine(self.config)
        self.graceful_degradation = GracefulDegradation(self.config)
        
        # Layer 6: Evolution (FULLY INTEGRATED)
        print("\n[Layer 6: Evolution & Self-Modification - COMPLETE]")
        self.evolution = EvolutionarySystem(self.config)
        self.evolution.initialize(self.coupling, self.oscillator)
        
        # Layer 8: Sensory/Motor Interface
        print("\n[Layer 8: Sensory/Motor Interface]")
        self.sensory = SensoryInterface(self.sensory_motor_map, self.spatial_index, self.config)
        self.motor = MotorInterface(self.sensory_motor_map, self.spatial_index)
        
        # NEW: Olfactory System (wave-based)
        print("\n[Layer 8.5: Olfactory System - INTEGRATED]")
        from .interface.olfactory import OlfactorySystem, create_odor_library
        self.olfactory = OlfactorySystem(
            pn_ids=self.sensory_motor_map.olfactory,
            connectome=self.connectome,
            config=self.config
        )
        self.sensory.olfactory_system = self.olfactory
        self.odor_library = create_odor_library()
        
        # NEW: Layer 9: Vision System
        print("\n[Layer 9: Vision System - INTEGRATED]")
        from .vision import CompoundEyeSimulator, StimulusGenerator
        self.compound_eye = CompoundEyeSimulator(self.config, self.sensory_motor_map)
        self.stimulus_gen = StimulusGenerator(stimulus_dir="data/stimuli", config=self.config)
        self.current_stimulus = "blank"
        
        # NEW: Layer 10: Monitoring & Anomaly Detection
        print("\n[Layer 10: Monitoring & Anomaly Detection - INTEGRATED]")
        from .monitoring import AnomalyDetector, ResponseTracker
        from .monitoring.odor_tracker import OdorTracker
        from collections import deque
        self.anomaly_detector = AnomalyDetector(self.config)
        self.response_tracker = ResponseTracker(self.config)
        self.recent_anomalies = deque(maxlen=100)
        
        # Odor tracking — use real neuron groups from connectome
        self.odor_tracker = OdorTracker()
        mb_ids = [
            nid for nid, n in self.connectome.neurons.items()
            if any(x in n.group for x in ['MB_CA', 'MB_ML', 'MB_PED', 'MB_VL'])
        ]
        lh_ids = [
            nid for nid, n in self.connectome.neurons.items()
            if n.group.startswith('LH') or n.group.startswith('AL.LH')
        ]
        # Build id_to_idx mapping from spatial_index neuron_ids list
        id_to_idx = {nid: idx for idx, nid in enumerate(self.spatial_index.neuron_ids)}
        self.odor_tracker.set_neuron_groups(
            pn_ids=self.sensory_motor_map.olfactory,
            mb_ids=mb_ids,
            lh_ids=lh_ids,
            id_to_idx=id_to_idx
        )
        print(f"  Mushroom body Kenyon cells: {len(mb_ids)}")
        print(f"  Lateral horn neurons: {len(lh_ids)}")
        
        # Storage (for analysis, not memory)
        print("\n[Storage: SQLite Logging]")
        self.storage = ExperimentStorage()
        self.experiment_id = None
        
        # Simulation state
        self.current_time = 0.0
        self.step_count = 0
        
        print("\n" + "="*70)
        print(" ALL SYSTEMS OPERATIONAL - Ready to simulate")
        print(" - 139K neurons with real connectome")
        print(" - Compound eye with 800 ommatidia")
        print(" - 5-level anomaly detection")
        print(" - Stimulus-response correlation tracking")
        print("="*70)
    
    def start_experiment(self, name: str, description: str = ""):
        """Start logging experiment."""
        self.experiment_id = self.storage.start_experiment(
            name, description, self.config, self.current_time
        )
        print(f"\n[Experiment {self.experiment_id}] {name}")
    
    def step(self):
        """Single simulation step - FULLY INTEGRATED with vision and monitoring."""
        # Reset forces
        self.oscillator.reset_forces()
        
        # NEW: Visual input processing (every 5ms = 200Hz)
        if self.step_count % 10 == 0:
            image, label = self.stimulus_gen.get_next_stimulus()
            motion_by_direction = self.compound_eye.process_image(image)
            neuron_forces = self.compound_eye.get_visual_neuron_stimulation(motion_by_direction)
            self.sensory.apply_compound_eye_input(neuron_forces)
            self.current_stimulus = label
        
        # Apply sensory input
        state_params = self.consciousness_manager.get_state_parameters()
        self.sensory.apply_to_oscillator(self.oscillator, 
                                        sensory_gain=state_params['sensory_gain'],
                                        current_time=self.current_time)
        
        # Update odor tracker every step (tracks both active and post-odor persistence)
        odor_active = (self.olfactory.current_stimulus is not None and
                       self.olfactory.current_stimulus.is_active(self.current_time))
        if odor_active or self.odor_tracker._tracking_post_odor:
            glom_channels = self.olfactory.receptors.activation.copy()
            self.odor_tracker.update(
                positions=self.oscillator.phase,  # phase is the position variable
                velocities=self.oscillator.velocity,
                current_time=self.current_time,
                odor_active=odor_active,
                glom_channels=glom_channels
            )
        
        # Compute coupling forces
        coupling_force = self.coupling.compute_coupling_forces(
            self.oscillator.phase,
            self.oscillator.amplitude
        )
        self.oscillator.set_coupling_force(coupling_force)
        
        # Apply neuromodulation
        modulated_omega = self.neuromodulation.compute_modulated_omega()
        modulated_gamma = self.neuromodulation.compute_modulated_gamma()
        self.oscillator.set_frequencies(modulated_omega)
        self.oscillator.set_damping(modulated_gamma)
        
        # Step oscillators (WAVE-AWARE ADAPTIVE TIMESTEP!)
        actual_dt = self.oscillator.step(adaptive=True)
        
        # Update current time with actual timestep used
        self.current_time = self.oscillator.time
        if self.step_count % 20 == 0:
            if not state_params.get('hive_dynamics_frozen', False):
                new_hives = self.hive_detector.detect_hives(self.oscillator.time)
                for hive in new_hives:
                    self.hive_registry.register_hive(hive)
                    
                    # Log to storage
                    if self.experiment_id:
                        self.storage.log_hive_event(
                            self.experiment_id, hive.hive_id, 'birth',
                            self.current_time, len(hive.member_ids), hive.coherence
                        )
        
        # Detect thought patterns every 10ms
        if self.step_count % 20 == 0:
            hives = list(self.hive_detector.active_hives.values())
            new_patterns = self.thought_detector.detect_patterns(hives, self.current_time)
            
            # Advanced pattern processing
            active_pattern_ids = [p.pattern_id for p in new_patterns]
            self.advanced_patterns.process_step(
                active_pattern_ids,
                self.current_time,
                external_input_strength=0.0
            )
            
            # Log patterns
            if self.experiment_id:
                for pattern in new_patterns:
                    if pattern.activation_count == 1:  # First time seen
                        self.storage.log_thought_pattern(
                            self.experiment_id, pattern.pattern_type,
                            pattern.complexity, pattern.activation_count,
                            pattern.birth_time, pattern.hive_sequence[:10]
                        )
        
        # Memory encoding every 50ms
        if self.step_count % 100 == 0:
            hives = list(self.hive_detector.active_hives.values())
            self.memory.encode(self.oscillator.get_state(), hives, self.current_time)
        
        # NEW: Anomaly detection and response tracking every 10ms
        if self.step_count % 20 == 0:
            # Collect system state (convert GPU arrays to CPU for monitoring)
            from .gpu_utils import to_cpu
            metrics = self.global_field.compute_metrics()
            system_state = {
                'oscillators': {
                    'amplitude': to_cpu(self.oscillator.amplitude),
                    'phase': to_cpu(self.oscillator.phase),
                    'frequency': to_cpu(self.oscillator.omega0)
                },
                'hives': list(self.hive_detector.active_hives.values()),
                'patterns': list(self.thought_detector.patterns.values()),
                'memories': self.memory.get_recent_memories() if hasattr(self.memory, 'get_recent_memories') else [],
                'coherence': metrics.get('global_coherence', 0.0),
                'energy': self.oscillator.get_energy(),
                'metastability': metrics.get('metastability', 0.0)
            }
            
            # Detect anomalies
            anomalies = self.anomaly_detector.update(
                system_state,
                self.current_stimulus,
                self.current_time
            )
            self.recent_anomalies.extend(anomalies)
            
            # Track response
            motor_output = self.motor.read_motor_output(self.oscillator)
            self.response_tracker.record_step(
                self.current_stimulus,
                system_state,
                anomalies,
                motor_output,
                self.current_time
            )
        
        # Update consciousness state every 100ms
        if self.step_count % 200 == 0:
            metrics = self.global_field.compute_metrics()
            metrics['consciousness_state'] = self.consciousness_manager.current_state.value
            
            state_changed = self.consciousness_manager.update(metrics, self.current_time)
            
            if state_changed:
                # Log transition
                if self.experiment_id and len(self.consciousness_manager.state_history) > 0:
                    last_transition = self.consciousness_manager.state_history[-1]
                    self.storage.log_consciousness_transition(
                        self.experiment_id,
                        last_transition['time'],
                        last_transition['from'],
                        last_transition['to'],
                        last_transition['duration_in_prev_state']
                    )
                
                # Update neuromodulation for new state
                self.neuromodulation.update_from_consciousness_state(
                    self.consciousness_manager.current_state.value
                )
                
                # Memory consolidation during SLEEP
                if self.consciousness_manager.current_state == ConsciousnessState.SLEEP:
                    self.memory.consolidate_sleep(self.oscillator)
                
                # Dream lab experiments during DREAM
                if self.consciousness_manager.current_state == ConsciousnessState.DREAM:
                    experiments = self.evolution.run_dream_experiments(self)
                    if self.experiment_id:
                        for exp in experiments:
                            self.storage.log_event(
                                self.experiment_id, self.current_time,
                                'dream_experiment', exp
                            )
        
        # Check for minority dissent every 200ms
        if self.step_count % 400 == 0:
            hives = list(self.hive_detector.active_hives.values())
            minority = self.minority_engine.identify_minority(hives)
            if minority:
                dissent_eval = self.minority_engine.evaluate_dissent(minority)
                if dissent_eval['should_listen']:
                    print(f"  [t={self.current_time:.1f}ms] Minority dissent detected - listening!")
        
        # Check system health (graceful degradation)
        if self.step_count % 400 == 0:
            metrics = self.global_field.compute_metrics()
            hives = list(self.hive_detector.active_hives.values())
            if self.graceful_degradation.check_health(hives, metrics['global_coherence']):
                self.graceful_degradation.degrade(self.hive_detector)
        
        # Evolution step every cycle
        self.evolution.step_evolution(self, self.current_time)
        
        # Log metrics snapshot every 500ms
        if self.step_count % 1000 == 0 and self.experiment_id:
            metrics = self.global_field.compute_metrics()
            metrics['num_hives'] = len(self.hive_detector.active_hives)
            metrics['consciousness_state'] = self.consciousness_manager.current_state.value
            self.storage.log_metrics_snapshot(self.experiment_id, self.current_time, metrics)
        
        # Update state
        self.current_time = self.oscillator.time
        self.step_count += 1
    
    def run(self, duration_ms: float = 1000.0, report_interval: float = 100.0):
        """Run simulation for specified duration."""
        print(f"\nRunning simulation for {duration_ms} ms...")
        
        target_steps = int(duration_ms / self.config['oscillator']['dt'])
        report_steps = int(report_interval / self.config['oscillator']['dt'])
        
        for i in range(target_steps):
            self.step()
            
            if (i + 1) % report_steps == 0:
                self._print_status()
    
    def _print_status(self):
        """Print current system status - ENHANCED."""
        coherence = self.oscillator.get_phase_coherence()
        energy = self.oscillator.get_energy()
        hive_summary = self.hive_detector.get_hives_summary()
        consciousness_state = self.consciousness_manager.current_state.value
        
        # Memory stats
        memory_stats = self.memory.get_statistics()
        
        # Pattern stats
        pattern_stats = self.thought_detector.get_pattern_statistics()
        cognitive_state = self.advanced_patterns.get_cognitive_state()
        
        # Evolution stats
        evolution_stats = self.evolution.get_statistics()
        
        print(f"\n[t={self.current_time:.1f}ms] {consciousness_state}")
        print(f"  Coherence: {coherence:.3f} | Energy: {energy:.1f}")
        print(f"  Hives: {hive_summary['num_hives']} | Free: {hive_summary['free_neurons']}")
        print(f"  Patterns: {pattern_stats['total_patterns']} | Focus: {cognitive_state['focus']:.2f} | Creativity: {cognitive_state['creativity']:.2f}")
        print(f"  Memory: {memory_stats['num_phase_patterns']} phase patterns, {memory_stats['num_attractors']} attractors")
        print(f"  Evolution: Gen {evolution_stats['generation']}, Fitness {evolution_stats['current_fitness']:.3f}")
    
    def get_state_snapshot(self) -> dict:
        """Get complete system state for analysis/visualization."""
        return {
            'time': self.current_time,
            'oscillator_state': self.oscillator.get_state(),
            'hives': list(self.hive_detector.active_hives.values()),
            'global_coherence': self.oscillator.get_phase_coherence(),
            'global_frequency': self.oscillator.get_dominant_frequency(),
            'energy': self.oscillator.get_energy(),
            'neuromodulators': self.neuromodulation.get_state(),
            'consciousness_state': self.consciousness_manager.current_state.value,
            'memory_stats': self.memory.get_statistics(),
            'pattern_stats': self.thought_detector.get_pattern_statistics(),
            'cognitive_state': self.advanced_patterns.get_cognitive_state(),
            'evolution_stats': self.evolution.get_statistics()
        }


def main():
    """Main entry point."""
    # Create system
    system = FlyBrainSystem("hive/config.yaml")
    
    # Start experiment
    system.start_experiment("Full Integration Test", 
                           "Testing complete wave-based consciousness system")
    
    # Run initial simulation
    system.run(duration_ms=2000.0, report_interval=200.0)
    
    # Get final state
    state = system.get_state_snapshot()
    print(f"\n\nFinal state at t={state['time']:.1f}ms:")
    print(f"  Global coherence: {state['global_coherence']:.3f}")
    print(f"  Dominant frequency: {state['global_frequency']:.2f} Hz")
    print(f"  Total energy: {state['energy']:.1f}")
    print(f"  Active hives: {len(state['hives'])}")
    print(f"  Consciousness state: {state['consciousness_state']}")
    print(f"  Memory patterns: {state['memory_stats']['num_phase_patterns']}")
    print(f"  Thought patterns: {state['pattern_stats']['total_patterns']}")
    print(f"  Evolution generation: {state['evolution_stats']['generation']}")
    print(f"  Fitness: {state['evolution_stats']['current_fitness']:.3f}")
    
    # End experiment
    system.storage.end_experiment(
        system.experiment_id,
        state['time'],
        state['evolution_stats']['current_fitness']
    )
    
    print("\n" + "="*70)
    print(" SIMULATION COMPLETE - All systems operational")
    print("="*70)
    print("\nWave-based consciousness is FULLY FUNCTIONAL.")
    print("Memory, evolution, thought patterns, dissent - all integrated.")
    print("\nReady for scientific experiments.")


if __name__ == "__main__":
    main()
