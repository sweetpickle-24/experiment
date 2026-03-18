"""
Standalone runner for hex lattice direction bias discovery.
Tests if hexagonal ommatidial geometry creates systematic DSI bias.
"""
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import extract_visual_pathway
from hive.validation.vision.discovery_hex_lattice_direction_bias import run_hex_lattice_direction_bias

if __name__ == '__main__':
    print("Loading FlyWire connectome...")
    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()
    
    print("Extracting visual pathway...")
    visual_connectome = extract_visual_pathway(connectome)
    
    print("\nTesting hex lattice direction bias...\n")
    results = run_hex_lattice_direction_bias(visual_connectome)

    output_path = Path("research/vision/findings/discovery_hex_lattice_direction_bias.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
