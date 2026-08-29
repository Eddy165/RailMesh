from enum import Enum
from typing import List, Optional, Literal, Dict, Tuple, Any
from pydantic import BaseModel, Field
from datetime import datetime, time
import uuid


class Station(BaseModel):
    id: str
    name: str
    capacity: int = Field(default=2, description="Number of parallel tracks/platforms")


class TrackSegment(BaseModel):
    id: str
    source_id: str
    target_id: str
    length_km: float
    capacity: int = Field(default=1, description="Trains that can occupy simultaneously")
    travel_time_mins: int


class NetworkSnapshot(BaseModel):
    timestamp: datetime
    stations: List[Station]
    segments: List[TrackSegment]


class PriorityClass(str, Enum):
    EXPRESS = "express"
    PASSENGER = "passenger"
    FREIGHT = "freight"


class Train(BaseModel):
    id: str
    name: str
    priority_class: PriorityClass


class ScheduleEntry(BaseModel):
    segment_id: str
    arrival_time: datetime
    departure_time: datetime


class TrainSchedule(BaseModel):
    train_id: str
    route: List[str] = Field(description="List of segment IDs")
    entries: List[ScheduleEntry]
    current_status: str = Field(default="SCHEDULED")
    current_delay_minutes: int = Field(default=0)


# ---- Disruption & Cascade ----

class DisruptionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    affected_station_or_segment: str
    delay_minutes: int
    cause: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    scenario_tag: Optional[str] = None  # e.g. "scenario_1", "scenario_3"


class CascadeImpact(BaseModel):
    train_id: str
    affected_segment_or_station: str
    estimated_delay_minutes: int
    impact_type: str  # "platform_conflict", "segment_blocked", "connecting_dependency"
    confidence: float = Field(ge=0.0, le=1.0)
    hop_distance: int = Field(default=1, description="How many hops from original disruption")


# ---- Agent Decision ----

class AgentDecision(BaseModel):
    train_id: str
    round_number: int
    action: Literal["accept", "counter_propose", "reject", "escalate"]
    proposed_change: Optional[Dict[str, Any]] = None
    rationale: str = Field(description="Human-readable explanation — mandatory field")


# ---- Negotiation ----

class NegotiationAction(str, Enum):
    PROPOSE = "PROPOSE"
    COUNTER = "COUNTER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    COMMIT = "COMMIT"
    ESCALATE = "ESCALATE"


class NegotiationMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = "default"
    sender_id: str
    receiver_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: NegotiationAction
    payload: dict = Field(description="Proposed schedule or reason")
    original_proposal_id: Optional[str] = None
    round_number: int = Field(default=1)


class RoundRecord(BaseModel):
    round_number: int
    decisions: List[AgentDecision]
    coordinator_summary: str


class NegotiationSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    disruption_event_id: str
    participating_trains: List[str]
    rounds: List[RoundRecord] = Field(default_factory=list)
    messages: List[NegotiationMessage] = Field(default_factory=list)
    terminal_state: Optional[Literal["consensus_reached", "escalated_unresolved", "max_rounds_exceeded"]] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

NegotiationState = NegotiationSession