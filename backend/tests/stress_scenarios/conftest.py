import pytest
from app.store import store
from app.models.base import Train, TrainSchedule, ScheduleEntry, PriorityClass
from app.data.synthetic import SyntheticDataLoader
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def reset_store_and_load_data():
    """Reset store and load full synthetic dataset before each stress test."""
    store.stations.clear()
    store.segments.clear()
    store.trains.clear()
    store.schedules.clear()
    store.disruption_events.clear()
    store.cascade_impacts.clear()
    store.sessions.clear()
    store.negotiation_logs.clear()

    loader = SyntheticDataLoader(seed=42)
    for s in loader.load_stations():
        store.stations[s.id] = s
    for seg in loader.load_segments():
        store.segments[seg.id] = seg
    for t in loader.load_trains():
        store.trains[t.id] = t
    for sch in loader.load_schedules():
        store.schedules[sch.train_id] = sch
    yield
