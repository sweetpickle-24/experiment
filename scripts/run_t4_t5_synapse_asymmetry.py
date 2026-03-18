"""
Standalone runner for T4/T5 synapse asymmetry discovery.
Pure connectome analysis — no simulation needed.
"""
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from hive.substrate.connectome import Connectome
from hive.validation.vision.discovery_t4_t5_synapse_asymmetry import run_t4_t5_synapse_asymmetry

if __name__ == '__main__':
    print("Loading FlyWire connectome...")
    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()
    
    print("\nAnalyzing T4/T5 synapse asymmetry...\n")
    results = run_t4_t5_synapse_asymmetry(connectome)

    output_path = Path("research/vision/findings/discovery_t4_t5_synapse_asymmetry.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
