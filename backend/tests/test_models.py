import pytest
from datetime import datetime, timezone
from app.models.base import (
    Station, TrackSegment, PriorityClass, Train, 
    ScheduleEntry, TrainSchedule, NegotiationAction, 
    NegotiationMessage, NegotiationState
)

def test_station_creation():
    station = Station(id="S1", name="Central")
    assert station.id == "S1"
    assert station.name == "Central"
    assert station.capacity == 2  # Default value

def test_track_segment_creation():
    segment = TrackSegment(
        id="TS1", 
        source_id="S1", 
        target_id="S2", 
        length_km=15.5, 
        travel_time_mins=12
    )
    assert segment.id == "TS1"
    assert segment.capacity == 1  # Default value
    assert segment.travel_time_mins == 12

def test_train_creation():
    train = Train(id="T1", name="Express-1", priority_class=PriorityClass.EXPRESS)
    assert train.priority_class == PriorityClass.EXPRESS

def test_train_schedule():
    now = datetime.now(timezone.utc)
    entry = ScheduleEntry(segment_id="TS1", arrival_time=now, departure_time=now)
    schedule = TrainSchedule(train_id="T1", route=["TS1"], entries=[entry])
    assert schedule.current_status == "SCHEDULED"
    assert len(schedule.entries) == 1

def test_negotiation_message():
    now = datetime.now(timezone.utc)
    msg = NegotiationMessage(
        message_id="M1",
        sender_id="T1",
        receiver_id="T2",
        timestamp=now,
        action=NegotiationAction.PROPOSE,
        payload={"new_arrival": now.isoformat()}
    )
    assert msg.action == NegotiationAction.PROPOSE
    assert msg.original_proposal_id is None
