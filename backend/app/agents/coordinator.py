from typing import Dict, Any, List
from app.mcp import world_state, negotiation
from app.models.base import PriorityClass, TrainSchedule, Train
from app.store import store # For deterministic fallback, we need access to train priorities

def get_train_priority(train_id: str) -> PriorityClass:
    train = store.trains.get(train_id)
    return train.priority_class if train else PriorityClass.FREIGHT

def resolve_fallback(train_ids: List[str], conflicting_segment: str) -> Dict[str, Any]:
    """
    Deterministic priority-based rule: express > passenger > freight.
    Ties broken by earliest scheduled time (simulated here by ID sorting for simplicity, 
    but should ideally look at schedule entries).
    """
    # Priority mapping for sorting
    priority_val = {
        PriorityClass.EXPRESS: 1,
        PriorityClass.PASSENGER: 2,
        PriorityClass.FREIGHT: 3
    }
    
    # Sort trains by priority (lower number is higher priority), then by ID to break ties
    sorted_trains = sorted(train_ids, key=lambda tid: (priority_val.get(get_train_priority(tid), 3), tid))
    
    winner = sorted_trains[0]
    losers = sorted_trains[1:]
    
    # Dummy final schedule for fallback resolution
    final_schedule = {
        "winner": winner,
        "losers": losers,
        "segment": conflicting_segment,
        "resolution": "DETERMINISTIC_FALLBACK"
    }
    return final_schedule

def coordinator_tick(session_id: str, is_timeout: bool = False) -> str:
    """
    Coordinator evaluates the session. 
    If accepted, it commits.
    If timed out, it enforces fallback and commits.
    """
    logs = negotiation.get_log(session_id)
    if not logs:
        return "NO_LOGS"
        
    last_msg = logs[-1]
    train_ids = list(set([m["sender_id"] for m in logs] + [m["receiver_id"] for m in logs]))
    # Remove BROADCAST or COORD
    train_ids = [tid for tid in train_ids if tid not in ("COORD", "BROADCAST")]
    
    if is_timeout:
        # Enforce deterministic fallback
        final_schedule = resolve_fallback(train_ids, "UNKNOWN_SEGMENT") # Need segment info in real app
        res = negotiation.commit("COORD", train_ids, final_schedule, session_id)
        return "COMMITTED_FALLBACK"
        
    if last_msg["action"] == "ACCEPT":
        # Commit the accepted schedule
        # Find the proposal that was accepted
        proposal_msg = next((m for m in logs if m["message_id"] == last_msg["original_proposal_id"]), None)
        if proposal_msg:
            final_schedule = proposal_msg.get("payload", {})
            res = negotiation.commit("COORD", train_ids, final_schedule, session_id)
            return "COMMITTED_AGREEMENT"
            
    return "PENDING"
