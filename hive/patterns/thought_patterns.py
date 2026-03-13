"""
Thought pattern detection and tracking.
Thoughts emerge as spatio-temporal phase patterns propagating across hives.
"""

import numpy as np
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from collections import deque


@dataclass
class ThoughtPattern:
    """A spatio-temporal phase pattern representing a thought."""
    pattern_id: int
    
    # Signature
    hive_sequence: List[int]  # Sequence of hive IDs involved
    phase_fingerprint: np.ndarray  # Phase relationships between hives
    frequency_composition: Dict[str, float]  # Band -> energy
    spatial_distribution: np.ndarray  # 3D center of mass
    timing: List[float]  # Activation times
    
    # Properties
    stability: float = 0.0  # How long pattern persists
    associative_strength: float = 0.0  # How easily triggered
    emotional_valence: float = 0.0  # Neuromodulator state during activation
    complexity: int = 0  # Number of hives involved
    
    # Lifecycle
    birth_time: float = 0.0
    last_activation: float = 0.0
    activation_count: int = 0
    
    # Type
    pattern_type: str = "sequential"  # sequential, parallel, recursive, interference


class ThoughtPatternDetector:
    """
    Detects and tracks thought patterns from hive activity.
    """
    
    def __init__(self, config: dict):
        self.config = config['patterns']
        self.next_pattern_id = 0
        
        # Active patterns
        self.patterns: Dict[int, ThoughtPattern] = {}
        
        # Pattern history
        self.pattern_window_size = self.config['pattern_window']
        self.recent_patterns: deque = deque(maxlen=self.pattern_window_size)
        
        # Current hive activations
        self.hive_activation_history: deque = deque(maxlen=200)  # Last 200 timesteps
    
    def detect_patterns(self, active_hives: List, current_time: float) -> List[ThoughtPattern]:
        """
        Detect thought patterns from current hive activity.
        Returns newly detected patterns.
        """
        # Record current hive activations
        activation = {
            'time': current_time,
            'hives': [(h.hive_id, h.coherence, h.mean_amplitude) for h in active_hives]
        }
        self.hive_activation_history.append(activation)
        
        new_patterns = []
        
        # Detect different pattern types
        sequential = self._detect_sequential_patterns()
        parallel = self._detect_parallel_patterns()
        # recursive = self._detect_recursive_patterns()
        # interference = self._detect_interference_patterns()
        
        new_patterns.extend(sequential)
        new_patterns.extend(parallel)
        
        # Add to known patterns
        for pattern in new_patterns:
            self.patterns[pattern.pattern_id] = pattern
            self.recent_patterns.append(pattern.pattern_id)
        
        return new_patterns
    
    def _detect_sequential_patterns(self) -> List[ThoughtPattern]:
        """
        Detect sequential activation patterns: A → B → C → D
        """
        patterns = []
        
        if len(self.hive_activation_history) < 5:
            return patterns
        
        # Look for sequences in recent history
        recent = list(self.hive_activation_history)[-10:]  # Last 10 timesteps
        
        # Extract hive activation sequences
        sequences = []
        for activation in recent:
            # Get hives with high amplitude
            active_hives = [h_id for h_id, coh, amp in activation['hives'] if amp > 0.5]
            if active_hives:
                sequences.append((activation['time'], active_hives))
        
        if len(sequences) < 3:
            return patterns
        
        # Find consistent sequences
        # Simple approach: look for same hives activating in sequence
        hive_seq = [h_id for _, hives in sequences for h_id in hives]
        if len(set(hive_seq)) >= 3:  # At least 3 different hives
            # This is a potential pattern
            times = [t for t, _ in sequences]
            pattern = ThoughtPattern(
                pattern_id=self.next_pattern_id,
                hive_sequence=hive_seq[:5],  # First 5
                phase_fingerprint=np.array([]),  # TODO: compute
                frequency_composition={},
                spatial_distribution=np.zeros(3),
                timing=times,
                complexity=len(set(hive_seq)),
                birth_time=times[0],
                last_activation=times[-1],
                pattern_type="sequential"
            )
            self.next_pattern_id += 1
            patterns.append(pattern)
        
        return patterns
    
    def _detect_parallel_patterns(self) -> List[ThoughtPattern]:
        """
        Detect parallel activation patterns: multiple hives active simultaneously.
        """
        patterns = []
        
        if len(self.hive_activation_history) < 2:
            return patterns
        
        # Look at current activation
        current = self.hive_activation_history[-1]
        active_hives = [h_id for h_id, coh, amp in current['hives'] if amp > 0.5 and coh > 0.6]
        
        if len(active_hives) >= 3:  # At least 3 hives active simultaneously
            pattern = ThoughtPattern(
                pattern_id=self.next_pattern_id,
                hive_sequence=active_hives,
                phase_fingerprint=np.array([]),  # TODO: compute phase relationships
                frequency_composition={},
                spatial_distribution=np.zeros(3),
                timing=[current['time']],
                complexity=len(active_hives),
                birth_time=current['time'],
                last_activation=current['time'],
                pattern_type="parallel"
            )
            self.next_pattern_id += 1
            patterns.append(pattern)
        
        return patterns
    
    def find_similar_patterns(self, pattern: ThoughtPattern, threshold: float = 0.7) -> List[int]:
        """
        Find known patterns similar to this one.
        Returns list of pattern IDs.
        """
        similar = []
        
        for pid, known_pattern in self.patterns.items():
            if known_pattern.pattern_type != pattern.pattern_type:
                continue
            
            # Compute similarity based on hive overlap
            overlap = len(set(pattern.hive_sequence) & set(known_pattern.hive_sequence))
            total = len(set(pattern.hive_sequence) | set(known_pattern.hive_sequence))
            
            if total > 0:
                similarity = overlap / total
                if similarity >= threshold:
                    similar.append(pid)
        
        return similar
    
    def is_novel_pattern(self, pattern: ThoughtPattern) -> bool:
        """Check if this pattern is novel (not seen before)."""
        similar = self.find_similar_patterns(pattern, threshold=self.config['pattern_similarity_threshold'])
        return len(similar) == 0
    
    def get_pattern_statistics(self) -> dict:
        """Get statistics about detected patterns."""
        if len(self.patterns) == 0:
            return {
                'total_patterns': 0,
                'unique_patterns': 0,
                'novel_rate': 0.0
            }
        
        types = {}
        for p in self.patterns.values():
            types[p.pattern_type] = types.get(p.pattern_type, 0) + 1
        
        return {
            'total_patterns': len(self.patterns),
            'unique_patterns': len(set(tuple(p.hive_sequence) for p in self.patterns.values())),
            'pattern_types': types,
            'recent_patterns': len(self.recent_patterns)
        }
