"""
GPU-accelerated oscillator engine.
Updates 139K neurons in parallel on GPU (MLX for Apple Silicon, CuPy for NVIDIA).
"""

import numpy as np
from dataclasses import dataclass
from ..gpu_utils import GPU_AVAILABLE, GPU_BACKEND, to_gpu, to_cpu, zeros, ones, get_array_module, synchronize

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    mx = None


@dataclass
class OscillatorState:
    """State of all oscillators at a given time."""
    phase: np.ndarray  # φ(t) for all neurons
    velocity: np.ndarray  # dφ/dt for all neurons
    amplitude: np.ndarray  # A(t) for all neurons
    time: float  # Current time in ms


class OscillatorEngineGPU:
    """
    GPU-accelerated damped harmonic oscillators.
    Each neuron: φ̈ + 2γφ̇ + ω₀²φ = F_coupling + F_external
    """
    
    def __init__(self, num_oscillators: int, config: dict):
        self.num_oscillators = num_oscillators
        self.config = config['oscillator']
        
        self.dt = self.config['dt']
        self.gamma_default = self.config['damping_default']
        
        backend_name = GPU_BACKEND if GPU_AVAILABLE else 'CPU'
        print(f"Initializing oscillator engine ({backend_name}, {num_oscillators:,} neurons)...")
        
        # State variables on GPU
        init_phase = (np.random.uniform(0, 2*np.pi, num_oscillators).astype(np.float32) 
                     if self.config['phase_init_random'] 
                     else np.zeros(num_oscillators, dtype=np.float32))
        self.phase = to_gpu(init_phase)
        self.velocity = zeros(num_oscillators, dtype=np.float32)
        self.amplitude = ones(num_oscillators, dtype=np.float32) * self.config['amplitude_init']
        
        # Parameters on GPU
        self.omega0 = zeros(num_oscillators, dtype=np.float32)  # Natural frequencies
        self.gamma = ones(num_oscillators, dtype=np.float32) * self.gamma_default  # Damping
        
        # Forces on GPU
        self.coupling_force = zeros(num_oscillators, dtype=np.float32)
        self.external_force = zeros(num_oscillators, dtype=np.float32)
        
        self.time = 0.0
        
        if GPU_AVAILABLE:
            if MLX_AVAILABLE:
                # MLX arrays don't have nbytes, estimate size
                mem_mb = num_oscillators * 7 * 4 / 1024 / 1024  # 7 arrays × 4 bytes (float32)
            else:
                mem_mb = (self.phase.nbytes + self.velocity.nbytes + self.amplitude.nbytes +
                         self.omega0.nbytes + self.gamma.nbytes + 
                         self.coupling_force.nbytes + self.external_force.nbytes) / 1024 / 1024
            print(f"GPU memory used: {mem_mb:.1f} MB")
    
    def set_frequencies(self, omega_array: np.ndarray):
        """Set natural frequencies."""
        self.omega0 = to_gpu(omega_array.astype(np.float32))
    
    def set_damping(self, gamma_array: np.ndarray):
        """Set damping coefficients."""
        self.gamma = to_gpu(gamma_array.astype(np.float32))
    
    def set_coupling_force(self, force_array: np.ndarray):
        """Set coupling forces (called from CouplingEngine)."""
        self.coupling_force = to_gpu(force_array.astype(np.float32))
    
    def add_external_force(self, force_array: np.ndarray):
        """Add external forces (sensory input)."""
        self.external_force += to_gpu(force_array.astype(np.float32))
    
    def reset_forces(self):
        """Reset forces to zero."""
        if MLX_AVAILABLE:
            self.external_force = zeros(self.num_oscillators, dtype=np.float32)
            self.coupling_force = zeros(self.num_oscillators, dtype=np.float32)
        else:
            xp = get_array_module(self.external_force)
            self.external_force.fill(0.0)
            self.coupling_force.fill(0.0)
    
    def step(self, adaptive=True):
        """
        Integrate one timestep using velocity Verlet (GPU-accelerated).
        
        Args:
            adaptive: If True, use wave-aware adaptive timestep
        """
        xp = get_array_module(self.phase)
        
        # WAVE PHYSICS: Check if system is in resonance (stable) or transitioning
        if adaptive and hasattr(self, '_last_coherence'):
            # Compute current coherence (wave synchronization)
            coherence = self._compute_coherence_fast()
            coherence_change = abs(coherence - self._last_coherence)
            
            # ADAPTIVE TIMESTEP based on wave dynamics:
            # - High coherence + low change = synchronized wave = USE LARGE DT
            # - Low coherence = incoherent = can use medium DT
            # - Rapid change = transition = use small DT
            
            if coherence > 0.8 and coherence_change < 0.01:
                # Synchronized stable wave - jump ahead!
                effective_dt = self.dt * 5.0  # 5× larger timestep
            elif coherence_change > 0.1:
                # Rapid transition - need fine resolution
                effective_dt = self.dt
            else:
                # Normal evolution
                effective_dt = self.dt * 2.0  # 2× larger
            
            self._last_coherence = coherence
        else:
            effective_dt = self.dt
            # Initialize tracking
            if not hasattr(self, '_last_coherence'):
                self._last_coherence = 0.5
        
        # Total force
        total_force = self.coupling_force + self.external_force
        
        # Acceleration: φ̈ = F - 2γφ̇ - ω₀²sin(φ)
        if MLX_AVAILABLE:
            acceleration = total_force - 2.0 * self.gamma * self.velocity - self.omega0**2 * mx.sin(self.phase)
        else:
            acceleration = total_force - 2.0 * self.gamma * self.velocity - self.omega0**2 * xp.sin(self.phase)
        
        # Velocity Verlet integration (with adaptive dt)
        # v(t+dt/2) = v(t) + a(t) * dt/2
        self.velocity += 0.5 * acceleration * effective_dt
        
        # φ(t+dt) = φ(t) + v(t+dt/2) * dt
        self.phase += self.velocity * effective_dt
        
        # Wrap phase to [-π, π]
        if MLX_AVAILABLE:
            self.phase = mx.arctan2(mx.sin(self.phase), mx.cos(self.phase))
        else:
            self.phase = xp.arctan2(xp.sin(self.phase), xp.cos(self.phase))
        
        # Recompute acceleration at new position
        if MLX_AVAILABLE:
            acceleration = total_force - 2.0 * self.gamma * self.velocity - self.omega0**2 * mx.sin(self.phase)
        else:
            acceleration = total_force - 2.0 * self.gamma * self.velocity - self.omega0**2 * xp.sin(self.phase)
        
        # v(t+dt) = v(t+dt/2) + a(t+dt) * dt/2
        self.velocity += 0.5 * acceleration * effective_dt
        
        # Update amplitude (envelope) - decays with damping
        if MLX_AVAILABLE:
            self.amplitude *= mx.exp(-self.gamma * effective_dt)
        else:
            self.amplitude *= xp.exp(-self.gamma * effective_dt)
        
        # Add small noise to prevent complete decay
        if MLX_AVAILABLE:
            noise = mx.random.normal(shape=(self.num_oscillators,), dtype=mx.float32) * 0.01
            self.amplitude += mx.abs(noise)
            self.amplitude = mx.clip(self.amplitude, 0.01, 10.0)
        elif xp == np:
            noise = np.random.normal(0, 0.01, self.num_oscillators).astype(np.float32)
            self.amplitude += xp.abs(noise)
            self.amplitude = xp.clip(self.amplitude, 0.01, 10.0)
        else:
            import cupy as cp
            noise = cp.random.normal(0, 0.01, self.num_oscillators).astype(cp.float32)
            self.amplitude += xp.abs(noise)
            self.amplitude = xp.clip(self.amplitude, 0.01, 10.0)
        
        # Don't sync every step - let MLX build compute graph
        # Only sync when state is actually read (get_state, get_phase_coherence, etc.)
        
        self.time += effective_dt
        
        return effective_dt  # Return actual timestep used
    
    def _compute_coherence_fast(self):
        """Fast coherence computation (wave synchronization measure)."""
        if MLX_AVAILABLE:
            z = mx.mean(mx.exp(1j * self.phase))
            return float(mx.abs(z))
        else:
            xp = get_array_module(self.phase)
            phase_cpu = to_cpu(self.phase)
            z = np.mean(np.exp(1j * phase_cpu))
            return abs(z)
    
    def get_state(self):
        """Get current state (returns CPU arrays in OscillatorState)."""
        # Force evaluation before reading (critical for MLX lazy evaluation)
        if MLX_AVAILABLE:
            synchronize()
        
        return OscillatorState(
            phase=to_cpu(self.phase),
            velocity=to_cpu(self.velocity),
            amplitude=to_cpu(self.amplitude),
            time=self.time
        )
    
    def set_state(self, state):
        """Set state from OscillatorState."""
        self.phase = to_gpu(state.phase.astype(np.float32))
        self.velocity = to_gpu(state.velocity.astype(np.float32))
        self.amplitude = to_gpu(state.amplitude.astype(np.float32))
        self.time = state.time
    
    def get_phase_coherence(self, indices: np.ndarray = None) -> float:
        """Compute phase coherence using Kuramoto order parameter."""
        # Force evaluation before reading
        if MLX_AVAILABLE:
            synchronize()
        
        if MLX_AVAILABLE:
            if indices is None:
                phases = self.phase
            else:
                phases = self.phase[to_gpu(indices)]
            
            # Order parameter: R = |⟨e^(iφ)⟩|
            complex_exp = mx.exp(1j * phases)
            z = mx.mean(complex_exp)
            return float(mx.abs(z))
        else:
            xp = get_array_module(self.phase)
            
            if indices is None:
                phases = self.phase
            else:
                phases = self.phase[to_gpu(indices)]
            
            # Order parameter: R = |⟨e^(iφ)⟩|
            z = xp.mean(xp.exp(1j * phases))
            coherence = float(xp.abs(z))
            
            return coherence
    
    def get_mean_phase(self, indices: np.ndarray = None) -> float:
        """Compute mean phase (circular mean)."""
        xp = get_array_module(self.phase)
        
        if indices is None:
            phases = self.phase
        else:
            phases = self.phase[to_gpu(indices)]
        
        z = xp.mean(xp.exp(1j * phases))
        mean_phase = float(xp.angle(z))
        
        return mean_phase
    
    def get_dominant_frequency(self, indices: np.ndarray = None) -> float:
        """Get dominant frequency from velocities."""
        xp = get_array_module(self.velocity)
        
        if indices is None:
            velocities = self.velocity
        else:
            velocities = self.velocity[to_gpu(indices)]
        
        # f = (1/2π) * dφ/dt, convert from rad/ms to Hz
        freqs = to_cpu(xp.abs(velocities)) / (2 * np.pi) * 1000
        dominant = float(np.median(freqs))
        
        return dominant
    
    def get_energy(self) -> float:
        """Compute total energy."""
        xp = get_array_module(self.amplitude)
        energy = float(xp.sum(self.amplitude ** 2))
        return energy
    
    def modulate_frequency(self, indices: np.ndarray, multiplier: float):
        """Modulate natural frequency."""
        indices_gpu = to_gpu(indices)
        self.omega0[indices_gpu] *= multiplier
    
    def modulate_damping(self, indices: np.ndarray, multiplier: float):
        """Modulate damping coefficient."""
        indices_gpu = to_gpu(indices)
        self.gamma[indices_gpu] *= multiplier
    
    def get_phase_differences(self, indices1: np.ndarray, indices2: np.ndarray) -> np.ndarray:
        """Compute phase differences between pairs."""
        xp = get_array_module(self.phase)
        
        indices1_gpu = to_gpu(indices1)
        indices2_gpu = to_gpu(indices2)
        
        diff = self.phase[indices2_gpu] - self.phase[indices1_gpu]
        diff = xp.arctan2(xp.sin(diff), xp.cos(diff))
        
        return to_cpu(diff)
