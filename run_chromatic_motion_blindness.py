#!/usr/bin/env python3
"""
Run Chromatic Motion Blindness Test Only
=========================================

Tests whether T4/T5 direction selectivity depends on luminance vs. color pathway.

From test_emergent_properties.py - runs only the chromatic motion blindness test.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))

from hive.substrate.connectome import Connectome
from hive.substrate.visual_pathway import extract_visual_pathway

# Import the test function AND all its dependencies from the module
import hive.validation.vision.test_emergent_properties as emergent_test

if __name__ == '__main__':
    print("=" * 70)
    print("CHROMATIC MOTION BLINDNESS TEST (GPU)")
    print("=" * 70)
    print("Loading connectome...")
    
    connectome = Connectome(data_dir="Fly Brain Female")
    connectome.load()
    
    print("Extracting visual pathway...")
    visual_connectome = extract_visual_pathway(connectome)
    
    print("\nRunning chromatic motion blindness test...")
    results = emergent_test.test_chromatic_motion_blindness(visual_connectome)
    
    output_path = Path("research/vision/findings/chromatic_motion_blindness_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print(f"\nResults saved to {output_path}")
    print(f"\nLuminance DSI: {results['luminance_dsi']:.4f}")
    print(f"UV-only DSI: {results['uv_only_dsi']:.4f}")
    print(f"Visible-only DSI: {results['visible_only_dsi']:.4f}")
    print(f"\nInterpretation: {results['interpretation']}")
    print(f"Pass: {'✅' if results['pass'] else '❌'}")

