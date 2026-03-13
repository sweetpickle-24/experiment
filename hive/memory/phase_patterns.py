"""
Wave-based memory system using phase-lock patterns, attractor basins, and interference.
Memory is encoded as stable oscillatory patterns, not discrete weights.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import deque


@dataclass
class PhasePattern:
    """A memory encoded as phase relationships between neuron groups."""
    pattern_id: int
    neuron_ids: np.ndarray  # Which neurons participate
    phase_signature: np.ndarray  # Phase relationships [0, 2π]
    amplitude_profile: np.ndarray  # Amplitude pattern
    frequency_mix: Dict[str, float]  # Energy per band
    
    # Metadata
    encoding_time: float
    strength: float  # How stable is this pattern
    activation_count: int = 0
    last_activation: float = 0.0
    
    def similarity(self, other: 'PhasePattern') -> float:
        """Compute similarity between two patterns."""
        # Neuron overlap
        neuron_overlap = len(set(self.neuron_ids) & set(other.neuron_ids)) / \
                        max(len(self.neuron_ids), len(other.neuron_ids))
        
        if neuron_overlap < 0.3:
            return 0.0
        
        # Phase similarity (circular correlation)
        common_neurons = list(set(self.neuron_ids) & set(other.neuron_ids))
        if len(common_neurons) < 3:
            return neuron_overlap * 0.5
        
        my_phases = self.phase_signature[:len(common_neurons)]
        other_phases = other.phase_signature[:len(common_neurons)]
        
        # Circular distance
        phase_diff = np.angle(np.exp(1j * (my_phases - other_phases)))
        phase_sim = 1.0 - np.mean(np.abs(phase_diff)) / np.pi
        
        return 0.5 * neuron_overlap + 0.5 * phase_sim


class PhasePatternMemory:
    """
    Memory storage using phase-lock patterns.
    Memories are stable phase relationships that emerge from repeated activation.
    """
    
    def __init__(self, config: dict):
        self.config = config['memory']
        self.patterns: Dict[int, PhasePattern] = {}
        self.next_pattern_id = 0
        
        # Short-term buffer
        self.recent_activations: deque = deque(maxlen=100)
        
        # Hebbian-like learning rate
        self.learning_rate = self.config.get('hebbian_learning_rate', 0.01)
        self.phase_lock_threshold = self.config.get('phase_lock_threshold', 0.8)
        
        # ID to index mapping (will be set externally)
        self.id_to_idx: Dict[int, int] = {}
    
    def encode_current_state(self, oscillator_state, hives: List, current_time: float) -> Optional[PhasePattern]:
        """
        Encode current oscillator state as a memory pattern.
        Only encodes if there's strong phase coherence.
        """
        if len(hives) == 0:
            return None
        
        # Collect all neurons from coherent hives
        coherent_hives = [h for h in hives if h.coherence > self.phase_lock_threshold]
        if len(coherent_hives) == 0:
            return None
        
        # Get participating neurons
        neuron_ids = []
        for hive in coherent_hives:
            neuron_ids.extend(list(hive.member_ids)[:50])  # Limit size
        
        if len(neuron_ids) < 10:
            return None
        
        neuron_ids = np.array(neuron_ids)
        
        # Convert IDs to indices for array access
        if not self.id_to_idx:
            # Fallback: assume IDs are indices (0..N-1)
            neuron_indices = neuron_ids
            valid_neuron_ids = neuron_ids
        else:
            id_to_idx_pairs = [(nid, self.id_to_idx.get(nid, -1)) for nid in neuron_ids]
            valid_pairs = [(nid, idx) for nid, idx in id_to_idx_pairs if idx >= 0]
            if len(valid_pairs) < 10:
                return None
            valid_neuron_ids = np.array([nid for nid, idx in valid_pairs])
            neuron_indices = np.array([idx for nid, idx in valid_pairs])
        
        # Extract phase signature
        phases = oscillator_state.phase[neuron_indices]
        amplitudes = oscillator_state.amplitude[neuron_indices]
        
        # Compute frequency composition
        velocities = oscillator_state.velocity[neuron_indices]
        freqs_hz = (velocities / (2 * np.pi)) * 1000
        
        freq_mix = {}
        bands = {'delta': (0.5, 4), 'theta': (4, 8), 'alpha': (8, 13), 
                'beta': (13, 30), 'gamma': (30, 100)}
        
        for band_name, (f_min, f_max) in bands.items():
            mask = (freqs_hz >= f_min) & (freqs_hz <= f_max)
            freq_mix[band_name] = np.sum(amplitudes[mask] ** 2)
        
        # Create pattern
        pattern = PhasePattern(
            pattern_id=self.next_pattern_id,
            neuron_ids=valid_neuron_ids,
            phase_signature=phases,
            amplitude_profile=amplitudes,
            frequency_mix=freq_mix,
            encoding_time=current_time,
            strength=np.mean([h.coherence for h in coherent_hives])
        )
        
        self.next_pattern_id += 1
        
        # Check if similar pattern exists
        similar_id = self._find_similar(pattern)
        if similar_id is not None:
            # Strengthen existing pattern
            self._strengthen_pattern(similar_id, pattern)
            return self.patterns[similar_id]
        else:
            # Store new pattern
            self.patterns[pattern.pattern_id] = pattern
            return pattern
    
    def _find_similar(self, pattern: PhasePattern, threshold: float = 0.7) -> Optional[int]:
        """Find if similar pattern already exists."""
        for pid, existing in self.patterns.items():
            if pattern.similarity(existing) >= threshold:
                return pid
        return None
    
    def _strengthen_pattern(self, pattern_id: int, new_activation: PhasePattern):
        """Strengthen existing pattern with new activation (Hebbian-like)."""
        existing = self.patterns[pattern_id]
        
        # Update strength
        existing.strength = existing.strength * (1 - self.learning_rate) + \
                          new_activation.strength * self.learning_rate
        
        # Update phase signature (moving average)
        # Find common neurons
        common_mask = np.isin(existing.neuron_ids, new_activation.neuron_ids)
        if np.any(common_mask):
            # Circular mean for phases
            old_phases = existing.phase_signature[common_mask]
            new_indices = [np.where(new_activation.neuron_ids == nid)[0][0] 
                          for nid in existing.neuron_ids[common_mask]]
            new_phases = new_activation.phase_signature[new_indices]
            
            # Circular mean
            combined = np.angle(
                (1 - self.learning_rate) * np.exp(1j * old_phases) +
                self.learning_rate * np.exp(1j * new_phases)
            )
            existing.phase_signature[common_mask] = combined
        
        existing.activation_count += 1
        existing.last_activation = new_activation.encoding_time
    
    def retrieve_by_partial_cue(self, cue_neuron_ids: np.ndarray, 
                                cue_phases: np.ndarray, 
                                threshold: float = 0.5) -> Optional[PhasePattern]:
        """
        Retrieve memory from partial cue (pattern completion).
        Given some neurons and their phases, find matching memory.
        """
        best_match = None
        best_similarity = 0.0
        
        # Create temporary pattern from cue
        cue_pattern = PhasePattern(
            pattern_id=-1,
            neuron_ids=cue_neuron_ids,
            phase_signature=cue_phases,
            amplitude_profile=np.ones_like(cue_phases),
            frequency_mix={},
            encoding_time=0.0,
            strength=1.0
        )
        
        # Find best matching stored pattern
        for pattern in self.patterns.values():
            sim = pattern.similarity(cue_pattern)
            if sim > best_similarity:
                best_similarity = sim
                best_match = pattern
        
        if best_similarity >= threshold:
            best_match.activation_count += 1
            return best_match
        
        return None
    
    def get_strongest_patterns(self, n: int = 10) -> List[PhasePattern]:
        """Get N strongest (most reinforced) patterns."""
        sorted_patterns = sorted(self.patterns.values(), 
                               key=lambda p: p.strength * p.activation_count,
                               reverse=True)
        return sorted_patterns[:n]
    
    def decay_patterns(self, decay_rate: float = 0.01):
        """Decay unused patterns over time."""
        to_remove = []
        for pid, pattern in self.patterns.items():
            pattern.strength *= (1 - decay_rate)
            if pattern.strength < 0.1:
                to_remove.append(pid)
        
        for pid in to_remove:
            del self.patterns[pid]


class AttractorBasinMemory:
    """
    Memory as attractor basins in the oscillator phase space.
    Stable resonance modes that the system naturally falls into.
    """
    
    def __init__(self, config: dict, coupling_engine):
        self.config = config['memory']
        self.coupling = coupling_engine
        
        # Attractor basins = modified coupling weights
        self.attractor_modifications: Dict[int, np.ndarray] = {}
        self.next_attractor_id = 0
        
        self.carving_rate = self.config.get('attractor_carving_rate', 0.005)
        
        # ID to index mapping
        self.id_to_idx: Dict[int, int] = {}
    
    def carve_attractor(self, oscillator_state, neuron_ids: np.ndarray) -> int:
        """
        Carve a new attractor basin by strengthening connections within a group.
        This makes the system more likely to return to this configuration.
        neuron_ids: Actual neuron IDs (not indices).
        """
        if len(neuron_ids) < 5:
            return -1
        
        # Convert IDs to indices
        if not self.id_to_idx:
            # Fallback: assume IDs are indices
            neuron_indices = neuron_ids
        else:
            neuron_indices = np.array([self.id_to_idx.get(nid, -1) for nid in neuron_ids])
            neuron_indices = neuron_indices[neuron_indices >= 0]
            if len(neuron_indices) < 5:
                return -1
        
        # Get modifications array for intra-group connections (pass indices, not IDs)
        weight_modifications = self.coupling.get_weight_modifications_array(neuron_indices)
        
        # Scale by carving rate
        weight_modifications *= self.carving_rate
        
        attractor_id = self.next_attractor_id
        self.attractor_modifications[attractor_id] = weight_modifications
        self.next_attractor_id += 1
        
        # Apply modification to coupling
        self.coupling.apply_weight_modifications(weight_modifications, scale=1.0)
        
        return attractor_id
    
    def activate_attractor(self, attractor_id: int):
        """Temporarily strengthen an attractor basin."""
        if attractor_id in self.attractor_modifications:
            self.coupling.apply_weight_modifications(self.attractor_modifications[attractor_id], scale=0.5)
    
    def deactivate_attractor(self, attractor_id: int):
        """Weaken attractor influence."""
        if attractor_id in self.attractor_modifications:
            self.coupling.apply_weight_modifications(self.attractor_modifications[attractor_id], scale=-0.5)


class WaveInterferenceMemory:
    """
    Holographic memory storage via wave interference patterns.
    Multiple memories superposed, retrieved by resonant frequency.
    """
    
    def __init__(self, config: dict):
        self.config = config['memory']
        
        # Interference patterns stored as frequency->phase_pattern
        self.interference_patterns: Dict[float, np.ndarray] = {}
    
    def encode_as_interference(self, frequencies: np.ndarray, 
                              phases: np.ndarray,
                              amplitudes: np.ndarray) -> float:
        """
        Encode memory as interference pattern at specific frequency.
        Returns resonant frequency.
        """
        # Compute dominant frequency
        resonant_freq = np.mean(frequencies[amplitudes > np.median(amplitudes)])
        
        # Store phase pattern at this frequency
        if resonant_freq in self.interference_patterns:
            # Superpose with existing
            self.interference_patterns[resonant_freq] = np.angle(
                np.exp(1j * self.interference_patterns[resonant_freq]) +
                np.exp(1j * phases)
            )
        else:
            self.interference_patterns[resonant_freq] = phases.copy()
        
        return resonant_freq
    
    def retrieve_by_frequency(self, target_freq: float, 
                             bandwidth: float = 2.0) -> Optional[np.ndarray]:
        """
        Retrieve pattern by resonant frequency (within bandwidth).
        """
        for stored_freq, pattern in self.interference_patterns.items():
            if abs(stored_freq - target_freq) < bandwidth:
                return pattern
        return None


class MemoryConsolidation:
    """
    Memory consolidation during sleep phase.
    Replays and strengthens important patterns.
    """
    
    def __init__(self, phase_memory: PhasePatternMemory,
                 attractor_memory: AttractorBasinMemory):
        self.phase_memory = phase_memory
        self.attractor_memory = attractor_memory
        
        self.replay_queue: deque = deque(maxlen=50)
    
    def consolidate_recent_memories(self, oscillator_engine, 
                                   replay_speed: float = 10.0,
                                   cycles: int = 100):
        """
        Consolidate memories during sleep by replaying them.
        replay_speed: how many times faster than real-time (10x typical)
        """
        # Get strongest recent patterns
        patterns = self.phase_memory.get_strongest_patterns(n=10)
        
        for pattern in patterns:
            # Carve attractor basin for this pattern
            self.attractor_memory.carve_attractor(
                oscillator_engine.get_state(),
                pattern.neuron_ids
            )
            
            # Strengthen phase pattern
            pattern.strength *= 1.1  # 10% boost during consolidation
    
    def prune_weak_memories(self, threshold: float = 0.2):
        """Remove weak, rarely accessed memories."""
        self.phase_memory.decay_patterns(decay_rate=0.05)


class IntegratedMemorySystem:
    """
    Complete wave-based memory system integrating all mechanisms.
    """
    
    def __init__(self, config: dict, coupling_engine):
        self.config = config
        
        self.phase_memory = PhasePatternMemory(config)
        self.attractor_memory = AttractorBasinMemory(config, coupling_engine)
        self.interference_memory = WaveInterferenceMemory(config)
        self.consolidation = MemoryConsolidation(
            self.phase_memory,
            self.attractor_memory
        )
        
        # Set ID mapping from coupling engine
        if hasattr(coupling_engine, 'id_to_idx'):
            self.phase_memory.id_to_idx = coupling_engine.id_to_idx
            self.attractor_memory.id_to_idx = coupling_engine.id_to_idx
    
    def encode(self, oscillator_state, hives: List, current_time: float):
        """Encode current state into all memory systems."""
        # Phase pattern memory
        pattern = self.phase_memory.encode_current_state(
            oscillator_state, hives, current_time
        )
        
        if pattern is not None:
            # Carve attractor (pattern.neuron_ids are already validated IDs)
            self.attractor_memory.carve_attractor(
                oscillator_state,
                pattern.neuron_ids
            )
            
            # Store as interference pattern
            # Convert IDs to indices for oscillator array access
            if hasattr(self.phase_memory, 'id_to_idx') and self.phase_memory.id_to_idx:
                indices = np.array([self.phase_memory.id_to_idx.get(nid, -1) for nid in pattern.neuron_ids])
                indices = indices[indices >= 0]
                if len(indices) > 0:
                    freqs = (oscillator_state.velocity[indices] / (2*np.pi)) * 1000
                    self.interference_memory.encode_as_interference(
                        freqs,
                        pattern.phase_signature,
                        pattern.amplitude_profile
                    )
            else:
                # Fallback: assume IDs are indices
                freqs = (oscillator_state.velocity[pattern.neuron_ids] / (2*np.pi)) * 1000
                self.interference_memory.encode_as_interference(
                    freqs,
                    pattern.phase_signature,
                    pattern.amplitude_profile
                )
    
    def retrieve(self, partial_cue_neurons: np.ndarray, 
                partial_cue_phases: np.ndarray) -> Optional[PhasePattern]:
        """Retrieve memory from partial cue."""
        return self.phase_memory.retrieve_by_partial_cue(
            partial_cue_neurons,
            partial_cue_phases
        )
    
    def consolidate_sleep(self, oscillator_engine):
        """Run memory consolidation during sleep."""
        self.consolidation.consolidate_recent_memories(oscillator_engine)
    
    def get_statistics(self) -> dict:
        """Get memory system statistics."""
        return {
            'num_phase_patterns': len(self.phase_memory.patterns),
            'num_attractors': len(self.attractor_memory.attractor_modifications),
            'num_interference_patterns': len(self.interference_memory.interference_patterns),
            'strongest_patterns': [
                {
                    'id': p.pattern_id,
                    'strength': p.strength,
                    'activations': p.activation_count,
                    'neurons': len(p.neuron_ids)
                }
                for p in self.phase_memory.get_strongest_patterns(5)
            ]
        }

