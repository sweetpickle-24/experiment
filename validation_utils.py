"""
Common utilities for validation experiments.
"""

import numpy as np
from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.data.door_client import DoorClient

def init_olfactory_brain(use_mlx=True):
    """
    Initialize olfactory system for validation experiments.
    
    Returns:
        tuple: (brain, door_client, connectome)
    """
    # Load connectome
    full_connectome = Connectome(data_dir="Fly Brain Female")
    full_connectome.load()
    
    # Extract olfactory pathway
    connectome = extract_olfactory_pathway(full_connectome)
    
    # Create brain configuration
    config = {
        'dt': 0.01,
        'gamma': 0.5,
        'omega0': 40.0,
        'coupling_strength': 2.0
    }
    
    # Initialize brain
    brain = SparseProbabilisticBrain(
        connectome=connectome,
        config=config,
        use_mlx=use_mlx
    )
    
    # Initialize DOoR client
    door_client = DoorClient()
    
    return brain, door_client, connectome
