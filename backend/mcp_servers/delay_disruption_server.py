"""
MCP Server B — Delay & Disruption
Tools: report_delay, get_active_disruptions, get_downstream_dependents, propose_reschedule
Runs on port 8002.
"""
from datetime import datetime, timezone
from mcp.server.mcpserver import MCPServer
from app.data.manager import get_data_provider
from app.store import store
from app.models.base import DisruptionEvent

mcp = MCPServer("DelayDisruption", version="1.0.0")

_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        _provider = get_data_provider()
    return _provider


def _log_tool_call(agent_id: str, tool: str, args: dict, result: dict, session_id: str = None):
    entry = {
        "event": "mcp_tool_call",
        "server": "DelayDisruption",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "tool": tool,
        "args": args,
        "result_summary": str(result)[:200],
    }
    if session_id:
        store._append_session_log(session_id, entry)


@mcp.tool()
def report_delay(train_id: str, delay_minutes: int, cause: str, agent_id: str = "unknown", session_id: str = None) -> dict:
    """Agent reports its own delay into the system."""
    event = DisruptionEvent(
        affected_station_or_segment=train_id,
        delay_minutes=delay_minutes,
        cause=cause,
    )
    store.add_disruption(event)
    # Update live schedule
    if train_id in store.schedules:
        store.schedules[train_id].current_delay_minutes = delay_minutes
        store.schedules[train_id].current_status = "DELAYED"
    result = {"ack": True, "event_id": event.event_id}
    _log_tool_call(agent_id, "report_delay", {"train_id": train_id, "delay_minutes": delay_minutes}, result, session_id)
    return result


@mcp.tool()
def get_active_disruptions(region: str = None, agent_id: str = "unknown", session_id: str = None) -> list:
    """Get all active disruption events, optionally filtered by region."""
    disruptions = store.get_active_disruptions()
    result = [d.model_dump(mode="json") for d in disruptions]
    if region:
        result = [d for d in result if region.lower() in d.get("affected_station_or_segment", "").lower()]
    _log_tool_call(agent_id, "get_active_disruptions", {"region": region}, {"count": len(result)}, session_id)
    return result


@mcp.tool()
def get_downstream_dependents(train_id: str, agent_id: str = "unknown", session_id: str = None) -> dict:
    """Get trains sharing track or platform ahead of this train."""
    provider = _get_provider()
    deps = provider.get_downstream_dependents(train_id)
    result = {"train_id": train_id, "dependents": deps}
    _log_tool_call(agent_id, "get_downstream_dependents", {"train_id": train_id}, result, session_id)
    return result


@mcp.tool()
def propose_reschedule(train_id: str, new_times: dict, agent_id: str = "unknown", session_id: str = None) -> dict:
    """Propose a rescheduling change. Returns ack + any conflict flags."""
    provider = _get_provider()
    conflicts = []
    for seg_id, times in new_times.items():
        occupants = store.get_segment_occupancy(seg_id)
        for occ in occupants:
            if occ.train_id != train_id:
                conflicts.append({"segment": seg_id, "conflicting_train": occ.train_id})
    result = {"ack": True, "train_id": train_id, "conflicts": conflicts}
    _log_tool_call(agent_id, "propose_reschedule", {"train_id": train_id}, result, session_id)
    return result


if __name__ == "__main__":
    import uvicorn
    app = mcp.sse_app()
    uvicorn.run(app, host="0.0.0.0", port=8002)
