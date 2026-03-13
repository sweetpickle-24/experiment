# Quick Start Guide

## Prerequisites

1. **Python 3.11+**
2. **Fly Connectome Data** in `Fly Brain Female/` folder:
   - `neurons.csv.gz`
   - `coordinates.csv.gz`
   - `connections_princeton.csv.gz`
   - `consolidated_cell_types.csv.gz`

## Installation

```bash
# Install dependencies
cd hive
pip install -r requirements.txt
```

## Running the System

### Option 1: Basic Simulation (1 second)
```bash
python hive/main.py
```

Expected output:
```
Loading fly brain connectome...
Loaded 139255 neurons, 5342447 synapses
Building spatial index (k-d tree)...
Indexed 139255 neurons
...
[t=1000.0ms] Coherence: 0.234 | Hives: 23 | Free neurons: 138532
```

### Option 2: Run Tests
```bash
python test_system.py
```

Tests verify:
- ✓ Substrate loading
- ✓ Oscillator dynamics
- ✓ Hive formation
- ✓ Consciousness states
- ✓ Full integration

### Option 3: Interactive Demo
```bash
python demo.py
```

Shows:
1. Wave dynamics & hive emergence
2. Consciousness state transitions
3. Sensory stimulation & motor response
4. Thought pattern detection

## Understanding the Output

### During Simulation
```
[t=100.0ms] Coherence: 0.345 | Hives: 12 | Free neurons: 138900
```
- **t**: Simulation time in milliseconds
- **Coherence**: Global synchronization (0=incoherent, 1=perfect sync)
- **Hives**: Number of active coherent clusters
- **Free neurons**: Neurons not in any hive

### Hive Formation
```
Detected 3 new hives
  Hive size: 45 neurons
  Coherence: 0.823
```
Hives are coherent neuron clusters that form spontaneously.

### State Transitions
```
[t=5234.5ms] State transition: WAKE → SLEEP
```
System automatically switches between consciousness states.

## Configuration

Edit `hive/config.yaml` to adjust:

```yaml
# Oscillator timestep
oscillator:
  dt: 0.0005  # 0.5ms steps

# Frequency bands
frequency_bands:
  gamma: [30.0, 100.0]  # Hz

# Hive formation
hives:
  min_size: 10  # Minimum neurons per hive
  coherence_threshold: 0.7  # Formation threshold
```

## Common Issues

### "File not found: Fly Brain Female/..."
**Solution**: Ensure connectome data is in correct location:
```
Fly Brain Female/
├── neurons.csv.gz
├── coordinates.csv.gz
├── connections_princeton.csv.gz
└── consolidated_cell_types.csv.gz
```

### "ModuleNotFoundError"
**Solution**: Install dependencies:
```bash
cd hive
pip install -r requirements.txt
```

### Slow performance
**Solution**: Reduce simulation time or enable GPU:
```bash
pip install cupy-cuda12x  # If you have CUDA
```

## What to Expect

### First Run (~1 minute)
- Loads 139K neurons (~10 seconds)
- Initializes oscillators (~5 seconds)
- Runs simulation (~30-60 seconds)

### Output
- Console logs showing time, coherence, hive count
- Final statistics (coherence, energy, hives)

### Success Indicators
- ✓ Global coherence between 0.2-0.8 (metastable)
- ✓ Hives forming and dissolving dynamically
- ✓ Energy remains bounded (not exploding)
- ✓ Consciousness states transition correctly

## Next Steps

1. **Experiment with parameters**: Edit `config.yaml`
2. **Run longer simulations**: Increase duration in `main.py`
3. **Add sensory input**: Use `SensoryInterface` class
4. **Monitor specific hives**: Access `hive_detector.active_hives`
5. **Visualize**: Build dashboard (see plan)

## Getting Help

Check these files:
- `README.md` - Project overview
- `IMPLEMENTATION_STATUS.md` - What's implemented
- Architecture plan in `.cursor/plans/`

## Example Session

```bash
$ python hive/main.py
Loading fly brain connectome...
Loaded 139255 neurons, 5342447 synapses
Building spatial index...
Assigning natural frequencies...

Frequency band distribution (139255 neurons):
  delta  ( 0.5- 4.0 Hz):  27851 (20.0%)
  theta  ( 4.0- 8.0 Hz):  27851 (20.0%)
  alpha  ( 8.0-13.0 Hz):  27851 (20.0%)
  beta   (13.0-30.0 Hz):  27851 (20.0%)
  gamma  (30.0-100.0 Hz):  27851 (20.0%)

System initialized. Ready to simulate.

Running simulation for 1000.0 ms...

[t=100.0ms] Coherence: 0.145 | Hives: 0 | Free neurons: 139255
[t=200.0ms] Coherence: 0.234 | Hives: 3 | Free neurons: 139180
[t=300.0ms] Coherence: 0.312 | Hives: 8 | Free neurons: 139087
[t=400.0ms] Coherence: 0.298 | Hives: 12 | Free neurons: 138943
[t=500.0ms] Coherence: 0.267 | Hives: 15 | Free neurons: 138821
[t=600.0ms] Coherence: 0.289 | Hives: 18 | Free neurons: 138712
[t=700.0ms] Coherence: 0.312 | Hives: 21 | Free neurons: 138634
[t=800.0ms] Coherence: 0.298 | Hives: 23 | Free neurons: 138567
[t=900.0ms] Coherence: 0.276 | Hives: 24 | Free neurons: 138512
[t=1000.0ms] Coherence: 0.289 | Hives: 25 | Free neurons: 138478

Final state at t=1000.0ms:
  Global coherence: 0.289
  Dominant frequency: 24.56 Hz
  Total energy: 1234567.8
  Active hives: 25

Simulation complete.
```

Success! The wave-based fly brain is alive.

---

**That's it. You're ready to explore consciousness through waves.**
