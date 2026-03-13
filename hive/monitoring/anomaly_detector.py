"""
Comprehensive anomaly detection system for fly brain monitoring.
Tracks anomalies at neuron, hive, pattern, memory, and global levels.
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class AnomalyEvent:
    """Detected anomaly in brain activity."""
    timestamp: float
    type: str  # 'neuron', 'hive', 'pattern', 'memory', 'global'
    subtype: str  # Specific anomaly
    severity: float  # 0-1
    neuron_ids: List[int] = field(default_factory=list)
    hive_ids: List[str] = field(default_factory=list)
    pattern_ids: List[str] = field(default_factory=list)
    description: str = ""
    stimulus_context: Optional[str] = None
    metric_value: float = 0.0


class AnomalyDetector:
    """
    Monitors brain activity for anomalies across all levels.
    """
    
    def __init__(self, config: dict):
        self.config = config['monitoring']['thresholds']
        
        # Thresholds
        self.amplitude_sigma = self.config['amplitude_sigma']
        self.coherence_jump = self.config['coherence_jump']
        self.pattern_novelty_threshold = self.config['pattern_novelty_threshold']
        self.memory_rapid_encoding = self.config['memory_rapid_encoding']
        
        # History tracking
        self.history_size = config['monitoring']['tracking']['anomaly_history_size']
        self.anomaly_history = deque(maxlen=self.history_size)
        
        # Baseline tracking
        self.neuron_amplitude_baseline = None
        self.neuron_amplitude_std = None
        self.prev_coherence = 0.0
        self.prev_energy = 0.0
        self.prev_metastability = 0.0
        self.known_patterns = set()
        self.prev_memory_strengths = {}
        
        # Statistics
        self.anomaly_counts = {
            'neuron': 0,
            'hive': 0,
            'pattern': 0,
            'memory': 0,
            'global': 0
        }
    
    def update(
        self,
        system_state: Dict,
        stimulus_label: str,
        timestamp: float
    ) -> List[AnomalyEvent]:
        """
        Analyze current state and detect anomalies.
        
        Args:
            system_state: Dict with keys: 'oscillators', 'hives', 'patterns', 'memories', 'coherence'
            stimulus_label: Current stimulus being presented
            timestamp: Current simulation time
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Extract state components
        osc_state = system_state.get('oscillators', {})
        hives = system_state.get('hives', [])
        patterns = system_state.get('patterns', [])
        memories = system_state.get('memories', [])
        coherence = system_state.get('coherence', 0.0)
        energy = system_state.get('energy', 0.0)
        metastability = system_state.get('metastability', 0.0)
        
        # A. Neuron-Level Anomalies
        if 'amplitude' in osc_state and 'phase' in osc_state:
            neuron_anomalies = self._detect_neuron_anomalies(
                osc_state, stimulus_label, timestamp
            )
            anomalies.extend(neuron_anomalies)
        
        # B. Hive-Level Anomalies
        hive_anomalies = self._detect_hive_anomalies(hives, stimulus_label, timestamp)
        anomalies.extend(hive_anomalies)
        
        # C. Pattern-Level Anomalies
        pattern_anomalies = self._detect_pattern_anomalies(patterns, stimulus_label, timestamp)
        anomalies.extend(pattern_anomalies)
        
        # D. Memory-Level Anomalies
        memory_anomalies = self._detect_memory_anomalies(memories, stimulus_label, timestamp)
        anomalies.extend(memory_anomalies)
        
        # E. Global-Level Anomalies
        global_anomalies = self._detect_global_anomalies(
            coherence, energy, metastability, stimulus_label, timestamp
        )
        anomalies.extend(global_anomalies)
        
        # Update history
        for anomaly in anomalies:
            self.anomaly_history.append(anomaly)
            self.anomaly_counts[anomaly.type] += 1
        
        # Update baselines
        self._update_baselines(system_state)
        
        return anomalies
    
    def _detect_neuron_anomalies(
        self,
        osc_state: Dict,
        stimulus_label: str,
        timestamp: float
    ) -> List[AnomalyEvent]:
        """Detect neuron-level anomalies."""
        from ..gpu_utils import to_cpu
        
        anomalies = []
        
        # Convert GPU arrays to CPU for numpy operations
        amplitude = to_cpu(osc_state.get('amplitude', np.array([])))
        phase = to_cpu(osc_state.get('phase', np.array([])))
        frequency = to_cpu(osc_state.get('frequency', np.array([])))
        
        if len(amplitude) == 0:
            return anomalies
        
        # Initialize baseline if needed
        if self.neuron_amplitude_baseline is None:
            self.neuron_amplitude_baseline = np.copy(amplitude)
            self.neuron_amplitude_std = np.std(amplitude) if np.std(amplitude) > 0 else 0.1
            return anomalies
        
        # 1. Amplitude spikes (neurons exceeding 3σ above baseline)
        amplitude_threshold = self.neuron_amplitude_baseline + self.amplitude_sigma * self.neuron_amplitude_std
        spike_neurons = np.where(amplitude > amplitude_threshold)[0]
        
        if len(spike_neurons) > 0:
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='neuron',
                subtype='amplitude_spike',
                severity=min(1.0, len(spike_neurons) / 100),
                neuron_ids=spike_neurons.tolist()[:50],  # Limit to 50
                description=f"{len(spike_neurons)} neurons with amplitude spikes",
                stimulus_context=stimulus_label,
                metric_value=float(np.max(amplitude[spike_neurons]))
            ))
        
        # 2. Silent neurons (amplitude near zero)
        silent_threshold = 0.05
        silent_neurons = np.where(amplitude < silent_threshold)[0]
        
        if len(silent_neurons) > 100:  # Many silent = anomaly
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='neuron',
                subtype='silent_neurons',
                severity=min(1.0, len(silent_neurons) / 1000),
                neuron_ids=silent_neurons.tolist()[:50],
                description=f"{len(silent_neurons)} silent neurons",
                stimulus_context=stimulus_label,
                metric_value=len(silent_neurons)
            ))
        
        return anomalies
    
    def _detect_hive_anomalies(
        self,
        hives: List,
        stimulus_label: str,
        timestamp: float
    ) -> List[AnomalyEvent]:
        """Detect hive-level anomalies."""
        anomalies = []
        
        if len(hives) == 0:
            return anomalies
        
        # 1. Rapid hive formation (many hives forming quickly)
        if len(hives) > 30:
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='hive',
                subtype='rapid_formation',
                severity=min(1.0, len(hives) / 50),
                hive_ids=[h.hive_id if hasattr(h, 'hive_id') else str(i) for i, h in enumerate(hives[:20])],
                description=f"{len(hives)} hives active simultaneously",
                stimulus_context=stimulus_label,
                metric_value=len(hives)
            ))
        
        # 2. Coherence surges (hives with very high coherence)
        high_coherence_hives = []
        for hive in hives:
            coherence = hive.coherence if hasattr(hive, 'coherence') else 0
            if coherence > 0.9:
                hive_id = hive.hive_id if hasattr(hive, 'hive_id') else str(id(hive))
                high_coherence_hives.append(hive_id)
        
        if len(high_coherence_hives) > 0:
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='hive',
                subtype='coherence_surge',
                severity=min(1.0, len(high_coherence_hives) / 10),
                hive_ids=high_coherence_hives[:20],
                description=f"{len(high_coherence_hives)} hives with >90% coherence",
                stimulus_context=stimulus_label,
                metric_value=len(high_coherence_hives)
            ))
        
        return anomalies
    
    def _detect_pattern_anomalies(
        self,
        patterns: List,
        stimulus_label: str,
        timestamp: float
    ) -> List[AnomalyEvent]:
        """Detect pattern-level anomalies."""
        anomalies = []
        
        if len(patterns) == 0:
            return anomalies
        
        # 1. Novel patterns (never seen before)
        novel_patterns = []
        for pattern in patterns:
            pattern_id = pattern.pattern_id if hasattr(pattern, 'pattern_id') else str(id(pattern))
            if pattern_id not in self.known_patterns:
                novel_patterns.append(pattern_id)
                self.known_patterns.add(pattern_id)
        
        if len(novel_patterns) > 0:
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='pattern',
                subtype='novel_pattern',
                severity=0.7,  # Novel patterns are interesting
                pattern_ids=novel_patterns[:10],
                description=f"{len(novel_patterns)} novel thought patterns emerged",
                stimulus_context=stimulus_label,
                metric_value=len(novel_patterns)
            ))
        
        # 2. Pattern cascade (many patterns simultaneously)
        if len(patterns) > 10:
            pattern_ids = [p.pattern_id if hasattr(p, 'pattern_id') else str(id(p)) for p in patterns]
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='pattern',
                subtype='pattern_cascade',
                severity=min(1.0, len(patterns) / 20),
                pattern_ids=pattern_ids[:20],
                description=f"{len(patterns)} patterns active simultaneously",
                stimulus_context=stimulus_label,
                metric_value=len(patterns)
            ))
        
        # 3. Pattern persistence (long-lasting patterns)
        persistent_patterns = []
        for pattern in patterns:
            if hasattr(pattern, 'stability') and pattern.stability > 0.8:
                pattern_id = pattern.pattern_id if hasattr(pattern, 'pattern_id') else str(id(pattern))
                persistent_patterns.append(pattern_id)
        
        if len(persistent_patterns) > 0:
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='pattern',
                subtype='persistent_pattern',
                severity=0.6,
                pattern_ids=persistent_patterns[:10],
                description=f"{len(persistent_patterns)} highly stable patterns",
                stimulus_context=stimulus_label,
                metric_value=len(persistent_patterns)
            ))
        
        return anomalies
    
    def _detect_memory_anomalies(
        self,
        memories: List,
        stimulus_label: str,
        timestamp: float
    ) -> List[AnomalyEvent]:
        """Detect memory-level anomalies."""
        anomalies = []
        
        if len(memories) == 0:
            return anomalies
        
        # Track rapid encoding
        rapid_encoding_memories = []
        for memory in memories:
            if not hasattr(memory, 'id'):
                continue
            
            mem_id = memory.id if hasattr(memory, 'id') else str(id(memory))
            strength = memory.strength if hasattr(memory, 'strength') else 0
            
            prev_strength = self.prev_memory_strengths.get(mem_id, 0)
            strength_increase = strength - prev_strength
            
            if strength_increase > self.memory_rapid_encoding:
                rapid_encoding_memories.append(mem_id)
            
            self.prev_memory_strengths[mem_id] = strength
        
        if len(rapid_encoding_memories) > 0:
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='memory',
                subtype='rapid_encoding',
                severity=min(1.0, len(rapid_encoding_memories) / 5),
                description=f"{len(rapid_encoding_memories)} memories rapidly encoded",
                stimulus_context=stimulus_label,
                metric_value=len(rapid_encoding_memories)
            ))
        
        return anomalies
    
    def _detect_global_anomalies(
        self,
        coherence: float,
        energy: float,
        metastability: float,
        stimulus_label: str,
        timestamp: float
    ) -> List[AnomalyEvent]:
        """Detect global-level anomalies."""
        anomalies = []
        
        # 1. Coherence jumps
        coherence_change = abs(coherence - self.prev_coherence)
        if coherence_change > self.coherence_jump:
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='global',
                subtype='coherence_jump',
                severity=min(1.0, coherence_change / 0.5),
                description=f"Global coherence jumped by {coherence_change:.2f}",
                stimulus_context=stimulus_label,
                metric_value=coherence_change
            ))
        
        # 2. Energy spikes
        if self.prev_energy > 0:
            energy_ratio = energy / self.prev_energy
            if energy_ratio > 1.5:  # 50% increase
                anomalies.append(AnomalyEvent(
                    timestamp=timestamp,
                    type='global',
                    subtype='energy_spike',
                    severity=min(1.0, (energy_ratio - 1.0) / 2.0),
                    description=f"System energy spiked by {(energy_ratio-1)*100:.1f}%",
                    stimulus_context=stimulus_label,
                    metric_value=energy_ratio
                ))
        
        # 3. Metastability shifts
        metastability_change = abs(metastability - self.prev_metastability)
        if metastability_change > 0.3:
            anomalies.append(AnomalyEvent(
                timestamp=timestamp,
                type='global',
                subtype='metastability_shift',
                severity=min(1.0, metastability_change / 0.5),
                description=f"Metastability shifted by {metastability_change:.2f}",
                stimulus_context=stimulus_label,
                metric_value=metastability_change
            ))
        
        self.prev_coherence = coherence
        self.prev_energy = energy
        self.prev_metastability = metastability
        
        return anomalies
    
    def _update_baselines(self, system_state: Dict):
        """Update baseline measurements for anomaly detection."""
        osc_state = system_state.get('oscillators', {})
        
        if 'amplitude' in osc_state:
            amplitude = osc_state['amplitude']
            if len(amplitude) > 0:
                # Exponential moving average
                if self.neuron_amplitude_baseline is not None:
                    alpha = 0.01  # Slow adaptation
                    self.neuron_amplitude_baseline = (
                        alpha * amplitude + (1 - alpha) * self.neuron_amplitude_baseline
                    )
                    self.neuron_amplitude_std = (
                        alpha * np.std(amplitude) + (1 - alpha) * self.neuron_amplitude_std
                    )
    
    def get_anomaly_summary(self, time_window: float = 10.0) -> Dict:
        """
        Get summary statistics for recent anomalies.
        
        Args:
            time_window: Time window in seconds
        
        Returns:
            Dictionary with anomaly statistics
        """
        if len(self.anomaly_history) == 0:
            return {
                'total_anomalies': 0,
                'by_type': {},
                'by_subtype': {},
                'mean_severity': 0.0,
                'recent_anomalies': []
            }
        
        # Filter recent anomalies
        latest_time = self.anomaly_history[-1].timestamp
        recent = [a for a in self.anomaly_history if a.timestamp > latest_time - time_window]
        
        # Count by type
        by_type = {}
        by_subtype = {}
        severities = []
        
        for anomaly in recent:
            by_type[anomaly.type] = by_type.get(anomaly.type, 0) + 1
            by_subtype[anomaly.subtype] = by_subtype.get(anomaly.subtype, 0) + 1
            severities.append(anomaly.severity)
        
        return {
            'total_anomalies': len(recent),
            'by_type': by_type,
            'by_subtype': by_subtype,
            'mean_severity': np.mean(severities) if severities else 0.0,
            'recent_anomalies': [
                {
                    'timestamp': a.timestamp,
                    'type': a.type,
                    'subtype': a.subtype,
                    'severity': a.severity,
                    'description': a.description,
                    'stimulus': a.stimulus_context
                }
                for a in recent[-20:]  # Last 20
            ]
        }
    
    def reset(self):
        """Reset anomaly detector state."""
        self.anomaly_history.clear()
        self.neuron_amplitude_baseline = None
        self.neuron_amplitude_std = None
        self.prev_coherence = 0.0
        self.prev_energy = 0.0
        self.prev_metastability = 0.0
        self.known_patterns.clear()
        self.prev_memory_strengths.clear()
        self.anomaly_counts = {k: 0 for k in self.anomaly_counts}
