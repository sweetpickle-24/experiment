"""
Core oscillator dynamics - the soul of the system.
Each neuron is a damped harmonic oscillator: d²φ/dt² + γ(dφ/dt) + ω₀²φ = F_input(t)
"""

import numpy as np
from typing import Tuple
from dataclasses import dataclass


@dataclass
class OscillatorState:
    """State of all oscillators at a given time."""
    phase: np.ndarray  # φ(t) for all neurons
    velocity: np.ndarray  # dφ/dt for all neurons
    amplitude: np.ndarray  # A(t) for all neurons
    time: float  # Current time in ms


class OscillatorEngine:
    """
    Vectorized oscillator dynamics for 139K coupled neurons.
    Uses 4th-order Runge-Kutta for numerical integration.
    """
    
    def __init__(self, num_oscillators: int, config: dict):
        self.num_oscillators = num_oscillators
        self.config = config
        self.dt = config['oscillator']['dt']
        
        # Oscillator parameters (one per neuron)
        self.omega0 = np.zeros(num_oscillators)  # Natural frequency
        self.gamma = np.full(num_oscillators, config['oscillator']['damping_default'])  # Damping
        
        # State variables
        self.phase = np.zeros(num_oscillators)
        self.velocity = np.zeros(num_oscillators)
        self.amplitude = np.full(num_oscillators, config['oscillator']['amplitude_init'])
        
        # External forcing
        self.external_force = np.zeros(num_oscillators)
        
        # Coupling will be set by coupling.py
        self.coupling_force = np.zeros(num_oscillators)
        
        # Time
        self.time = 0.0
        
        # Initialize phases
        if config['oscillator']['phase_init_random']:
            self.phase = np.random.uniform(0, 2*np.pi, num_oscillators)
    
    def set_frequencies(self, omega0: np.ndarray):
        """Set natural frequencies for all oscillators."""
        self.omega0 = omega0.copy()
    
    def set_damping(self, gamma: np.ndarray):
        """Set damping coefficients for all oscillators."""
        self.gamma = gamma.copy()
    
    def set_external_force(self, force: np.ndarray):
        """Set external forcing (sensory input)."""
        self.external_force = force.copy()
    
    def set_coupling_force(self, force: np.ndarray):
        """Set coupling force from synaptic connections."""
        self.coupling_force = force.copy()
    
    def step(self):
        """
        Single integration step using 4th-order Runge-Kutta.
        Solves: d²φ/dt² = -γ(dφ/dt) - ω₀²φ + F_total
        """
        # Convert to system of first-order ODEs:
        # dx/dt = v
        # dv/dt = -γv - ω₀²x + F
        
        # RK4 integration
        k1_x, k1_v = self._derivatives(self.phase, self.velocity)
        
        k2_x, k2_v = self._derivatives(
            self.phase + 0.5 * self.dt * k1_x,
            self.velocity + 0.5 * self.dt * k1_v
        )
        
        k3_x, k3_v = self._derivatives(
            self.phase + 0.5 * self.dt * k2_x,
            self.velocity + 0.5 * self.dt * k2_v
        )
        
        k4_x, k4_v = self._derivatives(
            self.phase + self.dt * k3_x,
            self.velocity + self.dt * k3_v
        )
        
        # Update state
        self.phase += (self.dt / 6.0) * (k1_x + 2*k2_x + 2*k3_x + k4_x)
        self.velocity += (self.dt / 6.0) * (k1_v + 2*k2_v + 2*k3_v + k4_v)
        
        # Wrap phase to [0, 2π]
        self.phase = np.mod(self.phase, 2 * np.pi)
        
        # Update amplitude (proportional to energy: A² ~ x² + v²)
        self.amplitude = np.sqrt(self.phase**2 + self.velocity**2)
        
        # Update time
        self.time += self.dt
    
    def _derivatives(self, x: np.ndarray, v: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute derivatives for ODE system.
        dx/dt = v
        dv/dt = -γv - ω₀²x + F_total
        """
        dx_dt = v
        
        # Total force = external + coupling
        F_total = self.external_force + self.coupling_force
        
        # Damped harmonic oscillator with forcing
        dv_dt = -self.gamma * v - (self.omega0 ** 2) * x + F_total
        
        return dx_dt, dv_dt
    
    def get_state(self) -> OscillatorState:
        """Get current state snapshot."""
        return OscillatorState(
            phase=self.phase.copy(),
            velocity=self.velocity.copy(),
            amplitude=self.amplitude.copy(),
            time=self.time
        )
    
    def set_state(self, state: OscillatorState):
        """Restore from state snapshot."""
        self.phase = state.phase.copy()
        self.velocity = state.velocity.copy()
        self.amplitude = state.amplitude.copy()
        self.time = state.time
    
    def get_phase_coherence(self, indices: np.ndarray = None) -> float:
        """
        Compute Kuramoto order parameter (global coherence).
        R = |⟨e^(iφ)⟩| where ⟨⟩ is mean over oscillators.
        R = 1: perfect sync, R = 0: incoherent
        """
        if indices is None:
            phases = self.phase
        else:
            phases = self.phase[indices]
        
        # Complex order parameter
        z = np.mean(np.exp(1j * phases))
        return np.abs(z)
    
    def get_mean_phase(self, indices: np.ndarray = None) -> float:
        """Get mean phase of a group of oscillators."""
        if indices is None:
            phases = self.phase
        else:
            phases = self.phase[indices]
        
        # Circular mean
        z = np.mean(np.exp(1j * phases))
        return np.angle(z)
    
    def get_dominant_frequency(self, indices: np.ndarray = None) -> float:
        """
        Estimate dominant frequency from recent phase evolution.
        Returns frequency in Hz.
        """
        if indices is None:
            velocities = self.velocity
        else:
            velocities = self.velocity[indices]
        
        # Instantaneous frequency: f = (1/2π) * dφ/dt
        # Convert from rad/ms to Hz
        mean_vel = np.mean(velocities)
        freq_hz = (mean_vel / (2 * np.pi)) * 1000  # ms to seconds
        return freq_hz
    
    def get_energy(self) -> float:
        """Total oscillator energy (sum of amplitudes squared)."""
        return np.sum(self.amplitude ** 2)
    
    def get_phase_differences(self, indices1: np.ndarray, indices2: np.ndarray) -> np.ndarray:
        """
        Compute phase differences between pairs of oscillators.
        indices1, indices2: Arrays of neuron INDICES (0..N-1), not IDs.
        Returns values in [-π, π].
        """
        diff = self.phase[indices2] - self.phase[indices1]
        # Wrap to [-π, π]
        diff = np.arctan2(np.sin(diff), np.cos(diff))
        return diff
    
    def modulate_frequency(self, indices: np.ndarray, multiplier: float):
        """Modulate natural frequency (neuromodulator effect)."""
        self.omega0[indices] *= multiplier
    
    def modulate_damping(self, indices: np.ndarray, multiplier: float):
        """Modulate damping coefficient (neuromodulator effect)."""
        self.gamma[indices] *= multiplier
    
    def reset_forces(self):
        """Reset external and coupling forces (call before recomputing)."""
        self.external_force.fill(0.0)
        self.coupling_force.fill(0.0)
