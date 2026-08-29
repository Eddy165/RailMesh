from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Station(BaseModel):
    id: str
    name: str
    capacity: int = Field(default=2, description="Number of parallel tracks/platforms at the station")

class TrackSegment(BaseModel):
    id: str
    source_id: str
    target_id: str
    length_km: float
    capacity: int = Field(default=1, description="Number of trains that can occupy the segment simultaneously")
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
    route: List[str] = Field(description="List of segment IDs forming the route")
    entries: List[ScheduleEntry]
    current_status: str = Field(default="SCHEDULED")

class NegotiationAction(str, Enum):
    PROPOSE = "PROPOSE"
    COUNTER = "COUNTER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    COMMIT = "COMMIT"

class NegotiationMessage(BaseModel):
    message_id: str
    sender_id: str
    receiver_id: str
    timestamp: datetime
    action: NegotiationAction
    payload: dict = Field(description="The actual proposed schedule changes or rejection reason")
    original_proposal_id: Optional[str] = None

class NegotiationState(BaseModel):
    session_id: str
    train_ids: List[str]
    messages: List[NegotiationMessage]
    status: str = Field(default="ACTIVE", description="ACTIVE, RESOLVED, or TIMED_OUT")
