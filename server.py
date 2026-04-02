"""
FastAPI server for the wave-based fly brain consciousness system.
Provides REST API and WebSocket endpoints for real-time visualization.
"""

import asyncio
import json
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

from hive.main import FlyBrainSystem


app = FastAPI(title="Fly Brain Wave Consciousness API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

brain_system: FlyBrainSystem | None = None
active_websockets: Set[WebSocket] = set()
is_running = False
brain_loading = True
brain_load_error = None

# ── Smell synthesis globals ────────────────────────────────────────────
_smell_db        = None          # SmellDatabase (lazy-loaded)
_olfactory_brain = None          # SparseProbabilisticBrain (olfactory pathway, fast_mode)
_smell_optimizer = None          # SmellOptimizer (lazy-loaded, requires _olfactory_brain)
_olf_brain_lock  = threading.Lock()

# Active synthesis jobs: job_id → SynthesisJob
@dataclass
class SynthesisJob:
    job_id:     str
    status:     str  = "queued"    # queued | running | done | error
    step:       int  = 0
    loss:       float = 0.0
    gradient_norm: float = 0.0
    top_matches: list  = field(default_factory=list)
    converged:  bool   = False
    glom_pattern: list = field(default_factory=list)
    history_loss: list = field(default_factory=list)
    error:      str    = ""

synthesis_jobs: dict[str, SynthesisJob] = {}

# ── Pydantic models ────────────────────────────────────────────────────

class SynthesizeRequest(BaseModel):
    target_odor:     str | None = None
    target_kc_pattern: list[float] | None = None
    mode:            str   = "fast"      # "fast" | "accurate"
    num_steps:       int   = 150
    region:          str   = "KC"

class CompareRequest(BaseModel):
    odor_a: str
    odor_b: str

class EncodeRequest(BaseModel):
    odor_name:    str
    concentration: float = 1.0


def load_brain_system():
    """Load brain system in background thread."""
    global brain_system, brain_loading, brain_load_error
    try:
        print("="*70)
        print("Loading REAL Fly Brain Connectome in background...")
        print("- 139,255 neurons with 3D coordinates")
        print("- 5.3 million synaptic connections")
        print("- Compound eye with 800 ommatidia")
        print("- 5-level anomaly detection")
        print("Server will be available immediately, brain loads in background...")
        print("="*70)
        brain_system = FlyBrainSystem(config_path="hive/config.yaml")
        brain_loading = False
        print("\n" + "="*70)
        print("REAL BRAIN SYSTEM LOADED AND OPERATIONAL!")
        print("="*70)
    except Exception as e:
        brain_load_error = str(e)
        brain_loading = False
        print(f"ERROR loading brain: {e}")


@app.on_event("startup")
async def startup_event():
    """Start brain loading in background thread."""
    thread = threading.Thread(target=load_brain_system, daemon=True)
    thread.start()


def serialize_snapshot(system: FlyBrainSystem) -> dict:
    """Convert system state to JSON-serializable format."""
    
    # Cache neuron ID list if not already cached
    if not hasattr(system, '_neuron_id_list_cache'):
        system._neuron_id_list_cache = list(system.connectome.neurons.keys())
    
    neurons_sample = []
    # Sample 1000 neurons evenly across the array
    neuron_id_list = system._neuron_id_list_cache
    step = max(1, len(neuron_id_list) // 1000)
    
    for i in range(0, len(neuron_id_list), step):
        if i < len(neuron_id_list) and i < len(system.oscillator.phase):
            nid = neuron_id_list[i]
            neurons_sample.append({
                'id': int(nid),
                'position': system.connectome.neurons[nid].position.tolist(),
                'phase': float(system.oscillator.phase[i]),
                'amplitude': float(system.oscillator.amplitude[i]),
                'frequency': float(system.oscillator.omega0[i]),
                'group': system.connectome.neurons[nid].group,
            })
    
    hives = []
    for hive_id, hive in system.hive_registry.hives.items():
        hives.append({
            'id': hive_id,
            'neuron_ids': [int(x) for x in list(hive.neuron_ids)[:100]],
            'centroid': hive.centroid.tolist(),
            'coherence': float(hive.coherence),
            'size': int(hive.size),
            'age': int(hive.age),
        })
    
    patterns = []
    if hasattr(system.thought_detector, 'recent_patterns') and len(system.thought_detector.recent_patterns) > 0:
        # Get last 20 pattern IDs and fetch from patterns dict
        recent_ids = list(system.thought_detector.recent_patterns)[-20:]
        for pid in recent_ids:
            if pid in system.thought_detector.patterns:
                pattern = system.thought_detector.patterns[pid]
                patterns.append({
                    'id': str(pattern.pattern_id),
                    'type': pattern.pattern_type,
                    'hive_ids': [str(hid) for hid in pattern.hive_sequence],  # Fixed: hive_sequence not hive_ids
                    'signature': str(pattern.phase_fingerprint[:5]) if len(pattern.phase_fingerprint) > 0 else '',  # Fixed: phase_fingerprint not signature
                    'stability': float(pattern.stability),
                    'complexity': int(pattern.complexity),
                    'timestamp': float(pattern.birth_time),  # Fixed: birth_time not timestamp
                })
    
    global_metrics = system.global_field.compute_metrics()
    
    consciousness = {
        'name': system.consciousness_manager.current_state.name,
        'global_coherence': float(global_metrics['global_coherence']),
        'dominant_frequency': float(global_metrics['dominant_frequency']),
        'metastability': float(global_metrics['metastability']),
        'energy': float(system.oscillator.get_energy()),
    }
    
    memories = []
    if hasattr(system.memory, 'phase_memory'):
        for mem_id, pattern in list(system.memory.phase_memory.patterns.items())[:10]:
            age_ms = float(system.current_time - pattern.encoding_time) if system.current_time > pattern.encoding_time else 0.0
            memories.append({
                'id': str(mem_id),
                'neuron_ids': [int(x) for x in pattern.neuron_ids[:50]],
                'strength': float(pattern.strength),
                'age': int(age_ms),
                'recall_count': int(pattern.activation_count),
            })
    
    metrics = {
        'timestamp': float(system.current_time),
        'active_neurons': int(np.sum(system.oscillator.amplitude > 0.1)),
        'active_hives': len(system.hive_registry.hives),
        'coherence': float(global_metrics['global_coherence']),
        'energy': float(system.oscillator.get_energy()),
        'consciousness_state': system.consciousness_manager.current_state.name,
    }
    
    # NEW: Visual input info
    visual = {
        'current_stimulus': system.current_stimulus if hasattr(system, 'current_stimulus') else 'none',
        'compound_eye_active': hasattr(system, 'compound_eye') and system.compound_eye is not None,
        'stimulus_gen_stats': system.stimulus_gen.get_statistics() if hasattr(system, 'stimulus_gen') else {}
    }
    
    # NEW: Anomaly data
    anomalies = []
    if hasattr(system, 'recent_anomalies'):
        for anomaly in list(system.recent_anomalies)[-20:]:
            anomalies.append({
                'timestamp': float(anomaly.timestamp),
                'type': anomaly.type,
                'subtype': anomaly.subtype,
                'severity': float(anomaly.severity),
                'description': anomaly.description,
                'stimulus_context': anomaly.stimulus_context
            })
    
    # NEW: Response tracking
    response_summary = {}
    if hasattr(system, 'response_tracker'):
        recent_responses = system.response_tracker.get_recent(5)
        response_summary = {
            'recent_responses': [
                {
                    'stimulus': r.stimulus_label,
                    'coherence_change': float(r.coherence_change),
                    'patterns': r.activated_patterns[:5],  # First 5
                    'anomaly_count': r.anomaly_count,
                    'memory_encoded': r.memory_encoded
                }
                for r in recent_responses
            ]
        }
    
    return {
        'neurons': neurons_sample,
        'hives': hives,
        'patterns': patterns,
        'consciousness': consciousness,
        'memories': memories,
        'metrics': metrics,
        'visual': visual,
        'anomalies': anomalies,
        'response_summary': response_summary
    }


async def broadcast_snapshot():
    """Broadcast current system state to all connected clients."""
    if not brain_system or not active_websockets:
        return
    
    try:
        snapshot = serialize_snapshot(brain_system)
        message = json.dumps(snapshot)
        
        disconnected = set()
        for ws in active_websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)
        
        active_websockets.difference_update(disconnected)
    except Exception as e:
        print(f"Error broadcasting: {e}")


async def simulation_loop():
    """Main simulation loop that steps the system and broadcasts updates."""
    global is_running
    
    while is_running:
        if brain_system:
            try:
                brain_system.step()
                await broadcast_snapshot()
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"Simulation error: {e}")
                import traceback
                traceback.print_exc()
                is_running = False
        else:
            await asyncio.sleep(0.1)


@app.websocket("/ws/brain")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time brain state updates."""
    await websocket.accept()
    active_websockets.add(websocket)
    print(f"[WS] Client connected. brain_loading={brain_loading}, brain_system={brain_system is not None}")
    
    try:
        # Wait for brain to load
        while brain_loading:
            print(f"[WS] Still loading, sending loading status...")
            await websocket.send_text(json.dumps({
                "status": "loading",
                "message": "Loading real fly brain connectome... please wait"
            }))
            await asyncio.sleep(1)
        
        print(f"[WS] Brain loaded! brain_load_error={brain_load_error}")
        
        # Check for load error
        if brain_load_error:
            print(f"[WS] Load error, sending error status")
            await websocket.send_text(json.dumps({
                "status": "error",
                "message": f"Failed to load brain: {brain_load_error}"
            }))
            return
        
        # Brain loaded, send initial snapshot
        if brain_system:
            print(f"[WS] Calling serialize_snapshot...")
            try:
                snapshot = serialize_snapshot(brain_system)
                print(f"[WS] Snapshot created, sending to client...")
                await websocket.send_text(json.dumps(snapshot))
                print(f"[WS] Sent initial snapshot to client, neurons: {len(snapshot.get('neurons', []))}, hives: {len(snapshot.get('hives', []))}")
            except Exception as e:
                print(f"[WS] ERROR serializing snapshot: {e}")
                import traceback
                traceback.print_exc()
        
        # Keep connection alive and send periodic updates
        while True:
            try:
                # Send updates every 100ms even when not running
                await asyncio.sleep(0.1)
                if brain_system:
                    snapshot = serialize_snapshot(brain_system)
                    await websocket.send_text(json.dumps(snapshot))
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"ERROR in websocket loop: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


@app.post("/api/control/start")
async def start_simulation():
    """Start the simulation loop."""
    global is_running
    if not is_running:
        is_running = True
        asyncio.create_task(simulation_loop())
        return {"status": "started"}
    return {"status": "already_running"}


@app.post("/api/control/stop")
async def stop_simulation():
    """Stop the simulation loop."""
    global is_running
    is_running = False
    return {"status": "stopped"}


@app.post("/api/control/reset")
async def reset_simulation():
    """Reset the brain system to initial state."""
    global brain_system, is_running
    is_running = False
    await asyncio.sleep(0.1)
    brain_system = FlyBrainSystem(config_path="hive/config.yaml")
    return {"status": "reset"}


@app.get("/api/status")
async def get_status():
    """Get current system status."""
    if brain_loading:
        return {
            "status": "loading",
            "message": "Loading real fly brain connectome...",
            "running": False,
            "connected_clients": len(active_websockets)
        }
    
    if brain_load_error:
        return {
            "status": "error",
            "message": brain_load_error,
            "running": False
        }
    
    if brain_system:
        return {
            "status": "ready",
            "running": is_running,
            "connected_clients": len(active_websockets),
            "simulation_time": float(brain_system.current_time),
            "consciousness_state": brain_system.consciousness_manager.current_state.name,
        }
    return {"status": "error", "message": "System not initialized"}


@app.get("/api/anomalies")
async def get_anomalies(time_window: float = 10.0):
    """Get anomalies from last N seconds."""
    if not brain_system or not hasattr(brain_system, 'anomaly_detector'):
        return {"error": "Anomaly detector not available"}
    
    summary = brain_system.anomaly_detector.get_anomaly_summary(time_window)
    return summary


@app.get("/api/responses/summary")
async def get_response_summary():
    """Get stimulus-response correlation summary."""
    if not brain_system or not hasattr(brain_system, 'response_tracker'):
        return {"error": "Response tracker not available"}
    
    summary = brain_system.response_tracker.get_overall_summary()
    return summary


@app.get("/api/responses/strongest")
async def get_strongest_responses(n: int = 5):
    """Get N strongest brain responses."""
    if not brain_system or not hasattr(brain_system, 'response_tracker'):
        return {"error": "Response tracker not available"}
    
    strongest = brain_system.response_tracker.get_strongest_responses(n)
    return {
        'strongest_responses': [
            {
                'stimulus': r.stimulus_label,
                'coherence_change': float(r.coherence_change),
                'energy_change': float(r.energy_change),
                'pattern_count': r.pattern_count,
                'anomaly_count': r.anomaly_count,
                'memory_encoded': r.memory_encoded
            }
            for r in strongest
        ]
    }


@app.get("/api/vision/stats")
async def get_vision_stats():
    """Get compound eye and stimulus statistics."""
    if not brain_system:
        return {"error": "System not initialized"}
    
    stats = {}
    
    if hasattr(brain_system, 'compound_eye'):
        stats['compound_eye'] = brain_system.compound_eye.get_statistics()
    
    if hasattr(brain_system, 'stimulus_gen'):
        stats['stimulus_generator'] = brain_system.stimulus_gen.get_statistics()
    
    if hasattr(brain_system, 'current_stimulus'):
        stats['current_stimulus'] = brain_system.current_stimulus
    
    return stats


# ═══════════════════════════════════════════════════════════════════════
#  SMELL SYNTHESIS — helpers
# ═══════════════════════════════════════════════════════════════════════

def _get_smell_db():
    """Lazy-load SmellDatabase (singleton)."""
    global _smell_db
    if _smell_db is None:
        from hive.data.smell_database import SmellDatabase
        _smell_db = SmellDatabase()
        kc_path = Path("data/digital_smell_database_full.json")
        if kc_path.exists():
            _smell_db.load_kc_fingerprints(kc_path)
    return _smell_db


def _get_olfactory_brain():
    """Lazy-load olfactory-pathway SparseProbabilisticBrain (fast_mode)."""
    global _olfactory_brain
    if _olfactory_brain is None:
        with _olf_brain_lock:
            if _olfactory_brain is None:
                from hive.substrate.connectome import Connectome
                from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
                from hive.engine.sparse_probabilistic import SparseProbabilisticBrain

                full = Connectome(data_dir="Fly Brain Female")
                full.load()
                conn = extract_olfactory_pathway(full)
                _olfactory_brain = SparseProbabilisticBrain(
                    conn, use_mlx=True, fast_mode=True
                )
                _olfactory_brain.reset(deterministic=True)
                _olfactory_brain.evolve(20.0)   # warm up JIT
    return _olfactory_brain


def _encode_odor_to_kc(glom: np.ndarray, brain, concentration: float = 1.0) -> np.ndarray:
    """Run one forward simulation pass and return KC pattern (normalized)."""
    strength = 50.0 * np.log10(1 + 10 * concentration)
    brain.reset(deterministic=True)
    brain.inject_odor(glom, strength=float(strength))
    brain.evolve(100.0)
    return brain.get_region_activity("KC", normalize_kc=True, target_sparsity=0.06)


def _get_smell_optimizer():
    """
    Lazy-load SmellOptimizer backed by DifferentiableSmellMapper.

    Builds the PN→KC weight matrix from the olfactory brain once; subsequent
    calls return the cached instance.  Thread-safe via _olf_brain_lock.
    """
    global _smell_optimizer
    if _smell_optimizer is None:
        with _olf_brain_lock:
            if _smell_optimizer is None:
                from hive.inverse.smell_optimizer import SmellOptimizer
                brain = _get_olfactory_brain()
                db    = _get_smell_db()
                _smell_optimizer = SmellOptimizer(brain, smell_db=db,
                                                  learning_rate=0.05)
    return _smell_optimizer


def _run_synthesis_job(job: SynthesisJob, target_kc: np.ndarray,
                        num_steps: int, mode: str) -> None:
    """
    Background thread: smell synthesis via SmellOptimizer.

    Fast mode    — nearest-neighbour in SmellDatabase KC space (O(N), ~1 ms).
    Accurate mode — Adam through DifferentiableSmellMapper (true autodiff).
    """
    try:
        job.status = "running"

        optimizer = _get_smell_optimizer()

        # Map server "accurate" alias → optimizer "gradient" mode
        opt_mode = "fast" if mode == "fast" else "gradient"

        glom, info = optimizer.encode_smell(
            target_kc,
            mode=opt_mode,
            num_steps=num_steps,
            verbose=False,
        )

        job.glom_pattern  = glom.tolist()
        job.loss          = float(info["loss"])
        job.step          = int(info["steps"]) if info["steps"] else num_steps
        job.converged     = bool(info["converged"])
        job.top_matches   = info.get("top_matches", [])
        job.history_loss  = info.get("history_loss", [job.loss])
        job.gradient_norm = float(info.get("history_grad", [0.0])[-1])
        job.status        = "done"

    except Exception as exc:
        job.error  = str(exc)
        job.status = "error"


# ═══════════════════════════════════════════════════════════════════════
#  SMELL SYNTHESIS — REST endpoints
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/smell/odorants")
async def get_odorant_list():
    """Lightweight list of all available odorants (name + family)."""
    try:
        db = _get_smell_db()
        return {
            "odorants": [
                {"name": e.name, "family": e.family, "has_kc": e.kc_pattern is not None}
                for e in db.entries.values()
            ],
            "total": len(db.entries),
            "with_kc": sum(1 for e in db.entries.values() if e.kc_pattern is not None),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/smell/database")
async def get_smell_database(include_kc: bool = False):
    """Full odorant entries. Set include_kc=true to include raw KC vectors."""
    try:
        db = _get_smell_db()
        return {
            "entries": db.get_all_entries(include_kc=include_kc),
            "stats":   db.stats(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/smell/encode")
async def encode_odor(req: EncodeRequest):
    """
    Run a forward-pass simulation for one odorant and return its KC pattern.
    Fast (~400ms on GPU). Result is also cached in SmellDatabase.
    """
    try:
        db    = _get_smell_db()
        entry = db.find_by_name(req.odor_name)
        if entry is None:
            raise HTTPException(status_code=404,
                                detail=f"Odorant '{req.odor_name}' not found")

        # Return cached if available
        if entry.kc_pattern is not None:
            return {
                "odor_name":   req.odor_name,
                "family":      entry.family,
                "glom_pattern": entry.glom_pattern,
                "kc_pattern":  entry.kc_pattern,
                "kc_active":   entry.kc_active,
                "kc_sparsity": entry.kc_sparsity,
                "cached":      True,
            }

        brain  = _get_olfactory_brain()
        glom   = np.array(entry.glom_pattern, dtype=np.float32)
        with _olf_brain_lock:
            kc = _encode_odor_to_kc(glom, brain, req.concentration)

        entry.kc_pattern  = kc.tolist()
        entry.kc_active   = int(np.sum(kc > 0.01))
        entry.kc_sparsity = float(entry.kc_active / len(kc))

        return {
            "odor_name":    req.odor_name,
            "family":       entry.family,
            "glom_pattern": entry.glom_pattern,
            "kc_pattern":   entry.kc_pattern,
            "kc_active":    entry.kc_active,
            "kc_sparsity":  entry.kc_sparsity,
            "cached":       False,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/smell/compare")
async def compare_odors(req: CompareRequest):
    """
    Compare two odorants: glomerular cosine similarity + KC decorrelation.
    """
    try:
        db = _get_smell_db()
        ea = db.find_by_name(req.odor_a)
        eb = db.find_by_name(req.odor_b)

        missing = [n for n, e in [(req.odor_a, ea), (req.odor_b, eb)] if e is None]
        if missing:
            raise HTTPException(status_code=404,
                                detail=f"Odorants not found: {missing}")

        glom_a = np.array(ea.glom_pattern, dtype=np.float32)
        glom_b = np.array(eb.glom_pattern, dtype=np.float32)

        def cosine(a, b):
            na, nb = np.linalg.norm(a), np.linalg.norm(b)
            if na < 1e-9 or nb < 1e-9:
                return 0.0
            return float(np.dot(a, b) / (na * nb))

        glom_sim = cosine(glom_a, glom_b)

        kc_sim: float | None = None
        if ea.kc_pattern is not None and eb.kc_pattern is not None:
            kc_a   = np.array(ea.kc_pattern, dtype=np.float32)
            kc_b   = np.array(eb.kc_pattern, dtype=np.float32)
            kc_sim = cosine(kc_a, kc_b)

        return {
            "odor_a":           req.odor_a,
            "odor_b":           req.odor_b,
            "glom_similarity":  glom_sim,
            "kc_similarity":    kc_sim,
            "decorrelation":    None if kc_sim is None else (glom_sim - kc_sim),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/smell/synthesize")
async def start_synthesis(req: SynthesizeRequest):
    """
    Start an async smell synthesis job.

    Supply either target_odor (name lookup) or target_kc_pattern (raw vector).
    Returns job_id; stream progress via WS /ws/synthesis/{job_id}.
    """
    try:
        db = _get_smell_db()

        # Resolve target KC pattern
        target_kc: np.ndarray | None = None

        if req.target_odor:
            entry = db.find_by_name(req.target_odor)
            if entry is None:
                raise HTTPException(status_code=404,
                                    detail=f"Odorant '{req.target_odor}' not found")
            if entry.kc_pattern is None:
                brain = _get_olfactory_brain()
                glom  = np.array(entry.glom_pattern, dtype=np.float32)
                with _olf_brain_lock:
                    kc = _encode_odor_to_kc(glom, brain)
                entry.kc_pattern  = kc.tolist()
                entry.kc_active   = int(np.sum(kc > 0.01))
                entry.kc_sparsity = float(entry.kc_active / len(kc))
            target_kc = np.array(entry.kc_pattern, dtype=np.float32)

        elif req.target_kc_pattern:
            target_kc = np.array(req.target_kc_pattern, dtype=np.float32)

        else:
            raise HTTPException(status_code=422,
                                detail="Provide target_odor or target_kc_pattern")

        job_id = str(uuid.uuid4())
        job    = SynthesisJob(job_id=job_id)
        synthesis_jobs[job_id] = job

        # Run in background thread (synthesis can take 10-30s in accurate mode)
        thread = threading.Thread(
            target=_run_synthesis_job,
            args=(job, target_kc, req.num_steps, req.mode),
            daemon=True,
        )
        thread.start()

        return {"job_id": job_id, "status": "queued"}

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/smell/synthesize/{job_id}")
async def get_synthesis_result(job_id: str):
    """Poll synthesis job status and result."""
    job = synthesis_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return {
        "job_id":       job.job_id,
        "status":       job.status,
        "step":         job.step,
        "loss":         job.loss,
        "gradient_norm": job.gradient_norm,
        "converged":    job.converged,
        "top_matches":  job.top_matches,
        "glom_pattern": job.glom_pattern,
        "history_loss": job.history_loss,
        "error":        job.error,
    }


# ── WebSocket: live synthesis progress ────────────────────────────────

@app.websocket("/ws/synthesis/{job_id}")
async def synthesis_ws(websocket: WebSocket, job_id: str):
    """
    Stream per-step synthesis progress for job_id.
    Sends JSON every 300ms until job is done or client disconnects.
    """
    await websocket.accept()

    try:
        # Wait up to 60s for the job to appear
        waited = 0.0
        while job_id not in synthesis_jobs and waited < 60:
            await asyncio.sleep(0.3)
            waited += 0.3

        if job_id not in synthesis_jobs:
            await websocket.send_text(json.dumps({"error": "Job not found"}))
            return

        job = synthesis_jobs[job_id]

        while True:
            payload = {
                "job_id":         job.job_id,
                "status":         job.status,
                "step":           job.step,
                "loss":           job.loss,
                "gradient_norm":  job.gradient_norm,
                "converged":      job.converged,
                "top_matches":    job.top_matches,
                "history_loss":   job.history_loss[-50:],   # last 50 points
            }
            await websocket.send_text(json.dumps(payload))

            if job.status in ("done", "error"):
                break

            await asyncio.sleep(0.3)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(json.dumps({"error": str(exc)}))
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
