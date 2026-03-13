"""
Minority dynamics and dissent engine.
Implements 9-vs-1 logic, false consensus detection, graceful degradation.
"""

import numpy as np
from typing import List, Optional
from ..hives import Hive


class MinorityEngine:
    """
    Detects and manages minority hives that contradict the majority.
    Minority opinions can override majority if historically successful.
    """
    
    def __init__(self, config: dict):
        self.config = config['dissent']
        self.minority_history = []
    
    def identify_minority(self, hives: List[Hive]) -> Optional[List[Hive]]:
        """
        Identify minority hives that contradict majority.
        """
        if len(hives) < 4:
            return None
        
        # Sort by coherence * amplitude
        scored = [(h, h.coherence * h.mean_amplitude) for h in hives]
        scored.sort(key=lambda x: -x[1])
        
        # Check if bottom hives form a strong minority
        minority_size = max(1, int(len(hives) * self.config['minority_threshold']))
        minority = [h for h, _ in scored[-minority_size:]]
        
        # Compute minority strength
        minority_coherence = np.mean([h.coherence for h in minority])
        majority_coherence = np.mean([h.coherence for h in scored[:-minority_size]])
        
        if minority_coherence > self.config['dissent_strength_threshold']:
            return minority
        
        return None
    
    def evaluate_dissent(self, minority_hives: List[Hive]) -> dict:
        """
        Evaluate strength of dissent and historical success.
        """
        if not minority_hives:
            return {'strength': 0.0, 'credibility': 0.0}
        
        # Current strength
        avg_coherence = np.mean([h.coherence for h in minority_hives])
        avg_amplitude = np.mean([h.mean_amplitude for h in minority_hives])
        strength = avg_coherence * avg_amplitude
        
        # Historical success rate
        success_rates = [h.success_rate() for h in minority_hives]
        credibility = np.mean(success_rates) if success_rates else 0.5
        
        return {
            'strength': strength,
            'credibility': credibility,
            'should_listen': strength > 0.5 and credibility > self.config['historical_success_threshold']
        }
    
    def detect_false_consensus(self, hives: List[Hive]) -> bool:
        """
        Detect if majority agreement is weak (false consensus).
        All agree weakly rather than having strong evidence.
        """
        if len(hives) < 3:
            return False
        
        amplitudes = [h.mean_amplitude for h in hives]
        coherences = [h.coherence for h in hives]
        
        # False consensus: low amplitude but high phase agreement
        avg_amplitude = np.mean(amplitudes)
        avg_coherence = np.mean(coherences)
        
        return (avg_amplitude < self.config['false_consensus_amplitude_threshold'] and 
                avg_coherence > 0.7)


class GracefulDegradation:
    """
    Handles system failures gracefully by simplifying processing.
    """
    
    def __init__(self, config: dict):
        self.config = config['dissent']
        self.degraded = False
    
    def check_health(self, hives: List[Hive], global_coherence: float) -> bool:
        """
        Check if system is failing and needs degradation.
        """
        if len(hives) == 0:
            return True  # Need degradation
        
        # Check for incoherence
        if global_coherence < 0.2:
            return True
        
        # Check for too many failed hives
        failure_rates = [h.failure_count / max(h.success_count + h.failure_count, 1) 
                        for h in hives]
        avg_failure = np.mean(failure_rates) if failure_rates else 0
        
        if avg_failure > 0.7:
            return True
        
        return False
    
    def degrade(self, hive_detector):
        """
        Simplify system by dissolving low-performing hives.
        """
        if self.degraded:
            return
        
        # Dissolve bottom 50% of hives by success rate
        hives = list(hive_detector.active_hives.values())
        if len(hives) < 2:
            return
        
        scored = sorted(hives, key=lambda h: h.success_rate())
        to_dissolve = scored[:len(scored)//2]
        
        for hive in to_dissolve:
            hive_detector.free_neurons.update(hive.member_ids)
            del hive_detector.active_hives[hive.hive_id]
        
        self.degraded = True
        print(f"  [GRACEFUL DEGRADATION] Dissolved {len(to_dissolve)} hives")
    
    def recover(self):
        """Mark system as recovered."""
        self.degraded = False
