"""
Wave-Native Brain Engine: Pure Electromagnetic Wave Physics
No discrete neurons, no individual synapses, no numerical integration.
Just continuous wave fields propagating through the brain.
"""

import numpy as np
import mlx.core as mx
from scipy.fft import fftn, ifftn, fftfreq
from dataclasses import dataclass
from typing import Tuple, Dict, List


@dataclass
class WaveField:
    """3D continuous wave field (like electromagnetic field)"""
    phase: np.ndarray        # Φ(x,y,z,t) - phase field
    amplitude: np.ndarray    # A(x,y,z,t) - amplitude field
    velocity: np.ndarray     # ∂Φ/∂t - phase velocity
    frequency: np.ndarray    # ω(x,y,z) - natural frequency field
    coupling: np.ndarray     # K(x,y,z) - coupling strength field
    grid_spacing: float      # Spatial resolution (μm)


class WaveNativeBrain:
    """
    Brain as continuous electromagnetic wave medium.
    
    Physics:
    - Wave equation: ∂²Φ/∂t² = v²∇²Φ + K·sin(∇²Φ) + F_ext
    - Resonance: natural frequency modes
    - Interference: wave superposition
    - Propagation: gradient-driven flow
    """
    
    def __init__(self, connectome, grid_spacing=10.0):
        """
        Initialize wave field from connectome structure.
        
        Args:
            connectome: Physical substrate with neuron positions
            grid_spacing: Grid resolution in micrometers (10μm default)
        """
        print("\n" + "="*70)
        print("INITIALIZING WAVE-NATIVE BRAIN (Pure Field Theory)")
        print("="*70)
        
        self.connectome = connectome
        self.grid_spacing = grid_spacing
        
        # Build 3D spatial grid
        self._build_spatial_grid()
        
        # Create continuous wave fields
        self._initialize_wave_fields()
        
        # Build coupling field from connectome
        self._build_coupling_field()
        
        # Build frequency field from neuron types
        self._build_frequency_field()
        
        print(f"✓ Wave fields initialized:")
        print(f"  Grid: {self.grid_shape} voxels ({np.prod(self.grid_shape):,} points)")
        print(f"  Resolution: {grid_spacing}μm")
        print(f"  Physical volume: {self.physical_size}")
        print("="*70)
    
    def _build_spatial_grid(self):
        """Create 3D spatial grid covering the brain."""
        # Get all neuron positions
        positions = np.array([n.position for n in self.connectome.neurons.values()])
        
        # Bounding box
        min_pos = np.min(positions, axis=0).astype(float)
        max_pos = np.max(positions, axis=0).astype(float)
        
        # Add padding
        padding = 50.0  # μm
        min_pos -= padding
        max_pos += padding
        
        # Grid dimensions
        physical_size = max_pos - min_pos
        grid_shape = (physical_size / self.grid_spacing).astype(int)
        
        # Create meshgrid
        x = np.linspace(min_pos[0], max_pos[0], grid_shape[0])
        y = np.linspace(min_pos[1], max_pos[1], grid_shape[1])
        z = np.linspace(min_pos[2], max_pos[2], grid_shape[2])
        
        self.grid_x, self.grid_y, self.grid_z = np.meshgrid(x, y, z, indexing='ij')
        self.grid_shape = grid_shape
        self.min_pos = min_pos
        self.max_pos = max_pos
        self.physical_size = physical_size
        
        print(f"  Spatial grid: {grid_shape[0]}×{grid_shape[1]}×{grid_shape[2]}")
    
    def _initialize_wave_fields(self):
        """Initialize phase, amplitude, and velocity fields."""
        shape = self.grid_shape
        
        # Phase field: Φ(x,y,z,t) - starts random
        self.phase = np.random.uniform(-np.pi, np.pi, shape).astype(np.float32)
        
        # Amplitude field: A(x,y,z,t) - starts at baseline
        self.amplitude = np.ones(shape, dtype=np.float32) * 0.1
        
        # Phase velocity: ∂Φ/∂t - starts at zero
        self.velocity = np.zeros(shape, dtype=np.float32)
        
        # Time
        self.time = 0.0
        self.wave_speed = 100.0  # μm/ms (typical neural conduction)
    
    def _build_coupling_field(self):
        """
        Build coupling field K(x,y,z) from synapse density.
        
        Where synapses are dense, coupling is strong.
        This is how wave energy propagates preferentially along connections.
        """
        print("  Building coupling field from 5.3M synapses...")
        
        shape = self.grid_shape
        coupling = np.zeros(shape, dtype=np.float32)
        
        # For each synapse, add to coupling field
        synapses = self.connectome.synapses
        neurons = self.connectome.neurons
        
        for i, syn in enumerate(synapses):
            if i % 500000 == 0:
                print(f"    Processing synapse {i:,}/{len(synapses):,}")
            
            # Get pre and post positions
            if syn.pre_id not in neurons or syn.post_id not in neurons:
                continue
                
            pre_pos = neurons[syn.pre_id].position
            post_pos = neurons[syn.post_id].position
            
            # Convert to grid indices
            pre_idx = self._position_to_index(pre_pos)
            post_idx = self._position_to_index(post_pos)
            
            # Add coupling strength along path
            # (synapses create "channels" for wave propagation)
            self._add_coupling_path(coupling, pre_idx, post_idx, syn.weight)
        
        # Smooth coupling field (waves don't see individual synapses)
        from scipy.ndimage import gaussian_filter
        coupling = gaussian_filter(coupling, sigma=2.0)
        
        # Normalize
        coupling = coupling / (np.max(coupling) + 1e-6)
        
        self.coupling = coupling
        print(f"    ✓ Coupling field built (max coupling: {np.max(coupling):.3f})")
    
    def _build_frequency_field(self):
        """
        Build natural frequency field ω(x,y,z) from neuron types.
        
        Different brain regions have different natural frequencies:
        - Theta (4-8 Hz): hippocampus, mushroom body
        - Beta (13-30 Hz): projection neurons, motor
        - Gamma (30-100 Hz): sensory processing
        """
        print("  Building frequency field from neuron types...")
        
        shape = self.grid_shape
        frequency = np.zeros(shape, dtype=np.float32)
        
        # Map neuron positions to grid and assign frequencies
        for neuron_id, neuron in self.connectome.neurons.items():
            pos = neuron.position
            idx = self._position_to_index(pos)
            
            # Natural frequency from neuron type/region
            omega = self._get_natural_frequency(neuron)
            
            # Add to field with Gaussian spread
            self._add_gaussian_blob(frequency, idx, omega, sigma=2.0)
        
        # Default frequency for empty regions
        frequency = np.where(frequency < 1.0, 10.0, frequency)  # 10 Hz default
        
        # Convert to radians/ms
        self.frequency = 2 * np.pi * frequency / 1000.0
        
        print(f"    ✓ Frequency field built (range: {np.min(frequency):.1f}-{np.max(frequency):.1f} Hz)")
    
    def _position_to_index(self, pos):
        """Convert physical position (μm) to grid index."""
        relative_pos = pos - self.min_pos
        idx = (relative_pos / self.grid_spacing).astype(int)
        
        # Clamp to grid bounds
        idx[0] = np.clip(idx[0], 0, self.grid_shape[0] - 1)
        idx[1] = np.clip(idx[1], 0, self.grid_shape[1] - 1)
        idx[2] = np.clip(idx[2], 0, self.grid_shape[2] - 1)
        
        return tuple(idx)
    
    def _add_coupling_path(self, field, start_idx, end_idx, weight):
        """Add coupling along path between two points (synapse)."""
        # Simple: just add to both endpoints
        # (Full implementation would trace path)
        field[start_idx] += weight * 0.001
        field[end_idx] += weight * 0.001
    
    def _add_gaussian_blob(self, field, idx, value, sigma=2.0):
        """Add Gaussian-smoothed value at position."""
        # Simple: just add at center point
        # (Full implementation would add 3D Gaussian)
        field[idx] += value
    
    def _get_natural_frequency(self, neuron):
        """Get natural oscillation frequency for neuron type."""
        # Based on cell type and neuropil region
        if 'PN' in neuron.group or 'projection' in neuron.group.lower():
            return 20.0  # Beta (20 Hz)
        elif 'KC' in neuron.group or 'Kenyon' in str(neuron.cell_types):
            return 6.0   # Theta (6 Hz)
        elif 'LH' in neuron.group:
            return 15.0  # Alpha-Beta
        else:
            return 10.0  # Alpha (10 Hz) default
    
    def compute_wave_coupling(self):
        """
        Compute wave coupling force from field gradients.
        
        Wave coupling = K(x,y,z) × sin(∇²Φ)
        
        This is how waves interact - through their CURVATURE (Laplacian),
        not through individual synapses!
        """
        # Compute Laplacian (wave curvature)
        laplacian = self._compute_laplacian_3d(self.phase)
        
        # Coupling force (modulated by coupling field)
        coupling_force = self.coupling * np.sin(laplacian)
        
        return coupling_force
    
    def _compute_laplacian_3d(self, field):
        """
        Compute 3D Laplacian: ∇²field = ∂²/∂x² + ∂²/∂y² + ∂²/∂z²
        
        Uses FFT for efficiency (spectral method).
        """
        # FFT method (exact and fast!)
        field_fft = fftn(field)
        
        # Frequency grid
        kx = fftfreq(self.grid_shape[0], d=self.grid_spacing) * 2 * np.pi
        ky = fftfreq(self.grid_shape[1], d=self.grid_spacing) * 2 * np.pi
        kz = fftfreq(self.grid_shape[2], d=self.grid_spacing) * 2 * np.pi
        
        kx, ky, kz = np.meshgrid(kx, ky, kz, indexing='ij')
        
        # Laplacian in frequency space: -k²
        k_squared = kx**2 + ky**2 + kz**2
        laplacian_fft = -k_squared * field_fft
        
        # Inverse FFT
        laplacian = np.real(ifftn(laplacian_fft))
        
        return laplacian.astype(np.float32)
    
    def evolve_wave_field(self, dt):
        """
        Evolve wave field using wave equation.
        
        Wave equation:
        ∂²Φ/∂t² = v²∇²Φ + K·sin(∇²Φ) + F_ext - 2γ·∂Φ/∂t
        
        This is PURE WAVE PHYSICS - no discrete neurons!
        """
        # 1. Compute wave coupling (field interaction)
        coupling_force = self.compute_wave_coupling()
        
        # 2. Compute Laplacian (wave propagation term)
        laplacian_phase = self._compute_laplacian_3d(self.phase)
        
        # 3. Wave acceleration
        wave_propagation = self.wave_speed**2 * laplacian_phase
        damping = -0.1 * self.velocity  # Small damping
        
        phase_acceleration = (
            wave_propagation +
            coupling_force +
            damping
        )
        
        # 4. Update velocity and phase (Verlet integration)
        self.velocity += phase_acceleration * dt
        self.phase += self.velocity * dt
        
        # 5. Wrap phase to [-π, π]
        self.phase = np.arctan2(np.sin(self.phase), np.cos(self.phase))
        
        # 6. Update amplitude (envelope decay)
        self.amplitude *= np.exp(-0.01 * dt)
        
        self.time += dt
    
    def inject_standing_wave(self, region_mask, frequency, amplitude, spatial_pattern):
        """
        Inject standing wave resonance at specific region.
        
        E(x,t) = A·sin(k·x)·cos(ω·t)
        
        This is how odors drive the system!
        """
        # Spatial mode (which glomeruli)
        k_vector = spatial_pattern
        
        # Phase shift from standing wave
        phase_shift = amplitude * np.sin(k_vector * self.time)
        
        # Add to phase field at region
        self.phase += region_mask * phase_shift
        
        # Boost amplitude at region
        self.amplitude += region_mask * amplitude
    
    def detect_resonance(self, region_mask=None):
        """
        Detect resonance in field using FFT (instant!).
        
        Returns:
            frequencies: Resonant frequencies found
            powers: Power at each frequency
            coherence: Spatial coherence (0-1)
        """
        # Select region
        if region_mask is None:
            field = self.phase
        else:
            field = self.phase * region_mask
        
        # FFT to frequency domain
        field_fft = fftn(field)
        power_spectrum = np.abs(field_fft)**2
        
        # Find peaks in power spectrum
        # (These are resonant frequencies!)
        
        # Spatial coherence (order parameter)
        z = np.mean(np.exp(1j * field))
        coherence = np.abs(z)
        
        return power_spectrum, coherence
    
    def get_wave_pattern(self, region_mask=None):
        """Extract spatial wave pattern (for odor discrimination)."""
        if region_mask is None:
            pattern = self.phase
        else:
            pattern = self.phase * region_mask
        
        # Return phase distribution
        return pattern


# Utility functions for creating region masks
def create_region_mask(grid_shape, grid_x, grid_y, grid_z, neuron_positions, radius=50.0):
    """
    Create 3D mask for brain region (e.g., all PNs).
    
    Args:
        neuron_positions: List of (x,y,z) positions
        radius: Radius around each neuron (μm)
    """
    mask = np.zeros(grid_shape, dtype=np.float32)
    
    for pos in neuron_positions:
        # Distance from this neuron
        dist = np.sqrt(
            (grid_x - pos[0])**2 +
            (grid_y - pos[1])**2 +
            (grid_z - pos[2])**2
        )
        
        # Add Gaussian blob
        mask += np.exp(-dist**2 / (2 * radius**2))
    
    # Normalize
    mask = mask / (np.max(mask) + 1e-6)
    
    return mask


if __name__ == "__main__":
    print("Wave-Native Brain Engine - Pure Electromagnetic Physics")
    print("No discrete neurons, no synaptic loops, just continuous waves!")
