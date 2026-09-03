# Quick start

**Last Updated**: 2026-09-03

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
  is roughly 86× slower on the olfactory subgraph.
- Around 16 GB RAM for full-brain runs.

## Install

```bash
pip install -r requirements.txt
```

MLX installs only on Apple silicon. On other platforms the engine falls back to
NumPy automatically.

---

## Running

### Olfactory validation suite

```bash
python3 scripts/run_all_validations.py
```

Runs five olfactory benchmarks on the 10,906-neuron olfactory subgraph and writes
`results/final/all_validations_results.json`. Takes about a minute on an M4 Pro after
the connectome loads.

Three of the five benchmarks did not reproduce their biological targets in the most
recent run. That is the expected outcome, not a setup failure. See the README for
which ones and why.

The suite is currently unseeded, so consecutive runs give different numbers. Do not
treat a single run as definitive.

### Concentration invariance

```bash
python3 tests/concentration_invariance_test.py
```

Writes `results/final/concentration_invariance_results.json`. Three odors across a
100-fold concentration range.

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

**`ModuleNotFoundError`** — run `pip install -r requirements.txt` from the repository
root, not from `hive/`.

**MLX import fails** — expected on non-Apple hardware. The engine falls back to
NumPy. Expect roughly 150 seconds per 100 ms of simulated biology on the olfactory
subgraph instead of 0.17 seconds.

**Slower than you expected** — the simulation runs slower than real time on all
hardware tested. 100 ms of biology takes about 170 ms of wall clock on an M4 Pro GPU.

---

## What to expect on a first run

Loading the connectome takes 6-10 seconds. The olfactory subgraph extraction runs
once per process. A 100 ms trial then takes roughly 0.17 seconds on GPU.

Console output reports per-benchmark results as they complete, followed by a summary
listing which passed and which failed.

---

## Next

- [README.md](README.md) — what the results mean, and their limitations
- [docs/00_START_HERE.md](docs/00_START_HERE.md) — documentation index
- `results/README.md` — which artifact backs which claim
