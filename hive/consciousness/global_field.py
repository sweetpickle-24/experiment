"""
Global field metrics computed from all oscillators.
Unified consciousness emerges from whole-brain coherence.
"""

import numpy as np
from scipy import signal


class GlobalFieldComputer:
    """
    Computes global consciousness metrics from oscillator field.
    """
    
    def __init__(self, oscillator_engine):
        self.oscillator = oscillator_engine
        self.num_neurons = oscillator_engine.num_oscillators
        
        # History for temporal metrics
        self.coherence_history = []
        self.frequency_history = []
    
    def compute_metrics(self) -> dict:
        """
        Compute all global field metrics.
        Returns comprehensive consciousness state.
        """
        # Global coherence (Kuramoto order parameter)
        global_coherence = self.oscillator.get_phase_coherence()
        
        # Dominant frequency
        dominant_freq = self.oscillator.get_dominant_frequency()
        
        # Phase gradient topology
        phase_topology = self._compute_phase_topology()
        
        # Cross-frequency coupling
        cfc = self._compute_cross_frequency_coupling()
        
        # Metastability (variance in recent coherence)
        metastability = self._compute_metastability(global_coherence)
        
        # Total energy
        energy = self.oscillator.get_energy()
        
        # Update history
        self.coherence_history.append(global_coherence)
        self.frequency_history.append(dominant_freq)
        
        # Keep last 200 samples
        if len(self.coherence_history) > 200:
            self.coherence_history.pop(0)
            self.frequency_history.pop(0)
        
        return {
            'global_coherence': global_coherence,
            'dominant_frequency': dominant_freq,
            'phase_topology': phase_topology,
            'cross_frequency_coupling': cfc,
            'metastability': metastability,
            'energy': energy,
            'anomaly_level': 0.0  # Placeholder
        }
    
    def _compute_phase_topology(self) -> str:
        """
        Compute spatial structure of phase differences.
        Returns: 'uniform', 'gradient', 'twisted', 'fragmented'
        """
        from ..gpu_utils import array_index, to_cpu
        
        # Sample subset for efficiency
        sample_size = min(1000, self.num_neurons)
        indices = np.random.choice(self.num_neurons, sample_size, replace=False)
        
        phases = array_index(self.oscillator.phase, indices)
        phases_cpu = to_cpu(phases)
        
        # Compute phase variance
        phase_variance = np.var(phases_cpu)
        
        # Classify topology
        if phase_variance < 0.5:
            return 'uniform'
        elif phase_variance < 2.0:
            return 'gradient'
        elif phase_variance < 5.0:
            return 'twisted'
        else:
            return 'fragmented'
    
    def _compute_cross_frequency_coupling(self) -> float:
        """
        Measure coupling between different frequency bands.
        High gamma nested in low theta = strong CFC.
        """
        # Simplified: measure correlation between amplitude and phase
        # In full implementation, would use phase-amplitude coupling
        
        # For now, return placeholder
        return 0.5
    
    def _compute_metastability(self, current_coherence: float) -> float:
        """
        Compute metastability: variance in coherence over recent window.
        High metastability = flexible, low = rigid.
        """
        if len(self.coherence_history) < 10:
            return 0.0
        
        recent = self.coherence_history[-20:]
        return np.var(recent)
    
    def get_band_coherence(self, band_indices: np.ndarray) -> float:
        """Compute coherence for specific frequency band."""
        return self.oscillator.get_phase_coherence(band_indices)
    
    def get_power_spectrum(self) -> dict:
        """
        Compute power spectrum across all neurons.
        Returns energy per frequency band.
        """
        # Simplified: use current frequencies
        # In full implementation, would use FFT of phase history
        
        velocities = self.oscillator.velocity
        amplitudes = self.oscillator.amplitude
        
        # Energy = amplitude²
        energies = amplitudes ** 2
        
        # Instantaneous frequencies
        freqs_hz = (velocities / (2 * np.pi)) * 1000
        
        # Bin into bands
        bands = {
            'delta': (0.5, 4.0),
            'theta': (4.0, 8.0),
            'alpha': (8.0, 13.0),
            'beta': (13.0, 30.0),
            'gamma': (30.0, 100.0)
        }
        
        power = {}
        for band_name, (f_min, f_max) in bands.items():
            mask = (freqs_hz >= f_min) & (freqs_hz <= f_max)
            power[band_name] = np.sum(energies[mask])
        
        return power
