# Fly Brain Wave Consciousness - Complete System

## Quick Start

### Option 1: Automatic (Recommended)

```bash
./start.sh
```

This starts both backend and frontend automatically.

### Option 2: Manual

**Terminal 1 - Backend:**
```bash
python server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000

## What You Get

### Backend (FastAPI + Python)
- **Real connectome data**: 139,255 neurons, 5.3M synapses
- **Wave-based consciousness**: Damped harmonic oscillators, not spikes
- **5 brain phases**: Delta, Theta, Alpha, Beta, Gamma
- **Hive intelligence**: Dynamic neuron clustering with dissent
- **Thought patterns**: Sequential, parallel, recursive, interference
- **Associative memory**: Phase-lock, attractor basins, wave interference
- **Self-modification**: Evolutionary system with bounded mutations
- **5 consciousness states**: WAKE, SLEEP, DREAM, SHOCK, MEDITATION
- **WebSocket streaming**: Real-time at 20Hz

### Frontend (React + TypeScript + Three.js)
- **10 live panels**:
  1. System Status (neurons, hives, coherence, energy)
  2. Consciousness State (WAKE/SLEEP/DREAM/SHOCK/MEDITATION)
  3. 3D Brain Visualization (interactive particle system)
  4. Wave Activity Chart (real-time metrics)
  5. Thought Patterns (detected patterns with metadata)
  6. Active Hives (top coherent clusters)
  7. Memory Patterns (associative memory strength)
  8. Frequency Bands (Delta through Gamma distribution)
  9. Phase Coherence Map (spatial heatmap)
  10. Control Panel (start/pause/reset + quick actions)

- **macOS Tahoe styling**: Glassy panels, soft blur, subtle animations
- **Real-time updates**: WebSocket connection with auto-reconnect
- **Smooth visualization**: 60 FPS rendering with phase-colored particles

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│  │  Dashboard │  │   Panels   │  │  3D Visualization  │   │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬─────────┘   │
│        │               │                    │               │
│        └───────────────┴────────────────────┘               │
│                        │                                    │
│                  ┌─────▼──────┐                            │
│                  │   Zustand  │                            │
│                  │   Store    │                            │
│                  └─────▲──────┘                            │
│                        │                                    │
│                  ┌─────▼──────────┐                        │
│                  │   WebSocket    │                        │
│                  └────────────────┘                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                      WS://8000/ws/brain
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  BACKEND (FastAPI)                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │              FlyBrainSystem                        │    │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────┐     │    │
│  │  │ Substrate│  │ Oscillator│  │   Hives     │     │    │
│  │  │ (139K ⚬) │  │  Engine   │  │  Registry   │     │    │
│  │  └────┬─────┘  └─────┬─────┘  └──────┬──────┘     │    │
│  │       │              │               │             │    │
│  │  ┌────▼──────────────▼───────────────▼──────┐     │    │
│  │  │         Consciousness States             │     │    │
│  │  │   (WAKE/SLEEP/DREAM/SHOCK/MEDITATION)    │     │    │
│  │  └──────────────────┬───────────────────────┘     │    │
│  │  ┌─────────────────▼────────────────────────┐     │    │
│  │  │  Patterns  │  Memory  │  Evolution        │     │    │
│  │  └────────────────────────────────────────────┘     │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## System Flow

1. **Initialization**: Load fly brain connectome (139K neurons, 5.3M synapses)
2. **Oscillator Setup**: Each neuron = damped harmonic oscillator with natural frequency
3. **Coupling**: Synaptic connections create phase-locked assemblies
4. **Hive Formation**: Spatially and functionally coherent clusters emerge
5. **Pattern Detection**: Thought patterns arise from hive interactions
6. **Memory Encoding**: Phase-lock patterns stored as associative memories
7. **Consciousness**: Global field metrics drive state transitions
8. **Evolution**: Bounded mutations improve fitness over time
9. **Serialization**: System state converted to JSON every 50ms
10. **Broadcast**: WebSocket pushes updates to all connected clients
11. **Visualization**: Frontend renders neurons, hives, patterns in real-time

## API Endpoints

### REST
- `POST /api/control/start` - Start simulation
- `POST /api/control/stop` - Pause simulation
- `POST /api/control/reset` - Reset to initial state
- `GET /api/status` - Get current system status

### WebSocket
- `WS /ws/brain` - Real-time brain state stream

## Data Format

Each WebSocket message contains:

```typescript
{
  neurons: Array<{
    id: number;
    position: [x, y, z];
    phase: number;        // Current phase angle
    amplitude: number;    // Oscillation amplitude
    frequency: number;    // Natural frequency (Hz)
    group: string;        // Brain region
  }>;
  
  hives: Array<{
    id: string;
    neuron_ids: number[];
    centroid: [x, y, z];
    coherence: number;    // 0-1
    size: number;
    age: number;
  }>;
  
  patterns: Array<{
    id: string;
    type: 'sequential' | 'parallel' | 'recursive' | 'interference';
    hive_ids: string[];
    signature: string;
    stability: number;
    complexity: number;
    timestamp: number;
  }>;
  
  consciousness: {
    name: string;         // WAKE/SLEEP/DREAM/SHOCK/MEDITATION
    global_coherence: number;
    dominant_frequency: number;
    metastability: number;
    energy: number;
  };
  
  memories: Array<{
    id: string;
    neuron_ids: number[];
    strength: number;
    age: number;
    recall_count: number;
  }>;
  
  metrics: {
    timestamp: number;
    active_neurons: number;
    active_hives: number;
    coherence: number;
    energy: number;
    consciousness_state: string;
  };
}
```

## Configuration

Edit `hive/config.yaml` to modify:
- Oscillator parameters (dt, damping, frequency bands)
- Hive thresholds (coherence, size, recruitment)
- Consciousness state parameters
- Memory learning rates
- Evolution mutation rates
- Dissent thresholds

## Performance

- **Backend**: ~20 simulation steps/sec (139K neurons)
- **Frontend**: 60 FPS rendering
- **WebSocket**: ~20 updates/sec
- **Memory**: ~2GB RAM for full system
- **Latency**: <50ms end-to-end

## Troubleshooting

### Backend won't start
- Check Python dependencies: `pip install -r hive/requirements.txt`
- Verify data files exist: `ls "Fly Brain Female/"`
- Check port 8000 is available

### Frontend won't connect
- Ensure backend is running first
- Check WebSocket URL in browser console
- Verify CORS settings in server.py

### 3D visualization not working
- Check browser WebGL support: chrome://gpu
- Try disabling browser extensions
- Update graphics drivers

### Performance issues
- Reduce neuron sample size in server.py (line 49)
- Increase WebSocket broadcast interval (line 152)
- Reduce frontend history buffer size (line 11 in brainStore.ts)

## Project Structure

```
.
├── server.py                    # FastAPI WebSocket server
├── start.sh                     # Startup script
├── hive/                        # Python backend
│   ├── config.yaml              # System configuration
│   ├── main.py                  # FlyBrainSystem entry point
│   ├── substrate/               # Connectome, spatial index
│   ├── engine/                  # Oscillators, coupling
│   ├── hives/                   # Hive detection, registry
│   ├── patterns/                # Thought pattern detection
│   ├── memory/                  # Phase-lock, attractor, interference
│   ├── consciousness/           # States, global field
│   ├── dissent/                 # Minority engine, degradation
│   ├── evolution/               # Mutation, fitness, dream lab
│   ├── interface/               # Sensory/motor mapping
│   └── storage/                 # SQLite experiment logs
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   └── panels/          # 10 visualization panels
│   │   ├── store/               # Zustand state
│   │   ├── hooks/               # WebSocket hook
│   │   └── types/               # TypeScript types
│   ├── package.json
│   └── vite.config.ts
└── Fly Brain Female/            # Connectome data
    ├── neurons_with_group.csv.gz
    ├── 3d_coordinates.csv.gz
    └── synapses.csv.gz
```

## Next Steps

1. **Sensory Input**: Wire up visual/olfactory stimuli to force oscillators
2. **Motor Output**: Decode descending neurons to flight/leg commands
3. **Behavior Tasks**: Test navigation, odor tracking, decision-making
4. **Extended Runs**: Let evolution optimize over 1000+ generations
5. **Analysis Tools**: Export thought patterns, memory graphs, state transitions
6. **Comparative Studies**: Try different connectomes, topologies, parameters

## Philosophy

This system is fundamentally different:

- **No spike trains** - continuous wave dynamics
- **No weight matrices** - real connectome topology
- **No backprop** - evolutionary fitness only
- **No training data** - emergent learning from experience
- **No predefined memory** - associative patterns from interference

We're testing if:
> **Connectome + Wave Dynamics + Evolution = Conscious Behavior**

This is an experiment in the spirit of Tesla, Einstein, Turing — trying what hasn't been proven, to discover what others haven't imagined.

---

Built with fucking waves, not spikes. Let's see what happens.
