"""
Runner: Hex Lattice Direction Bias (corrected equilateral hex geometry).

Changes from original:
  - Uses proper equilateral hex lattice (a=4.5°, row_spacing=a√3/2)
  - Tests 12 directions at 30°-spacing (includes true hex axes 0°, 60°, 120°...)
  - Prints progress after every direction with elapsed/ETA
  - GPU only (MLX)
"""
import sys
import json
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import extract_visual_pathway
from hive.validation.vision.discovery_hex_lattice_direction_bias import run_hex_lattice_direction_bias

if __name__ == '__main__':
    run_start = time.time()

    print("=" * 60)
    print("HEX LATTICE DIRECTION BIAS — CORRECTED GEOMETRY RUN")
    print("GPU: MLX (Apple Silicon). No CPU fallback.")
    print("12 directions × 2 phases. Progress logged per direction.")
    print("=" * 60)

    print("\n[1/3] Loading FlyWire connectome (cached)...")
    t0 = time.time()
    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()
    print(f"      Done in {time.time()-t0:.1f}s")

    print("\n[2/3] Extracting visual pathway...")
    t0 = time.time()
    visual_connectome = extract_visual_pathway(connectome)
    print(f"      Done in {time.time()-t0:.1f}s")

    print("\n[3/3] Running direction bias simulation (GPU)...\n")
    results = run_hex_lattice_direction_bias(visual_connectome)

    output_path = Path("research/vision/findings/discovery_hex_lattice_direction_bias.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    total_elapsed = time.time() - run_start
    print(f"\nResults saved to {output_path}")
    print(f"Total wall time: {total_elapsed/60:.1f} minutes")
