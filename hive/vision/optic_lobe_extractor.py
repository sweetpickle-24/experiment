#!/usr/bin/env python3
"""
Optic Lobe Extractor

Standalone script to extract visual pathway (~53,000 neurons) from
full FlyWire connectome and cache to JSON for fast loading.

Usage:
    python hive/vision/optic_lobe_extractor.py

Output:
    data/vision/optic_lobe/flywire_optic_lobe.json
"""

import sys
import time
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import (
    extract_visual_pathway,
    analyze_visual_connectivity
)


def main():
    """Extract optic lobe from FlyWire and save to cache."""
    print("\n" + "="*70)
    print("OPTIC LOBE EXTRACTION FROM FLYWIRE")
    print("="*70)
    
    # Step 1: Load full FlyWire brain
    print("\n[1/4] Loading full FlyWire brain...")
    start_time = time.time()
    
    full_connectome = Connectome(data_dir="Fly Brain Female")
    full_connectome.load()
    
    load_time = time.time() - start_time
    print(f"✓ Loaded in {load_time:.1f}s")
    print(f"  Total neurons: {len(full_connectome.neurons):,}")
    print(f"  Total synapses: {len(full_connectome.synapses):,}")
    
    # Step 2: Extract visual pathway
    print("\n[2/4] Extracting visual pathway...")
    extract_start = time.time()
    
    visual_connectome = extract_visual_pathway(full_connectome)
    
    extract_time = time.time() - extract_start
    print(f"✓ Extracted in {extract_time:.1f}s")
    
    # Step 3: Analyze connectivity
    print("\n[3/4] Analyzing visual connectivity...")
    analyze_visual_connectivity(visual_connectome)
    
    # Step 4: Save to cache
    print("\n[4/4] Saving to cache...")
    output_dir = Path("data/vision/optic_lobe")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "flywire_optic_lobe.json"
    save_start = time.time()
    
    visual_connectome.save(str(output_path))
    
    save_time = time.time() - save_start
    print(f"✓ Saved to {output_path} in {save_time:.1f}s")
    
    # Summary statistics
    total_time = time.time() - start_time
    
    print("\n" + "="*70)
    print("EXTRACTION COMPLETE")
    print("="*70)
    print(f"\nStatistics:")
    print(f"  Input neurons: {len(full_connectome.neurons):,}")
    print(f"  Output neurons: {len(visual_connectome.neurons):,}")
    print(f"  Reduction: {100*(1 - len(visual_connectome.neurons)/len(full_connectome.neurons)):.1f}%")
    print(f"  ")
    print(f"  Input synapses: {len(full_connectome.synapses):,}")
    print(f"  Output synapses: {len(visual_connectome.synapses):,}")
    print(f"  Reduction: {100*(1 - len(visual_connectome.synapses)/len(full_connectome.synapses)):.1f}%")
    print(f"  ")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Memory saved: ~{(len(full_connectome.neurons) - len(visual_connectome.neurons)) * 0.001:.0f} MB")
    
    print("\n✓ Optic lobe connectome ready for vision experiments")
    print("="*70)
    
    return visual_connectome


if __name__ == "__main__":
    try:
        visual_connectome = main()
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure FlyWire data is in 'Fly Brain Female/' directory")
        print("Expected files:")
        print("  - Fly Brain Female/neurons.csv.gz")
        print("  - Fly Brain Female/connections_princeton.csv.gz")
        print("  - Fly Brain Female/consolidated_cell_types.csv.gz")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
