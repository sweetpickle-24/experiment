"""
Spatial indexing for efficient proximity queries.
Uses k-d tree for fast nearest neighbor searches.
"""

import numpy as np
import pickle
from pathlib import Path
from typing import List, Tuple
from scipy.spatial import cKDTree


class SpatialIndex:
    """
    K-d tree for fast spatial queries on neuron positions.
    Critical for hive formation and distance-dependent delays.
    """
    
    def __init__(self, connectome):
        """Build spatial index from connectome (with caching)."""
        self.connectome = connectome
        cache_file = Path(connectome.data_dir) / "spatial_index_cache.pkl"
        
        # Try loading from cache first
        if cache_file.exists():
            print(f"Loading spatial index from cache...")
            try:
                with open(cache_file, 'rb') as f:
                    cached = pickle.load(f)
                    self.neuron_ids = cached['neuron_ids']
                    self.positions = cached['positions']
                    self.tree = cached['tree']
                print(f"✓ Loaded spatial index from cache (instant)")
                return
            except Exception as e:
                print(f"Cache load failed ({e}), rebuilding spatial index...")
        
        # Cache miss - build from scratch
        print("Building spatial index (k-d tree) from scratch...")
        
        # Extract all positions and IDs
        self.neuron_ids = list(connectome.neurons.keys())
        self.positions = np.array([
            connectome.neurons[nid].position 
            for nid in self.neuron_ids
        ])
        
        # Build k-d tree
        self.tree = cKDTree(self.positions)
        print(f"✓ Indexed {len(self.neuron_ids)} neurons")
        
        # Save to cache
        print(f"Saving spatial index cache...")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'neuron_ids': self.neuron_ids,
                    'positions': self.positions,
                    'tree': self.tree,
                }, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"✓ Spatial index cache saved!")
        except Exception as e:
            print(f"Warning: Failed to save spatial index cache ({e})")
    
    def find_nearest(self, neuron_id: int, k: int = 10) -> List[Tuple[int, float]]:
        """
        Find k nearest neighbors to a neuron.
        Returns list of (neuron_id, distance) tuples.
        """
        idx = self.neuron_ids.index(neuron_id)
        pos = self.positions[idx]
        
        # Query k+1 because first result is the neuron itself
        distances, indices = self.tree.query(pos, k=k+1)
        
        # Skip first result (self)
        neighbors = [
            (self.neuron_ids[indices[i]], distances[i])
            for i in range(1, len(indices))
        ]
        return neighbors
    
    def find_within_radius(self, neuron_id: int, radius: float) -> List[Tuple[int, float]]:
        """
        Find all neurons within radius (μm) of a neuron.
        Returns list of (neuron_id, distance) tuples.
        """
        idx = self.neuron_ids.index(neuron_id)
        pos = self.positions[idx]
        
        indices = self.tree.query_ball_point(pos, radius)
        
        neighbors = []
        for i in indices:
            if i != idx:  # Skip self
                nid = self.neuron_ids[i]
                dist = np.linalg.norm(pos - self.positions[i])
                neighbors.append((nid, dist))
        
        return neighbors
    
    def find_nearest_in_region(self, neuron_id: int, region: str, k: int = 10) -> List[Tuple[int, float]]:
        """
        Find k nearest neighbors in a specific brain region.
        """
        # Get all neurons in target region
        region_ids = self.connectome.get_neurons_in_region(region)
        if not region_ids:
            return []
        
        # Get positions of region neurons
        region_indices = [self.neuron_ids.index(nid) for nid in region_ids]
        region_positions = self.positions[region_indices]
        
        # Build temporary tree for this region
        region_tree = cKDTree(region_positions)
        
        # Query
        idx = self.neuron_ids.index(neuron_id)
        pos = self.positions[idx]
        distances, indices = region_tree.query(pos, k=min(k, len(region_ids)))
        
        neighbors = [
            (region_ids[indices[i]], distances[i])
            for i in range(len(indices))
            if region_ids[indices[i]] != neuron_id  # Skip if querying neuron is in region
        ]
        return neighbors
    
    def compute_spatial_gradient(self, neuron_ids: List[int], k: int = 20) -> np.ndarray:
        """
        Compute spatial gradient values for a set of neurons.
        Returns array of average distances to k nearest neighbors.
        Useful for detecting spatial clusters.
        """
        gradients = np.zeros(len(neuron_ids))
        
        for i, nid in enumerate(neuron_ids):
            neighbors = self.find_nearest(nid, k)
            if neighbors:
                avg_dist = np.mean([dist for _, dist in neighbors])
                gradients[i] = avg_dist
        
        return gradients
    
    def get_transmission_delay(self, pre_id: int, post_id: int, speed: float = 100.0) -> float:
        """
        Compute transmission delay based on distance.
        Default speed: 100 μm/ms (0.1 m/s, typical for unmyelinated axons).
        Returns delay in milliseconds.
        """
        distance = self.connectome.distance(pre_id, post_id)
        return distance / speed
