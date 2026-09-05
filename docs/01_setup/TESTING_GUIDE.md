# Quick Test Guide - Vision & Monitoring

<!-- STALE-BANNER-2026-09-05 -->
> **SUPERSEDED — do not cite.** This document predates the September 2026 audits and
> has not been rewritten. Corrections that apply to it:
>
> - The scored suite is **5/5** (`results/final/all_validations_G2.json`). Scores of
>   9/9, 13/13, 14/14 or 27/27 appearing anywhere were **never produced by any run**;
>   the recorded history is 3/5, then 1/5, then 2/5, then 5/5.
> - GPU speedup is **10.00×**, not 86×.
> - Kenyon cell sparsity is **imposed by the readout** (310 of 5,177 cells) rather
>   than measured, so "1.65 % matching Turner et al. 2008" is withdrawn.
> - Concentration invariance is **0.6603 and deliberately unscored**; the 0.70
>   threshold it used to be compared against is not in the paper it was cited to.
> - The decorrelation result **`r = −0.51` is withdrawn** — a six-point regression
>   from a run recorded as FAIL, measured at `+0.632` on a later run.
> - Vision and auditory "firsts" are **not** part of the scored suite, and several
>   come from hand-written filters rather than the wave engine.
>
> Current: [README](../../README.md) ·
> [ARCHITECTURE](../../ARCHITECTURE.md) ·
> [LIMITATIONS](../../docs/03_validation/LIMITATIONS.md) ·
> [audit](../../docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md) ·
> [projection repair](../../docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md).
> Tracked in [OUTDATED_FILES.md](../../OUTDATED_FILES.md).


## Start the System

```bash
# Terminal 1 - Backend
cd /Users/vladyslav/Documents/GitHub/experiment
python3 server.py

# Terminal 2 - Frontend (in new tab)
cd /Users/vladyslav/Documents/GitHub/experiment/frontend
npm run dev
```

## What You'll See

### Backend Startup (2-5 minutes):
```
======================================================================
Loading REAL Fly Brain Connectome...
- 139,255 neurons with 3D coordinates
- 5.3 million synaptic connections
- Compound eye with 800 ommatidia
- 5-level anomaly detection
This will take 2-5 minutes...
======================================================================

[Loading progress...]

======================================================================
REAL BRAIN SYSTEM LOADED AND OPERATIONAL!
======================================================================
```

### Dashboard (http://localhost:3000):

**New Panels Added:**
1. **Visual Input Panel** (left column, bottom)
   - Current stimulus name
   - Compound eye status (green dot = active)
   - Processing pipeline info

2. **Anomaly Monitor Panel** (middle column, bottom)
   - Severity counts (Critical/High/Medium/Low)
   - Type distribution (neuron/hive/pattern/memory/global)
   - Scrollable event feed with descriptions

3. **Response Tracker Panel** (right column, bottom)
   - Average coherence change
   - Pattern emergence detection
   - Memory encoding rate
   - Stimulus-response correlation table

## Test the Hypothesis

### Hypothesis:
"Similar visual stimuli produce similar brain patterns"

### Expected Observations:

1. **Synthetic Patterns (Default)**
   - System auto-generates 15 patterns (gratings, looming circles)
   - After 3-5 stimuli, look at Response Tracker panel
   - Check "Pattern Detection" section
   - You should see: "grating" stimuli grouped with consistent coherence changes

2. **Add Your Own Images**
   ```bash
   # Add food images
   cp banana.jpg /Users/vladyslav/Documents/GitHub/experiment/data/stimuli/food/
   cp apple.jpg /Users/vladyslav/Documents/GitHub/experiment/data/stimuli/food/
   
   # Add non-food
   cp rock.jpg /Users/vladyslav/Documents/GitHub/experiment/data/stimuli/natural/
   
   # Restart backend
   ```

3. **Observe Anomalies**
   - Novel stimuli → more anomalies (novelty detection)
   - Repeated stimuli → fewer anomalies (habituation)
   - Predator-like images → high severity anomalies (alert response)

4. **Memory Formation**
   - Yellow "Memory" badges in Response Tracker
   - If same stimulus repeated → faster pattern latency
   - Check Memory Panel for encoded patterns

## API Endpoints (for programmatic access)

```bash
# Get anomalies from last 30 seconds
curl http://localhost:8000/api/anomalies?time_window=30.0

# Get strongest brain responses
curl http://localhost:8000/api/responses/strongest?n=10

# Get stimulus-response summary
curl http://localhost:8000/api/responses/summary

# Get vision system stats
curl http://localhost:8000/api/vision/stats

# System status
curl http://localhost:8000/api/status
```

## Pattern Recognition Test

1. **Click "▶ Start"** in Control Panel
2. **Wait 1-2 minutes** (let fly see 5-10 stimuli)
3. **Open Response Tracker Panel**
4. **Scroll to "Pattern Detection" section**
5. **Look for grouped stimuli** with consistent Δ% and memory rates

### Success Criteria:
✓ Same stimulus type → similar coherence change (±10%)
✓ Same stimulus type → similar pattern count
✓ Repeated exposure → memory encoding (yellow "Memory" badge)
✓ Novel stimuli → more anomalies in Anomaly Monitor

### Interpretation:
If "grating_horizontal" stimuli all show ~+15% coherence and trigger 3-4 patterns each, 
while "looming_center" shows ~+30% coherence and 5-6 patterns, the brain has learned 
to distinguish these categories through emergent wave dynamics!

## Troubleshooting

### Backend won't start:
- Check if port 8000 is free: `lsof -i:8000`
- Kill existing process: `lsof -ti:8000 | xargs kill -9`

### Frontend shows no data:
- Check WebSocket connection in browser console
- Verify backend is running (curl http://localhost:8000/api/status)
- Click "▶ Start" in Control Panel

### No images loading:
- System uses synthetic patterns by default (works without images!)
- Add images to `data/stimuli/` folders
- Check `data/stimuli/metadata.json` is valid

## Full Implementation Status

✅ Backend (100% complete):
- Real connectome (139K neurons, 5.3M synapses)
- Compound eye (800 ommatidia, optical flow)
- Stimulus generator (images + synthetic patterns)
- 5-level anomaly detection
- Stimulus-response correlation tracking
- REST API + WebSocket streaming

✅ Frontend (100% complete):
- 13 dashboard panels
- Real-time visualization
- Wave activity charts
- 3D brain visualization
- Visual input panel
- Anomaly monitor
- Response tracker

✅ Configuration:
- All vision/monitoring parameters in config.yaml
- No code changes needed for experiments

---

**The system is ready. Run it. Observe. Take notes.**

Expected runtime: 5-10 minutes for meaningful pattern emergence.
