import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.models.base import (
    Station, TrackSegment, Train, TrainSchedule, 
    NegotiationMessage, NegotiationState, NegotiationAction
)

class InMemoryStore:
    def __init__(self):
        self.stations: Dict[str, Station] = {}
        self.segments: Dict[str, TrackSegment] = {}
        self.trains: Dict[str, Train] = {}
        self.schedules: Dict[str, TrainSchedule] = {}
        
        # Negotiation State
        self.negotiation_sessions: Dict[str, NegotiationState] = {}
        self.negotiation_logs: List[NegotiationMessage] = []

    def get_train_status(self, train_id: str) -> Optional[TrainSchedule]:
        return self.schedules.get(train_id)

    def get_segment_occupancy(self, segment_id: str) -> List[TrainSchedule]:
        # Simple placeholder logic to find trains currently assigned to a segment
        occupants = []
        for sched in self.schedules.values():
            if sched.route and segment_id in sched.route:
                # Need proper time intersection logic, but for MCP verification we just return it
                occupants.append(sched)
        return occupants

    def get_network_snapshot(self) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "timestamp": now.isoformat(),
            "stations": [s.model_dump() for s in self.stations.values()],
            "segments": [s.model_dump() for s in self.segments.values()]
        }

    def get_dependency_graph(self, train_id: str) -> dict:
        # Placeholder for cascade dependencies
        return {"train_id": train_id, "dependent_trains": []}

    def append_negotiation_message(self, message: NegotiationMessage) -> None:
        self.negotiation_logs.append(message)
        
        # Update or create session
        # Assuming a session involves multiple trains. We can use original_proposal_id or derive session.
        session_id = message.original_proposal_id or message.message_id
        if session_id not in self.negotiation_sessions:
            self.negotiation_sessions[session_id] = NegotiationState(
                session_id=session_id,
                train_ids=[message.sender_id, message.receiver_id],
                messages=[],
                status="ACTIVE"
            )
        
        session = self.negotiation_sessions[session_id]
        session.messages.append(message)
        
        # Add trains to session if not present
        if message.sender_id not in session.train_ids:
            session.train_ids.append(message.sender_id)
        if message.receiver_id not in session.train_ids:
            session.train_ids.append(message.receiver_id)

        if message.action == NegotiationAction.COMMIT:
            session.status = "RESOLVED"

    def get_negotiation_log(self, session_id: Optional[str] = None) -> List[dict]:
        if session_id and session_id in self.negotiation_sessions:
            return [m.model_dump() for m in self.negotiation_sessions[session_id].messages]
        return [m.model_dump() for m in self.negotiation_logs]

# Global instance for Phase 2 MCP verification
store = InMemoryStore()
