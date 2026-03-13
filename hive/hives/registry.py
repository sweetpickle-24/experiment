"""
Hive lifecycle management: birth, growth, merge, split, death.
"""

from typing import List, Optional, Set
from .detector import Hive
import numpy as np


class HiveRegistry:
    """
    Manages hive lifecycle events and maintains hive metadata.
    """
    
    def __init__(self, config: dict):
        self.config = config['hives']
        self.hives: dict[int, Hive] = {}
        self.lifecycle_log: List[dict] = []
    
    def register_hive(self, hive: Hive):
        """Register a newly born hive."""
        self.hives[hive.hive_id] = hive
        self.lifecycle_log.append({
            'event': 'birth',
            'hive_id': hive.hive_id,
            'time': hive.birth_time,
            'size': len(hive.member_ids),
            'coherence': hive.coherence
        })
    
    def remove_hive(self, hive_id: int, current_time: float):
        """Remove a dead hive."""
        if hive_id in self.hives:
            hive = self.hives[hive_id]
            self.lifecycle_log.append({
                'event': 'death',
                'hive_id': hive_id,
                'time': current_time,
                'lifespan': hive.lifespan,
                'final_coherence': hive.coherence,
                'success_rate': hive.success_rate()
            })
            del self.hives[hive_id]
    
    def try_merge(self, hive1: Hive, hive2: Hive, coherence_threshold: float = 0.8) -> Optional[Hive]:
        """
        Attempt to merge two hives if they're highly coherent with each other.
        Returns merged hive if successful.
        """
        # Check if hives are compatible for merging
        # (similar frequencies, high inter-hive coherence)
        
        freq_diff = abs(hive1.mean_frequency - hive2.mean_frequency)
        if freq_diff > 5.0:  # More than 5 Hz difference
            return None
        
        # For now, simple merge
        merged = Hive(
            hive_id=hive1.hive_id,  # Keep first ID
            member_ids=hive1.member_ids | hive2.member_ids,
            birth_time=min(hive1.birth_time, hive2.birth_time),
            coherence=(hive1.coherence + hive2.coherence) / 2,
            mean_frequency=(hive1.mean_frequency + hive2.mean_frequency) / 2
        )
        
        self.lifecycle_log.append({
            'event': 'merge',
            'hive1_id': hive1.hive_id,
            'hive2_id': hive2.hive_id,
            'new_hive_id': merged.hive_id,
            'new_size': len(merged.member_ids)
        })
        
        return merged
    
    def try_split(self, hive: Hive, oscillator_engine) -> Optional[List[Hive]]:
        """
        Split a hive if it has bimodal phase distribution.
        Returns list of new hives if split successful.
        """
        if len(hive.member_ids) < 2 * self.config['min_size']:
            return None
        
        # Get phases of all members
        # TODO: Implement clustering on phases
        # For now, skip splitting
        return None
    
    def update_success(self, hive_id: int, success: bool):
        """Update success/failure counts for a hive."""
        if hive_id in self.hives:
            hive = self.hives[hive_id]
            if success:
                hive.success_count += 1
            else:
                hive.failure_count += 1
