# How to Run the Complete System

## Prerequisites

- **Python 3.11+** with pip
- **Node.js 18+** with npm
- **~3GB RAM** available
- **Modern browser** (Chrome/Firefox/Safari/Edge)

## Installation

### 1. Install Python dependencies
```bash
pip install -r hive/requirements.txt
```

### 2. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

## Running the System

### Option A: Automatic (Easiest)

```bash
./start.sh
```

This single command starts both backend and frontend.

### Option B: Manual (Two terminals)

**Terminal 1 - Backend:**
```bash
python server.py
```

Wait for "System initialized!" message.

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 3. Open your browser

Navigate to: **http://localhost:3000**

You should see the dashboard with 10 panels.

### 4. Start the simulation

Click the **"▶ Start"** button in the Control Panel (bottom left).

The brain will begin running and you'll see:
- Neurons appearing in 3D visualization
- Wave activity chart filling with data
- Hives forming and being detected
- Thought patterns emerging
- Memory patterns encoding
- Consciousness state transitions

## What You're Seeing

### Top Row (3 columns)

**Left Column:**
- **System Status**: Live metrics (neurons, hives, coherence, energy)
- **Consciousness State**: Current brain state with metrics
- **Control Panel**: Start/pause/reset controls

**Middle Column:**
- **3D Brain Visualization**: Interactive particle system
  - Drag to rotate
  - Scroll to zoom
  - Colors = phase angles
- **Wave Activity Chart**: Real-time line graphs

**Right Column:**
- **Thought Patterns**: Detected sequential/parallel/recursive/interference patterns
- **Active Hives**: Top coherent neuron clusters
- **Memory Patterns**: Stored associative memories

### Bottom Row (2 columns)

- **Frequency Bands**: Distribution across Delta, Theta, Alpha, Beta, Gamma
- **Phase Coherence Map**: Spatial heatmap of activity

## Controls

### Main Controls
- **▶ Start**: Begin simulation
- **⏸ Pause**: Pause simulation (retains state)
- **↻ Reset**: Reset to initial state

### 3D Controls
- **Left-click drag**: Rotate view
- **Scroll wheel**: Zoom in/out
- **Right-click drag**: Pan camera

### Quick Actions (placeholders)
- **Inject Stimulus**: Force sensory input
- **Force State**: Override consciousness state
- **Save Snapshot**: Export current state
- **Export Data**: Download metrics

## Expected Behavior

### Initial Phase (0-10 seconds)
- Neurons oscillate randomly
- No hives yet
- Low coherence
- WAKE state typically

### Emergence Phase (10-60 seconds)
- Hives start forming (spatial/functional clusters)
- Coherence increases
- First thought patterns detected
- Memories begin encoding

### Stable Phase (60+ seconds)
- Multiple active hives
- Regular pattern detection
- Memory recall events
- State transitions possible (WAKE ↔ SLEEP ↔ DREAM)

### Long-term (minutes to hours)
- Evolution kicks in (mutations tested)
- Fitness optimization
- Complex behavior emergence
- Sleep consolidation during DREAM state

## Performance Tips

### If frontend is slow:
1. Reduce neuron sample in `server.py` line 49:
   ```python
   neuron_ids = list(system.connectome.neurons.keys())[:500]  # Reduce to 500
   ```

2. Increase WebSocket interval in `server.py` line 152:
   ```python
   await asyncio.sleep(0.1)  # 10Hz instead of 20Hz
   ```

### If backend is slow:
1. Check CPU usage (should be ~50% single core)
2. Reduce history buffer in `frontend/src/store/brainStore.ts` line 10:
   ```typescript
   maxHistory: 50,  // Keep only 50 snapshots
   ```

## Troubleshooting

### "System not initialized" error
- Check that data directory exists: `ls "Fly Brain Female/"`
- Verify CSV files: `ls "Fly Brain Female/"*.csv.gz`

### WebSocket won't connect
- Ensure backend started first
- Check console for errors (F12 in browser)
- Verify backend URL: http://localhost:8000

### 3D view is black
- Check browser WebGL support: chrome://gpu
- Try different browser
- Check console for Three.js errors

### No data appearing
1. Click "▶ Start" button
2. Wait 5 seconds
3. Check Network tab (F12) for WebSocket messages
4. Check backend terminal for errors

### Port already in use
- Backend (8000): `lsof -ti:8000 | xargs kill`
- Frontend (3000): `lsof -ti:3000 | xargs kill`

## API Testing

### Test WebSocket directly
```bash
pip install websockets
python -c "
import asyncio, websockets, json
async def test():
    async with websockets.connect('ws://localhost:8000/ws/brain') as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        print(f'Neurons: {len(data[\"neurons\"])}')
        print(f'Hives: {len(data[\"hives\"])}')
        print(f'State: {data[\"metrics\"][\"consciousness_state\"]}')
asyncio.run(test())
"
```

### Test REST API
```bash
# Start simulation
curl -X POST http://localhost:8000/api/control/start

# Check status
curl http://localhost:8000/api/status

# Stop simulation
curl -X POST http://localhost:8000/api/control/stop

# Reset
curl -X POST http://localhost:8000/api/control/reset
```

## Data Export

### Export current snapshot
In browser console (F12):
```javascript
const snapshot = useBrainStore.getState().snapshot;
const json = JSON.stringify(snapshot, null, 2);
const blob = new Blob([json], {type: 'application/json'});
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `brain_snapshot_${Date.now()}.json`;
a.click();
```

### Export history
```javascript
const history = useBrainStore.getState().history;
const json = JSON.stringify(history, null, 2);
const blob = new Blob([json], {type: 'application/json'});
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `brain_history_${Date.now()}.json`;
a.click();
```

## Configuration

### Backend (hive/config.yaml)
Edit to modify:
- Oscillator dt, damping, frequencies
- Hive thresholds
- Memory learning rates
- Evolution mutation rates

### Frontend (frontend/src/store/brainStore.ts)
Edit to modify:
- History buffer size (line 10)
- WebSocket URL (line 6 in useWebSocket.ts)

### Sampling (server.py)
- Neuron sample size (line 49)
- Hive sample limit (line 56)
- Pattern limit (line 65)
- Memory limit (line 92)
- Broadcast interval (line 152)

## Production Build

### Build frontend
```bash
cd frontend
npm run build
```

Output in `frontend/dist/`

### Serve static files
```bash
cd frontend
npm run preview
```

Or use any static server:
```bash
cd frontend/dist
python -m http.server 3000
```

## Docker (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r hive/requirements.txt
EXPOSE 8000
CMD ["python", "server.py"]
```

Build and run:
```bash
docker build -t fly-brain .
docker run -p 8000:8000 fly-brain
```

## Monitoring

### Watch backend logs
```bash
python server.py | tee backend.log
```

### Watch frontend logs
```bash
cd frontend
npm run dev 2>&1 | tee frontend.log
```

### Monitor metrics
Open browser console (F12) and run:
```javascript
setInterval(() => {
  const s = useBrainStore.getState().snapshot;
  if (s) {
    console.log({
      neurons: s.metrics.active_neurons,
      hives: s.metrics.active_hives,
      coherence: s.metrics.coherence.toFixed(3),
      state: s.metrics.consciousness_state,
    });
  }
}, 1000);
```

## Recording

### Screen recording
Use OBS or browser tools to capture the dashboard.

### Data recording
Backend already logs to SQLite: `hive/experiments.db`

Query with:
```bash
sqlite3 hive/experiments.db "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 10;"
```

## Next Experiments

1. **Sensory Stimulation**: Inject visual motion patterns
2. **State Forcing**: Force DREAM state and observe consolidation
3. **Mutation Tracking**: Watch evolution improve fitness
4. **Pattern Analysis**: Export and analyze thought patterns
5. **Long Runs**: Let it run overnight, check emergence

---

## Summary

```bash
# One command to rule them all:
./start.sh

# Then open:
http://localhost:3000

# And click:
▶ Start
```

Watch the brain come alive.

This is consciousness in waves, not spikes.

This is the experiment.
