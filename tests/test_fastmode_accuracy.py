"""
Quality check: does fast_mode (dt=0.5ms) preserve biological validation results?

Compares dt=0.1ms vs dt=0.5ms on three core metrics:
  1. KC sparsity            (target: 1-3%,   Turner 2008)
  2. Concentration invariance r (target: >0.70, Turner 2008)
  3. KC pattern correlation between the two dt values (sanity check)

Pass = results are within biological noise (~5-10%) of each other.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import numpy as np
import time

print("Loading olfactory subgraph...")
from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.data.door_client import DoorClient

full_connectome = Connectome(data_dir="Fly Brain Female")
full_connectome.load()
connectome = extract_olfactory_pathway(full_connectome)
door_client = DoorClient()

ODOR        = "coffee"
STRENGTH    = 50.0
DURATION_MS = 300.0        # same as discrimination test
CONCENTRATIONS = [1.0, 2.0, 5.0, 10.0]   # for invariance check


def get_odor_pattern(odor_name):
    names = door_client.get_all_odorants()
    match = next((n for n in names if odor_name.lower() in n.lower()), names[0])
    return np.array(door_client.get_glomerular_pattern(match), dtype=np.float32)


def run_trial(brain, glom_pattern, concentration=1.0, duration=DURATION_MS):
    """Inject odor at concentration, evolve, return KC activity."""
    brain.reset(deterministic=True)
    brain.inject_odor(glom_pattern * concentration, strength=STRENGTH)
    brain.evolve(duration)
    kc = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
    return kc


def kc_sparsity(kc):
    from hive.substrate.connectome import Connectome
    total_kcs = 5279   # known count
    active = np.sum(kc > 0)
    return active / total_kcs * 100.0   # percent


print(f"\nOdor: {ODOR}  |  duration: {DURATION_MS}ms  |  concentrations: {CONCENTRATIONS}")
glom = get_odor_pattern(ODOR)

results = {}

for dt_label, fast in [("dt=0.1ms (original)", False), ("dt=0.5ms (fast_mode)", True)]:
    print(f"\n{'─'*55}")
    print(f"Running: {dt_label}")
    brain = SparseProbabilisticBrain(connectome, use_mlx=True, fast_mode=fast)

    # Warmup (triggers JIT)
    brain.reset(deterministic=True)
    brain.evolve(20.0)

    t0 = time.perf_counter()

    # ── Metric 1: KC sparsity at baseline concentration ──────────────
    kc_base = run_trial(brain, glom, concentration=1.0)
    sparsity_pct = kc_sparsity(kc_base)

    # ── Metric 2: Concentration invariance ───────────────────────────
    kc_patterns = []
    for conc in CONCENTRATIONS:
        kc = run_trial(brain, glom, concentration=conc)
        kc_patterns.append(kc)

    # Correlate each concentration against baseline (1×)
    base = kc_patterns[0]
    inv_corrs = []
    for kc in kc_patterns[1:]:
        if np.std(base) > 1e-9 and np.std(kc) > 1e-9:
            r = np.corrcoef(base, kc)[0, 1]
            inv_corrs.append(r)
    mean_inv_r = float(np.mean(inv_corrs)) if inv_corrs else 0.0

    elapsed = time.perf_counter() - t0

    results[dt_label] = {
        'sparsity_pct' : sparsity_pct,
        'inv_r'        : mean_inv_r,
        'kc_base'      : kc_base,
        'elapsed_s'    : elapsed,
    }
    print(f"  KC sparsity        : {sparsity_pct:.2f}%   (target: 1-3%)")
    print(f"  Concentration inv r: {mean_inv_r:.3f}    (target: >0.70)")
    print(f"  Elapsed            : {elapsed:.2f}s for {len(CONCENTRATIONS)} trials × {DURATION_MS}ms")

# ── Cross-dt pattern correlation ─────────────────────────────────────
kc_v1 = results["dt=0.1ms (original)"]['kc_base']
kc_v2 = results["dt=0.5ms (fast_mode)"]['kc_base']

if np.std(kc_v1) > 1e-9 and np.std(kc_v2) > 1e-9:
    cross_r = np.corrcoef(kc_v1, kc_v2)[0, 1]
else:
    cross_r = 0.0

active_v1 = np.sum(kc_v1 > 0)
active_v2 = np.sum(kc_v2 > 0)
overlap    = np.sum((kc_v1 > 0) & (kc_v2 > 0))

print("\n" + "="*55)
print("COMPARISON SUMMARY")
print("="*55)
print(f"{'Metric':<30} {'dt=0.1ms':>12} {'dt=0.5ms':>12}  {'Target':>10}")
print("-"*55)

r1 = results["dt=0.1ms (original)"]
r2 = results["dt=0.5ms (fast_mode)"]

sp1, sp2 = r1['sparsity_pct'], r2['sparsity_pct']
ri1, ri2 = r1['inv_r'],        r2['inv_r']

print(f"{'KC sparsity (%)':<30} {sp1:>12.2f} {sp2:>12.2f}  {'1–3%':>10}")
print(f"{'Conc. invariance r':<30} {ri1:>12.3f} {ri2:>12.3f}  {'>0.70':>10}")
print(f"{'Active KCs (base)':<30} {active_v1:>12} {active_v2:>12}  {'87 est.':>10}")
print(f"{'Cross-dt KC overlap':<30} {overlap:>12}  {'(of active)':>22}")
print(f"{'Cross-dt r':<30} {cross_r:>12.3f}  {'(sanity)':>22}")
print()

# ── Pass/Fail ─────────────────────────────────────────────────────────
print("PASS/FAIL")
print("-"*55)

def check(label, val, lo, hi, target_str):
    status = "✅ PASS" if lo <= val <= hi else "❌ FAIL"
    print(f"  {status}  {label}: {val:.3f}  (target: {target_str})")

check("KC sparsity  dt=0.1",  sp1/100, 0.01, 0.03, "1-3%")
check("KC sparsity  dt=0.5",  sp2/100, 0.01, 0.03, "1-3%")
check("Inv r        dt=0.1",  ri1,     0.70, 1.00, ">0.70")
check("Inv r        dt=0.5",  ri2,     0.70, 1.00, ">0.70")

diff_sp = abs(sp1 - sp2)
diff_ri = abs(ri1 - ri2)
bio_noise = 5.0    # % — biological noise threshold

print(f"\n  Δ sparsity between dt values : {diff_sp:.2f}%  ({'within' if diff_sp < bio_noise else 'EXCEEDS'} {bio_noise}% bio noise)")
print(f"  Δ inv r   between dt values : {diff_ri:.3f}   ({'within' if diff_ri < 0.05 else 'EXCEEDS'} 0.05 tolerance)")
