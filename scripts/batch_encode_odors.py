"""
Batch Odor Encoder
==================

**Date**: 2026-03-24

Encodes all odorants in the DoOR database to KC fingerprints by running
the olfactory-pathway SparseProbabilisticBrain in fast_mode (dt=0.5ms).

Runtime estimate:
  372 odorants × ~37ms/simulation ≈ 14 seconds on M4 Pro GPU.

Usage:
    python scripts/batch_encode_odors.py [--max N] [--out PATH]

Args:
    --max N   : Encode only the first N odorants (default: all).
    --out PATH: Output JSON path (default: data/digital_smell_database_full.json).
"""

import sys
import json
import time
import argparse
import numpy as np
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUT = REPO_ROOT / "data" / "digital_smell_database_full.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max", type=int, default=None, metavar="N",
                   help="Encode only first N odorants")
    p.add_argument("--out", type=str, default=str(DEFAULT_OUT), metavar="PATH",
                   help="Output JSON path")
    return p


def main():
    args = build_parser().parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("BATCH ODOR ENCODER")
    print("=" * 70)

    # ── Load olfactory connectome ──────────────────────────────────────
    print("\n[1] Loading olfactory subgraph...")
    t0 = time.perf_counter()

    from hive.substrate.connectome import Connectome
    from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
    from hive.engine.sparse_probabilistic import SparseProbabilisticBrain

    full_connectome = Connectome(data_dir=str(REPO_ROOT / "Fly Brain Female"))
    full_connectome.load()
    connectome = extract_olfactory_pathway(full_connectome)

    t_load = time.perf_counter() - t0
    print(f"  {len(connectome.neurons):,} neurons, "
          f"{len(connectome.synapses):,} synapses ({t_load:.1f}s)")

    # ── Build brain (fast_mode=True, dt=0.5ms) ─────────────────────────
    print("\n[2] Initialising brain (fast_mode=True)...")
    brain = SparseProbabilisticBrain(connectome, use_mlx=True, fast_mode=True)

    # Warmup JIT
    print("  Warming up JIT...")
    brain.reset(deterministic=True)
    brain.evolve(20.0)
    print("  JIT warm.")

    # ── Load smell database (glomerular patterns) ──────────────────────
    print("\n[3] Loading smell database...")
    from hive.data.smell_database import SmellDatabase
    db = SmellDatabase()
    db_stats = db.stats()
    print(f"  {db_stats['total_odorants']} odorants available")

    odorant_names = list(db.entries.keys())
    if args.max is not None:
        odorant_names = odorant_names[: args.max]
    print(f"  Encoding {len(odorant_names)} odorants")

    # ── Check for existing results (resume support) ────────────────────
    existing: dict[str, dict] = {}
    if out_path.exists():
        try:
            with open(out_path) as f:
                existing_list = json.load(f)
            existing = {rec["odor_name"]: rec for rec in existing_list}
            print(f"  Resuming: {len(existing)} already encoded")
        except Exception:
            existing = {}

    # ── Encode loop ────────────────────────────────────────────────────
    print("\n[4] Encoding...")
    print("-" * 70)
    print(f"  {'#':>5}  {'Odorant':<35}  {'KC active':>10}  {'Sparsity':>9}  {'Time':>6}")
    print("-" * 70)

    results: list[dict] = []
    t_total_start = time.perf_counter()
    n_skipped = 0

    for idx, name in enumerate(odorant_names):
        # Reuse already-encoded result
        if name in existing:
            results.append(existing[name])
            n_skipped += 1
            continue

        entry = db.entries[name]
        glom  = np.array(entry.glom_pattern, dtype=np.float32)

        t_start = time.perf_counter()
        brain.reset(deterministic=True)
        # Use log-scale strength (same as concentration invariance validation)
        strength = 50.0 * np.log10(1 + 10 * 1.0)   # concentration = 1.0
        brain.inject_odor(glom, strength=float(strength))
        brain.evolve(100.0)
        # normalize_kc=True applies APL WTA inhibition (biological sparsity)
        kc = brain.get_region_activity("KC", normalize_kc=True, target_sparsity=0.06)
        elapsed = (time.perf_counter() - t_start) * 1000  # ms

        kc_active   = int(np.sum(kc > 0.01))
        kc_sparsity = kc_active / len(kc)
        pn          = brain.get_region_activity("PN")

        rec = {
            "odor_name":         name,
            "family":            entry.family,
            "glomerular_pattern": glom.tolist(),
            "pn_pattern":        pn.tolist(),
            "kc_pattern":        kc.tolist(),
            "kc_active":         kc_active,
            "kc_sparsity":       float(kc_sparsity),
            "simulation_ms":     float(elapsed),
            "encoded_at":        "2026-03-24",
        }
        results.append(rec)

        if (idx + 1) % 10 == 0 or idx < 5:
            print(f"  {idx+1:>5}  {name:<35}  {kc_active:>10}  "
                  f"{kc_sparsity:>8.2%}  {elapsed:>5.0f}ms")

    t_total = time.perf_counter() - t_total_start

    # ── Save ───────────────────────────────────────────────────────────
    with open(out_path, "w") as f:
        json.dump(results, f, separators=(",", ":"))

    n_encoded = len(results) - n_skipped
    size_mb   = out_path.stat().st_size / 1024 / 1024

    print("-" * 70)
    print(f"\n✓ Done")
    print(f"  Encoded:  {n_encoded} new  |  {n_skipped} skipped (cached)")
    print(f"  Total:    {len(results)} odorants")
    print(f"  Time:     {t_total:.1f}s  ({t_total/max(1,n_encoded)*1000:.0f}ms/odor)")
    print(f"  Output:   {out_path}  ({size_mb:.1f} MB)")

    # Summary stats
    sparsities = [r["kc_sparsity"] for r in results if "kc_sparsity" in r]
    if sparsities:
        print(f"\n  KC sparsity stats:")
        print(f"    mean   = {np.mean(sparsities):.3%}")
        print(f"    median = {np.median(sparsities):.3%}")
        print(f"    min    = {np.min(sparsities):.3%}")
        print(f"    max    = {np.max(sparsities):.3%}")
        print(f"  Biological target: 1-3% — {'✓ PASS' if np.mean(sparsities) < 0.05 else '⚠ check'}")

    print("=" * 70)
    print("Done. Update SmellDatabase via db.load_kc_fingerprints() or restart server.")


if __name__ == "__main__":
    main()
