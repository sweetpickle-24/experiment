"""
The 5 consciousness states: WAKE, SLEEP, DREAM, SHOCK, MEDITATION
"""

from enum import Enum
import numpy as np


class ConsciousnessState(Enum):
    """The five fundamental consciousness states."""
    WAKE = "WAKE"
    SLEEP = "SLEEP"
    DREAM = "DREAM"
    SHOCK = "SHOCK"
    MEDITATION = "MEDITATION"


class ConsciousnessStateManager:
    """
    Manages transitions between consciousness states.
    Each state has distinct oscillatory signatures and behaviors.
    """
    
    def __init__(self, config: dict):
        self.config = config['consciousness']
        self.current_state = ConsciousnessState.WAKE
        self.state_entry_time = 0.0
        self.time_in_state = 0.0
        
        # Circadian rhythm (for WAKE <-> SLEEP)
        self.circadian_phase = 0.0  # [0, 2π]
        self.circadian_period = 60000.0  # 1 minute cycles (scaled down from 24h)
        
        # State history
        self.state_history = []
    
    def update(self, global_metrics: dict, current_time: float):
        """
        Update consciousness state based on global metrics.
        Returns True if state changed.
        """
        self.time_in_state = current_time - self.state_entry_time
        
        # Update circadian rhythm
        self.circadian_phase = (current_time / self.circadian_period) * 2 * np.pi
        
        # Check for state transitions
        new_state = self._evaluate_transitions(global_metrics, current_time)
        
        if new_state != self.current_state:
            self._transition_to(new_state, current_time)
            return True
        
        return False
    
    def _evaluate_transitions(self, metrics: dict, current_time: float) -> ConsciousnessState:
        """
        Evaluate which state we should be in based on metrics.
        """
        coherence = metrics['global_coherence']
        anomaly_level = metrics.get('anomaly_level', 0.0)
        sensory_input = metrics.get('sensory_input_strength', 0.0)
        
        current = self.current_state
        
        # WAKE → SHOCK (sudden anomaly)
        if current == ConsciousnessState.WAKE:
            if anomaly_level > self.config['transitions']['wake_to_shock_anomaly']:
                return ConsciousnessState.SHOCK
            
            # WAKE → SLEEP (circadian rhythm)
            if np.cos(self.circadian_phase) < -0.7:  # Night phase
                return ConsciousnessState.SLEEP
            
            # WAKE → MEDITATION (no input)
            if self.time_in_state > self.config['transitions']['wake_to_meditation_idle']:
                if sensory_input < 0.1:
                    return ConsciousnessState.MEDITATION
        
        # SHOCK → WAKE (threat subsides)
        elif current == ConsciousnessState.SHOCK:
            if self.time_in_state > self.config['transitions']['shock_to_wake_time']:
                if anomaly_level < 2.0:
                    return ConsciousnessState.WAKE
        
        # SLEEP → WAKE (circadian)
        elif current == ConsciousnessState.SLEEP:
            if np.cos(self.circadian_phase) > 0.7:  # Day phase
                return ConsciousnessState.WAKE
            
            # SLEEP → DREAM (randomly, 20% of sleep)
            if np.random.random() < 0.002:  # Low probability per step
                return ConsciousnessState.DREAM
        
        # DREAM → SLEEP (dream ends)
        elif current == ConsciousnessState.DREAM:
            if self.time_in_state > 5000:  # 5 second dreams
                return ConsciousnessState.SLEEP
        
        # MEDITATION → WAKE (input returns)
        elif current == ConsciousnessState.MEDITATION:
            if sensory_input > 0.5:
                return ConsciousnessState.WAKE
        
        return current
    
    def _transition_to(self, new_state: ConsciousnessState, current_time: float):
        """Execute state transition."""
        old_state = self.current_state
        
        self.state_history.append({
            'from': old_state.value,
            'to': new_state.value,
            'time': current_time,
            'duration_in_prev_state': self.time_in_state
        })
        
        self.current_state = new_state
        self.state_entry_time = current_time
        self.time_in_state = 0.0
        
        print(f"[t={current_time:.1f}ms] State transition: {old_state.value} → {new_state.value}")
    
    def get_state_parameters(self) -> dict:
        """Get parameters for current state."""
        state_name = self.current_state.value.lower()
        params = self.config.get(state_name, {})
        
        return {
            'state': self.current_state,
            'sensory_gain': params.get('sensory_gain', 1.0),
            'motor_enabled': params.get('motor_enabled', True),
            'coherence_target': params.get('global_coherence_target', 0.5),
            'hive_dynamics_frozen': params.get('hive_dynamics_frozen', False)
        }
    
    def force_state(self, state: ConsciousnessState, current_time: float):
        """Manually force a state transition (for testing)."""
        if state != self.current_state:
            self._transition_to(state, current_time)
