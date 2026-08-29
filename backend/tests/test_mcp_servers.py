import pytest
from app.mcp.world_state import get_train_status, get_segment_occupancy, get_network_snapshot, get_dependency_graph
from app.mcp.negotiation import propose, counter, accept, reject, commit, get_log
from app.store import store
from app.models.base import Station, TrackSegment, Train, TrainSchedule, ScheduleEntry, PriorityClass
from datetime import datetime, timezone

@pytest.fixture(autouse=True)
def reset_store():
    # Reset store before each test
    store.stations.clear()
    store.segments.clear()
    store.trains.clear()
    store.schedules.clear()
    store.negotiation_sessions.clear()
    store.negotiation_logs.clear()

def test_world_state_mcp():
    # Setup some data
    now = datetime.now(timezone.utc)
    station = Station(id="S1", name="Station 1")
    segment = TrackSegment(id="SEG1", source_id="S1", target_id="S2", length_km=10.0, travel_time_mins=10)
    store.stations["S1"] = station
    store.segments["SEG1"] = segment
    
    entry = ScheduleEntry(segment_id="SEG1", arrival_time=now, departure_time=now)
    schedule = TrainSchedule(train_id="T1", route=["SEG1"], entries=[entry])
    store.schedules["T1"] = schedule

    # Test tools
    status_res = get_train_status("T1")
    assert status_res["train_id"] == "T1"

    status_res_missing = get_train_status("T2")
    assert "error" in status_res_missing

    snapshot = get_network_snapshot()
    assert len(snapshot["stations"]) == 1
    assert snapshot["stations"][0]["id"] == "S1"

    occupants = get_segment_occupancy("SEG1")
    assert occupants["segment_id"] == "SEG1"
    assert len(occupants["occupants"]) == 1
    assert occupants["occupants"][0]["train_id"] == "T1"

def test_negotiation_mcp():
    # Propose
    prop_res = propose("T1", "T2", {"arrival": "10:00"})
    assert prop_res["action"] == "PROPOSE"
    msg_id = prop_res["message_id"]

    # Counter
    count_res = counter("T2", "T1", msg_id, {"arrival": "10:15"})
    assert count_res["action"] == "COUNTER"
    assert count_res["original_proposal_id"] == msg_id

    # Accept
    acc_res = accept("T1", "T2", msg_id)
    assert acc_res["action"] == "ACCEPT"

    # Reject
    rej_res = reject("T2", "T1", msg_id, "Track full")
    assert rej_res["action"] == "REJECT"

    # Commit
    com_res = commit("COORD", ["T1", "T2"], {"final": "schedule"}, "default")
    assert com_res["action"] == "COMMIT"

    # Get log
    logs = get_log("default")
    assert len(logs) == 5
    assert logs[-1]["action"] == "COMMIT"
