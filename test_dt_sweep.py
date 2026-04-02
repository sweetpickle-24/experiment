"""
dt sweep: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0 ms

Measures for each dt value:
  - RT factor  (how many × faster than biological time)
  - Mean binary correlation r across 2 real odors
  - Δr vs dt=0.1ms baseline

Same protocol used in the validated concentration_invariance_test.py:
  - normalize_kc=True, target_sparsity=0.06
  - log10 concentration scaling
  - 5 concentrations × 100ms each
  - binary correlation threshold=0.01
"""
import numpy as np
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.data.door_client import DoorClient

# ── Setup ──────────────────────────────────────────────────────────────
print("Loading connectome...")
full = Connectome(data_dir="Fly Brain Female"); full.load()
conn = extract_olfactory_pathway(full)
door = DoorClient()

# Two real odors (isoamyl acetate is missing from DB so skip it)
TEST_ODORS   = ['benzaldehyde', '2-heptanone']
CONCS        = [0.1, 0.5, 1.0, 5.0, 10.0]
BIO_DURATION = 100.0  # ms

DT_VALUES = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]


def concentration_invariance_r(brain):
    """Run exact validated protocol, return mean binary correlation r."""
    all_r = []
    for odor in TEST_ODORS:
        glom = door.get_glomerular_pattern(odor)
        if glom is None:
            continue
        pats = {}
        for conc in CONCS:
            brain.reset(deterministic=True)
            s = 50.0 * np.log10(1 + 10 * conc)
            brain.inject_odor(glom, strength=s)
            brain.evolve(BIO_DURATION)
            kc = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
            pats[conc] = kc
        clist = sorted(CONCS)
        for i, c1 in enumerate(clist):
            for c2 in clist[i + 1:]:
                p1 = (pats[c1] > 0.01).astype(float)
                p2 = (pats[c2] > 0.01).astype(float)
                if np.std(p1) > 0 and np.std(p2) > 0:
                    all_r.append(np.corrcoef(p1, p2)[0, 1])
    return float(np.mean(all_r)) if all_r else 0.0


def rt_factor(brain):
    """Measure RT factor: bio_duration / wall_time."""
    brain.reset(deterministic=True)
    brain.evolve(20.0)  # warmup / JIT trigger
    brain.reset(deterministic=True)
    t0 = time.perf_counter()
    brain.evolve(BIO_DURATION)
    if brain.use_mlx:
        import mlx.core as mx; mx.eval(brain.mean_amplitude)
    wall = time.perf_counter() - t0
    return (BIO_DURATION / 1000.0) / wall


# ── Run sweep ──────────────────────────────────────────────────────────
print(f"\nSweeping dt = {DT_VALUES} ms")
print(f"Test odors: {TEST_ODORS}  |  {len(CONCS)} concentrations × {BIO_DURATION}ms\n")

results = {}
baseline_r = None

for dt_val in DT_VALUES:
    print(f"── dt = {dt_val} ms {'─'*40}")

    # Patch dt directly; fast_mode is just a convenience wrapper
    brain = SparseProbabilisticBrain(conn, use_mlx=True, fast_mode=False)
    brain.dt = dt_val
    # Recompute constants for new dt
    brain._precompute_step_constants()
    # Rebuild compiled kernel for new dt/constants
    brain._compiled_step = None
    brain._build_compiled_step()

    rt = rt_factor(brain)
    r  = concentration_invariance_r(brain)

    if baseline_r is None:
        baseline_r = r

    delta_r = abs(r - baseline_r)
    quality = "✅ same" if delta_r < 0.05 else ("⚠️  degraded" if delta_r < 0.15 else "❌ broken")

    results[dt_val] = dict(rt=rt, r=r, delta_r=delta_r, quality=quality)
    print(f"   RT factor: {rt:.2f}×  |  r = {r:.4f}  |  Δr = {delta_r:.4f}  {quality}\n")

# ── Summary table ──────────────────────────────────────────────────────
print("=" * 65)
print(f"{'dt (ms)':>8}  {'RT factor':>10}  {'inv r':>8}  {'Δr vs 0.1ms':>12}  {'Quality':>14}")
print("-" * 65)
for dt_val in DT_VALUES:
    r = results[dt_val]
    print(f"{dt_val:>8}  {r['rt']:>10.2f}×  {r['r']:>8.4f}  {r['delta_r']:>12.4f}  {r['quality']:>14}")
print("=" * 65)
print(f"\nBaseline r (dt=0.1ms): {baseline_r:.4f}")
print("Quality threshold: Δr < 0.05 = same, < 0.15 = degraded, ≥ 0.15 = broken")
