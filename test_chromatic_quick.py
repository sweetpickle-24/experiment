#!/usr/bin/env python3
"""Quick chromatic motion blindness test"""
import sys
sys.path.insert(0, '/Users/vladyslav/Documents/GitHub/experiment')

print("Importing...")
from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import extract_visual_pathway, get_visual_region_neurons
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
import numpy as np

print("Loading connectome...")
connectome = Connectome(data_dir="Fly Brain Female")
connectome.load()

print("Extracting visual pathway...")
visual_connectome = extract_visual_pathway(connectome)

print("Testing chromatic motion blindness...")
print(f"Medulla neurons: {len(list(get_visual_region_neurons(visual_connectome, 'MEDULLA')))}")
print(f"Lobula neurons: {len(list(get_visual_region_neurons(visual_connectome, 'LOBULA')))}")

print("Initializing brain with MLX...")
brain = SparseProbabilisticBrain(visual_connectome, use_mlx=True)
print(f"Brain initialized: {brain.num_neurons} neurons")

print("✅ Setup complete - ready to run test")
