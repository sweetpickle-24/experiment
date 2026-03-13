"""
Pattern completion and associative prediction.
Brain "filling in the blanks" from partial activation.
"""

import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CompletionCandidate:
    """A possible completion of a partial pattern."""
    pattern_id: int
    completion_confidence: float
    predicted_neurons: np.ndarray
    predicted_phases: np.ndarray
    historical_frequency: float
    energy_cost: float


class PatternCompletion:
    """
    Completes partial thought patterns based on memory and context.
    """
    
    def __init__(self, thought_detector, config: dict):
        self.thought_detector = thought_detector
        self.config = config['patterns']
        
        # Track completion statistics
        self.completion_history = []
        self.completion_accuracy = {}
    
    def complete_partial_pattern(self, 
                                 partial_hive_ids: List[int],
                                 current_context: dict,
                                 max_candidates: int = 5) -> List[CompletionCandidate]:
        """
        Given partial hive activation, predict likely completions.
        """
        if len(partial_hive_ids) == 0:
            return []
        
        # Find historical patterns that match the partial cue
        candidates = []
        
        for pattern in self.thought_detector.patterns.values():
            # Check overlap with partial cue
            overlap = len(set(partial_hive_ids) & set(pattern.hive_sequence))
            if overlap == 0:
                continue
            
            overlap_ratio = overlap / len(partial_hive_ids)
            if overlap_ratio < 0.3:  # Need at least 30% match
                continue
            
            # Compute completion confidence
            confidence = self._compute_confidence(
                pattern,
                partial_hive_ids,
                current_context
            )
            
            # Get neurons that would be activated in completion
            predicted_neurons, predicted_phases = self._predict_activation(pattern)
            
            # Energy cost (simpler = better)
            energy_cost = len(pattern.hive_sequence) - len(partial_hive_ids)
            
            # Historical frequency (how often has this pattern occurred?)
            historical_freq = pattern.activation_count / max(
                sum(p.activation_count for p in self.thought_detector.patterns.values()),
                1
            )
            
            candidates.append(CompletionCandidate(
                pattern_id=pattern.pattern_id,
                completion_confidence=confidence,
                predicted_neurons=predicted_neurons,
                predicted_phases=predicted_phases,
                historical_frequency=historical_freq,
                energy_cost=energy_cost
            ))
        
        # Rank candidates
        candidates = self._rank_candidates(candidates, current_context)
        
        return candidates[:max_candidates]
    
    def _compute_confidence(self, pattern, partial_hive_ids: List[int], 
                           context: dict) -> float:
        """
        Compute confidence that this pattern will complete.
        Based on: overlap, historical frequency, context match.
        """
        # Overlap with partial cue
        overlap = len(set(partial_hive_ids) & set(pattern.hive_sequence))
        overlap_score = overlap / len(pattern.hive_sequence)
        
        # Historical activation
        history_score = min(pattern.activation_count / 10.0, 1.0)
        
        # Context match (consciousness state, recent patterns)
        context_score = self._match_context(pattern, context)
        
        # Weighted combination
        confidence = (
            0.4 * overlap_score +
            0.3 * history_score +
            0.3 * context_score
        )
        
        return confidence
    
    def _match_context(self, pattern, context: dict) -> float:
        """
        Check if pattern matches current context.
        Context includes: consciousness state, recent patterns, sensory input.
        """
        score = 0.5  # Default neutral
        
        # Consciousness state context
        current_state = context.get('consciousness_state', 'WAKE')
        # Different states favor different patterns
        # (could be learned, for now simple heuristic)
        
        # Recent pattern context
        recent_patterns = context.get('recent_patterns', [])
        if len(recent_patterns) > 0:
            # Check if this pattern typically follows recent ones
            # (simplified - just check if it appeared near them before)
            score += 0.2
        
        return min(score, 1.0)
    
    def _predict_activation(self, pattern) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict which neurons and phases would activate in completion.
        """
        # For now, return stored pattern signature
        # In full implementation, would predict based on dynamics
        return (
            np.array(pattern.hive_sequence),  # Hive IDs
            np.zeros(len(pattern.hive_sequence))  # Placeholder phases
        )
    
    def _rank_candidates(self, candidates: List[CompletionCandidate],
                        context: dict) -> List[CompletionCandidate]:
        """
        Rank completion candidates by combined score.
        """
        for candidate in candidates:
            # Combined score
            candidate.combined_score = (
                0.4 * candidate.completion_confidence +
                0.3 * candidate.historical_frequency +
                0.3 * (1.0 / (1.0 + candidate.energy_cost))  # Prefer simpler
            )
        
        # Sort by combined score
        return sorted(candidates, key=lambda c: c.combined_score, reverse=True)
    
    def competitive_completion(self, partial_hive_ids: List[int],
                              context: dict) -> Optional[CompletionCandidate]:
        """
        Run competitive completion: multiple candidates compete.
        Winner is activated, others suppressed.
        """
        candidates = self.complete_partial_pattern(partial_hive_ids, context)
        
        if len(candidates) == 0:
            return None
        
        # Competition: highest confidence wins
        winner = candidates[0]
        
        # Record this completion
        self.completion_history.append({
            'partial_cue': partial_hive_ids,
            'winner': winner.pattern_id,
            'competitors': [c.pattern_id for c in candidates[1:]]
        })
        
        return winner
    
    def context_dependent_completion(self, partial_hive_ids: List[int],
                                    state: str) -> Optional[CompletionCandidate]:
        """
        Completion depends on consciousness state.
        Same partial cue → different completions in WAKE vs DREAM.
        """
        context = {
            'consciousness_state': state,
            'recent_patterns': []
        }
        
        return self.competitive_completion(partial_hive_ids, context)
