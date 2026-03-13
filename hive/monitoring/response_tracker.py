"""
Response tracker for correlating stimuli with brain state changes.
Monitors how the fly brain responds to different visual inputs.
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict


@dataclass
class StimulusResponse:
    """Record of brain response to a stimulus."""
    stimulus_label: str
    stimulus_onset: float
    stimulus_offset: Optional[float] = None
    
    # Brain state changes
    baseline_coherence: float = 0.0
    peak_coherence: float = 0.0
    coherence_change: float = 0.0
    
    baseline_energy: float = 0.0
    peak_energy: float = 0.0
    energy_change: float = 0.0
    
    # Pattern activity
    activated_patterns: List[str] = field(default_factory=list)
    pattern_latency: float = 0.0  # Time to first pattern
    pattern_count: int = 0
    
    # Hive activity
    active_hives: int = 0
    peak_hive_count: int = 0
    
    # Memory
    memory_encoded: bool = False
    memory_strength: float = 0.0
    memory_ids: List[str] = field(default_factory=list)
    
    # Anomalies
    anomalies_detected: List = field(default_factory=list)
    anomaly_count: int = 0
    
    # Motor output
    motor_output: Dict[str, float] = field(default_factory=dict)
    
    # Duration
    response_duration: float = 0.0


class ResponseTracker:
    """
    Tracks brain responses to stimuli.
    Correlates stimulus types with emergent patterns and behaviors.
    """
    
    def __init__(self, config: Optional[dict] = None):
        # Configuration
        if config and 'monitoring' in config and 'tracking' in config['monitoring']:
            self.response_window = config['monitoring']['tracking']['response_tracking_window']
        else:
            self.response_window = 5.0  # seconds
        
        # Current response being tracked
        self.current_response: Optional[StimulusResponse] = None
        self.current_stimulus: Optional[str] = None
        self.stimulus_onset_time: float = 0.0
        
        # Response history
        self.response_history = deque(maxlen=100)
        
        # Baseline tracking (pre-stimulus)
        self.baseline_coherence = 0.0
        self.baseline_energy = 0.0
        self.baseline_hive_count = 0
        
        # Pattern timing
        self.first_pattern_time: Optional[float] = None
        
        # Statistics
        self.stimulus_response_map = defaultdict(list)  # stimulus -> list of responses
    
    def start_stimulus(self, stimulus_label: str, timestamp: float):
        """
        Mark start of a new stimulus presentation.
        
        Args:
            stimulus_label: Name/ID of stimulus
            timestamp: Current simulation time
        """
        # Save previous response if any
        if self.current_response is not None:
            self.current_response.stimulus_offset = timestamp
            self.current_response.response_duration = timestamp - self.stimulus_onset_time
            self.response_history.append(self.current_response)
            self.stimulus_response_map[self.current_stimulus].append(self.current_response)
        
        # Start new response
        self.current_stimulus = stimulus_label
        self.stimulus_onset_time = timestamp
        self.first_pattern_time = None
        
        self.current_response = StimulusResponse(
            stimulus_label=stimulus_label,
            stimulus_onset=timestamp,
            baseline_coherence=self.baseline_coherence,
            baseline_energy=self.baseline_energy,
            active_hives=self.baseline_hive_count
        )
    
    def record_step(
        self,
        stimulus_label: str,
        system_state: Dict,
        anomalies: List,
        motor_output: Dict,
        timestamp: float
    ):
        """
        Record brain state during stimulus presentation.
        
        Args:
            stimulus_label: Current stimulus
            system_state: Current brain state
            anomalies: Anomalies detected this step
            motor_output: Motor neuron activity
            timestamp: Current time
        """
        # Start new stimulus tracking if changed
        if stimulus_label != self.current_stimulus:
            self.start_stimulus(stimulus_label, timestamp)
        
        if self.current_response is None:
            return
        
        # Extract state
        coherence = system_state.get('coherence', 0.0)
        energy = system_state.get('energy', 0.0)
        hives = system_state.get('hives', [])
        patterns = system_state.get('patterns', [])
        memories = system_state.get('memories', [])
        
        # Update baselines (during blank/ISI)
        if stimulus_label == "blank":
            self.baseline_coherence = coherence
            self.baseline_energy = energy
            self.baseline_hive_count = len(hives)
            return
        
        # Track peak values
        if coherence > self.current_response.peak_coherence:
            self.current_response.peak_coherence = coherence
        
        if energy > self.current_response.peak_energy:
            self.current_response.peak_energy = energy
        
        if len(hives) > self.current_response.peak_hive_count:
            self.current_response.peak_hive_count = len(hives)
        
        # Track patterns
        if len(patterns) > 0 and self.first_pattern_time is None:
            self.first_pattern_time = timestamp
            self.current_response.pattern_latency = timestamp - self.stimulus_onset_time
        
        for pattern in patterns:
            pattern_id = pattern.pattern_id if hasattr(pattern, 'pattern_id') else str(id(pattern))
            if pattern_id not in self.current_response.activated_patterns:
                self.current_response.activated_patterns.append(pattern_id)
        
        self.current_response.pattern_count = len(patterns)
        
        # Track memory formation
        if len(memories) > len(self.current_response.memory_ids):
            for memory in memories:
                mem_id = memory.id if hasattr(memory, 'id') else str(id(memory))
                if mem_id not in self.current_response.memory_ids:
                    self.current_response.memory_ids.append(mem_id)
                    self.current_response.memory_encoded = True
                    
                    strength = memory.strength if hasattr(memory, 'strength') else 0
                    if strength > self.current_response.memory_strength:
                        self.current_response.memory_strength = strength
        
        # Track anomalies
        if len(anomalies) > 0:
            self.current_response.anomalies_detected.extend(anomalies)
            self.current_response.anomaly_count = len(self.current_response.anomalies_detected)
        
        # Update motor output (keep most recent)
        self.current_response.motor_output = motor_output
        
        # Calculate changes
        self.current_response.coherence_change = (
            self.current_response.peak_coherence - self.current_response.baseline_coherence
        )
        self.current_response.energy_change = (
            self.current_response.peak_energy - self.current_response.baseline_energy
        )
    
    def get_recent(self, n: int = 5) -> List[StimulusResponse]:
        """Get last N responses."""
        return list(self.response_history)[-n:]
    
    def get_summary_by_stimulus(self, stimulus_label: str) -> Dict:
        """
        Get summary statistics for a specific stimulus type.
        
        Args:
            stimulus_label: Stimulus to summarize
        
        Returns:
            Dictionary with average response metrics
        """
        responses = self.stimulus_response_map.get(stimulus_label, [])
        
        if len(responses) == 0:
            return {
                'stimulus': stimulus_label,
                'presentation_count': 0,
                'avg_coherence_change': 0.0,
                'avg_pattern_count': 0.0,
                'avg_pattern_latency': 0.0,
                'memory_formation_rate': 0.0,
                'avg_anomaly_count': 0.0
            }
        
        return {
            'stimulus': stimulus_label,
            'presentation_count': len(responses),
            'avg_coherence_change': np.mean([r.coherence_change for r in responses]),
            'avg_energy_change': np.mean([r.energy_change for r in responses]),
            'avg_pattern_count': np.mean([r.pattern_count for r in responses]),
            'avg_pattern_latency': np.mean([r.pattern_latency for r in responses if r.pattern_latency > 0]),
            'memory_formation_rate': sum(1 for r in responses if r.memory_encoded) / len(responses),
            'avg_anomaly_count': np.mean([r.anomaly_count for r in responses]),
            'unique_patterns': len(set(p for r in responses for p in r.activated_patterns))
        }
    
    def get_overall_summary(self) -> Dict:
        """Get overall summary across all stimuli."""
        all_stimuli = list(self.stimulus_response_map.keys())
        
        summaries = {}
        for stimulus in all_stimuli:
            summaries[stimulus] = self.get_summary_by_stimulus(stimulus)
        
        return {
            'total_responses': len(self.response_history),
            'unique_stimuli': len(all_stimuli),
            'by_stimulus': summaries
        }
    
    def get_strongest_responses(self, n: int = 5) -> List[StimulusResponse]:
        """
        Get N responses with strongest reactions.
        
        Args:
            n: Number of top responses to return
        
        Returns:
            List of responses sorted by reaction strength
        """
        # Sort by combined metric: coherence change + pattern count + anomaly count
        scored_responses = []
        for response in self.response_history:
            score = (
                response.coherence_change * 2.0 +
                response.pattern_count * 0.1 +
                response.anomaly_count * 0.5
            )
            scored_responses.append((score, response))
        
        scored_responses.sort(reverse=True, key=lambda x: x[0])
        return [r for _, r in scored_responses[:n]]
    
    def get_statistics(self) -> Dict:
        """Get general statistics."""
        return {
            'total_responses': len(self.response_history),
            'unique_stimuli': len(self.stimulus_response_map),
            'current_stimulus': self.current_stimulus,
            'tracking_window': self.response_window
        }
    
    def reset(self):
        """Reset response tracker state."""
        self.current_response = None
        self.current_stimulus = None
        self.stimulus_onset_time = 0.0
        self.response_history.clear()
        self.baseline_coherence = 0.0
        self.baseline_energy = 0.0
        self.baseline_hive_count = 0
        self.first_pattern_time = None
        self.stimulus_response_map.clear()
