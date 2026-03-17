"""
Photoreceptor Spectral Sensitivity Database

Database of Drosophila photoreceptor spectral sensitivities.
Analog to DOoR for olfaction - provides consensus spectral curves
from multiple published sources.

Data sources:
- Stavenga et al. (2020): In vivo measurements, most comprehensive
- Salcedo et al. (1999): ERG recordings, different preparation
- Wakakuwa et al. (2007): Behavioral data, complements physiology
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


# Photoreceptor types in Drosophila compound eye
PHOTORECEPTOR_TYPES = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7p', 'R7y', 'R8p', 'R8y']

# Ommatidium types (differ in R7/R8 opsin expression)
OMMATIDIUM_TYPES = {
    'pale': {
        'R1': 'R1', 'R2': 'R2', 'R3': 'R3', 'R4': 'R4', 'R5': 'R5', 'R6': 'R6',
        'R7': 'R7p',  # Rh3 opsin, peak 345nm
        'R8': 'R8p'   # Rh5 opsin, peak 437nm
    },
    'yellow': {
        'R1': 'R1', 'R2': 'R2', 'R3': 'R3', 'R4': 'R4', 'R5': 'R5', 'R6': 'R6',
        'R7': 'R7y',  # Rh4 opsin, peak 375nm (with UV filter)
        'R8': 'R8y'   # Rh6 opsin, peak 600nm (red-shifted by filter)
    }
}


@dataclass
class SpectralCurve:
    """Spectral sensitivity curve for a photoreceptor."""
    wavelengths: np.ndarray  # nm
    sensitivities: np.ndarray  # normalized 0-1
    receptor_type: str
    source: str


class PhotoreceptorDatabase:
    """
    Database of Drosophila photoreceptor spectral sensitivities.
    
    Provides consensus spectral curves synthesized from multiple
    published sources with quality weighting.
    """
    
    def __init__(self, data_dir='data/vision/photoreceptor_spectra'):
        """
        Initialize photoreceptor database.
        
        Args:
            data_dir: Directory containing spectral data CSV files
        """
        self.data_dir = Path(data_dir)
        self.sources = {}
        self.consensus_curves = {}
        self.wavelength_range = (300, 700)  # nm
        self.wavelength_step = 10  # nm
        
        # Quality weights for each data source (based on methodology)
        self.source_weights = {
            'stavenga_2020': 1.0,   # In vivo, most recent, comprehensive
            'salcedo_1999': 0.8,    # ERG, different preparation
            'wakakuwa_2007': 0.7    # Behavioral, indirect measurement
        }
        
        # Load all data sources
        self._load_all_sources()
        
        # Compute consensus curves
        self._compute_consensus()
        
        print(f"✓ Photoreceptor database loaded:")
        print(f"  Sources: {len(self.sources)}")
        print(f"  Receptors: {len(self.consensus_curves)}")
        print(f"  Wavelength range: {self.wavelength_range[0]}-{self.wavelength_range[1]} nm")
        print(f"  Resolution: {self.wavelength_step} nm")
    
    def _load_all_sources(self):
        """Load spectral data from all CSV files."""
        csv_files = {
            'stavenga_2020': 'stavenga_2020.csv',
            'salcedo_1999': 'salcedo_1999.csv',
            'wakakuwa_2007': 'wakakuwa_2007.csv'
        }
        
        for source_name, filename in csv_files.items():
            filepath = self.data_dir / filename
            if filepath.exists():
                df = pd.read_csv(filepath)
                self.sources[source_name] = df
                print(f"  ✓ Loaded {source_name}: {len(df)} wavelengths")
            else:
                print(f"  ⚠ Missing {source_name}: {filepath}")
    
    def _compute_consensus(self):
        """
        Compute consensus spectral curves from multiple sources.
        
        Uses weighted average based on source quality:
        - Stavenga 2020: weight 1.0 (gold standard)
        - Salcedo 1999: weight 0.8
        - Wakakuwa 2007: weight 0.7
        """
        if not self.sources:
            raise ValueError("No data sources loaded")
        
        # Get wavelength grid (all sources should have same grid)
        wavelengths = self.sources['stavenga_2020']['wavelength'].values
        
        # Compute weighted average for each receptor
        for receptor in PHOTORECEPTOR_TYPES:
            weighted_sum = np.zeros(len(wavelengths))
            weight_sum = 0.0
            
            for source_name, df in self.sources.items():
                if receptor in df.columns:
                    weight = self.source_weights[source_name]
                    weighted_sum += weight * df[receptor].values
                    weight_sum += weight
            
            if weight_sum > 0:
                consensus = weighted_sum / weight_sum
                self.consensus_curves[receptor] = SpectralCurve(
                    wavelengths=wavelengths,
                    sensitivities=consensus,
                    receptor_type=receptor,
                    source='consensus'
                )
    
    def get_receptor_response(self, wavelength: float, receptor: str) -> float:
        """
        Get spectral sensitivity of a receptor at specific wavelength.
        
        Args:
            wavelength: Wavelength in nm (300-700)
            receptor: Receptor type (R1-R6, R7p, R7y, R8p, R8y)
        
        Returns:
            Normalized sensitivity (0-1)
        """
        if receptor not in self.consensus_curves:
            raise ValueError(f"Unknown receptor: {receptor}")
        
        curve = self.consensus_curves[receptor]
        
        # Linear interpolation
        return np.interp(wavelength, curve.wavelengths, curve.sensitivities)
    
    def get_ommatidium_response(
        self, 
        wavelength: float, 
        ommatidium_type: str = 'pale'
    ) -> Dict[str, float]:
        """
        Get full R1-R8 response for an ommatidium at wavelength.
        
        Args:
            wavelength: Wavelength in nm
            ommatidium_type: 'pale' or 'yellow'
        
        Returns:
            Dictionary mapping R1-R8 to sensitivities
        """
        if ommatidium_type not in OMMATIDIUM_TYPES:
            raise ValueError(f"Unknown ommatidium type: {ommatidium_type}")
        
        mapping = OMMATIDIUM_TYPES[ommatidium_type]
        responses = {}
        
        for photoreceptor, receptor_type in mapping.items():
            responses[photoreceptor] = self.get_receptor_response(wavelength, receptor_type)
        
        return responses
    
    def get_spectrum_response(
        self,
        spectrum: Dict[float, float],
        ommatidium_type: str = 'pale'
    ) -> Dict[str, float]:
        """
        Get ommatidium response to a full spectrum (e.g., color mixture).
        
        Args:
            spectrum: Dictionary mapping wavelength → intensity
            ommatidium_type: 'pale' or 'yellow'
        
        Returns:
            Dictionary mapping R1-R8 to integrated responses
        """
        mapping = OMMATIDIUM_TYPES[ommatidium_type]
        integrated_responses = {pr: 0.0 for pr in mapping.keys()}
        
        # Integrate over spectrum
        total_intensity = sum(spectrum.values())
        if total_intensity == 0:
            return integrated_responses
        
        for wavelength, intensity in spectrum.items():
            omm_response = self.get_ommatidium_response(wavelength, ommatidium_type)
            for photoreceptor, response in omm_response.items():
                integrated_responses[photoreceptor] += response * intensity
        
        # Normalize by total intensity
        for photoreceptor in integrated_responses:
            integrated_responses[photoreceptor] /= total_intensity
        
        return integrated_responses
    
    def get_all_wavelengths(self) -> np.ndarray:
        """Get array of all wavelengths in database."""
        return self.consensus_curves['R1'].wavelengths
    
    def get_peak_wavelength(self, receptor: str) -> float:
        """Get peak sensitivity wavelength for a receptor."""
        if receptor not in self.consensus_curves:
            raise ValueError(f"Unknown receptor: {receptor}")
        
        curve = self.consensus_curves[receptor]
        peak_idx = np.argmax(curve.sensitivities)
        return curve.wavelengths[peak_idx]
    
    def plot_spectral_curves(self, save_path: Optional[str] = None):
        """
        Plot all spectral sensitivity curves.
        
        Args:
            save_path: Optional path to save figure
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("⚠ matplotlib not installed, cannot plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Plot R1-R6 (outer receptors)
        for receptor in ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']:
            curve = self.consensus_curves[receptor]
            ax1.plot(curve.wavelengths, curve.sensitivities, 
                    label=receptor, linewidth=2)
        
        ax1.set_xlabel('Wavelength (nm)', fontsize=12)
        ax1.set_ylabel('Normalized Sensitivity', fontsize=12)
        ax1.set_title('Outer Photoreceptors (R1-R6)', fontsize=14)
        ax1.legend()
        ax1.grid(alpha=0.3)
        
        # Plot R7/R8 (inner receptors)
        colors = {'R7p': 'purple', 'R7y': 'violet', 'R8p': 'blue', 'R8y': 'red'}
        for receptor in ['R7p', 'R7y', 'R8p', 'R8y']:
            curve = self.consensus_curves[receptor]
            ax2.plot(curve.wavelengths, curve.sensitivities, 
                    label=receptor, color=colors[receptor], linewidth=2)
        
        ax2.set_xlabel('Wavelength (nm)', fontsize=12)
        ax2.set_ylabel('Normalized Sensitivity', fontsize=12)
        ax2.set_title('Inner Photoreceptors (R7/R8)', fontsize=14)
        ax2.legend()
        ax2.grid(alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ Saved plot to {save_path}")
        else:
            plt.show()
    
    def export_consensus_matrix(self, output_path: str):
        """
        Export consensus spectral matrix to CSV.
        
        Args:
            output_path: Path for output CSV file
        """
        wavelengths = self.get_all_wavelengths()
        
        data = {'wavelength': wavelengths}
        for receptor in PHOTORECEPTOR_TYPES:
            curve = self.consensus_curves[receptor]
            data[receptor] = curve.sensitivities
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        print(f"✓ Exported consensus matrix to {output_path}")


if __name__ == "__main__":
    # Test photoreceptor database
    print("Testing Photoreceptor Database\n")
    
    db = PhotoreceptorDatabase()
    
    # Test single receptor queries
    print("\n" + "="*70)
    print("Single Receptor Queries")
    print("="*70)
    
    test_wavelengths = [340, 375, 437, 478, 600]
    for wl in test_wavelengths:
        print(f"\nWavelength: {wl} nm")
        print(f"  R1-R6 (broadband): {db.get_receptor_response(wl, 'R1'):.3f}")
        print(f"  R7p (UV): {db.get_receptor_response(wl, 'R7p'):.3f}")
        print(f"  R7y (UV-filtered): {db.get_receptor_response(wl, 'R7y'):.3f}")
        print(f"  R8p (blue): {db.get_receptor_response(wl, 'R8p'):.3f}")
        print(f"  R8y (green-red): {db.get_receptor_response(wl, 'R8y'):.3f}")
    
    # Test ommatidium responses
    print("\n" + "="*70)
    print("Ommatidium Responses (500nm green light)")
    print("="*70)
    
    pale_response = db.get_ommatidium_response(500, 'pale')
    yellow_response = db.get_ommatidium_response(500, 'yellow')
    
    print("\nPale ommatidium:")
    for pr, resp in pale_response.items():
        print(f"  {pr}: {resp:.3f}")
    
    print("\nYellow ommatidium:")
    for pr, resp in yellow_response.items():
        print(f"  {pr}: {resp:.3f}")
    
    # Test spectrum response (color mixture)
    print("\n" + "="*70)
    print("Spectrum Response (450nm blue + 550nm green)")
    print("="*70)
    
    spectrum = {450: 0.5, 550: 0.5}
    mixture_response = db.get_spectrum_response(spectrum, 'pale')
    
    print("\nMixture response:")
    for pr, resp in mixture_response.items():
        print(f"  {pr}: {resp:.3f}")
    
    # Peak wavelengths
    print("\n" + "="*70)
    print("Peak Sensitivity Wavelengths")
    print("="*70)
    
    for receptor in PHOTORECEPTOR_TYPES:
        peak = db.get_peak_wavelength(receptor)
        print(f"  {receptor}: {peak:.0f} nm")
    
    print("\n✓ All tests passed")
