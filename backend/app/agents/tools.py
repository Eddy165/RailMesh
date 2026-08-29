from langchain_core.tools import tool
from typing import Dict, List, Any
import json
from app.mcp import world_state, negotiation

# Wrap WorldState MCP functions as LangChain tools

@tool
def get_train_status(train_id: str) -> str:
    """Fetch the current schedule and status for a specific train."""
    return json.dumps(world_state.get_train_status(train_id))

@tool
def get_segment_occupancy(segment_id: str) -> str:
    """Get a list of trains that are scheduled to occupy a specific track segment."""
    return json.dumps(world_state.get_segment_occupancy(segment_id))

@tool
def get_network_snapshot() -> str:
    """Retrieve the current snapshot of the entire railway network."""
    return json.dumps(world_state.get_network_snapshot())

@tool
def get_dependency_graph(train_id: str) -> str:
    """Get the dependency graph (which trains affect which) starting from a specific train."""
    return json.dumps(world_state.get_dependency_graph(train_id))

# Wrap Negotiation MCP functions as LangChain tools

@tool
def propose(sender_id: str, receiver_id: str, proposed_schedule: Dict[str, Any]) -> str:
    """Propose a schedule change to another train or coordinator."""
    return json.dumps(negotiation.propose(sender_id, receiver_id, proposed_schedule))

@tool
def counter(sender_id: str, receiver_id: str, original_proposal_id: str, counter_schedule: Dict[str, Any]) -> str:
    """Counter a previous proposal with a new schedule."""
    return json.dumps(negotiation.counter(sender_id, receiver_id, original_proposal_id, counter_schedule))

@tool
def accept(sender_id: str, receiver_id: str, original_proposal_id: str) -> str:
    """Accept a proposed schedule change."""
    return json.dumps(negotiation.accept(sender_id, receiver_id, original_proposal_id))

@tool
def reject(sender_id: str, receiver_id: str, original_proposal_id: str, reason: str) -> str:
    """Reject a proposed schedule change with a reason."""
    return json.dumps(negotiation.reject(sender_id, receiver_id, original_proposal_id, reason))

@tool
def get_log(session_id: str = None) -> str:
    """Get the negotiation log for a specific session or the entire history."""
    return json.dumps(negotiation.get_log(session_id))
