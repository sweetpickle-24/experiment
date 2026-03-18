"""
Standalone runner for calcium oscillations discovery test.
No connectome required — pure phototransduction simulation.
"""
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from hive.validation.vision.test_emergent_properties import test_calcium_oscillations

if __name__ == '__main__':
    print("Running calcium oscillations test...\n")
    results = test_calcium_oscillations(
        photon_rates=[1e1, 1e2, 1e3, 1e4, 1e5],
        duration_ms=500.0,
        dt_ms=0.1,
    )

    output_path = Path("research/vision/findings/discovery_calcium_oscillations.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
