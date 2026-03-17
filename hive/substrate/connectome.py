"""
Physical substrate: Load and index the fly connectome.
The hardware layer - 139K neurons, 5.3M synapses, 3D spatial coordinates.
"""

import gzip
import csv
import pickle
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
from pathlib import Path


@dataclass
class Neuron:
    """A single neuron (bee) in the fly brain."""
    root_id: int
    position: np.ndarray  # [x, y, z] coordinates
    group: str  # Neuropil region (e.g., "ME", "LO.LOP")
    nt_type: str  # Primary neurotransmitter (ACH, GABA, GLUT, etc.)
    nt_scores: Dict[str, float]  # All neurotransmitter scores
    cell_types: List[str]  # Cell type annotations


@dataclass
class Synapse:
    """A synaptic connection between two neurons."""
    pre_id: int  # Presynaptic neuron
    post_id: int  # Postsynaptic neuron
    weight: int  # Synapse count
    nt_type: str  # Neurotransmitter type
    neuropil: str  # Brain region where synapse exists


class Connectome:
    """
    The fly brain connectome - the physical chip.
    Loads all neurons, synapses, and spatial structure.
    """
    
    def __init__(self, data_dir: str = "Fly Brain Female"):
        self.data_dir = Path(data_dir)
        self.cache_file = self.data_dir / "connectome_cache.pkl"
        self.neurons: Dict[int, Neuron] = {}
        self.synapses: List[Synapse] = []
        self.adjacency: Dict[int, List[Tuple[int, float, str]]] = {}  # pre -> [(post, weight, nt)]
        
        self.min_pos = None
        self.max_pos = None
        self.center_pos = None
        
    def load(self):
        """Load all connectome data (with pickle caching for speed)."""
        # Try loading from cache first
        if self.cache_file.exists():
            print(f"Loading connectome from cache ({self.cache_file})...")
            try:
                with open(self.cache_file, 'rb') as f:
                    cached = pickle.load(f)
                self.neurons = cached['neurons']
                self.synapses = cached['synapses']
                self.adjacency = cached['adjacency']
                self.min_pos = cached['min_pos']
                self.max_pos = cached['max_pos']
                self.center_pos = cached['center_pos']
                print(f"✓ Loaded {len(self.neurons)} neurons, {len(self.synapses)} synapses from cache (instant)")
                return
            except Exception as e:
                print(f"Cache load failed ({e}), rebuilding from CSVs...")
        
        # Cache miss - load from CSVs
        print("Loading fly brain connectome from CSVs (first time only, ~2-3 minutes)...")
        self._load_neurons()
        self._load_coordinates()
        self._load_cell_types()
        self._load_connections()
        self._compute_spatial_bounds()
        print(f"Loaded {len(self.neurons)} neurons, {len(self.synapses)} synapses")
        
        # Save to cache
        print(f"Saving connectome cache to {self.cache_file}...")
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump({
                    'neurons': self.neurons,
                    'synapses': self.synapses,
                    'adjacency': self.adjacency,
                    'min_pos': self.min_pos,
                    'max_pos': self.max_pos,
                    'center_pos': self.center_pos,
                }, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"✓ Cache saved! Next startup will be instant.")
        except Exception as e:
            print(f"Warning: Failed to save cache ({e}). Will reload from CSVs next time.")
        
    def _load_neurons(self):
        """Load neuron metadata (neurotransmitter profiles)."""
        path = self.data_dir / "neurons.csv.gz"
        with gzip.open(path, 'rt') as f:
            reader = csv.DictReader(f)
            for row in reader:
                root_id = int(row['root_id'])
                nt_scores = {
                    'da': float(row['da_avg']),
                    'ser': float(row['ser_avg']),
                    'gaba': float(row['gaba_avg']),
                    'glut': float(row['glut_avg']),
                    'ach': float(row['ach_avg']),
                    'oct': float(row['oct_avg'])
                }
                self.neurons[root_id] = Neuron(
                    root_id=root_id,
                    position=np.zeros(3),  # Will be filled later
                    group=row['group'],
                    nt_type=row['nt_type'] if row['nt_type'] else 'UNKNOWN',
                    nt_scores=nt_scores,
                    cell_types=[]  # Will be filled later
                )
    
    def _load_coordinates(self):
        """Load 3D spatial coordinates for all neurons."""
        path = self.data_dir / "coordinates.csv.gz"
        with gzip.open(path, 'rt') as f:
            reader = csv.DictReader(f)
            for row in reader:
                root_id = int(row['root_id'])
                if root_id in self.neurons:
                    pos_str = row['position'].strip('[]')
                    pos = np.array([int(x) for x in pos_str.split()])
                    self.neurons[root_id].position = pos
    
    def _load_cell_types(self):
        """Load cell type annotations."""
        path = self.data_dir / "consolidated_cell_types.csv.gz"
        with gzip.open(path, 'rt') as f:
            reader = csv.DictReader(f)
            for row in reader:
                root_id = int(row['root_id'])
                if root_id in self.neurons:
                    types = [row['primary_type']]
                    if row['additional_type(s)']:
                        types.extend(row['additional_type(s)'].split(','))
                    self.neurons[root_id].cell_types = types
    
    def _load_connections(self):
        """Load synaptic connections."""
        path = self.data_dir / "connections_princeton.csv.gz"
        count = 0
        with gzip.open(path, 'rt') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pre_id = int(row['pre_root_id'])
                post_id = int(row['post_root_id'])
                
                # Only keep connections where both neurons exist
                if pre_id in self.neurons and post_id in self.neurons:
                    syn = Synapse(
                        pre_id=pre_id,
                        post_id=post_id,
                        weight=int(row['syn_count']),
                        nt_type=row['nt_type'],
                        neuropil=row['neuropil']
                    )
                    self.synapses.append(syn)
                    
                    # Build adjacency list
                    if pre_id not in self.adjacency:
                        self.adjacency[pre_id] = []
                    self.adjacency[pre_id].append((post_id, syn.weight, syn.nt_type))
                    
                count += 1
                if count % 500000 == 0:
                    print(f"  Loaded {count} connections...")
    
    def _compute_spatial_bounds(self):
        """Compute bounding box and center of brain."""
        positions = np.array([n.position for n in self.neurons.values()])
        self.min_pos = positions.min(axis=0)
        self.max_pos = positions.max(axis=0)
        self.center_pos = (self.min_pos + self.max_pos) / 2
        
        print(f"Spatial extent: {self.min_pos} to {self.max_pos}")
        print(f"Brain center: {self.center_pos}")
        print(f"Brain size: {self.max_pos - self.min_pos} μm")
    
    def get_neuron(self, neuron_id: int) -> Optional[Neuron]:
        """Get neuron by ID."""
        return self.neurons.get(neuron_id)
    
    def get_postsynaptic(self, neuron_id: int) -> List[Tuple[int, float, str]]:
        """Get all postsynaptic targets of a neuron."""
        return self.adjacency.get(neuron_id, [])
    
    def get_neurons_in_region(self, region: str) -> List[int]:
        """Get all neuron IDs in a specific neuropil region."""
        return [nid for nid, n in self.neurons.items() if n.group == region]
    
    def get_neurons_by_type(self, cell_type: str) -> List[int]:
        """Get all neurons of a specific cell type."""
        return [nid for nid, n in self.neurons.items() if cell_type in n.cell_types]
    
    def distance(self, id1: int, id2: int) -> float:
        """Euclidean distance between two neurons (in μm)."""
        n1 = self.neurons.get(id1)
        n2 = self.neurons.get(id2)
        if n1 is None or n2 is None:
            return np.inf
        return np.linalg.norm(n1.position - n2.position)
    
    def summary(self) -> Dict:
        """Get summary statistics."""
        nt_counts = {}
        for n in self.neurons.values():
            nt_counts[n.nt_type] = nt_counts.get(n.nt_type, 0) + 1
        
        region_counts = {}
        for n in self.neurons.values():
            region_counts[n.group] = region_counts.get(n.group, 0) + 1
        
        return {
            'num_neurons': len(self.neurons),
            'num_synapses': len(self.synapses),
            'neurotransmitters': nt_counts,
            'top_regions': sorted(region_counts.items(), key=lambda x: -x[1])[:10],
            'spatial_extent': (self.min_pos, self.max_pos),
            'brain_size': self.max_pos - self.min_pos
        }
    
    def save(self, filepath: str):
        """
        Save connectome to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        import json
        from pathlib import Path
        
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for JSON serialization
        data = {
            'neurons': {
                str(nid): {
                    'root_id': n.root_id,
                    'position': n.position.tolist(),
                    'group': n.group,
                    'nt_type': n.nt_type,
                    'nt_scores': n.nt_scores,
                    'cell_types': n.cell_types
                }
                for nid, n in self.neurons.items()
            },
            'synapses': [
                {
                    'pre_id': s.pre_id,
                    'post_id': s.post_id,
                    'weight': s.weight,
                    'nt_type': s.nt_type,
                    'neuropil': s.neuropil
                }
                for s in self.synapses
            ],
            'adjacency': {
                str(pre): [(post, float(weight), nt) for post, weight, nt in targets]
                for pre, targets in self.adjacency.items()
            },
            'spatial_bounds': {
                'min': self.min_pos.tolist() if self.min_pos is not None else None,
                'max': self.max_pos.tolist() if self.max_pos is not None else None,
                'center': self.center_pos.tolist() if self.center_pos is not None else None
            }
        }
        
        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(data, f)
        
        print(f"  Connectome saved: {len(self.neurons):,} neurons, {len(self.synapses):,} synapses")
    
    def load_json(self, filepath: str):
        """
        Load connectome from JSON file.
        
        Args:
            filepath: Path to JSON file
        """
        import json
        
        print(f"Loading connectome from {filepath}...")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Load neurons
        self.neurons = {}
        for nid_str, n_data in data['neurons'].items():
            nid = int(nid_str)
            self.neurons[nid] = Neuron(
                root_id=n_data['root_id'],
                position=np.array(n_data['position']),
                group=n_data['group'],
                nt_type=n_data['nt_type'],
                nt_scores=n_data['nt_scores'],
                cell_types=n_data['cell_types']
            )
        
        # Load synapses
        self.synapses = [
            Synapse(
                pre_id=s['pre_id'],
                post_id=s['post_id'],
                weight=s['weight'],
                nt_type=s['nt_type'],
                neuropil=s['neuropil']
            )
            for s in data['synapses']
        ]
        
        # Load adjacency
        self.adjacency = {
            int(pre_str): [(post, weight, nt) for post, weight, nt in targets]
            for pre_str, targets in data['adjacency'].items()
        }
        
        # Load spatial bounds
        bounds = data['spatial_bounds']
        self.min_pos = np.array(bounds['min']) if bounds['min'] else None
        self.max_pos = np.array(bounds['max']) if bounds['max'] else None
        self.center_pos = np.array(bounds['center']) if bounds['center'] else None
        
        print(f"✓ Loaded {len(self.neurons):,} neurons, {len(self.synapses):,} synapses")


if __name__ == "__main__":
    # Test loading
    connectome = Connectome()
    connectome.load()
    
    summary = connectome.summary()
    print("\nConnectome Summary:")
    print(f"Neurons: {summary['num_neurons']}")
    print(f"Synapses: {summary['num_synapses']}")
    print(f"\nNeurotransmitter distribution:")
    for nt, count in summary['neurotransmitters'].items():
        print(f"  {nt}: {count}")
    print(f"\nTop 10 brain regions:")
    for region, count in summary['top_regions']:
        print(f"  {region}: {count}")
