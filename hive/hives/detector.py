"""
Adaptive hive detection using spatial, functional, and phase-lock mechanisms.
Hives are coherent clusters of oscillating neurons.
"""

import numpy as np
from typing import List, Set, Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Hive:
    """A coherent cluster of neurons (bees)."""
    hive_id: int
    member_ids: Set[int] = field(default_factory=set)
    
    # Collective dynamics
    collective_phase: float = 0.0
    coherence: float = 0.0
    mean_amplitude: float = 0.0
    mean_frequency: float = 0.0
    
    # Specialization
    specialization: Optional[str] = None  # e.g., "visual_motion", "olfactory"
    input_response_pattern: Optional[np.ndarray] = None
    
    # Lifecycle
    birth_time: float = 0.0
    lifespan: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    
    # Spatial properties
    center_position: Optional[np.ndarray] = None
    spatial_extent: float = 0.0
    
    def success_rate(self) -> float:
        """Historical success rate."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5
    
    def age(self, current_time: float) -> float:
        """Age in milliseconds."""
        return current_time - self.birth_time


class HiveDetector:
    """
    Real-time detection of coherent hive formations using three mechanisms:
    1. Spatial clustering (proximity + coherence)
    2. Functional specialization (response to specific inputs)
    3. Phase-lock assemblies (sustained synchronization)
    """
    
    def __init__(self, connectome, spatial_index, oscillator_engine, config: dict):
        self.connectome = connectome
        self.spatial_index = spatial_index
        self.oscillator = oscillator_engine
        self.config = config['hives']
        
        self.next_hive_id = 0
        self.active_hives: Dict[int, Hive] = {}
        
        # Coherence history for each potential hive
        self.coherence_history: Dict[frozenset, List[tuple]] = defaultdict(list)  # (time, coherence)
        
        # Free neurons (not in any hive)
        self.free_neurons: Set[int] = set(connectome.neurons.keys())
    
    def detect_hives(self, current_time: float) -> List[Hive]:
        """
        Run all detection mechanisms and update active hives.
        Returns list of newly formed hives.
        """
        new_hives = []
        
        # 1. Spatial clustering
        spatial_candidates = self._detect_spatial_clusters()
        
        # 2. Phase-lock assemblies
        phaselock_candidates = self._detect_phaselock_assemblies()
        
        # 3. Functional specialization (requires input history - skip for now)
        # functional_candidates = self._detect_functional_groups()
        
        # Merge candidates
        all_candidates = spatial_candidates + phaselock_candidates
        
        # Validate and create hives
        for candidate_ids in all_candidates:
            if self._validate_hive_candidate(candidate_ids, current_time):
                hive = self._create_hive(candidate_ids, current_time)
                if hive:
                    new_hives.append(hive)
        
        # Update existing hives
        self._update_existing_hives(current_time)
        
        # Check for deaths
        self._check_hive_deaths(current_time)
        
        return new_hives
    
    def _detect_spatial_clusters(self) -> List[Set[int]]:
        """Find spatially coherent clusters."""
        candidates = []
        radius = self.config['spatial_radius']
        
        # Sample some free neurons
        sample_size = min(len(self.free_neurons), 100)
        if sample_size == 0:
            return []
        
        sample = np.random.choice(list(self.free_neurons), sample_size, replace=False)
        
        for neuron_id in sample:
            # Find nearby neurons
            neighbors = self.spatial_index.find_within_radius(neuron_id, radius)
            neighbor_ids = {nid for nid, _ in neighbors if nid in self.free_neurons}
            neighbor_ids.add(neuron_id)
            
            if len(neighbor_ids) < self.config['min_size']:
                continue
            
            # Check if they're coherent
            indices = [self.spatial_index.neuron_ids.index(nid) for nid in neighbor_ids]
            coherence = self.oscillator.get_phase_coherence(np.array(indices))
            
            if coherence >= self.config['coherence_threshold']:
                candidates.append(neighbor_ids)
        
        # Remove overlapping candidates (keep largest)
        candidates = self._remove_overlaps(candidates)
        return candidates
    
    def _detect_phaselock_assemblies(self) -> List[Set[int]]:
        """Find groups with sustained phase coherence."""
        candidates = []
        
        # Strategy: cluster neurons by their connectivity and phase relationships
        # For efficiency, sample from free neurons
        
        sample_size = min(len(self.free_neurons), 50)
        if sample_size == 0:
            return []
        
        sample = np.random.choice(list(self.free_neurons), sample_size, replace=False)
        
        for seed_id in sample:
            # Get strongly connected neurons (bidirectional or strong unidirectional)
            connected = self._get_strongly_connected(seed_id)
            
            if len(connected) < self.config['min_size']:
                continue
            
            # Check phase coherence
            indices = [self.spatial_index.neuron_ids.index(nid) for nid in connected if nid in self.spatial_index.neuron_ids]
            if len(indices) < self.config['min_size']:
                continue
            
            coherence = self.oscillator.get_phase_coherence(np.array(indices))
            
            if coherence >= self.config['coherence_threshold']:
                candidates.append(connected)
        
        candidates = self._remove_overlaps(candidates)
        return candidates
    
    def _get_strongly_connected(self, neuron_id: int, threshold: float = 5.0) -> Set[int]:
        """Get neurons strongly connected to this one."""
        connected = {neuron_id}
        
        # Outgoing
        targets = self.connectome.get_postsynaptic(neuron_id)
        for target_id, weight, _ in targets:
            if weight >= threshold and target_id in self.free_neurons:
                connected.add(target_id)
        
        # Limit size
        if len(connected) > 50:
            connected = set(list(connected)[:50])
        
        return connected
    
    def _remove_overlaps(self, candidates: List[Set[int]]) -> List[Set[int]]:
        """Remove overlapping candidates, keeping largest."""
        if len(candidates) <= 1:
            return candidates
        
        # Sort by size (largest first)
        candidates = sorted(candidates, key=len, reverse=True)
        
        kept = []
        used_neurons = set()
        
        for candidate in candidates:
            # Check if mostly unused neurons
            overlap = len(candidate & used_neurons)
            if overlap < len(candidate) * 0.5:  # Less than 50% overlap
                kept.append(candidate - used_neurons)  # Remove overlapping neurons
                used_neurons.update(candidate)
        
        return kept
    
    def _validate_hive_candidate(self, candidate_ids: Set[int], current_time: float) -> bool:
        """Validate that a candidate should become a hive."""
        if len(candidate_ids) < self.config['min_size']:
            return False
        
        # Check coherence history
        candidate_frozen = frozenset(candidate_ids)
        history = self.coherence_history[candidate_frozen]
        
        # Add current measurement
        indices = [self.spatial_index.neuron_ids.index(nid) for nid in candidate_ids if nid in self.spatial_index.neuron_ids]
        if len(indices) < self.config['min_size']:
            return False
        
        coherence = self.oscillator.get_phase_coherence(np.array(indices))
        history.append((current_time, coherence))
        
        # Keep only recent history (last 200ms)
        history = [(t, c) for t, c in history if current_time - t <= 200]
        self.coherence_history[candidate_frozen] = history
        
        if len(history) < 2:
            return False
        
        # Check sustained coherence
        duration = current_time - history[0][0]
        avg_coherence = np.mean([c for _, c in history])
        
        if duration >= self.config['coherence_duration'] and avg_coherence >= self.config['coherence_threshold']:
            return True
        
        return False
    
    def _create_hive(self, member_ids: Set[int], current_time: float) -> Optional[Hive]:
        """Create a new hive from validated candidates."""
        # Remove from free neurons
        member_ids = member_ids & self.free_neurons
        if len(member_ids) < self.config['min_size']:
            return None
        
        self.free_neurons -= member_ids
        
        # Compute initial properties
        from ..gpu_utils import array_index, to_cpu, mean as gpu_mean
        indices = [self.spatial_index.neuron_ids.index(nid) for nid in member_ids]
        indices_array = np.array(indices)
        
        coherence = self.oscillator.get_phase_coherence(indices_array)
        mean_phase = self.oscillator.get_mean_phase(indices_array)
        
        # Get amplitude using GPU-safe indexing
        amplitudes_subset = array_index(self.oscillator.amplitude, indices_array)
        mean_amplitude = float(to_cpu(gpu_mean(amplitudes_subset)))
        
        mean_frequency = self.oscillator.get_dominant_frequency(indices_array)
        
        # Compute spatial center
        positions = np.array([self.connectome.neurons[nid].position for nid in member_ids])
        center = np.mean(positions, axis=0)
        extent = np.max(np.linalg.norm(positions - center, axis=1))
        
        hive = Hive(
            hive_id=self.next_hive_id,
            member_ids=member_ids,
            collective_phase=mean_phase,
            coherence=coherence,
            mean_amplitude=mean_amplitude,
            mean_frequency=mean_frequency,
            birth_time=current_time,
            center_position=center,
            spatial_extent=extent
        )
        
        self.active_hives[self.next_hive_id] = hive
        self.next_hive_id += 1
        
        return hive
    
    def _update_existing_hives(self, current_time: float):
        """Update properties of existing hives."""
        for hive in self.active_hives.values():
            indices = [self.spatial_index.neuron_ids.index(nid) for nid in hive.member_ids if nid in self.spatial_index.neuron_ids]
            if len(indices) == 0:
                continue
            
            indices_array = np.array(indices)
            
            hive.coherence = self.oscillator.get_phase_coherence(indices_array)
            hive.collective_phase = self.oscillator.get_mean_phase(indices_array)
            
            # Get amplitude using GPU-safe indexing
            from ..gpu_utils import array_index, to_cpu, mean as gpu_mean
            amplitudes_subset = array_index(self.oscillator.amplitude, indices_array)
            hive.mean_amplitude = float(to_cpu(gpu_mean(amplitudes_subset)))
            
            hive.mean_frequency = self.oscillator.get_dominant_frequency(indices_array)
            hive.lifespan = current_time - hive.birth_time
            
            # Try to recruit nearby free neurons
            self._try_recruit(hive, current_time)
    
    def _try_recruit(self, hive: Hive, current_time: float):
        """Try to recruit nearby free neurons into hive."""
        if len(self.free_neurons) == 0:
            return
        
        # Sample some members to check neighborhood
        sample_size = min(len(hive.member_ids), 5)
        sample = np.random.choice(list(hive.member_ids), sample_size, replace=False)
        
        candidates = set()
        for member_id in sample:
            neighbors = self.spatial_index.find_within_radius(
                member_id, 
                self.config['recruitment_radius']
            )
            for nid, _ in neighbors:
                if nid in self.free_neurons:
                    candidates.add(nid)
        
        # Check if candidates are coherent with hive
        if len(candidates) == 0:
            return
        
        hive_indices = [self.spatial_index.neuron_ids.index(nid) for nid in hive.member_ids if nid in self.spatial_index.neuron_ids]
        
        for candidate_id in list(candidates)[:5]:  # Limit recruitment rate
            candidate_idx = self.spatial_index.neuron_ids.index(candidate_id)
            test_indices = hive_indices + [candidate_idx]
            
            coherence = self.oscillator.get_phase_coherence(np.array(test_indices))
            
            if coherence >= self.config['recruitment_coherence']:
                hive.member_ids.add(candidate_id)
                self.free_neurons.remove(candidate_id)
    
    def _check_hive_deaths(self, current_time: float):
        """Check for hives that should dissolve."""
        to_remove = []
        
        for hive_id, hive in self.active_hives.items():
            # Death condition: low coherence sustained
            if hive.coherence < self.config['death_coherence']:
                # Check history
                recent_time = current_time - self.config['death_duration']
                if hive.birth_time < recent_time:  # Old enough to die
                    to_remove.append(hive_id)
        
        # Dissolve hives
        for hive_id in to_remove:
            hive = self.active_hives[hive_id]
            self.free_neurons.update(hive.member_ids)
            del self.active_hives[hive_id]
    
    def get_hive_by_neuron(self, neuron_id: int) -> Optional[Hive]:
        """Find which hive a neuron belongs to."""
        for hive in self.active_hives.values():
            if neuron_id in hive.member_ids:
                return hive
        return None
    
    def get_hives_summary(self) -> dict:
        """Get summary statistics."""
        if len(self.active_hives) == 0:
            return {
                'num_hives': 0,
                'total_members': 0,
                'free_neurons': len(self.free_neurons)
            }
        
        sizes = [len(h.member_ids) for h in self.active_hives.values()]
        coherences = [h.coherence for h in self.active_hives.values()]
        ages = [h.lifespan for h in self.active_hives.values()]
        
        return {
            'num_hives': len(self.active_hives),
            'total_members': sum(sizes),
            'free_neurons': len(self.free_neurons),
            'avg_hive_size': np.mean(sizes),
            'avg_coherence': np.mean(coherences),
            'avg_age': np.mean(ages),
            'oldest_hive': max(ages) if ages else 0
        }
