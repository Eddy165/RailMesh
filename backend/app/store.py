import uuid
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from app.models.base import (
    Station, TrackSegment, Train, TrainSchedule,
    NegotiationMessage, NegotiationSession, NegotiationAction,
    DisruptionEvent, AgentDecision, RoundRecord, CascadeImpact
)


LOGS_DIR = Path("logs/sessions")


class InMemoryStore:
    def __init__(self):
        self.stations: Dict[str, Station] = {}
        self.segments: Dict[str, TrackSegment] = {}
        self.trains: Dict[str, Train] = {}
        self.schedules: Dict[str, TrainSchedule] = {}
        self.disruption_events: Dict[str, DisruptionEvent] = {}
        self.cascade_impacts: Dict[str, List[CascadeImpact]] = {}  # event_id -> impacts
        self.sessions: Dict[str, NegotiationSession] = {}
        # Legacy compat
        self.negotiation_sessions: Dict[str, NegotiationSession] = self.sessions
        self.negotiation_logs: List[NegotiationMessage] = []

    # ---- Train / Network ----

    def get_train_status(self, train_id: str) -> Optional[TrainSchedule]:
        return self.schedules.get(train_id)

    def get_segment_occupancy(self, segment_id: str) -> List[TrainSchedule]:
        return [
            sched for sched in self.schedules.values()
            if sched.route and segment_id in sched.route
        ]

    def get_network_snapshot(self) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "timestamp": now.isoformat(),
            "stations": [s.model_dump() for s in self.stations.values()],
            "segments": [s.model_dump() for s in self.segments.values()],
            "trains": [t.model_dump() for t in self.trains.values()],
        }

    def get_dependency_graph(self, train_id: str) -> dict:
        """Return trains that share any segment with the given train."""
        sched = self.schedules.get(train_id)
        if not sched:
            return {"train_id": train_id, "dependent_trains": []}
        deps = []
        for other_id, other_sched in self.schedules.items():
            if other_id == train_id:
                continue
            shared = set(sched.route) & set(other_sched.route)
            if shared:
                deps.append({"train_id": other_id, "shared_segments": list(shared)})
        return {"train_id": train_id, "dependent_trains": deps}

    # ---- Disruptions ----

    def add_disruption(self, event: DisruptionEvent) -> None:
        self.disruption_events[event.event_id] = event

    def get_active_disruptions(self) -> List[DisruptionEvent]:
        return list(self.disruption_events.values())

    def set_cascade_impacts(self, event_id: str, impacts: List[CascadeImpact]) -> None:
        self.cascade_impacts[event_id] = impacts

    def get_cascade_impacts(self, event_id: str) -> List[CascadeImpact]:
        return self.cascade_impacts.get(event_id, [])

    # ---- Sessions ----

    def create_session(self, session: NegotiationSession) -> None:
        self.sessions[session.session_id] = session
        self._ensure_log_dir(session.session_id)
        self._append_session_log(session.session_id, {
            "event": "session_started",
            "session_id": session.session_id,
            "disruption_event_id": session.disruption_event_id,
            "participating_trains": session.participating_trains,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        return self.sessions.get(session_id)

    def add_decision_to_session(self, session_id: str, decision: AgentDecision) -> None:
        session = self.sessions.get(session_id)
        if not session:
            return
        # Ensure the round record exists
        rn = decision.round_number
        while len(session.rounds) < rn:
            session.rounds.append(RoundRecord(
                round_number=len(session.rounds) + 1,
                decisions=[],
                coordinator_summary=""
            ))
        session.rounds[rn - 1].decisions.append(decision)
        self._append_session_log(session_id, {
            "event": "agent_decision",
            "session_id": session_id,
            "train_id": decision.train_id,
            "round_number": decision.round_number,
            "action": decision.action,
            "proposed_change": decision.proposed_change,
            "rationale": decision.rationale,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def set_round_summary(self, session_id: str, round_number: int, summary: str) -> None:
        session = self.sessions.get(session_id)
        if session and len(session.rounds) >= round_number:
            session.rounds[round_number - 1].coordinator_summary = summary

    def finalize_session(self, session_id: str, terminal_state: str) -> None:
        session = self.sessions.get(session_id)
        if session:
            session.terminal_state = terminal_state
            session.ended_at = datetime.now(timezone.utc)
            self._append_session_log(session_id, {
                "event": "session_finalized",
                "session_id": session_id,
                "terminal_state": terminal_state,
                "total_rounds": len(session.rounds),
                "timestamp": session.ended_at.isoformat(),
            })

    # ---- Legacy negotiation log (for backward compat with existing tests) ----

    def append_negotiation_message(self, message: NegotiationMessage) -> None:
        self.negotiation_logs.append(message)
        session_id = message.session_id
        if session_id not in self.sessions:
            # Auto-create legacy session
            session = NegotiationSession(
                session_id=session_id,
                disruption_event_id="legacy",
                participating_trains=[message.sender_id, message.receiver_id],
            )
            self.sessions[session_id] = session
        session = self.sessions[session_id]
        session.messages.append(message)
        if message.sender_id not in session.participating_trains:
            session.participating_trains.append(message.sender_id)
        if message.receiver_id not in session.participating_trains:
            session.participating_trains.append(message.receiver_id)
        if message.action == NegotiationAction.COMMIT:
            session.terminal_state = "consensus_reached"

    def get_negotiation_log(self, session_id: Optional[str] = None) -> List[dict]:
        if session_id and session_id in self.sessions:
            return [m.model_dump(mode="json") for m in self.sessions[session_id].messages]
        return [m.model_dump(mode="json") for m in self.negotiation_logs]

    # ---- JSONL audit log ----

    def _ensure_log_dir(self, session_id: str) -> None:
        log_path = LOGS_DIR / session_id
        log_path.mkdir(parents=True, exist_ok=True)

    def _append_session_log(self, session_id: str, entry: dict) -> None:
        try:
            log_path = LOGS_DIR / session_id / "audit.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass  # Never crash the main flow due to logging


# Global singleton
store = InMemoryStore()
