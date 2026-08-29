from typing import Dict, Any, List, Optional
from app.mcp import world_state, negotiation
from app.models.base import PriorityClass, Train, AgentDecision
from app.store import store


PRIORITY_VAL = {
    PriorityClass.EXPRESS: 1,
    PriorityClass.PASSENGER: 2,
    PriorityClass.FREIGHT: 3,
}


def get_train_priority(train_id: str) -> PriorityClass:
    train = store.trains.get(train_id)
    return train.priority_class if train else PriorityClass.FREIGHT


def resolve_fallback(train_ids: List[str], conflicting_segment: str) -> Dict[str, Any]:
    """
    Deterministic priority-based fallback: express > passenger > freight.
    Ties broken alphabetically by ID.
    """
    sorted_trains = sorted(
        train_ids,
        key=lambda tid: (PRIORITY_VAL.get(get_train_priority(tid), 3), tid)
    )
    winner = sorted_trains[0]
    losers = sorted_trains[1:]
    return {
        "winner": winner,
        "losers": losers,
        "segment": conflicting_segment,
        "resolution": "DETERMINISTIC_FALLBACK",
    }


def coordinator_tick(session_id: str, is_timeout: bool = False) -> str:
    """
    Legacy coordinator for backward-compat with existing tests.
    Evaluates the session negotiation log.
    """
    logs = negotiation.get_log(session_id)
    if not logs:
        return "NO_LOGS"

    last_msg = logs[-1]
    train_ids = list(set(
        [m["sender_id"] for m in logs] + [m["receiver_id"] for m in logs]
    ))
    train_ids = [tid for tid in train_ids if tid not in ("COORD", "BROADCAST")]

    if is_timeout:
        final_schedule = resolve_fallback(train_ids, "UNKNOWN_SEGMENT")
        negotiation.commit("COORD", train_ids, final_schedule, session_id)
        return "COMMITTED_FALLBACK"

    if last_msg["action"] == "ACCEPT":
        proposal_msg = next(
            (m for m in logs if m["message_id"] == last_msg.get("original_proposal_id")), None
        )
        if proposal_msg:
            final_schedule = proposal_msg.get("payload", {})
            negotiation.commit("COORD", train_ids, final_schedule, session_id)
            return "COMMITTED_AGREEMENT"

    return "PENDING"
