"""
DOoR Database Client: Interface to Database of Odorant Responses

Provides access to real Drosophila olfactory receptor responses:
- Odorants × receptors response matrix, shape read from the data file
- Maps receptor responses to glomerular patterns
- Compatible with existing Odor dataclass

Data source: DoOR 2.0 (neuro.uni-konstanz.de/DoOR)

Odorant names in the shipped matrix are lowercase with underscores and no
spaces. Callers frequently pass spaced names ('ethyl acetate') or synonyms
('isoamyl acetate'). Every lookup therefore goes through
normalize_odorant_name, and a name that cannot be resolved raises
OdorantNotFoundError. It must never degrade to a zero vector: a zero pattern
correlates with itself at exactly 1.0 at every concentration, which silently
inflates any invariance or similarity measure computed over it.
"""

import difflib
import logging
import re
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


# Default DOoR receptor list (simplified - real data would have all 40)
DOOR_RECEPTORS = [
    'Or10a', 'Or13a', 'Or22a', 'Or35a', 'Or42a', 'Or42b', 'Or43a', 'Or43b',
    'Or45a', 'Or45b', 'Or46a', 'Or47a', 'Or47b', 'Or49a', 'Or49b', 'Or56a',
    'Or59a', 'Or59b', 'Or63a', 'Or65a', 'Or67a', 'Or67b', 'Or67c', 'Or69a',
    'Or71a', 'Or82a', 'Or83a', 'Or83b', 'Or85a', 'Or85b', 'Or85c', 'Or85d',
    'Or85e', 'Or85f', 'Or88a', 'Or92a', 'Or98a', 'Or98b', 'Gr21a', 'Gr63a'
]


class OdorantNotFoundError(KeyError):
    """
    Raised when an odorant name cannot be resolved against the loaded matrix.

    Carries the close matches so the caller can see whether the name is a
    spelling variant, a synonym, or genuinely absent from the database.
    """

    def __init__(self, name: str, candidates: List[str], n_known: int):
        self.name = name
        self.candidates = candidates
        self.n_known = n_known
        if candidates:
            hint = "closest names in the database: " + ", ".join(repr(c) for c in candidates)
        else:
            hint = "no similar names in the database"
        super().__init__(
            f"Odorant {name!r} is not in the DoOR matrix ({n_known} odorants loaded); {hint}"
        )

    def __str__(self) -> str:
        # KeyError.__str__ reprs the whole message, which double-quotes it.
        return self.args[0]


# Names used in this codebase that denote a molecule stored under a different
# name in the DoOR matrix. Isoamyl acetate, isopentyl acetate and 3-methylbutyl
# acetate are three names for the same ester.
ODORANT_SYNONYMS = {
    'isoamyl_acetate': 'isopentyl_acetate',
    '3-methylbutyl_acetate': 'isopentyl_acetate',
    'isoamylacetate': 'isopentyl_acetate',
    'co2': 'carbon_dioxide',
    'carbon_dioxide_gas': 'carbon_dioxide',
    'propionic_acid': 'propanoic_acid',
    'propionate': 'propanoic_acid',
}


def _canonical_form(name: str) -> str:
    """Lowercase, trim, collapse internal whitespace, unify separators."""
    s = re.sub(r'\s+', ' ', str(name).strip().lower())
    return s.replace(' ', '_')


def normalize_odorant_name(name: str, known_names) -> str:
    """
    Resolve an odorant name to the exact key used in the DoOR matrix.

    Tried in order: exact, lowercase, whitespace-collapsed with spaces mapped to
    underscores, the synonym table, then hyphen/underscore substitutions. The
    first candidate present in known_names wins.

    Args:
        name:        Name as written by the caller.
        known_names: Sequence of odorant names in the loaded matrix.

    Returns:
        The matching entry of known_names.

    Raises:
        OdorantNotFoundError: if no candidate matches. Never returns a
            placeholder or a zero vector.
    """
    if name is None:
        raise OdorantNotFoundError('None', [], len(known_names))

    known = set(known_names)

    if name in known:
        return name

    base = _canonical_form(name)
    candidates = [base, ODORANT_SYNONYMS.get(base)]

    # Separator variants: the matrix mixes hyphens and underscores
    # ('2-heptanone' but 'ethyl_acetate'), and callers guess wrong either way.
    for variant in (base.replace('-', '_'), base.replace('_', '-')):
        candidates.append(variant)
        candidates.append(ODORANT_SYNONYMS.get(variant))

    for candidate in candidates:
        if candidate and candidate in known:
            return candidate

    close = difflib.get_close_matches(base, list(known_names), n=5, cutoff=0.6)
    raise OdorantNotFoundError(name, close, len(known_names))


class DoorClient:
    """
    Interface to DOoR database of odorant responses.
    
    Provides:
    - Load DOoR consensus matrix
    - Query odorant responses
    - Map 40 receptors → 20 glomerular channels
    """
    
    def __init__(self, data_dir='data', allow_synthetic=False):
        """
        Initialize DOoR client.
        
        Args:
            data_dir: Directory containing DOoR data files
            allow_synthetic: permit fabricated response data when the data file
                is absent. Off by default. Anything measured from synthetic data
                describes a random matrix, not Drosophila.
        """
        self.data_dir = Path(data_dir)
        self.response_matrix = None
        self.odorant_names = []
        self.receptor_names = DOOR_RECEPTORS
        self.pca_projection = None
        self.projection_method = None
        self.is_synthetic = False
        self.allow_synthetic = allow_synthetic
        
        # Try to load real data
        self._load_door_data()
    
    def _load_door_data(self):
        """
        Load the DoOR response matrix.

        Raises rather than fabricating data when the file is absent. The
        synthetic generator previously ran on this path and wrote its output to
        the canonical filename, so a missing download left a random matrix
        sitting where the real one belongs, indistinguishable on inspection.
        """
        door_file = self.data_dir / 'door_consensus_matrix.npy'
        
        if door_file.exists():
            print(f"Loading DOoR data from {door_file}...")
            data = np.load(door_file, allow_pickle=True).item()
            self.response_matrix = data['responses']
            self.odorant_names = list(data['odorants'])
            self.receptor_names = list(data['receptors'])
            self.is_synthetic = bool(data.get('synthetic', False))
            if self.is_synthetic:
                logger.warning(
                    "DoOR matrix at %s is SYNTHETIC (fabricated). Results derived "
                    "from it do not describe Drosophila.", door_file
                )
            print(f"✓ Loaded {len(self.odorant_names)} odorants × {len(self.receptor_names)} receptors")
        elif self.allow_synthetic:
            logger.warning(
                "DoOR data file %s not found; generating SYNTHETIC data because "
                "allow_synthetic=True. Do not quote any number derived from this.",
                door_file,
            )
            self._generate_synthetic_door_data()
            self.is_synthetic = True
            print(f"✓ Generated synthetic data: {len(self.odorant_names)} odorants × {len(self.receptor_names)} receptors")
        else:
            raise FileNotFoundError(
                f"DoOR response matrix not found at {door_file}. "
                f"Run scripts/download_door_data.py to fetch it, or pass "
                f"DoorClient(allow_synthetic=True) to work with fabricated data."
            )
    
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
        
        # Held in memory only. This deliberately does not write to
        # door_consensus_matrix.npy: a fabricated matrix under the canonical
        # filename is indistinguishable from the real download on inspection,
        # and every later run would silently consume it.
        logger.warning(
            "Synthetic DoOR matrix generated in memory (%d odorants). Not written "
            "to disk.", len(self.odorant_names)
        )
    
    def resolve_odorant_name(self, odorant_name: str) -> str:
        """
        Resolve a caller-supplied name to the exact key in the loaded matrix.

        Raises:
            OdorantNotFoundError: if the name cannot be resolved.
        """
        return normalize_odorant_name(odorant_name, self.odorant_names)

    def get_odorant_response(self, odorant_name: str) -> np.ndarray:
        """
        Get receptor response vector for an odorant.
        
        Args:
            odorant_name: Name of odorant. Spacing, case and hyphen/underscore
                differences are resolved, as are the synonyms in
                ODORANT_SYNONYMS.
        
        Returns:
            Receptor response vector, one entry per receptor in the matrix.

        Raises:
            OdorantNotFoundError: if the name cannot be resolved. This does not
                fall back to a zero vector.
        """
        resolved = self.resolve_odorant_name(odorant_name)
        idx = self.odorant_names.index(resolved)
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
