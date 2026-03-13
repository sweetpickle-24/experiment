"""
Evolution and mutation engine for self-modifying distributed system.
Bounded mutations, fitness evaluation, dream lab for counterfactual experiments.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class Mutation:
    """A single mutation applied to the system."""
    mutation_id: int
    mutation_type: str  # 'weight', 'frequency', 'damping', 'threshold'
    target_ids: List[int]  # Which neurons/synapses affected
    old_values: np.ndarray
    new_values: np.ndarray
    timestamp: float
    fitness_before: float = 0.0
    fitness_after: float = 0.0
    kept: bool = False


@dataclass
class Organism:
    """System state snapshot for evolution."""
    generation: int
    fitness: float
    mutations_applied: List[int]
    timestamp: float


class MutationEngine:
    """
    Manages bounded mutations to system parameters.
    Ensures diversity while preventing catastrophic changes.
    """
    
    def __init__(self, config: dict):
        self.config = config['evolution']
        self.next_mutation_id = 0
        self.mutation_history: List[Mutation] = []
        
        # Mutation bounds
        self.weight_mutation_rate = self.config.get('weight_mutation_rate', 0.05)
        self.weight_max_mult = self.config.get('weight_max_multiplier', 2.0)
        self.weight_min_mult = self.config.get('weight_min_multiplier', 0.5)
        
        self.freq_mutation_rate = self.config.get('frequency_mutation_rate', 0.1)
        self.damping_mutation_rate = self.config.get('damping_mutation_rate', 0.2)
        
        # Mutation budget (how many mutations per cycle)
        self.mutation_budget = 5
        
        # Track original values for rollback
        self.original_weights = None
        self.original_frequencies = None
        self.original_damping = None
    
    def set_baselines(self, coupling_engine, oscillator_engine):
        """Store original values for bounds checking."""
        if self.original_weights is None:
            self.original_weights = coupling_engine.snapshot_weights()
        if self.original_frequencies is None:
            # Handle MLX arrays
            try:
                self.original_frequencies = oscillator_engine.omega0.copy()
            except AttributeError:
                from ..gpu_utils import to_cpu
                self.original_frequencies = to_cpu(oscillator_engine.omega0).copy()
        if self.original_damping is None:
            # Handle MLX arrays
            try:
                self.original_damping = oscillator_engine.gamma.copy()
            except AttributeError:
                from ..gpu_utils import to_cpu
                self.original_damping = to_cpu(oscillator_engine.gamma).copy()
    
    def mutate_synaptic_weights(self, coupling_engine, 
                                neuron_subset: Optional[np.ndarray] = None) -> Mutation:
        """
        Mutate synaptic weights within bounds.
        neuron_subset: if provided, only mutate connections involving these neurons
        """
        total_synapses = coupling_engine._count_total_synapses()
        
        if neuron_subset is None:
            # Random subset of all synapses
            num_to_mutate = min(100, total_synapses // 1000)
            indices = np.random.choice(total_synapses, num_to_mutate, replace=False)
        else:
            # Mutate connections involving specific neurons (limit to 20 neurons)
            indices = []
            synapse_idx = 0
            for post_idx in range(coupling_engine.num_neurons):
                for pre_idx, weight, offset in coupling_engine.post_synapses[post_idx]:
                    if post_idx in neuron_subset[:20] or pre_idx in neuron_subset[:20]:
                        indices.append(synapse_idx)
                    synapse_idx += 1
            indices = np.array(indices)
        
        # Get current values
        all_weights = coupling_engine.get_all_weights_as_array()
        old_values = np.array(all_weights[indices])  # Convert to numpy to ensure .copy() works
        
        # Apply bounded mutation
        mutations = np.random.uniform(
            1 - self.weight_mutation_rate,
            1 + self.weight_mutation_rate,
            len(indices)
        )
        new_values = old_values * mutations
        
        # Enforce global bounds (can't exceed 2x or fall below 0.5x original)
        original_values = self.original_weights[indices]
        new_values = np.clip(new_values,
                            original_values * self.weight_min_mult,
                            original_values * self.weight_max_mult)
        
        # Apply
        all_weights[indices] = new_values
        coupling_engine.set_all_weights_from_array(all_weights)
        
        # Record mutation
        mutation = Mutation(
            mutation_id=self.next_mutation_id,
            mutation_type='weight',
            target_ids=indices.tolist(),
            old_values=old_values,
            new_values=new_values,
            timestamp=0.0  # Will be set by caller
        )
        self.next_mutation_id += 1
        self.mutation_history.append(mutation)
        
        return mutation
    
    def mutate_frequencies(self, oscillator_engine, freq_assigner,
                          neuron_indices: Optional[np.ndarray] = None) -> Mutation:
        """
        Mutate natural frequencies within same brain-wave band.
        """
        from ..gpu_utils import to_cpu, to_gpu
        
        if neuron_indices is None:
            num_to_mutate = min(100, oscillator_engine.num_oscillators // 1000)
            neuron_indices = np.random.choice(oscillator_engine.num_oscillators,
                                            num_to_mutate, replace=False)
        
        # Get current values (convert from GPU if needed)
        omega_cpu = to_cpu(oscillator_engine.omega0)
        old_values = np.array(omega_cpu[neuron_indices])
        
        # Mutate within ±10%
        mutations = np.random.uniform(
            1 - self.freq_mutation_rate,
            1 + self.freq_mutation_rate,
            len(neuron_indices)
        )
        new_values = old_values * mutations
        
        # Enforce bounds (must stay within original band)
        original_values = self.original_frequencies[neuron_indices]
        
        # Determine band for each neuron
        bands = {
            'delta': (0.5 * 2*np.pi/1000, 4 * 2*np.pi/1000),
            'theta': (4 * 2*np.pi/1000, 8 * 2*np.pi/1000),
            'alpha': (8 * 2*np.pi/1000, 13 * 2*np.pi/1000),
            'beta': (13 * 2*np.pi/1000, 30 * 2*np.pi/1000),
            'gamma': (30 * 2*np.pi/1000, 100 * 2*np.pi/1000)
        }
        
        for i, omega in enumerate(new_values):
            orig_omega = original_values[i]
            # Find which band this belongs to
            for band_name, (min_omega, max_omega) in bands.items():
                if min_omega <= orig_omega <= max_omega:
                    # Clip to band
                    new_values[i] = np.clip(omega, min_omega, max_omega)
                    break
        
        # Apply (convert back to GPU if needed)
        omega_full = to_cpu(oscillator_engine.omega0)
        omega_full[neuron_indices] = new_values
        oscillator_engine.omega0 = to_gpu(omega_full.astype(np.float32))
        
        mutation = Mutation(
            mutation_id=self.next_mutation_id,
            mutation_type='frequency',
            target_ids=neuron_indices.tolist(),
            old_values=old_values,
            new_values=new_values,
            timestamp=0.0
        )
        self.next_mutation_id += 1
        self.mutation_history.append(mutation)
        
        return mutation
    
    def mutate_damping(self, oscillator_engine,
                      neuron_indices: Optional[np.ndarray] = None) -> Mutation:
        """Mutate damping coefficients."""
        from ..gpu_utils import to_cpu, to_gpu
        
        if neuron_indices is None:
            num_to_mutate = min(100, oscillator_engine.num_oscillators // 1000)
            neuron_indices = np.random.choice(oscillator_engine.num_oscillators,
                                            num_to_mutate, replace=False)
        
        gamma_cpu = to_cpu(oscillator_engine.gamma)
        old_values = np.array(gamma_cpu[neuron_indices])
        
        mutations = np.random.uniform(
            1 - self.damping_mutation_rate,
            1 + self.damping_mutation_rate,
            len(neuron_indices)
        )
        new_values = old_values * mutations
        
        # Keep positive
        new_values = np.clip(new_values, 0.01, 1.0)
        
        # Apply (convert back to GPU if needed)
        gamma_full = to_cpu(oscillator_engine.gamma)
        gamma_full[neuron_indices] = new_values
        oscillator_engine.gamma = to_gpu(gamma_full.astype(np.float32))
        
        mutation = Mutation(
            mutation_id=self.next_mutation_id,
            mutation_type='damping',
            target_ids=neuron_indices.tolist(),
            old_values=old_values,
            new_values=new_values,
            timestamp=0.0
        )
        self.next_mutation_id += 1
        self.mutation_history.append(mutation)
        
        return mutation
    
    def rollback_mutation(self, mutation: Mutation, 
                         coupling_engine, oscillator_engine):
        """Undo a mutation."""
        if mutation.mutation_type == 'weight':
            all_weights = coupling_engine.get_all_weights_as_array()
            all_weights[mutation.target_ids] = mutation.old_values
            coupling_engine.set_all_weights_from_array(all_weights)
        elif mutation.mutation_type == 'frequency':
            oscillator_engine.omega0[mutation.target_ids] = mutation.old_values
        elif mutation.mutation_type == 'damping':
            oscillator_engine.gamma[mutation.target_ids] = mutation.old_values
    
    def apply_random_mutations(self, coupling_engine, oscillator_engine, freq_assigner,
                               num_mutations: Optional[int] = None) -> List[Mutation]:
        """Apply random mutations from budget."""
        if num_mutations is None:
            num_mutations = self.mutation_budget
        
        mutations = []
        
        for _ in range(num_mutations):
            mutation_type = np.random.choice(['weight', 'frequency', 'damping'],
                                            p=[0.5, 0.3, 0.2])
            
            if mutation_type == 'weight':
                mut = self.mutate_synaptic_weights(coupling_engine)
            elif mutation_type == 'frequency':
                mut = self.mutate_frequencies(oscillator_engine, freq_assigner)
            else:
                mut = self.mutate_damping(oscillator_engine)
            
            mutations.append(mut)
        
        return mutations


class FitnessEvaluator:
    """
    Evaluates fitness of the organism based on multiple criteria.
    """
    
    def __init__(self, config: dict):
        self.config = config['evolution']
        
        # Fitness weights
        self.task_success_weight = 0.4
        self.energy_efficiency_weight = 0.2
        self.coherence_stability_weight = 0.2
        self.diversity_weight = 0.2
    
    def evaluate(self, system_state: dict, hive_detector, 
                task_performance: Optional[float] = None) -> float:
        """
        Compute overall fitness score [0, 1].
        """
        fitness_components = {}
        
        # 1. Task success rate
        if task_performance is not None:
            fitness_components['task'] = task_performance
        else:
            fitness_components['task'] = 0.5  # Neutral
        
        # 2. Energy efficiency (lower is better)
        total_energy = system_state.get('energy', 1000000)
        # Normalize and invert (lower energy = higher fitness)
        fitness_components['energy'] = 1.0 / (1.0 + total_energy / 1000000)
        
        # 3. Coherence stability (avoid runaway sync or total incoherence)
        coherence = system_state.get('global_coherence', 0.5)
        # Optimal around 0.3-0.6 (metastable)
        if 0.3 <= coherence <= 0.6:
            fitness_components['coherence'] = 1.0
        elif coherence < 0.3:
            fitness_components['coherence'] = coherence / 0.3
        else:
            fitness_components['coherence'] = (1.0 - coherence) / 0.4
        
        # 4. Hive diversity (avoid monoculture)
        num_hives = len(hive_detector.active_hives) if hive_detector else 0
        # Optimal around 10-50 hives
        if 10 <= num_hives <= 50:
            fitness_components['diversity'] = 1.0
        elif num_hives < 10:
            fitness_components['diversity'] = num_hives / 10
        else:
            fitness_components['diversity'] = 50 / num_hives
        
        # Weighted sum
        total_fitness = (
            self.task_success_weight * fitness_components['task'] +
            self.energy_efficiency_weight * fitness_components['energy'] +
            self.coherence_stability_weight * fitness_components['coherence'] +
            self.diversity_weight * fitness_components['diversity']
        )
        
        return total_fitness


class DreamLab:
    """
    Counterfactual experimentation during DREAM state.
    Test mutations in simulation before applying to real system.
    """
    
    def __init__(self, config: dict):
        self.config = config['evolution']
        self.experiment_history: List[dict] = []
        
        self.dream_experiments_per_cycle = self.config.get('dream_experiments_per_cycle', 5)
        self.dream_experiment_duration = self.config.get('dream_experiment_duration', 100)
    
    def run_counterfactual_experiment(self, system, mutation_engine, 
                                     fitness_evaluator) -> dict:
        """
        Run a counterfactual: what if we apply this mutation?
        Returns experiment result.
        """
        # Snapshot current state
        from ..gpu_utils import to_cpu
        original_weights = system.coupling.snapshot_weights()
        original_omega = np.array(to_cpu(system.oscillator.omega0))
        original_gamma = np.array(to_cpu(system.oscillator.gamma))
        original_state = system.oscillator.get_state()
        
        # Apply radical mutation
        mutations = mutation_engine.apply_random_mutations(
            system.coupling,
            system.oscillator,
            system.freq_assigner,
            num_mutations=3  # More aggressive in dreams
        )
        
        # Run for dream duration
        initial_fitness = fitness_evaluator.evaluate(
            system.get_state_snapshot(),
            system.hive_detector
        )
        
        for _ in range(self.dream_experiment_duration):
            system.step()
        
        final_fitness = fitness_evaluator.evaluate(
            system.get_state_snapshot(),
            system.hive_detector
        )
        
        # Record result
        experiment = {
            'mutations': [m.mutation_id for m in mutations],
            'fitness_before': initial_fitness,
            'fitness_after': final_fitness,
            'improvement': final_fitness - initial_fitness,
            'successful': final_fitness > initial_fitness
        }
        
        self.experiment_history.append(experiment)
        
        # Restore state (it was just a dream)
        from ..gpu_utils import to_gpu
        system.coupling.restore_weights(original_weights)
        system.oscillator.omega0 = to_gpu(original_omega.astype(np.float32))
        system.oscillator.gamma = to_gpu(original_gamma.astype(np.float32))
        system.oscillator.set_state(original_state)
        
        # Rollback mutations (not strictly necessary since we restored from snapshot, but keep for consistency)
        for mutation in reversed(mutations):
            mutation_engine.rollback_mutation(
                mutation,
                system.coupling,
                system.oscillator
            )
        
        return experiment
    
    def get_promising_mutations(self, threshold: float = 0.1) -> List[dict]:
        """Get experiments that showed improvement."""
        return [exp for exp in self.experiment_history 
                if exp['improvement'] > threshold]


class EvolutionarySystem:
    """
    Complete evolutionary system integrating mutation, selection, and dream lab.
    """
    
    def __init__(self, config: dict):
        self.config = config
        
        self.mutation_engine = MutationEngine(config)
        self.fitness_evaluator = FitnessEvaluator(config)
        self.dream_lab = DreamLab(config)
        
        self.generation = 0
        self.organisms: List[Organism] = []
        
        self.evaluation_interval = config['evolution'].get('fitness_evaluation_interval', 1000)
        self.steps_since_eval = 0
        
        self.current_mutations: List[Mutation] = []
        self.last_fitness = 0.5
    
    def initialize(self, coupling_engine, oscillator_engine):
        """Set up baseline tracking."""
        self.mutation_engine.set_baselines(coupling_engine, oscillator_engine)
    
    def step_evolution(self, system, current_time: float):
        """
        Called each simulation step to manage evolution.
        """
        self.steps_since_eval += 1
        
        # Periodic evaluation
        if self.steps_since_eval >= self.evaluation_interval:
            self._evaluate_and_select(system, current_time)
            self.steps_since_eval = 0
    
    def _evaluate_and_select(self, system, current_time: float):
        """
        Evaluate current fitness and decide whether to keep mutations.
        """
        current_fitness = self.fitness_evaluator.evaluate(
            system.get_state_snapshot(),
            system.hive_detector
        )
        
        print(f"\n[Evolution] Generation {self.generation}")
        print(f"  Fitness: {current_fitness:.3f} (previous: {self.last_fitness:.3f})")
        
        # Update mutation fitness scores
        for mut in self.current_mutations:
            mut.fitness_after = current_fitness
        
        # Selection: keep if improved
        if current_fitness > self.last_fitness:
            print(f"  ✓ Keeping {len(self.current_mutations)} mutations (improvement: +{current_fitness - self.last_fitness:.3f})")
            for mut in self.current_mutations:
                mut.kept = True
            
            # Record successful organism
            self.organisms.append(Organism(
                generation=self.generation,
                fitness=current_fitness,
                mutations_applied=[m.mutation_id for m in self.current_mutations],
                timestamp=current_time
            ))
        else:
            print(f"  ✗ Reverting {len(self.current_mutations)} mutations (decline: {current_fitness - self.last_fitness:.3f})")
            # Rollback all mutations
            for mut in reversed(self.current_mutations):
                self.mutation_engine.rollback_mutation(
                    mut,
                    system.coupling,
                    system.oscillator
                )
        
        # Update for next generation
        self.last_fitness = max(current_fitness, self.last_fitness)
        self.generation += 1
        
        # Apply new mutations
        self.current_mutations = self.mutation_engine.apply_random_mutations(
            system.coupling,
            system.oscillator,
            system.freq_assigner
        )
        
        for mut in self.current_mutations:
            mut.timestamp = current_time
            mut.fitness_before = current_fitness
    
    def run_dream_experiments(self, system) -> List[dict]:
        """Run counterfactual experiments in dream state."""
        experiments = []
        
        for _ in range(self.dream_lab.dream_experiments_per_cycle):
            exp = self.dream_lab.run_counterfactual_experiment(
                system,
                self.mutation_engine,
                self.fitness_evaluator
            )
            experiments.append(exp)
        
        return experiments
    
    def get_statistics(self) -> dict:
        """Get evolution statistics."""
        return {
            'generation': self.generation,
            'current_fitness': self.last_fitness,
            'total_mutations': len(self.mutation_engine.mutation_history),
            'kept_mutations': sum(1 for m in self.mutation_engine.mutation_history if m.kept),
            'successful_organisms': len(self.organisms),
            'dream_experiments': len(self.dream_lab.experiment_history),
            'promising_dreams': len(self.dream_lab.get_promising_mutations())
        }

