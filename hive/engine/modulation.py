"""
Neuromodulation: dopamine, serotonin, octopamine effects on oscillator dynamics.
"""

import numpy as np


class NeuromodulatorSystem:
    """
    Manages neuromodulator levels and their effects on:
    - Natural frequencies (ω₀)
    - Damping coefficients (γ)
    - Coupling strengths (w_ij)
    """
    
    def __init__(self, num_neurons: int, config: dict):
        self.num_neurons = num_neurons
        self.config = config
        self.nm_config = config['neurotransmitters']
        
        # Global neuromodulator levels [0, 1]
        self.dopamine = 0.5
        self.serotonin = 0.5
        self.octopamine = 0.5
        
        # Baseline parameters (before modulation)
        self.baseline_omega = None
        self.baseline_gamma = None
        self.baseline_coupling_multiplier = 1.0
    
    def set_baselines(self, omega: np.ndarray, gamma: np.ndarray):
        """Store baseline parameters."""
        # Handle MLX arrays (don't have .copy() method)
        try:
            self.baseline_omega = omega.copy()
            self.baseline_gamma = gamma.copy()
        except AttributeError:
            # MLX array - use np.array() to convert
            import numpy as np
            self.baseline_omega = np.array(omega)
            self.baseline_gamma = np.array(gamma)
    
    def set_dopamine(self, level: float):
        """Set dopamine level [0, 1]. Higher = arousal, faster processing."""
        self.dopamine = np.clip(level, 0.0, 1.0)
    
    def set_serotonin(self, level: float):
        """Set serotonin level [0, 1]. Higher = longer timescales, integration."""
        self.serotonin = np.clip(level, 0.0, 1.0)
    
    def set_octopamine(self, level: float):
        """Set octopamine level [0, 1]. Higher = stronger coupling (fly's adrenaline)."""
        self.octopamine = np.clip(level, 0.0, 1.0)
    
    def compute_modulated_omega(self) -> np.ndarray:
        """
        Compute modulated natural frequencies based on dopamine.
        DA increases ω₀ → faster oscillations.
        """
        if self.baseline_omega is None:
            raise ValueError("Must set baselines first")
        
        # Dopamine effect: [0.8, 1.2] range
        da_mult = self.nm_config['dopamine']['frequency_multiplier']
        multiplier = 1.0 + (da_mult - 1.0) * self.dopamine
        
        return self.baseline_omega * multiplier
    
    def compute_modulated_gamma(self) -> np.ndarray:
        """
        Compute modulated damping based on serotonin.
        5-HT decreases γ → longer timescales, more integration.
        """
        if self.baseline_gamma is None:
            raise ValueError("Must set baselines first")
        
        # Serotonin effect: reduces damping
        ser_mult = self.nm_config['serotonin']['damping_multiplier']
        multiplier = 1.0 + (ser_mult - 1.0) * self.serotonin
        
        return self.baseline_gamma * multiplier
    
    def get_coupling_multiplier(self) -> float:
        """
        Get global coupling strength multiplier based on neuromodulators.
        Octopamine increases coupling strength.
        """
        oct_mult = self.nm_config['octopamine']['coupling_multiplier']
        oct_effect = 1.0 + (oct_mult - 1.0) * self.octopamine
        
        ser_mult = self.nm_config['serotonin']['coupling_multiplier']
        ser_effect = 1.0 + (ser_mult - 1.0) * self.serotonin
        
        return oct_effect * ser_effect
    
    def update_from_consciousness_state(self, state_name: str):
        """
        Automatically set neuromodulator levels based on consciousness state.
        """
        if state_name == 'WAKE':
            self.set_dopamine(0.7)  # Alert
            self.set_serotonin(0.5)  # Balanced
            self.set_octopamine(0.5)  # Normal
        
        elif state_name == 'SLEEP':
            self.set_dopamine(0.2)  # Low arousal
            self.set_serotonin(0.8)  # High integration
            self.set_octopamine(0.3)  # Reduced coupling
        
        elif state_name == 'DREAM':
            self.set_dopamine(0.6)  # Moderate arousal
            self.set_serotonin(0.7)  # High integration
            self.set_octopamine(0.4)  # Moderate coupling
        
        elif state_name == 'SHOCK':
            self.set_dopamine(1.0)  # Maximum arousal
            self.set_serotonin(0.2)  # Fast responses
            self.set_octopamine(1.0)  # Maximum coupling
        
        elif state_name == 'MEDITATION':
            self.set_dopamine(0.3)  # Low arousal
            self.set_serotonin(0.9)  # Maximum integration
            self.set_octopamine(0.6)  # Moderate-high coupling
    
    def get_state(self) -> dict:
        """Get current neuromodulator state."""
        return {
            'dopamine': self.dopamine,
            'serotonin': self.serotonin,
            'octopamine': self.octopamine,
            'omega_multiplier': self.compute_modulated_omega()[0] / self.baseline_omega[0] if self.baseline_omega is not None else 1.0,
            'gamma_multiplier': self.compute_modulated_gamma()[0] / self.baseline_gamma[0] if self.baseline_gamma is not None else 1.0,
            'coupling_multiplier': self.get_coupling_multiplier()
        }
