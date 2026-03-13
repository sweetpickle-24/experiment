"""
Inter-hive communication via phase resonance.
"""

import numpy as np
from typing import List, Tuple
from .detector import Hive


class HiveCommunication:
    """
    Manages communication between hives via phase resonance.
    Hives with harmonic frequency relationships synchronize.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.communication_graph = {}  # (hive1_id, hive2_id) -> strength
    
    def compute_inter_hive_coupling(self, hives: List[Hive]) -> dict:
        """
        Compute coupling strength between all pairs of hives.
        Returns dict: (hive1_id, hive2_id) -> coupling_strength
        """
        coupling = {}
        
        for i, hive1 in enumerate(hives):
            for hive2 in hives[i+1:]:
                strength = self._compute_resonance(hive1, hive2)
                if strength > 0.1:  # Threshold for significant coupling
                    coupling[(hive1.hive_id, hive2.hive_id)] = strength
        
        self.communication_graph = coupling
        return coupling
    
    def _compute_resonance(self, hive1: Hive, hive2: Hive) -> float:
        """
        Compute resonance strength between two hives.
        Strong if frequencies are harmonically related (2:1, 3:2, etc.)
        """
        f1 = hive1.mean_frequency
        f2 = hive2.mean_frequency
        
        if f1 == 0 or f2 == 0:
            return 0.0
        
        # Check for harmonic relationships
        ratio = f1 / f2
        
        # Common harmonic ratios
        harmonics = [1.0, 2.0, 0.5, 1.5, 0.667, 3.0, 0.333]
        
        min_distance = min(abs(ratio - h) for h in harmonics)
        
        # Convert distance to strength (closer = stronger)
        if min_distance < 0.1:
            strength = 1.0 - 10 * min_distance
            
            # Modulate by coherence and amplitude
            strength *= (hive1.coherence * hive2.coherence)
            strength *= min(hive1.mean_amplitude, hive2.mean_amplitude)
            
            return strength
        
        return 0.0
    
    def get_communicating_hives(self, hive_id: int) -> List[Tuple[int, float]]:
        """
        Get list of hives communicating with this one.
        Returns list of (other_hive_id, strength) tuples.
        """
        communicating = []
        
        for (id1, id2), strength in self.communication_graph.items():
            if id1 == hive_id:
                communicating.append((id2, strength))
            elif id2 == hive_id:
                communicating.append((id1, strength))
        
        return communicating
    
    def amplify_hive(self, hive: Hive, multiplier: float):
        """Amplify a hive's activity (increase amplitude)."""
        # This would modify the oscillator amplitudes
        # For now, just update the hive's mean amplitude
        hive.mean_amplitude *= multiplier
    
    def suppress_hive(self, hive: Hive, multiplier: float):
        """Suppress a hive's activity (decrease amplitude)."""
        hive.mean_amplitude *= multiplier
