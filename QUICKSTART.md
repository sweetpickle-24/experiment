# Quick start

**Last Updated**: 2026-09-04

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

The documented receptor-to-glomerular projection is `projection='sklearn_pca'`, and
it requires scikit-learn. The repository contains two virtualenvs and only `.venv`
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

```bash
.venv/bin/python scripts/run_all_validations.py
```

Runs five olfactory benchmarks on the 10,906-neuron olfactory subgraph and writes
`results/final/all_validations_results.json`. A few minutes on an M4 Pro after the
connectome loads.

Most of the five benchmarks do not reproduce their biological targets. That is the
expected outcome, not a setup failure. Before reading any of them, read
[docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md](docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md),
which records, per benchmark, whether the cited paper contains the target it is
scored against. Three did not, and one citation does not exist.

The suite is seeded (`SEED = 42`) and both backends are reproducible bit-for-bit at
a fixed seed. Note that with `reset(deterministic=True)` the seed has no effect at
all: the trajectory carries no randomness, so repeats are bit-identical and cannot
be averaged for power. Benchmarks that need trial-to-trial variability use
`reset(deterministic=False)` with an explicitly declared seed list.

### Concentration invariance

```bash
.venv/bin/python tests/concentration_invariance_test.py
```

Writes `results/final/concentration_invariance_results.json`. Three odors across a
100-fold concentration range. The 0.70 target this test is scored against is not in
Turner et al. 2008; see the validity audit.

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
listing which passed and which failed.

---

## Next

- [README.md](README.md) — what the results mean, and their limitations
- [docs/00_START_HERE.md](docs/00_START_HERE.md) — documentation index
- `results/README.md` — which artifact backs which claim
