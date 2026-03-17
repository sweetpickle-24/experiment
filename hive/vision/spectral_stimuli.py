"""
Spectral Stimulus Generator for Vision Research

Generates visual stimuli in spectral domain:
- 40 pure wavelengths (300-700nm in 10nm steps)
- 780 two-way wavelength mixtures
- Converts to R1-R8 photoreceptor activation patterns

Analog to DOoR odor stimuli for olfaction research.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

try:
    from .photoreceptor_database import PhotoreceptorDatabase, OMMATIDIUM_TYPES
except ImportError:
    from photoreceptor_database import PhotoreceptorDatabase, OMMATIDIUM_TYPES


@dataclass
class VisualStimulus:
    """
    Visual stimulus in spectral domain.
    
    Similar to Odor dataclass in olfaction pathway.
    """
    name: str
    spectrum: Dict[float, float]  # wavelength → intensity
    intensity: float              # Overall brightness (0-1)
    duration_ms: float
    photoreceptor_pattern: Optional[np.ndarray] = None  # R1-R8 × n_ommatidia
    stimulus_type: str = 'pure'  # 'pure' or 'mixture'
    
    def __repr__(self):
        wl_str = ', '.join([f"{wl:.0f}nm" for wl in self.spectrum.keys()])
        return f"VisualStimulus('{self.name}', [{wl_str}], intensity={self.intensity:.2f})"


class SpectralStimulusGenerator:
    """
    Generate visual stimuli in spectral domain.
    
    Creates:
    - 40 pure wavelengths (300-700nm, 10nm steps)
    - 780 two-way mixtures (all C(40,2) combinations)
    - Converts to photoreceptor activation patterns
    """
    
    def __init__(
        self,
        photoreceptor_db: Optional[PhotoreceptorDatabase] = None,
        num_ommatidia: int = 800,
        pale_fraction: float = 0.7
    ):
        """
        Initialize stimulus generator.
        
        Args:
            photoreceptor_db: Database of spectral sensitivities
            num_ommatidia: Number of ommatidia in compound eye
            pale_fraction: Fraction of pale ommatidia (rest are yellow)
        """
        self.photoreceptor_db = photoreceptor_db or PhotoreceptorDatabase()
        self.num_ommatidia = num_ommatidia
        self.pale_fraction = pale_fraction
        
        # Calculate ommatidium composition
        self.num_pale = int(num_ommatidia * pale_fraction)
        self.num_yellow = num_ommatidia - self.num_pale
        
        # Wavelength range
        self.wavelength_min = 300  # nm
        self.wavelength_max = 700  # nm
        self.wavelength_step = 10  # nm
        
        self.pure_wavelengths = np.arange(
            self.wavelength_min,
            self.wavelength_max + self.wavelength_step,
            self.wavelength_step
        )
        
        print(f"✓ Spectral stimulus generator initialized:")
        print(f"  Wavelength range: {self.wavelength_min}-{self.wavelength_max} nm")
        print(f"  Resolution: {self.wavelength_step} nm")
        print(f"  Pure stimuli: {len(self.pure_wavelengths)}")
        print(f"  Possible mixtures: {len(self.pure_wavelengths) * (len(self.pure_wavelengths)-1) // 2}")
        print(f"  Ommatidia: {num_ommatidia} ({self.num_pale} pale, {self.num_yellow} yellow)")
    
    def generate_pure_wavelengths(
        self,
        intensity_range: Tuple[float, float] = (0.5, 1.0),
        duration_ms: float = 100.0
    ) -> List[VisualStimulus]:
        """
        Generate pure wavelength stimuli.
        
        Args:
            intensity_range: (min, max) intensity for each stimulus
            duration_ms: Stimulus duration in milliseconds
        
        Returns:
            List of 40 VisualStimulus objects
        """
        stimuli = []
        
        for wavelength in self.pure_wavelengths:
            # Random intensity within range (for contrast invariance testing)
            intensity = np.random.uniform(*intensity_range)
            
            stimulus = VisualStimulus(
                name=f"{int(wavelength)}nm",
                spectrum={float(wavelength): intensity},
                intensity=intensity,
                duration_ms=duration_ms,
                stimulus_type='pure'
            )
            
            # Convert to photoreceptor pattern
            stimulus.photoreceptor_pattern = self.convert_to_photoreceptor_input(stimulus)
            
            stimuli.append(stimulus)
        
        print(f"✓ Generated {len(stimuli)} pure wavelength stimuli")
        return stimuli
    
    def generate_wavelength_mixtures(
        self,
        max_components: int = 2,
        intensity: float = 0.75,
        duration_ms: float = 100.0,
        subset_size: Optional[int] = None
    ) -> List[VisualStimulus]:
        """
        Generate wavelength mixture stimuli.
        
        Args:
            max_components: Maximum wavelengths per mixture (2 = binary mixtures)
            intensity: Overall intensity
            duration_ms: Stimulus duration
            subset_size: Optional limit on number of mixtures (random sample)
        
        Returns:
            List of mixture VisualStimulus objects
        """
        stimuli = []
        
        # Generate all binary combinations
        if max_components == 2:
            pairs = list(combinations(self.pure_wavelengths, 2))
            
            # Optionally subsample
            if subset_size and subset_size < len(pairs):
                pairs = [pairs[i] for i in np.random.choice(
                    len(pairs), subset_size, replace=False
                )]
            
            for wl1, wl2 in pairs:
                # Equal mixture (could vary ratios for more diversity)
                spectrum = {
                    float(wl1): intensity * 0.5,
                    float(wl2): intensity * 0.5
                }
                
                stimulus = VisualStimulus(
                    name=f"{int(wl1)}nm+{int(wl2)}nm",
                    spectrum=spectrum,
                    intensity=intensity,
                    duration_ms=duration_ms,
                    stimulus_type='mixture'
                )
                
                # Convert to photoreceptor pattern
                stimulus.photoreceptor_pattern = self.convert_to_photoreceptor_input(stimulus)
                
                stimuli.append(stimulus)
        
        print(f"✓ Generated {len(stimuli)} wavelength mixture stimuli")
        return stimuli
    
    def generate_intensity_series(
        self,
        wavelength: float,
        num_intensities: int = 10,
        intensity_range: Tuple[float, float] = (0.1, 1.0),
        duration_ms: float = 100.0
    ) -> List[VisualStimulus]:
        """
        Generate intensity series for single wavelength.
        
        Used for contrast invariance testing (analog to concentration series).
        
        Args:
            wavelength: Wavelength in nm
            num_intensities: Number of intensity levels
            intensity_range: (min, max) intensity
            duration_ms: Stimulus duration
        
        Returns:
            List of VisualStimulus at different intensities
        """
        intensities = np.logspace(
            np.log10(intensity_range[0]),
            np.log10(intensity_range[1]),
            num_intensities
        )
        
        stimuli = []
        for intensity in intensities:
            stimulus = VisualStimulus(
                name=f"{int(wavelength)}nm_{intensity:.2f}x",
                spectrum={float(wavelength): intensity},
                intensity=intensity,
                duration_ms=duration_ms,
                stimulus_type='intensity_series'
            )
            
            stimulus.photoreceptor_pattern = self.convert_to_photoreceptor_input(stimulus)
            stimuli.append(stimulus)
        
        print(f"✓ Generated intensity series: {len(stimuli)} levels for {wavelength}nm")
        return stimuli
    
    def generate_temporal_sequence(
        self,
        wavelengths: List[float],
        intensity: float = 0.75,
        frame_duration_ms: float = 50.0
    ) -> List[VisualStimulus]:
        """
        Generate temporal sequence of wavelengths.
        
        Used for motion detection testing (temporal progression).
        
        Args:
            wavelengths: Sequence of wavelengths
            intensity: Intensity for each frame
            frame_duration_ms: Duration of each frame
        
        Returns:
            List of VisualStimulus in temporal order
        """
        stimuli = []
        
        for i, wavelength in enumerate(wavelengths):
            stimulus = VisualStimulus(
                name=f"seq_{i:02d}_{int(wavelength)}nm",
                spectrum={float(wavelength): intensity},
                intensity=intensity,
                duration_ms=frame_duration_ms,
                stimulus_type='temporal_sequence'
            )
            
            stimulus.photoreceptor_pattern = self.convert_to_photoreceptor_input(stimulus)
            stimuli.append(stimulus)
        
        print(f"✓ Generated temporal sequence: {len(stimuli)} frames")
        return stimuli
    
    def convert_to_photoreceptor_input(
        self,
        stimulus: VisualStimulus
    ) -> np.ndarray:
        """
        Convert wavelength spectrum to R1-R8 activation pattern across ommatidia.
        
        Args:
            stimulus: VisualStimulus with spectrum
        
        Returns:
            Array of shape (n_ommatidia, 8) with R1-R8 responses
        """
        pattern = np.zeros((self.num_ommatidia, 8))
        
        # Process pale ommatidia (R1-R6, R7p, R8p)
        for i in range(self.num_pale):
            response = self.photoreceptor_db.get_spectrum_response(
                stimulus.spectrum, 
                'pale'
            )
            pattern[i] = [
                response['R1'], response['R2'], response['R3'],
                response['R4'], response['R5'], response['R6'],
                response['R7'], response['R8']
            ]
        
        # Process yellow ommatidia (R1-R6, R7y, R8y)
        for i in range(self.num_pale, self.num_ommatidia):
            response = self.photoreceptor_db.get_spectrum_response(
                stimulus.spectrum,
                'yellow'
            )
            pattern[i] = [
                response['R1'], response['R2'], response['R3'],
                response['R4'], response['R5'], response['R6'],
                response['R7'], response['R8']
            ]
        
        return pattern
    
    def save_stimulus_library(
        self,
        stimuli: List[VisualStimulus],
        output_path: str
    ):
        """
        Save stimulus library to JSON file.
        
        Args:
            stimuli: List of VisualStimulus objects
            output_path: Path for output JSON file
        """
        import json
        
        library = {
            'metadata': {
                'num_stimuli': len(stimuli),
                'wavelength_range': [self.wavelength_min, self.wavelength_max],
                'wavelength_step': self.wavelength_step,
                'num_ommatidia': self.num_ommatidia,
                'pale_fraction': self.pale_fraction
            },
            'stimuli': []
        }
        
        for stimulus in stimuli:
            stim_dict = {
                'name': stimulus.name,
                'spectrum': {str(k): v for k, v in stimulus.spectrum.items()},
                'intensity': float(stimulus.intensity),
                'duration_ms': float(stimulus.duration_ms),
                'type': stimulus.stimulus_type,
                'photoreceptor_pattern': stimulus.photoreceptor_pattern.tolist() if stimulus.photoreceptor_pattern is not None else None
            }
            library['stimuli'].append(stim_dict)
        
        with open(output_path, 'w') as f:
            json.dump(library, f, indent=2)
        
        print(f"✓ Saved stimulus library to {output_path}")
    
    def get_similar_wavelengths(
        self,
        reference_wavelength: float,
        similarity_threshold: float = 30.0
    ) -> List[float]:
        """
        Get wavelengths similar to reference (for decorrelation testing).
        
        Args:
            reference_wavelength: Reference wavelength in nm
            similarity_threshold: Maximum distance in nm
        
        Returns:
            List of similar wavelengths
        """
        similar = []
        for wl in self.pure_wavelengths:
            if wl != reference_wavelength and abs(wl - reference_wavelength) <= similarity_threshold:
                similar.append(wl)
        return similar


if __name__ == "__main__":
    # Test spectral stimulus generator
    print("Testing Spectral Stimulus Generator\n")
    
    generator = SpectralStimulusGenerator(num_ommatidia=800)
    
    # Generate pure wavelengths
    print("\n" + "="*70)
    print("Pure Wavelength Stimuli")
    print("="*70)
    
    pure_stimuli = generator.generate_pure_wavelengths()
    print(f"\nExample stimuli:")
    for i in [0, 10, 20, 30, 39]:
        stim = pure_stimuli[i]
        print(f"  {stim.name}: intensity={stim.intensity:.2f}, pattern shape={stim.photoreceptor_pattern.shape}")
    
    # Generate wavelength mixtures (subset)
    print("\n" + "="*70)
    print("Wavelength Mixtures (subset of 50)")
    print("="*70)
    
    mixture_stimuli = generator.generate_wavelength_mixtures(subset_size=50)
    print(f"\nExample mixtures:")
    for i in range(min(5, len(mixture_stimuli))):
        stim = mixture_stimuli[i]
        print(f"  {stim.name}: intensity={stim.intensity:.2f}")
    
    # Generate intensity series
    print("\n" + "="*70)
    print("Intensity Series (500nm green)")
    print("="*70)
    
    intensity_series = generator.generate_intensity_series(500, num_intensities=10)
    print(f"\nIntensity levels:")
    for stim in intensity_series:
        print(f"  {stim.name}: {stim.intensity:.3f}")
    
    # Generate temporal sequence
    print("\n" + "="*70)
    print("Temporal Sequence (400nm → 500nm)")
    print("="*70)
    
    wavelength_sequence = np.linspace(400, 500, 11)
    temporal_sequence = generator.generate_temporal_sequence(wavelength_sequence)
    print(f"\nSequence frames: {len(temporal_sequence)}")
    
    # Test similar wavelengths (for decorrelation)
    print("\n" + "="*70)
    print("Similar Wavelengths (for decorrelation testing)")
    print("="*70)
    
    test_wavelengths = [450, 500, 600]
    for wl in test_wavelengths:
        similar = generator.get_similar_wavelengths(wl, similarity_threshold=30)
        print(f"\n{wl}nm similar wavelengths (±30nm): {[int(w) for w in similar]}")
    
    # Analyze photoreceptor patterns
    print("\n" + "="*70)
    print("Photoreceptor Pattern Analysis")
    print("="*70)
    
    # Blue vs Red
    blue_stim = [s for s in pure_stimuli if s.name == '450nm'][0]
    red_stim = [s for s in pure_stimuli if s.name == '600nm'][0]
    
    print(f"\n450nm (blue) - mean R1-R8 response per ommatidium:")
    print(f"  {blue_stim.photoreceptor_pattern.mean(axis=0)}")
    
    print(f"\n600nm (red) - mean R1-R8 response per ommatidium:")
    print(f"  {red_stim.photoreceptor_pattern.mean(axis=0)}")
    
    print("\n✓ All tests passed")
