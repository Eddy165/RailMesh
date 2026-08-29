"""
RailMesh FastAPI Backend
Endpoints:
  POST /scenarios/inject  — trigger a disruption
  GET  /sessions/{id}     — full negotiation transcript
  WS   /sessions/{id}/stream — live negotiation feed
  GET  /network/state     — current train positions + delays
  POST /cascade/preview   — cascade engine preview
  GET/POST /config/data-mode — read/toggle data mode
"""
import asyncio
import os
import uuid
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models.base import DisruptionEvent, CascadeImpact, NegotiationSession
from app.store import store
from app.data.manager import get_data_provider
from app.data.synthetic import SyntheticDataLoader
from cascade.propagation_engine import propagate
from app.agents.negotiation_engine import run_negotiation_session

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


app = FastAPI(
    title="RailMesh",
    description="Swarm-Based Railway Delay Cascade Simulator & Advisory Layer",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections per session
_ws_connections: dict = {}  # session_id -> list[WebSocket]

# Data mode state
_data_mode = os.environ.get("RAILMESH_DATA_MODE", "synthetic")


# ---- Startup ----

@app.on_event("startup")
def startup():
    global _data_mode
    _init_store(_data_mode)


def _init_store(mode: str):
    """Load data from the configured mode into the store."""
    try:
        provider = get_data_provider(mode)
        store.stations = {s.id: s for s in provider.get_stations()}
        store.segments = {seg.id: seg for seg in provider.get_segments()}
        store.trains = {t.id: t for t in provider.get_trains()}
        store.schedules = {sch.train_id: sch for sch in provider.get_schedules()}
    except Exception as e:
        print(f"Warning: failed to init store with mode={mode}: {e}")


# ---- Request/Response models ----

class InjectScenarioRequest(BaseModel):
    scenario: Optional[str] = None  # e.g. "scenario_1_two_train_conflict"
    custom_event: Optional[dict] = None
    seed: int = 42


class CascadePreviewRequest(BaseModel):
    affected: str
    delay_minutes: int
    cause: str


class DataModeRequest(BaseModel):
    mode: str  # "synthetic" or "static"


# ---- Endpoints ----

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/scenarios/inject")
async def inject_scenario(req: InjectScenarioRequest, background_tasks: BackgroundTasks):
    """Trigger a disruption event, run cascade analysis, start negotiation session."""
    global _data_mode

    if req.scenario:
        loader = SyntheticDataLoader(seed=req.seed)
        disruption = loader.generate_disruption_event(req.scenario)
    elif req.custom_event:
        disruption = DisruptionEvent(**req.custom_event)
    else:
        raise HTTPException(status_code=400, detail="Provide scenario or custom_event")

    store.add_disruption(disruption)

    # Run cascade engine
    impacts = propagate(disruption, store)
    store.set_cascade_impacts(disruption.event_id, impacts)

    # Determine participating trains
    affected_trains = list({imp.train_id for imp in impacts})
    if not affected_trains:
        affected_trains = ["T12952", "T12810"]  # fallback for demo
    affected_trains = affected_trains[:4]  # cap at 4 for demo

    session_id = str(uuid.uuid4())

    # Run negotiation in background so endpoint returns immediately
    async def run_session_bg():
        conns = _ws_connections.get(session_id, [])
        for ws in conns:
            try:
                await ws.send_json({"event": "session_started", "session_id": session_id})
            except Exception:
                pass

        session = run_negotiation_session(
            session_id=session_id,
            disruption=disruption,
            participating_trains=affected_trains,
            max_rounds=int(os.environ.get("RAILMESH_MAX_ROUNDS", "5")),
        )

        # Notify WebSocket clients
        for ws in _ws_connections.get(session_id, []):
            try:
                await ws.send_json({
                    "event": "session_complete",
                    "session_id": session_id,
                    "terminal_state": session.terminal_state,
                    "total_rounds": len(session.rounds),
                })
            except Exception:
                pass

    background_tasks.add_task(run_session_bg)

    return {
        "session_id": session_id,
        "disruption_event_id": disruption.event_id,
        "affected_trains": affected_trains,
        "cascade_impact_count": len(impacts),
        "status": "started",
    }


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Get the full negotiation transcript for a session."""
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session.model_dump(mode="json")


@app.get("/sessions")
def list_sessions():
    """List all sessions."""
    return [
        {
            "session_id": sid,
            "terminal_state": s.terminal_state,
            "participating_trains": s.participating_trains,
            "total_rounds": len(s.rounds),
            "started_at": s.started_at.isoformat() if s.started_at else None,
        }
        for sid, s in store.sessions.items()
    ]


@app.websocket("/sessions/{session_id}/stream")
async def session_stream(websocket: WebSocket, session_id: str):
    """Live-stream negotiation rounds to the frontend."""
    await websocket.accept()
    _ws_connections.setdefault(session_id, []).append(websocket)
    try:
        # Send current state if session already exists
        existing = store.get_session(session_id)
        if existing:
            await websocket.send_json({
                "event": "current_state",
                "session": existing.model_dump(mode="json")
            })
        # Keep alive until disconnect
        while True:
            await asyncio.sleep(1)
            try:
                await websocket.send_json({"event": "heartbeat"})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        conns = _ws_connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)


@app.get("/network/state")
def network_state():
    """Current train positions and delays."""
    trains = []
    for train_id, sched in store.schedules.items():
        train = store.trains.get(train_id)
        trains.append({
            "train_id": train_id,
            "name": train.name if train else train_id,
            "priority_class": train.priority_class.value if train else "unknown",
            "current_segment": sched.route[0] if sched.route else None,
            "route": sched.route,
            "current_status": sched.current_status,
            "current_delay_minutes": sched.current_delay_minutes,
        })
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trains": trains,
        "stations": [s.model_dump() for s in store.stations.values()],
        "segments": [s.model_dump() for s in store.segments.values()],
        "active_disruptions": [
            d.model_dump(mode="json") for d in store.get_active_disruptions()
        ],
    }


@app.post("/cascade/preview")
def cascade_preview(req: CascadePreviewRequest):
    """Run cascade engine without triggering negotiation."""
    event = DisruptionEvent(
        affected_station_or_segment=req.affected,
        delay_minutes=req.delay_minutes,
        cause=req.cause,
    )
    impacts = propagate(event, store)
    return {
        "disruption": event.model_dump(mode="json"),
        "impacts": [i.model_dump() for i in impacts],
        "affected_train_count": len(impacts),
    }


@app.get("/config/data-mode")
def get_data_mode():
    return {"mode": _data_mode}


@app.post("/config/data-mode")
def set_data_mode(req: DataModeRequest):
    global _data_mode
    valid = {"synthetic", "static", "SYNTHETIC", "STATIC_REAL"}
    if req.mode not in valid:
        raise HTTPException(status_code=400, detail=f"Mode must be one of {valid}")
    _data_mode = req.mode
    _init_store(req.mode)
    return {"mode": _data_mode, "status": "reloaded"}
