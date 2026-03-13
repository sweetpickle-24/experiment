"""
Advanced pattern operations: composition, chains, inhibition, meta-cognition, language.
"""

import numpy as np
from typing import List, Dict, Optional, Set, Tuple
from collections import deque
from dataclasses import dataclass


# ============================================================================
# PATTERN COMPOSITION
# ============================================================================

class PatternComposition:
    """Creative synthesis of new patterns from existing ones."""
    
    def __init__(self, thought_detector, config: dict):
        self.thought_detector = thought_detector
        self.config = config
        
        self.synthesized_patterns = []
    
    def blend_patterns(self, pattern_id1: int, pattern_id2: int, 
                      blend_ratio: float = 0.5):
        """
        Smooth interpolation between two thought patterns.
        Creates hybrid pattern.
        """
        p1 = self.thought_detector.patterns.get(pattern_id1)
        p2 = self.thought_detector.patterns.get(pattern_id2)
        
        if p1 is None or p2 is None:
            return None
        
        # Blend hive sequences
        combined_hives = list(set(p1.hive_sequence) | set(p2.hive_sequence))
        
        # Create blended pattern
        # (simplified - could do phase interpolation)
        from patterns.thought_patterns import ThoughtPattern
        
        blended = ThoughtPattern(
            pattern_id=self.thought_detector.next_pattern_id,
            hive_sequence=combined_hives[:10],  # Limit size
            phase_fingerprint=np.array([]),
            frequency_composition={},
            spatial_distribution=np.zeros(3),
            timing=[],
            complexity=len(combined_hives),
            birth_time=0.0,
            pattern_type="blended"
        )
        
        self.thought_detector.next_pattern_id += 1
        self.synthesized_patterns.append(blended)
        
        return blended
    
    def mutate_pattern(self, pattern_id: int, mutation_strength: float = 0.1):
        """
        Slightly perturb existing pattern to explore variations.
        """
        pattern = self.thought_detector.patterns.get(pattern_id)
        if pattern is None:
            return None
        
        # Mutate hive sequence (add/remove random hives)
        mutated_sequence = pattern.hive_sequence.copy()
        
        if np.random.random() < mutation_strength and len(mutated_sequence) > 2:
            # Remove random hive
            mutated_sequence.pop(np.random.randint(len(mutated_sequence)))
        
        if np.random.random() < mutation_strength:
            # Add random hive
            new_hive = np.random.randint(0, 100)  # Random hive ID
            mutated_sequence.append(new_hive)
        
        # Create mutated pattern
        from patterns.thought_patterns import ThoughtPattern
        
        mutated = ThoughtPattern(
            pattern_id=self.thought_detector.next_pattern_id,
            hive_sequence=mutated_sequence,
            phase_fingerprint=pattern.phase_fingerprint.copy(),
            frequency_composition=pattern.frequency_composition.copy(),
            spatial_distribution=pattern.spatial_distribution.copy(),
            timing=pattern.timing.copy(),
            complexity=len(mutated_sequence),
            birth_time=0.0,
            pattern_type="mutated"
        )
        
        self.thought_detector.next_pattern_id += 1
        self.synthesized_patterns.append(mutated)
        
        return mutated
    
    def bind_cross_modal(self, visual_pattern_id: int, 
                        olfactory_pattern_id: int):
        """
        Link patterns from different sensory modalities.
        Creates association (e.g., smell → visual memory).
        """
        # Simplified implementation
        # In full version, would create binding pattern
        pass


# ============================================================================
# THOUGHT CHAINS (Stream of Consciousness)
# ============================================================================

class ThoughtChainTracker:
    """Tracks stream of consciousness: sequence of thought patterns."""
    
    def __init__(self, config: dict):
        self.config = config['patterns']
        
        self.chain_window = self.config.get('pattern_window', 100)
        self.thought_chain: deque = deque(maxlen=self.chain_window)
        
        # Metrics
        self.jumps_detected = 0
        self.focus_periods = []
        self.creativity_score = 0.0
    
    def add_pattern(self, pattern_id: int, timestamp: float):
        """Add pattern to thought chain."""
        self.thought_chain.append((pattern_id, timestamp))
        
        # Analyze chain
        if len(self.thought_chain) >= 3:
            self._analyze_recent_chain()
    
    def _analyze_recent_chain(self):
        """Analyze recent thought patterns."""
        recent = list(self.thought_chain)[-10:]
        pattern_ids = [pid for pid, _ in recent]
        
        # Detect jumps (sudden transitions)
        if len(pattern_ids) >= 2:
            # Simple: check if consecutive patterns are very different
            # (would need similarity metric in full implementation)
            pass
    
    def measure_focus(self, pattern_detector) -> float:
        """
        How long does system stay within related pattern families?
        High focus = patterns are related, low = scattered.
        """
        if len(self.thought_chain) < 5:
            return 0.5
        
        recent = list(self.thought_chain)[-20:]
        unique_patterns = len(set(pid for pid, _ in recent))
        
        # Focus = fewer unique patterns = more repetition
        focus = 1.0 - (unique_patterns / len(recent))
        
        return focus
    
    def measure_creativity(self) -> float:
        """
        Rate of novel pattern generation vs repetition.
        High creativity = many new patterns, low = stuck in loops.
        """
        if len(self.thought_chain) < 10:
            return 0.5
        
        recent = list(self.thought_chain)[-50:]
        pattern_ids = [pid for pid, _ in recent]
        
        # Creativity = ratio of unique patterns
        creativity = len(set(pattern_ids)) / len(pattern_ids)
        
        return creativity
    
    def detect_attentional_capture(self, external_input_strength: float,
                                   threshold: float = 0.5) -> bool:
        """
        Detect if external input interrupted internal thought chain.
        """
        return external_input_strength > threshold


# ============================================================================
# PATTERN INHIBITION (Cognitive Control)
# ============================================================================

class PatternInhibition:
    """Thought suppression and cognitive control."""
    
    def __init__(self, config: dict):
        self.config = config['patterns']
        
        self.suppressed_patterns: Set[int] = set()
        self.inhibition_strength: Dict[int, float] = {}
        
        self.alpha_suppression_strength = self.config.get(
            'alpha_suppression_strength', 0.8
        )
    
    def suppress_pattern(self, pattern_id: int, strength: float = 1.0):
        """
        Suppress unwanted pattern (executive control).
        """
        self.suppressed_patterns.add(pattern_id)
        self.inhibition_strength[pattern_id] = strength
    
    def is_suppressed(self, pattern_id: int) -> bool:
        """Check if pattern is currently suppressed."""
        return pattern_id in self.suppressed_patterns
    
    def release_suppression(self, pattern_id: int):
        """Stop suppressing pattern."""
        self.suppressed_patterns.discard(pattern_id)
        self.inhibition_strength.pop(pattern_id, None)
    
    def detect_rumination(self, thought_chain_tracker, 
                         threshold: int = 5) -> Optional[int]:
        """
        Identify stuck patterns that won't release.
        If same pattern repeats > threshold times, it's rumination.
        """
        if len(thought_chain_tracker.thought_chain) < threshold:
            return None
        
        recent = list(thought_chain_tracker.thought_chain)[-threshold*2:]
        pattern_ids = [pid for pid, _ in recent]
        
        # Check for repeated pattern
        from collections import Counter
        counts = Counter(pattern_ids)
        
        for pattern_id, count in counts.most_common(1):
            if count >= threshold:
                return pattern_id
        
        return None
    
    def force_state_transition(self, pattern_id: int):
        """
        Force system out of stuck pattern.
        (Would trigger consciousness state change in full implementation)
        """
        self.suppress_pattern(pattern_id, strength=1.0)
        print(f"  [Cognitive Control] Forcing transition away from stuck pattern {pattern_id}")


# ============================================================================
# META-COGNITION (Thinking About Thinking)
# ============================================================================

class MetaCognition:
    """Self-modeling and thinking about thinking."""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Self-model
        self.self_model = {
            'current_patterns': [],
            'confidence_in_patterns': 0.0,
            'internal_state': 'exploring',
            'goal': None,
            'doubt_level': 0.0
        }
        
        # Higher-order patterns (patterns about patterns)
        self.meta_patterns = []
    
    def monitor_patterns(self, active_patterns: List[int]):
        """Monitor which patterns are currently active."""
        self.self_model['current_patterns'] = active_patterns
    
    def evaluate_patterns(self, pattern_confidences: Dict[int, float]) -> float:
        """
        Evaluate quality of current thought patterns.
        Meta-level judgment.
        """
        if len(pattern_confidences) == 0:
            return 0.0
        
        avg_confidence = np.mean(list(pattern_confidences.values()))
        self.self_model['confidence_in_patterns'] = avg_confidence
        
        return avg_confidence
    
    def generate_doubt(self, dissent_strength: float) -> float:
        """
        Generate doubt pattern based on dissent.
        Self-questioning mechanism.
        """
        doubt = min(dissent_strength * 1.5, 1.0)
        self.self_model['doubt_level'] = doubt
        
        return doubt
    
    def set_intention(self, goal: str):
        """
        Set future-oriented intention pattern.
        Guides action selection.
        """
        self.self_model['goal'] = goal
        self.self_model['internal_state'] = 'goal_directed'
    
    def self_reflection(self) -> dict:
        """
        Introspective report of current cognitive state.
        """
        return {
            'active_patterns': len(self.self_model['current_patterns']),
            'confidence': self.self_model['confidence_in_patterns'],
            'state': self.self_model['internal_state'],
            'doubt': self.self_model['doubt_level'],
            'has_goal': self.self_model['goal'] is not None
        }


# ============================================================================
# PATTERN LANGUAGE (Symbolic Representation)
# ============================================================================

class PatternLanguage:
    """
    Symbolic representation of patterns for interpretability.
    Assigns labels, builds grammar.
    """
    
    def __init__(self):
        self.pattern_labels: Dict[int, str] = {}
        self.pattern_semantics: Dict[int, str] = {}
        self.transition_grammar: Dict[Tuple[int, int], float] = {}
        
        # Predefined semantic categories
        self.semantic_categories = {
            'sensory': ['visual_', 'odor_', 'touch_'],
            'motor': ['move_', 'wing_', 'approach_'],
            'cognitive': ['attend_', 'remember_', 'decide_'],
            'emotional': ['threat_', 'reward_', 'neutral_']
        }
    
    def assign_label(self, pattern_id: int, 
                    hive_context: List, 
                    behavior_context: Optional[str] = None) -> str:
        """
        Assign human-readable label to pattern.
        """
        # Simple heuristic labeling
        if behavior_context:
            label = behavior_context
        else:
            # Auto-generate based on hive composition
            label = f"pattern_{pattern_id}"
        
        self.pattern_labels[pattern_id] = label
        return label
    
    def infer_semantics(self, pattern_id: int, 
                       sensory_context: dict,
                       motor_output: dict) -> str:
        """
        Infer what pattern "means" behaviorally.
        """
        semantics = "unknown"
        
        # Check sensory context
        if sensory_context.get('visual_motion'):
            semantics = "visual_attention"
        elif sensory_context.get('odor'):
            semantics = "odor_processing"
        
        # Check motor output
        if motor_output.get('wing_left', 0) > 0.5:
            semantics += "_turn_left"
        
        self.pattern_semantics[pattern_id] = semantics
        return semantics
    
    def build_transition_grammar(self, thought_chain_tracker):
        """
        Learn which pattern transitions are common (grammar rules).
        """
        chain = list(thought_chain_tracker.thought_chain)
        
        for i in range(len(chain) - 1):
            from_pattern = chain[i][0]
            to_pattern = chain[i+1][0]
            
            transition = (from_pattern, to_pattern)
            self.transition_grammar[transition] = \
                self.transition_grammar.get(transition, 0) + 1
    
    def export_dictionary(self) -> dict:
        """
        Export pattern dictionary for analysis/visualization.
        """
        return {
            'labels': self.pattern_labels,
            'semantics': self.pattern_semantics,
            'grammar': {
                f"{from_p}->{to_p}": count
                for (from_p, to_p), count in 
                sorted(self.transition_grammar.items(), 
                      key=lambda x: -x[1])[:50]  # Top 50 transitions
            }
        }
    
    def get_readable_chain(self, thought_chain_tracker) -> List[str]:
        """Convert pattern ID chain to readable labels."""
        chain = list(thought_chain_tracker.thought_chain)
        return [
            self.pattern_labels.get(pid, f"unknown_{pid}")
            for pid, _ in chain
        ]


# ============================================================================
# INTEGRATED ADVANCED PATTERNS
# ============================================================================

class AdvancedPatternSystem:
    """
    Integrates all advanced pattern operations.
    """
    
    def __init__(self, thought_detector, config: dict):
        self.thought_detector = thought_detector
        self.config = config
        
        self.composition = PatternComposition(thought_detector, config)
        self.chains = ThoughtChainTracker(config)
        self.inhibition = PatternInhibition(config)
        self.meta_cognition = MetaCognition(config)
        self.language = PatternLanguage()
    
    def process_step(self, active_patterns: List[int], 
                    current_time: float,
                    external_input_strength: float = 0.0):
        """Process one step of advanced pattern dynamics."""
        
        # Track thought chain
        for pattern_id in active_patterns:
            self.chains.add_pattern(pattern_id, current_time)
        
        # Meta-cognition: monitor patterns
        self.meta_cognition.monitor_patterns(active_patterns)
        
        # Check for rumination
        stuck_pattern = self.inhibition.detect_rumination(self.chains)
        if stuck_pattern is not None:
            self.inhibition.force_state_transition(stuck_pattern)
        
        # Update grammar
        self.language.build_transition_grammar(self.chains)
    
    def get_cognitive_state(self) -> dict:
        """Get comprehensive cognitive state."""
        return {
            'focus': self.chains.measure_focus(self.thought_detector),
            'creativity': self.chains.measure_creativity(),
            'suppressed_patterns': len(self.inhibition.suppressed_patterns),
            'meta_cognition': self.meta_cognition.self_reflection(),
            'known_patterns': len(self.language.pattern_labels)
        }
