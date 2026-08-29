from datetime import datetime, timezone
from app.store import store
from app.models.base import DisruptionEvent
from app.data.manager import get_data_provider

_provider = None

def _get_provider():
    global _provider
    if _provider is None:
        _provider = get_data_provider()
    return _provider


def report_delay(train_id: str, delay_minutes: int, cause: str, agent_id: str = "unknown", session_id: str = None) -> dict:
    event = DisruptionEvent(
        affected_station_or_segment=train_id,
        delay_minutes=delay_minutes,
        cause=cause,
    )
    store.add_disruption(event)
    if train_id in store.schedules:
        store.schedules[train_id].current_delay_minutes = delay_minutes
        store.schedules[train_id].current_status = "DELAYED"
    return {"ack": True, "event_id": event.event_id}


def get_active_disruptions(region: str = None, agent_id: str = "unknown", session_id: str = None) -> list:
    disruptions = store.get_active_disruptions()
    result = [d.model_dump(mode="json") for d in disruptions]
    if region:
        result = [d for d in result if region.lower() in d.get("affected_station_or_segment", "").lower()]
    return result


def get_downstream_dependents(train_id: str, agent_id: str = "unknown", session_id: str = None) -> dict:
    provider = _get_provider()
    deps = provider.get_downstream_dependents(train_id)
    return {"train_id": train_id, "dependents": deps}


def propose_reschedule(train_id: str, new_times: dict, agent_id: str = "unknown", session_id: str = None) -> dict:
    conflicts = []
    for seg_id in new_times:
        occupants = store.get_segment_occupancy(seg_id)
        for occ in occupants:
            if occ.train_id != train_id:
                conflicts.append({"segment": seg_id, "conflicting_train": occ.train_id})
    return {"ack": True, "train_id": train_id, "conflicts": conflicts}
