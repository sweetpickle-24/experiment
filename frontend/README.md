# Fly Brain Wave Consciousness - Frontend

Real-time visualization dashboard for the wave-based fly brain consciousness system.

## Features

### 10 Live Dashboard Panels

1. **System Status** - Active neurons, hives, coherence, energy
2. **Consciousness State** - Current state (WAKE/SLEEP/DREAM/SHOCK/MEDITATION) with metrics
3. **3D Brain Visualization** - Interactive Three.js rendering of neurons and hives with phase-colored particles
4. **Wave Activity Chart** - Real-time line charts for coherence, frequency, and energy over time
5. **Thought Patterns** - Sequential, parallel, recursive, and interference patterns
6. **Active Hives** - Top hives sorted by coherence with size and age
7. **Memory Patterns** - Stored memories with strength, age, and recall counts
8. **Frequency Bands** - Distribution across Delta, Theta, Alpha, Beta, Gamma bands
9. **Phase Coherence Map** - 2D heatmap showing spatial activity patterns
10. **Control Panel** - Start/pause/reset simulation with system controls

## Tech Stack

- **React 18** - UI framework
- **TypeScript 5** - Type safety
- **Vite** - Build tool
- **Zustand** - State management
- **Recharts** - Charts
- **Three.js + React Three Fiber** - 3D visualization
- **Tailwind CSS** - Styling (macOS Tahoe style)

## Installation

```bash
cd frontend
npm install
```

## Running

Start the backend first:

```bash
cd ..
python server.py
```

Then start the frontend:

```bash
npm run dev
```

Open http://localhost:3000

## Architecture

### WebSocket Connection

- Connects to `ws://localhost:8000/ws/brain`
- Auto-reconnects on disconnect
- Receives real-time snapshots every 50ms

### Data Flow

1. FastAPI server serializes brain state
2. WebSocket broadcasts to all connected clients
3. Zustand store updates with new snapshot
4. React components re-render with fresh data
5. History buffer maintains last 100 snapshots for charts

### Styling

Following macOS "Tahoe" design guidelines:

- Clean, minimal, soft, glassy panels
- Subtle blur and translucency
- 18px border radius
- Soft shadows and borders
- System font stack
- Accent color: #0A84FF
- Smooth animations (180ms cubic-bezier)

## Key Files

- `src/types/brain.ts` - TypeScript types for brain data
- `src/store/brainStore.ts` - Zustand state management
- `src/hooks/useWebSocket.ts` - WebSocket connection hook
- `src/components/Dashboard.tsx` - Main dashboard layout
- `src/components/panels/*.tsx` - Individual panel components
- `tailwind.config.js` - Tahoe color theme
- `vite.config.ts` - Proxy config for API/WebSocket

## Development

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Features in Detail

### 3D Brain Visualization

- **Particle System**: Each neuron rendered as colored point
- **Phase Coloring**: HSL color based on oscillator phase angle
- **Amplitude Sizing**: Point size based on amplitude
- **Hive Spheres**: Wireframe spheres showing hive boundaries
- **Orbit Controls**: Drag to rotate, scroll to zoom
- **Real-time Updates**: Colors update every frame based on phase

### Wave Activity Chart

- **3 Metrics**: Coherence %, Frequency Hz, Energy
- **Rolling Window**: Last 50 snapshots
- **Smooth Lines**: No dots, clean visualization
- **Custom Tooltip**: Dark theme matching Tahoe style
- **Legend**: Color-coded metric labels

### Thought Patterns Panel

- **Pattern Types**: Sequential (→), Parallel (⫙), Recursive (↻), Interference (~)
- **Metadata**: Hives involved, stability %, complexity score
- **Signature**: Hash preview for pattern identification
- **Timestamp**: When pattern was detected
- **Auto-scroll**: Shows 8 most recent patterns

### Control Panel

- **Start/Pause/Reset**: Control simulation state
- **Connection Status**: Live indicator
- **Simulation Time**: Elapsed time in seconds
- **Quick Actions**: Inject stimulus, force state, save snapshot, export data (placeholders)

## Browser Support

Modern browsers with WebSocket and WebGL support:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
