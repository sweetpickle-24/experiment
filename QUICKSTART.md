# Quick start

**Last Updated**: 2026-09-05

Setup and first run. Read the [README](README.md) first for what the results mean
and what they do not.

---

## Prerequisites

- **Python 3.11 or newer** (developed on 3.14.3)
- **Connectome data** in `Fly Brain Female/`, not distributed with this repository:
  - `neurons.csv.gz`
  - `coordinates.csv.gz`
  - `connections_princeton.csv.gz`
  - `consolidated_cell_types.csv.gz`
- **Apple silicon** for GPU acceleration via MLX. The CPU path works everywhere but
  is 10.00× slower on the olfactory subgraph
  (`results/final/cpu_vs_mlx_speedup.json`; the older 86× figure is discarded).
- Around 16 GB RAM for full-brain runs.

## Install

```bash
pip install -r requirements.txt
```

MLX installs only on Apple silicon. On other platforms the engine falls back to
NumPy automatically.

## Which interpreter

**Use `.venv/bin/python` for anything whose numbers you intend to quote.**

The current receptor-to-glomerular projection is `projection='glomerular'`, the
published one-to-one map. The two PCA-style projections remain selectable, and one of
them requires scikit-learn. The repository contains two virtualenvs and only `.venv`
has it:

```bash
.venv/bin/python -c "import sklearn, mlx.core"   # succeeds
python3        -c "import sklearn"               # ModuleNotFoundError
```

`validation_utils.assert_reportable_environment` now checks this before the
connectome load and names the interpreter in the error, instead of failing several
seconds later inside `DoorClient`. Do not work around it by switching to
`projection='uncentered_svd'`: that is a different projection and produces different
glomerular patterns.

---

## Running

### Olfactory validation suite

The five scored benchmarks are separate modules, each writing its own result file
with its own configuration block, aggregated afterwards.

**The engine defaults are deliberately the old pipeline**, so that results recorded
before 2026-09-05 stay reproducible. A bare run therefore reproduces the **2/5**
baseline, not the current 5/5. Three environment variables select the input pipeline;
see `benchmark_harness.stimulus_path_config`.

```bash
# The current configuration: 5/5
export FLYBRAIN_PROJECTION=glomerular
export FLYBRAIN_GLOM_MAPPING=glomerulus
export FLYBRAIN_STRICT=1

for b in temporal mixtures discrimination similarity; do
  .venv/bin/python -m benchmarks_repaired.$b --output ${b}_G2.json
done
.venv/bin/python -m benchmarks_repaired.learning --cpu --output learning_G2.json
.venv/bin/python -m benchmarks_repaired.concentration_invariance \
    --output concentration_invariance_G2.json
.venv/bin/python scripts/run_repaired_suite.py --suffix G2 \
    --output all_validations_G2.json
```

Or in one command, which does exactly the above:

```bash
.venv/bin/python scripts/run_glomerular_ladder.py --rung G2
```

Unset those variables to reproduce the 2/5 baseline. Expect a few hours on CPU per
configuration; the learning benchmark and its learning-rate sweep dominate. Each
result file records which pipeline actually ran, so a file cannot misreport itself.

`scripts/run_all_validations.py` still exists and runs the **pre-audit** suite. It is
kept only so the superseded numbers stay reproducible; its targets are the
misattributed ones. Before reading anything it produces, see
[docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md](docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md),
which records per benchmark whether the cited paper contains the target it was scored
against. Four of six did not, and one citation does not exist.

### Comparing input pipelines

```bash
.venv/bin/python tests/diagnose_glomerular_projection.py     # seconds, no simulation
.venv/bin/python scripts/run_glomerular_ladder.py --rung G1
.venv/bin/python scripts/run_glomerular_ladder.py --compare
```

The diagnostic compares three receptor-to-channel projections directly and needs no
simulation. The ladder re-runs the whole suite under a different input pipeline; see
[docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md](docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md).

### Regenerating the odorant fingerprint database

```bash
.venv/bin/python scripts/batch_encode_odors.py
```

Encodes all 372 DoOR odorants to Kenyon cell fingerprints, about 22 minutes on CPU.
The artifact carries its own configuration block, and the encoder refuses to resume
from a file produced under a different pipeline.

The suite is seeded (`SEED = 42`) and both backends are reproducible bit-for-bit at
a fixed seed. Note that with `reset(deterministic=True)` the seed has no effect at
all: the trajectory carries no randomness, so repeats are bit-identical and cannot
be averaged for power. Benchmarks that need trial-to-trial variability use
`reset(deterministic=False)` with an explicitly declared seed list.

### Concentration invariance

```bash
.venv/bin/python -m benchmarks_repaired.concentration_invariance
```

Five odorants across a 100-fold concentration range. Reported but **not scored**: the
0.70 target it used to be compared against is not in Turner et al. 2008, and the
other quantity that paper measures is pinned to a constant by this model's readout.

The older `tests/concentration_invariance_test.py` runs the pre-audit version.

### Cross-language benchmarks

```bash
python3 benchmarks/real_connectome/export_connectome.py    # once, exports binaries
python3 benchmarks/real_connectome/python_mlx_benchmark.py
```

Rust and Julia equivalents live alongside. Note that the two benchmark families use
opposite conventions: `rt_factor` is biology over wall clock, `realtime_ratio` is
wall clock over biology.

### Interactive demo

```bash
python3 scripts/demo.py
```

---

## Configuration

Physics parameters are set in the engine constructor, not in a config file:

```python
# hive/engine/sparse_probabilistic.py
self.dt = 0.5 if fast_mode else 0.1   # ms
self.gamma = 0.1
```

`fast_mode=True` uses a 0.5 ms timestep for roughly 5× fewer integration steps. It is
intended for interactive use and is not used in any validation run. The accuracy cost
has been measured informally but never written to a file, so treat it as
uncharacterised.

Timesteps above about 2 ms are numerically unstable for the APL feedback loop under
forward Euler.

`hive/config.yaml` configures the older standalone `hive/main.py` simulation, which
is separate from the validation path.

---

## Common problems

**`File not found: Fly Brain Female/...`** — the connectome data is not in the
repository. Place the four `.csv.gz` files in `Fly Brain Female/` at the repository
root.

**`RuntimeError: scikit-learn is not importable under ...`** — you are on the wrong
interpreter. Use `.venv/bin/python`. See "Which interpreter" above.

**`ModuleNotFoundError`** — run `pip install -r requirements.txt` from the repository
root, not from `hive/`.

**MLX import fails** — expected on non-Apple hardware. The engine falls back to
NumPy. Expect 4.87 seconds per 100 ms of simulated biology on the olfactory subgraph
instead of 0.49 seconds (`results/final/cpu_vs_mlx_speedup.json`).

**Slower than you expected** — the simulation runs slower than real time on all
hardware tested. 100 ms of biology takes 0.49 s of wall clock on an M4 Pro GPU
(0.205× real time) and 4.87 s on CPU (0.0205×).

---

## What to expect on a first run

Loading the connectome and building the engine takes about 8 seconds. The olfactory
subgraph extraction runs once per process. A 100 ms trial then takes 0.49 seconds on
GPU, 4.87 seconds on CPU.

Console output reports per-benchmark results as they complete, followed by a summary
listing which passed and which failed. On the default configuration all five pass;
read [docs/03_validation/LIMITATIONS.md](docs/03_validation/LIMITATIONS.md) for what
that does and does not establish.

---

## Next

- [README.md](README.md) — what the project is and what the results are
- [ARCHITECTURE.md](ARCHITECTURE.md) — how the system is built, stage by stage
- [docs/03_validation/LIMITATIONS.md](docs/03_validation/LIMITATIONS.md) — what the
  numbers cannot support
- [docs/00_START_HERE.md](docs/00_START_HERE.md) — documentation index
- `results/README.md` — which artifact backs which claim
