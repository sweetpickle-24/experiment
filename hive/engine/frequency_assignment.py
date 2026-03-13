"""
Frequency assignment for oscillators based on neurotransmitter profiles and spatial location.
"""

import numpy as np
from typing import Dict


class FrequencyAssigner:
    """
    Assigns natural frequencies (ω₀) to neurons based on:
    1. Neurotransmitter type
    2. Brain region
    3. Spatial gradients (nearby neurons have similar frequencies)
    """
    
    def __init__(self, connectome, spatial_index, config: dict):
        self.connectome = connectome
        self.spatial_index = spatial_index
        self.config = config
        self.bands = config['frequency_bands']
        self.nt_config = config['neurotransmitters']
    
    def assign_frequencies(self) -> Dict[int, float]:
        """
        Assign natural frequency to each neuron.
        Returns dict: neuron_id -> frequency (Hz)
        """
        print("Assigning natural frequencies...")
        
        frequencies = {}
        band_counts = {name: 0 for name in self.bands.keys()}
        
        for neuron_id, neuron in self.connectome.neurons.items():
            # Determine frequency band from neurotransmitter
            band_name = self._get_frequency_band(neuron)
            band_min, band_max = self.bands[band_name]
            
            # Sample within band (with some variation)
            base_freq = np.random.uniform(band_min, band_max)
            
            # Apply spatial gradient (nearby neurons slightly correlated)
            spatial_modulation = self._compute_spatial_modulation(neuron_id)
            freq = base_freq * spatial_modulation
            
            # Ensure still within band
            freq = np.clip(freq, band_min, band_max)
            
            # Convert to angular frequency (rad/ms)
            omega = 2 * np.pi * freq / 1000.0
            
            frequencies[neuron_id] = omega
            band_counts[band_name] += 1
        
        self._print_frequency_summary(band_counts)
        return frequencies
    
    def _get_frequency_band(self, neuron) -> str:
        """Determine which frequency band this neuron belongs to."""
        nt_type = neuron.nt_type.lower()
        
        # Check neurotransmitter preferences
        if nt_type in self.nt_config:
            preferred = self.nt_config[nt_type].get('preferred_band')
            if preferred and preferred in self.bands:
                return preferred
        
        # Default assignments based on common neurotransmitter roles
        if nt_type == 'gaba':
            return 'alpha'
        elif nt_type == 'glut':
            return 'beta'
        elif nt_type == 'ach':
            return 'theta'
        else:
            # Unknown or modulatory - distribute across bands
            # Use neuron ID hash to deterministically assign
            band_names = list(self.bands.keys())
            idx = hash(neuron.root_id) % len(band_names)
            return band_names[idx]
    
    def _compute_spatial_modulation(self, neuron_id: int, k: int = 10) -> float:
        """
        Compute spatial modulation based on local neighborhood.
        Nearby neurons should have slightly correlated frequencies.
        Returns multiplier in range [0.9, 1.1]
        """
        # Get nearest neighbors
        neighbors = self.spatial_index.find_nearest(neuron_id, k=k)
        
        if not neighbors:
            return 1.0
        
        # Average distance to neighbors
        avg_dist = np.mean([dist for _, dist in neighbors])
        
        # Convert to modulation (closer = more similar)
        # Normalize by typical brain scale (~100 μm)
        normalized_dist = avg_dist / 100.0
        
        # Small random modulation correlated with local density
        modulation = 1.0 + 0.1 * np.random.randn() * np.exp(-normalized_dist)
        
        # Clip to reasonable range
        return np.clip(modulation, 0.9, 1.1)
    
    def _print_frequency_summary(self, band_counts: Dict[str, int]):
        """Print summary of frequency band distribution."""
        total = sum(band_counts.values())
        print(f"\nFrequency band distribution ({total} neurons):")
        for band_name in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
            count = band_counts[band_name]
            pct = 100 * count / total if total > 0 else 0
            freq_range = self.bands[band_name]
            print(f"  {band_name:6s} ({freq_range[0]:5.1f}-{freq_range[1]:5.1f} Hz): "
                  f"{count:6d} ({pct:5.1f}%)")
    
    def get_band_indices(self, frequencies: Dict[int, float], band_name: str) -> np.ndarray:
        """
        Get indices of all neurons in a specific frequency band.
        frequencies: dict from neuron_id to omega (rad/ms)
        """
        band_min, band_max = self.bands[band_name]
        
        # Convert omega back to Hz for comparison
        indices = []
        for neuron_id, omega in frequencies.items():
            freq_hz = (omega / (2 * np.pi)) * 1000.0
            if band_min <= freq_hz <= band_max:
                idx = self.spatial_index.neuron_ids.index(neuron_id)
                indices.append(idx)
        
        return np.array(indices)
    
    def mutate_frequencies(self, frequencies: Dict[int, float], 
                          mutation_rate: float = 0.1,
                          neuron_ids: list = None) -> Dict[int, float]:
        """
        Mutate frequencies for evolution.
        mutation_rate: fraction to change (default ±10%)
        Returns new frequency dict.
        """
        new_frequencies = frequencies.copy()
        
        if neuron_ids is None:
            neuron_ids = list(frequencies.keys())
        
        for neuron_id in neuron_ids:
            omega = frequencies[neuron_id]
            
            # Convert to Hz
            freq_hz = (omega / (2 * np.pi)) * 1000.0
            
            # Determine current band
            current_band = None
            for band_name, (band_min, band_max) in self.bands.items():
                if band_min <= freq_hz <= band_max:
                    current_band = band_name
                    break
            
            if current_band is None:
                continue
            
            # Mutate within band
            band_min, band_max = self.bands[current_band]
            new_freq = freq_hz * np.random.uniform(1 - mutation_rate, 1 + mutation_rate)
            new_freq = np.clip(new_freq, band_min, band_max)
            
            # Convert back to rad/ms
            new_omega = 2 * np.pi * new_freq / 1000.0
            new_frequencies[neuron_id] = new_omega
        
        return new_frequencies
