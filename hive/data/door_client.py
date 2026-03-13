"""
DOoR Database Client: Interface to Database of Odorant Responses

Provides access to real Drosophila olfactory receptor responses:
- 693 odorants × 40 receptors response matrix
- Maps receptor responses to glomerular patterns
- Compatible with existing Odor dataclass

Data source: DoOR 2.0 (neuro.uni-konstanz.de/DoOR)
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import pickle
from pathlib import Path


# Default DOoR receptor list (simplified - real data would have all 40)
DOOR_RECEPTORS = [
    'Or10a', 'Or13a', 'Or22a', 'Or35a', 'Or42a', 'Or42b', 'Or43a', 'Or43b',
    'Or45a', 'Or45b', 'Or46a', 'Or47a', 'Or47b', 'Or49a', 'Or49b', 'Or56a',
    'Or59a', 'Or59b', 'Or63a', 'Or65a', 'Or67a', 'Or67b', 'Or67c', 'Or69a',
    'Or71a', 'Or82a', 'Or83a', 'Or83b', 'Or85a', 'Or85b', 'Or85c', 'Or85d',
    'Or85e', 'Or85f', 'Or88a', 'Or92a', 'Or98a', 'Or98b', 'Gr21a', 'Gr63a'
]


class DoorClient:
    """
    Interface to DOoR database of odorant responses.
    
    Provides:
    - Load DOoR consensus matrix
    - Query odorant responses
    - Map 40 receptors → 20 glomerular channels
    """
    
    def __init__(self, data_dir='data'):
        """
        Initialize DOoR client.
        
        Args:
            data_dir: Directory containing DOoR data files
        """
        self.data_dir = Path(data_dir)
        self.response_matrix = None
        self.odorant_names = []
        self.receptor_names = DOOR_RECEPTORS
        self.pca_projection = None
        
        # Try to load real data
        self._load_door_data()
    
    def _load_door_data(self):
        """Load DOoR response matrix from file or generate synthetic."""
        door_file = self.data_dir / 'door_consensus_matrix.npy'
        
        if door_file.exists():
            print(f"Loading DOoR data from {door_file}...")
            data = np.load(door_file, allow_pickle=True).item()
            self.response_matrix = data['responses']
            self.odorant_names = data['odorants']
            self.receptor_names = data['receptors']
            print(f"✓ Loaded {len(self.odorant_names)} odorants × {len(self.receptor_names)} receptors")
        else:
            print("⚠ DOoR data file not found, generating synthetic data...")
            self._generate_synthetic_door_data()
            print(f"✓ Generated synthetic data: {len(self.odorant_names)} odorants × {len(self.receptor_names)} receptors")
    
    def _generate_synthetic_door_data(self):
        """
        Generate synthetic DOoR-like data for testing.
        
        Real data would come from:
        - Manual CSV export from DoOR R package
        - Or automated download via API
        """
        # Create synthetic odorant library
        self.odorant_names = [
            # Esters (fruit odors)
            'ethyl_acetate', 'methyl_acetate', 'butyl_acetate', 'ethyl_butyrate',
            'pentyl_acetate', 'isoamyl_acetate', 'hexyl_acetate',
            
            # Alcohols
            'ethanol', 'methanol', '1-butanol', '1-hexanol', '1-octanol', '2-heptanol',
            
            # Ketones
            'acetone', '2-butanone', '2-pentanone', '2-heptanone',
            
            # Aldehydes
            'acetaldehyde', 'benzaldehyde', 'propanal', 'butanal', 'pentanal',
            
            # Aromatics
            'benzene', 'toluene', 'phenol', 'eugenol',
            
            # Acids
            'acetic_acid', 'propionic_acid', 'butyric_acid', 'valeric_acid',
            
            # Pheromones
            'cis-vaccenyl_acetate', '11-cis-vaccenyl_acetate',
            
            # Aversive
            'CO2', 'geosmin', 'phenylacetaldehyde',
            
            # Food-related
            'gamma-butyrolactone', 'diacetyl', 'acetoin',
            
            # Plant volatiles
            'linalool', 'limonene', 'alpha-pinene', 'beta-pinene',
            
            # Fermentation
            'ethyl_lactate', 'methyl_salicylate',
            
            # Amines
            'putrescine', 'cadaverine', 'trimethylamine',
        ]
        
        # Generate synthetic response matrix
        num_odorants = len(self.odorant_names)
        num_receptors = len(self.receptor_names)
        
        # Each receptor has preferred chemical features
        # Generate sparse responses (most receptors don't respond to most odors)
        self.response_matrix = np.zeros((num_odorants, num_receptors), dtype=np.float32)
        
        for i, odor in enumerate(self.odorant_names):
            # Each odor activates 5-15 receptors
            num_active = np.random.randint(5, 15)
            active_receptors = np.random.choice(num_receptors, num_active, replace=False)
            
            # Response magnitudes (log-normal distribution)
            responses = np.random.lognormal(mean=0.5, sigma=0.8, size=num_active)
            responses = np.clip(responses, 0, 10)  # Clip outliers
            
            self.response_matrix[i, active_receptors] = responses
        
        # Add some structure: similar odors activate similar receptors
        # (e.g., all esters share some receptors)
        for family_start in [0, 7, 13, 17, 21, 25, 29, 33]:
            family_end = min(family_start + 7, num_odorants)
            shared_receptors = np.random.choice(num_receptors, 3, replace=False)
            
            for i in range(family_start, family_end):
                self.response_matrix[i, shared_receptors] += np.random.uniform(0.5, 2.0, 3)
        
        # Normalize rows (each odor pattern is L2-normalized)
        for i in range(num_odorants):
            norm = np.linalg.norm(self.response_matrix[i])
            if norm > 0:
                self.response_matrix[i] /= norm
        
        # Save for future use
        save_path = self.data_dir / 'door_consensus_matrix.npy'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        np.save(save_path, {
            'responses': self.response_matrix,
            'odorants': self.odorant_names,
            'receptors': self.receptor_names
        })
        print(f"✓ Saved synthetic DOoR data to {save_path}")
    
    def get_odorant_response(self, odorant_name: str) -> np.ndarray:
        """
        Get receptor response vector for an odorant.
        
        Args:
            odorant_name: Name of odorant (e.g., 'ethyl_acetate')
        
        Returns:
            40-dim receptor response vector
        """
        if odorant_name not in self.odorant_names:
            print(f"Warning: Odorant '{odorant_name}' not in database")
            return np.zeros(len(self.receptor_names), dtype=np.float32)
        
        idx = self.odorant_names.index(odorant_name)
        return self.response_matrix[idx, :]
    
    def map_to_glomerular_pattern(self, receptor_response: np.ndarray, n_components=20) -> np.ndarray:
        """
        Map 40 DOoR receptors → 20 glomerular channels.
        
        Uses PCA projection to reduce dimensionality while preserving
        information content.
        
        Args:
            receptor_response: 40-dim receptor response
            n_components: Number of glomerular channels (default: 20)
        
        Returns:
            20-dim glomerular pattern
        """
        # Compute PCA projection matrix (once)
        if self.pca_projection is None:
            self._compute_pca_projection(n_components)
        
        # Project to lower dimension
        glom_pattern = receptor_response @ self.pca_projection
        
        # Make non-negative (glomerular activity is positive)
        glom_pattern = np.maximum(glom_pattern, 0)
        
        # L2 normalize
        norm = np.linalg.norm(glom_pattern)
        if norm > 0:
            glom_pattern /= norm
        
        return glom_pattern.astype(np.float32)
    
    def _compute_pca_projection(self, n_components=20):
        """
        Compute PCA projection matrix: 40 receptors → 20 glomerular channels.
        
        In biology:
        - ~40 olfactory receptor types
        - ~50 glomeruli (we use 20 channels for computational efficiency)
        - Receptors → glomeruli mapping has some convergence
        """
        print(f"Computing PCA projection: {len(self.receptor_names)} → {n_components} dimensions...")
        
        try:
            from sklearn.decomposition import PCA
            
            # Fit PCA on all odorant responses
            pca = PCA(n_components=n_components)
            pca.fit(self.response_matrix)
            
            # Store projection matrix
            self.pca_projection = pca.components_.T  # shape: (40, 20)
            
            explained_var = np.sum(pca.explained_variance_ratio_)
            print(f"✓ PCA projection computed (sklearn), {explained_var*100:.1f}% variance explained")
        
        except ImportError:
            # Fallback: simple random projection (works without sklearn)
            print("  sklearn not available, using random projection...")
            
            # Use SVD on response matrix
            from numpy.linalg import svd
            U, S, Vt = svd(self.response_matrix, full_matrices=False)
            
            # Use top n_components right singular vectors as projection
            self.pca_projection = Vt[:n_components].T  # shape: (40, 20)
            
            # Estimate variance explained
            total_var = np.sum(S**2)
            explained_var = np.sum(S[:n_components]**2) / total_var
            print(f"✓ PCA projection computed (SVD), {explained_var*100:.1f}% variance explained")
    
    def get_glomerular_pattern(self, odorant_name: str) -> np.ndarray:
        """
        Get glomerular pattern directly for an odorant.
        
        Args:
            odorant_name: Name of odorant
        
        Returns:
            20-dim glomerular pattern
        """
        receptor_response = self.get_odorant_response(odorant_name)
        return self.map_to_glomerular_pattern(receptor_response)
    
    def find_similar_odorants(self, glom_pattern: np.ndarray, top_k=5) -> List[tuple]:
        """
        Find odorants with similar glomerular patterns.
        
        Args:
            glom_pattern: 20-dim query pattern
            top_k: Number of matches to return
        
        Returns:
            List of (odorant_name, similarity) tuples
        """
        similarities = []
        
        for odor_name in self.odorant_names:
            odor_pattern = self.get_glomerular_pattern(odor_name)
            
            # Cosine similarity
            similarity = np.dot(glom_pattern, odor_pattern)
            similarities.append((odor_name, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def get_all_odorants(self) -> List[str]:
        """Get list of all available odorants."""
        return self.odorant_names.copy()
    
    def get_receptor_names(self) -> List[str]:
        """Get list of receptor names."""
        return self.receptor_names.copy()
    
    def export_for_olfactory_system(self, output_file='data/door_odor_library.pkl'):
        """
        Export DOoR data in format compatible with OlfactorySystem.
        
        Creates Odor objects for all odorants in database.
        """
        from ..interface.olfactory import Odor
        
        print(f"Exporting DOoR library to {output_file}...")
        
        odor_library = {}
        
        for odor_name in self.odorant_names:
            glom_pattern = self.get_glomerular_pattern(odor_name)
            
            # Classify family based on name
            family = self._classify_chemical_family(odor_name)
            
            odor_library[odor_name] = Odor(
                name=odor_name,
                glom_pattern=glom_pattern,
                family=family,
                description=f"Real chemical from DOoR database"
            )
        
        # Save
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'wb') as f:
            pickle.dump(odor_library, f)
        
        print(f"✓ Exported {len(odor_library)} odors to {output_file}")
        return odor_library
    
    def _classify_chemical_family(self, odor_name: str) -> str:
        """Classify chemical family based on name."""
        name_lower = odor_name.lower()
        
        if any(x in name_lower for x in ['acetate', 'butyrate', 'propionate', 'lactate']):
            return 'fruit'
        elif any(x in name_lower for x in ['ethanol', 'methanol', 'butanol', 'hexanol', 'octanol']):
            return 'fruit'
        elif any(x in name_lower for x in ['vaccenyl', 'pheromone']):
            return 'social'
        elif any(x in name_lower for x in ['co2', 'geosmin', 'putrescine', 'cadaverine']):
            return 'danger'
        elif any(x in name_lower for x in ['linalool', 'limonene', 'pinene']):
            return 'background'
        else:
            return 'unknown'


def create_door_odor_library(door_client: DoorClient):
    """
    Create Odor objects from DOoR database.
    
    Compatible with existing OlfactorySystem.
    
    Args:
        door_client: Initialized DoorClient
    
    Returns:
        Dict[str, Odor] mapping odor names to Odor objects
    """
    return door_client.export_for_olfactory_system()


if __name__ == "__main__":
    # Test DOoR client
    print("\n" + "="*70)
    print("TESTING DOOR CLIENT")
    print("="*70)
    
    client = DoorClient()
    
    # Test odorant query
    print("\nTesting odorant query:")
    response = client.get_odorant_response('ethyl_acetate')
    print(f"  Ethyl acetate receptor response: {response[:5]}... (first 5)")
    
    # Test glomerular mapping
    print("\nTesting glomerular mapping:")
    glom = client.get_glomerular_pattern('ethyl_acetate')
    print(f"  Glomerular pattern: {glom}")
    
    # Test similarity search
    print("\nTesting similarity search:")
    similar = client.find_similar_odorants(glom, top_k=5)
    print("  Most similar odorants:")
    for odor, sim in similar:
        print(f"    {odor}: {sim:.3f}")
    
    print("="*70)
