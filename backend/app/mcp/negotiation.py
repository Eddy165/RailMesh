import uuid
from datetime import datetime, timezone
from mcp.server.mcpserver import MCPServer
from app.store import store
from app.models.base import NegotiationAction, NegotiationMessage

# Create the Negotiation MCPServer
# Protocol execution: propose, counter, accept, reject, commit, get_log.

mcp = MCPServer("Negotiation")

def _record_action(action: NegotiationAction, sender_id: str, receiver_id: str, payload: dict, original_proposal_id: str = None) -> dict:
    msg_id = str(uuid.uuid4())
    msg = NegotiationMessage(
        message_id=msg_id,
        sender_id=sender_id,
        receiver_id=receiver_id,
        timestamp=datetime.now(timezone.utc),
        action=action,
        payload=payload,
        original_proposal_id=original_proposal_id
    )
    store.append_negotiation_message(msg)
    return msg.model_dump(mode="json")

@mcp.tool()
def propose(sender_id: str, receiver_id: str, proposed_schedule: dict) -> dict:
    """Propose a schedule change to another train or coordinator."""
    return _record_action(NegotiationAction.PROPOSE, sender_id, receiver_id, {"proposed_schedule": proposed_schedule})

@mcp.tool()
def counter(sender_id: str, receiver_id: str, original_proposal_id: str, counter_schedule: dict) -> dict:
    """Counter a previous proposal with a new schedule."""
    return _record_action(NegotiationAction.COUNTER, sender_id, receiver_id, {"counter_schedule": counter_schedule}, original_proposal_id)

@mcp.tool()
def accept(sender_id: str, receiver_id: str, original_proposal_id: str) -> dict:
    """Accept a proposed schedule change."""
    return _record_action(NegotiationAction.ACCEPT, sender_id, receiver_id, {"status": "accepted"}, original_proposal_id)

@mcp.tool()
def reject(sender_id: str, receiver_id: str, original_proposal_id: str, reason: str) -> dict:
    """Reject a proposed schedule change with a reason."""
    return _record_action(NegotiationAction.REJECT, sender_id, receiver_id, {"reason": reason}, original_proposal_id)

@mcp.tool()
def commit(coordinator_id: str, train_ids: list[str], final_schedule: dict, session_id: str) -> dict:
    """Coordinator commits the final schedule, avoiding split-brain."""
    # Assuming coordinator broadcasts to all involved trains. 
    # For simplicity, we record one COMMIT message.
    return _record_action(NegotiationAction.COMMIT, coordinator_id, "BROADCAST", {"final_schedule": final_schedule}, session_id)

@mcp.tool()
def get_log(session_id: str = None) -> list[dict]:
    """Get the negotiation log for a specific session or the entire history."""
    return store.get_negotiation_log(session_id)
