from langchain_core.tools import tool
from typing import Dict, List, Any, Optional
import json
from app.mcp import world_state, negotiation


# ---- Schedule & Position tools (Server A) ----

@tool
def get_train_status(train_id: str) -> str:
    """Fetch the current schedule and status for a specific train."""
    return json.dumps(world_state.get_train_status(train_id))


@tool
def get_segment_occupancy(segment_id: str) -> str:
    """Get trains scheduled on a specific track segment."""
    return json.dumps(world_state.get_segment_occupancy(segment_id))


@tool
def get_network_snapshot() -> str:
    """Retrieve the current snapshot of the entire railway network."""
    return json.dumps(world_state.get_network_snapshot())


@tool
def get_dependency_graph(train_id: str) -> str:
    """Get which trains share segments with the given train."""
    return json.dumps(world_state.get_dependency_graph(train_id))


# ---- Delay & Disruption tools (Server B) ----

@tool
def report_delay(train_id: str, delay_minutes: int, cause: str) -> str:
    """Report this train's delay into the system."""
    from app.mcp.delay_disruption import report_delay as _report
    return json.dumps(_report(train_id=train_id, delay_minutes=delay_minutes, cause=cause))


@tool
def get_active_disruptions(region: Optional[str] = None) -> str:
    """Get all active disruptions, optionally filtered by region/segment."""
    from app.mcp.delay_disruption import get_active_disruptions as _get
    return json.dumps(_get(region=region))


@tool
def get_downstream_dependents_tool(train_id: str) -> str:
    """Get trains that share track/platform downstream of this train."""
    from app.mcp.delay_disruption import get_downstream_dependents as _get
    return json.dumps(_get(train_id=train_id))


@tool
def propose_reschedule_tool(train_id: str, new_times: Dict[str, Any]) -> str:
    """Propose a rescheduling change and get back conflict flags."""
    from app.mcp.delay_disruption import propose_reschedule as _propose
    return json.dumps(_propose(train_id=train_id, new_times=new_times))


# ---- Negotiation tools ----

@tool
def propose(sender_id: str, receiver_id: str, proposed_schedule: Dict[str, Any], session_id: str = "default") -> str:
    """Propose a schedule change to another train."""
    return json.dumps(negotiation.propose(sender_id, receiver_id, proposed_schedule, session_id))


@tool
def counter(sender_id: str, receiver_id: str, original_proposal_id: str, counter_schedule: Dict[str, Any], session_id: str = "default") -> str:
    """Counter a previous proposal with a modified schedule."""
    return json.dumps(negotiation.counter(sender_id, receiver_id, original_proposal_id, counter_schedule, session_id))


@tool
def accept(sender_id: str, receiver_id: str, original_proposal_id: str, session_id: str = "default") -> str:
    """Accept a proposed schedule change."""
    return json.dumps(negotiation.accept(sender_id, receiver_id, original_proposal_id, session_id))


@tool
def reject(sender_id: str, receiver_id: str, original_proposal_id: str, reason: str, session_id: str = "default") -> str:
    """Reject a proposed schedule change with a reason."""
    return json.dumps(negotiation.reject(sender_id, receiver_id, original_proposal_id, reason, session_id))


@tool
def get_log(session_id: str = None) -> str:
    """Get the negotiation log for a session or all history."""
    return json.dumps(negotiation.get_log(session_id))
