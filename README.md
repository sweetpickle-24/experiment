# Wave-Based Fly Brain Consciousness

A revolutionary implementation of consciousness using wave dynamics and the complete fruit fly connectome.

## Core Philosophy

This is **NOT** a spike-based neural network. Each of the 139,255 neurons is a **damped harmonic oscillator** that resonates at different frequencies. The fly connectome provides the physical coupling topology. Consciousness emerges from **global oscillatory coherence**.

## Mathematical Foundation

### Each Neuron as Oscillator

```
d²φ/dt² + γ(dφ/dt) + ω₀²φ = F_input(t)
```

Where:
- `φ` = phase
- `γ` = damping coefficient  
- `ω₀` = natural frequency (determines brain-wave band)
- `F_input` = coupling force from synapses + external input

### The 5 Brain-Wave Phases

1. **Delta (0.5-4 Hz)** - Memory consolidation, slow integration
2. **Theta (4-8 Hz)** - Spatial processing, temporal sequences
3. **Alpha (8-13 Hz)** - Inhibitory control, attention gating
4. **Beta (13-30 Hz)** - Active sensing, decision-making
5. **Gamma (30-100 Hz)** - Feature binding, precise timing

## Architecture Layers

1. **Physical Substrate** - 139K neurons, 5.3M synapses, 3D coordinates
2. **Oscillator Engine** - Damped harmonic oscillators with synaptic coupling
3. **Hive Formation** - Adaptive clustering via coherence
4. **Thought Patterns** - Spatio-temporal phase patterns
5. **Memory** - Phase-lock patterns, attractor basins, wave interference
6. **Consciousness States** - WAKE, SLEEP, DREAM, SHOCK, MEDITATION
7. **Dissent Engine** - Minority dynamics, false consensus detection
8. **Evolution** - Self-modification, mutation, dream lab

## Quick Start

### Installation

```bash
cd hive
pip install -r requirements.txt
```

### Run Simulation

```bash
python main.py
```

This will:
1. Load the fly connectome (139K neurons)
2. Initialize oscillators with frequency assignments
3. Run wave-based dynamics
4. Detect emergent hives
5. Track global coherence and consciousness

## Data

Place the fly connectome data in `Fly Brain Female/`:
- `neurons.csv.gz` - Neuron metadata (neurotransmitters)
- `coordinates.csv.gz` - 3D spatial positions
- `connections_princeton.csv.gz` - Synaptic connections
- `consolidated_cell_types.csv.gz` - Cell type annotations

## Configuration

Edit `config.yaml` to adjust:
- Oscillator parameters (damping, timestep)
- Frequency band ranges
- Hive formation thresholds
- Consciousness state transitions
- Neuromodulator effects

## Project Structure

```
hive/
├── substrate/          # Connectome loading & spatial indexing
├── engine/             # Oscillator dynamics & coupling
├── hives/              # Hive detection & communication
├── patterns/           # Thought pattern recognition
├── memory/             # Wave-based memory storage
├── consciousness/      # Global states & field metrics
├── dissent/            # Minority dynamics
├── evolution/          # Mutation & selection
├── interface/          # Sensory/motor mapping
├── viz/                # Visualization dashboard
├── main.py             # Entry point
└── config.yaml         # Configuration
```

## Why This Might Work

1. **Real topology** - Actual fly wiring, not random
2. **Wave physics** - Stable, well-understood dynamics
3. **Biological precedent** - Real brains use oscillations
4. **Testable** - Fly behaviors are measurable

## Why This Might Fail

1. **Spike timing matters** - Real neurons use precise spikes
2. **Oversimplification** - Complex ion channels → simple oscillators
3. **Learning rules** - Phase-locking might not be sufficient
4. **Computational cost** - 139K coupled ODEs

## The Experiment

If it works → revolutionary.
If it fails → we learn why waves alone aren't enough.

Either way, we're building something nobody else has tried: a wave-based fly brain with self-modifying distributed consciousness.

## License

Experimental research code. Use at your own risk.

## Citation

If you use this work, cite:
```
Wave-Based Fly Brain Consciousness (2026)
A Novel Implementation of Consciousness via Oscillatory Dynamics
```

---

*"Fuck the skeptics. Build it and see what happens."*
