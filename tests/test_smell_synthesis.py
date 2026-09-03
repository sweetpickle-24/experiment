"""
Smell Synthesis Test — SmellOptimizer round-trip validation
============================================================

**Date**: 2026-03-24

Tests both modes of the new SmellOptimizer:

  1. Fast mode   — nearest-neighbour KC lookup (SmellDatabase)
  2. Gradient mode — Adam through DifferentiableSmellMapper (true autodiff)

Round-trip protocol
-------------------
For each test odorant:
  a. Look up its precomputed KC fingerprint from SmellDatabase.
  b. Feed the KC fingerprint to the optimizer as the "target".
  c. Measure whether the recovered glom_pattern matches the original.
  d. Check that top_matches includes the original odorant name.

Usage
-----
    python3 test_smell_synthesis.py                  # all tests
    python3 test_smell_synthesis.py --mode fast      # fast only
    python3 test_smell_synthesis.py --mode gradient  # gradient only
    python3 test_smell_synthesis.py --odor geraniol  # specific odorant
"""

import argparse
import sys
import time
import numpy as np
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


# ── Helpers ───────────────────────────────────────────────────────────────

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def load_components():
    """Load SmellDatabase and olfactory brain."""
    print("Loading SmellDatabase...")
    from hive.data.smell_database import SmellDatabase
    db = SmellDatabase()
    print(f"  {len(db.entries)} odorants, {len(db.kc_names)} with KC fingerprints")

    if len(db.kc_names) == 0:
        print("\n⚠  No KC fingerprints found.")
        print("   Run:  python3 scripts/batch_encode_odors.py")
        sys.exit(1)

    print("\nLoading olfactory brain...")
    from hive.substrate.connectome import Connectome
    from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
    from hive.engine.sparse_probabilistic import SparseProbabilisticBrain

    full = Connectome(data_dir="Fly Brain Female")
    full.load()
    conn  = extract_olfactory_pathway(full)
    brain = SparseProbabilisticBrain(conn, use_mlx=True, fast_mode=True)
    brain.reset(deterministic=True)
    brain.evolve(20.0)   # JIT warm-up

    return db, brain


def test_mode(optimizer, db, odorant_names, mode: str, num_steps: int = 80):
    print(f"\n{'='*70}")
    print(f"MODE: {mode.upper()}")
    print(f"{'='*70}")

    results = []

    for name in odorant_names:
        entry = db.find_by_name(name)
        if entry is None or entry.kc_pattern is None:
            print(f"  ⚠ Skipping {name!r} — no KC fingerprint")
            continue

        target_kc  = np.array(entry.kc_pattern, dtype=np.float32)
        orig_glom  = np.array(entry.glom_pattern, dtype=np.float32)

        print(f"\n── {name} ──────────────────────────────────────────────────")
        t0 = time.perf_counter()

        glom, info = optimizer.encode_smell(
            target_kc,
            mode=mode,
            num_steps=num_steps,
            verbose=(mode == "gradient"),
        )

        elapsed = time.perf_counter() - t0

        # Metrics
        glom_sim   = cosine_sim(glom, orig_glom)
        top_names  = [m["name"] for m in info.get("top_matches", [])]
        recovered  = name in top_names

        status = "✅" if glom_sim > 0.5 or recovered else "⚠"
        print(
            f"  {status}  glom_sim={glom_sim:.3f}  "
            f"loss={info['loss']:.4f}  "
            f"recovered={'YES' if recovered else 'no'}  "
            f"elapsed={elapsed:.2f}s"
        )
        if top_names:
            print(f"     top matches: {top_names[:3]}")

        results.append({
            "name":      name,
            "glom_sim":  glom_sim,
            "loss":      info["loss"],
            "recovered": recovered,
            "elapsed":   elapsed,
        })

    # Summary
    if results:
        mean_sim  = np.mean([r["glom_sim"] for r in results])
        mean_loss = np.mean([r["loss"]     for r in results])
        n_rec     = sum(r["recovered"] for r in results)
        print(f"\n── Summary ({mode}) ─────────────────────────────────────────")
        print(f"  Mean glom similarity : {mean_sim:.3f}")
        print(f"  Mean loss            : {mean_loss:.4f}")
        print(f"  Recovery rate        : {n_rec}/{len(results)}")
        print(f"  Total elapsed        : {sum(r['elapsed'] for r in results):.2f}s")

    return results


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Smell synthesis round-trip test")
    parser.add_argument("--mode",  default="both",
                        choices=["fast", "gradient", "both"])
    parser.add_argument("--odor",  default=None,
                        help="Test a single odorant (default: use preset list)")
    parser.add_argument("--steps", type=int, default=80,
                        help="Gradient-mode optimizer steps")
    args = parser.parse_args()

    db, brain = load_components()

    # ── Build SmellOptimizer ──────────────────────────────────────────────
    from hive.inverse.smell_optimizer import SmellOptimizer
    optimizer = SmellOptimizer(brain, smell_db=db, learning_rate=0.05)

    # ── Select odorants to test ───────────────────────────────────────────
    if args.odor:
        test_odorants = [args.odor]
    else:
        # Representative cross-family subset (must have KC fingerprints)
        candidates = [
            "benzaldehyde", "2-heptanone", "geraniol", "ethyl_acetate",
            "isoamyl_acetate", "hexanol", "linalool", "octanoic_acid",
        ]
        test_odorants = [n for n in candidates if db.find_by_name(n)
                         and db.find_by_name(n).kc_pattern is not None]
        if not test_odorants:
            # Fall back to first 5 with KC fingerprints
            test_odorants = db.kc_names[:5]
        print(f"\nTest odorants: {test_odorants}")

    # ── Run tests ─────────────────────────────────────────────────────────
    all_results = {}

    if args.mode in ("fast", "both"):
        all_results["fast"] = test_mode(optimizer, db, test_odorants, "fast")

    if args.mode in ("gradient", "both"):
        all_results["gradient"] = test_mode(
            optimizer, db, test_odorants, "gradient", num_steps=args.steps
        )

    # ── Cross-mode comparison ─────────────────────────────────────────────
    if "fast" in all_results and "gradient" in all_results:
        fast_sims = [r["glom_sim"] for r in all_results["fast"]]
        grad_sims = [r["glom_sim"] for r in all_results["gradient"]]
        print("\n── Mode comparison ──────────────────────────────────────────")
        print(f"  Fast mode mean glom_sim     : {np.mean(fast_sims):.3f}")
        print(f"  Gradient mode mean glom_sim : {np.mean(grad_sims):.3f}")
        improved = sum(g > f for g, f in zip(grad_sims, fast_sims))
        print(f"  Gradient improved over fast : {improved}/{len(fast_sims)}")

    print("\n✓ Smell synthesis test complete.")


if __name__ == "__main__":
    main()
