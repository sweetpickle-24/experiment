"""
Proper fast_mode accuracy test.

Uses the EXACT same protocol as concentration_invariance_test.py:
  - Same odors (benzaldehyde, 2-heptanone, geosmin)
  - Same concentrations (0.1, 0.5, 1.0, 5.0, 10.0)
  - Same log scaling: strength = 50 * log10(1 + 10*conc)
  - Same normalization: normalize_kc=True, target_sparsity=0.06
  - Same binary correlation metric (threshold=0.01)
  - Same 100ms duration

Runs for both dt=0.1ms (fast_mode=False) and dt=0.5ms (fast_mode=True).
Pass threshold: mean binary correlation > 0.70 (Turner 2008 benchmark).
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

# ── Exact same settings as concentration_invariance_test.py ─────────
TEST_ODORS      = ['benzaldehyde', '2-heptanone', 'geosmin']
CONCENTRATIONS  = [0.1, 0.5, 1.0, 5.0, 10.0]
DURATION_MS     = 100.0
BASE_STRENGTH   = 50.0
THRESHOLD       = 0.70   # Turner 2008 benchmark

print("Loading connectome...")
full_connectome = Connectome(data_dir="Fly Brain Female")
full_connectome.load()
connectome = extract_olfactory_pathway(full_connectome)
door_client = DoorClient()
print(f"  {connectome.neurons.__len__()} neurons, {len(connectome.synapses)} synapses\n")


def run_concentration_invariance(brain, label):
    """Run the exact validated concentration invariance protocol."""
    # Warmup (triggers JIT)
    brain.reset(deterministic=True)
    brain.evolve(20.0)

    all_binary_corrs = []
    odor_means = {}

    for odor_name in TEST_ODORS:
        glom = door_client.get_glomerular_pattern(odor_name)
        if glom is None:
            glom = np.random.rand(20) * 0.5

        patterns = {}
        for conc in CONCENTRATIONS:
            brain.reset(deterministic=True)
            scaled_strength = BASE_STRENGTH * np.log10(1 + 10 * conc)
            brain.inject_odor(glom, strength=scaled_strength)
            brain.evolve(duration=DURATION_MS)
            kc = brain.get_region_activity('KC', normalize_kc=True, target_sparsity=0.06)
            patterns[conc] = kc

        # Pairwise binary correlations (same as original test)
        odor_corrs = []
        conc_list = sorted(CONCENTRATIONS)
        for i, c1 in enumerate(conc_list):
            for c2 in conc_list[i+1:]:
                p1 = (patterns[c1] > 0.01).astype(float)
                p2 = (patterns[c2] > 0.01).astype(float)
                if np.std(p1) > 0 and np.std(p2) > 0:
                    r = np.corrcoef(p1, p2)[0, 1]
                else:
                    r = 1.0 if np.allclose(p1, p2) else 0.0
                odor_corrs.append(r)
                all_binary_corrs.append(r)

        odor_mean = np.mean(odor_corrs)
        odor_means[odor_name] = odor_mean
        status = "✅" if odor_mean > THRESHOLD else "❌"
        print(f"  {status} {odor_name:<20} r = {odor_mean:.4f}")

    mean_r = float(np.mean(all_binary_corrs))
    passed = mean_r > THRESHOLD
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n  {status}  Overall mean binary correlation: {mean_r:.4f}  (target: >{THRESHOLD})")
    return mean_r, passed


# ── Run both modes ───────────────────────────────────────────────────
results = {}
for label, fast in [("dt=0.1ms fast_mode=False (original)", False),
                    ("dt=0.5ms fast_mode=True  (fast mode)", True)]:
    print(f"\n{'='*60}")
    print(f"Configuration: {label}")
    print(f"{'='*60}")
    brain = SparseProbabilisticBrain(connectome, use_mlx=True, fast_mode=fast)
    t0 = time.perf_counter()
    mean_r, passed = run_concentration_invariance(brain, label)
    elapsed = time.perf_counter() - t0
    results[label] = {'r': mean_r, 'passed': passed, 'elapsed': elapsed}
    print(f"  Elapsed: {elapsed:.1f}s")

# ── Final comparison ─────────────────────────────────────────────────
print("\n" + "="*60)
print("FINAL COMPARISON")
print("="*60)
for label, res in results.items():
    sym = "✅ PASS" if res['passed'] else "❌ FAIL"
    print(f"  {sym}  {label}")
    print(f"         r = {res['r']:.4f}  ({res['elapsed']:.1f}s)")

r_vals = [r['r'] for r in results.values()]
if len(r_vals) == 2:
    delta = abs(r_vals[0] - r_vals[1])
    print(f"\n  Δr between modes: {delta:.4f}  ({'within tolerance' if delta < 0.05 else 'EXCEEDS tolerance'})")
