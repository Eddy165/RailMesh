"""
MCP Server A — Schedule & Position
Tools: get_schedule, get_position, get_route_graph, get_platform_occupancy
Runs on port 8001 via FastMCP/MCPServer SSE transport.
"""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from mcp.server.mcpserver import MCPServer
from app.data.manager import get_data_provider
from app.store import store

mcp = MCPServer("SchedulePosition", version="1.0.0")

_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        _provider = get_data_provider()
    return _provider


def _log_tool_call(agent_id: str, tool: str, args: dict, result: dict, session_id: str = None):
    entry = {
        "event": "mcp_tool_call",
        "server": "SchedulePosition",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "tool": tool,
        "args": args,
        "result_summary": str(result)[:200],
    }
    if session_id:
        store._append_session_log(session_id, entry)


@mcp.tool()
def get_schedule(train_id: str, agent_id: str = "unknown", session_id: str = None) -> dict:
    """Get the full schedule (route + timetable) for a train."""
    provider = _get_provider()
    sched = provider.get_schedule(train_id)
    result = sched.model_dump(mode="json") if sched else {"error": f"Train {train_id} not found"}
    _log_tool_call(agent_id, "get_schedule", {"train_id": train_id}, result, session_id)
    return result


@mcp.tool()
def get_position(train_id: str, agent_id: str = "unknown", session_id: str = None) -> dict:
    """Get the current position (segment) of a train."""
    provider = _get_provider()
    sched = provider.get_schedule(train_id)
    if not sched:
        return {"error": f"Train {train_id} not found"}
    # Use live store delay if available
    live = store.schedules.get(train_id)
    delay = live.current_delay_minutes if live else 0
    result = {
        "train_id": train_id,
        "current_segment": sched.route[0] if sched.route else None,
        "status": sched.current_status,
        "current_delay_minutes": delay,
    }
    _log_tool_call(agent_id, "get_position", {"train_id": train_id}, result, session_id)
    return result


@mcp.tool()
def get_route_graph(agent_id: str = "unknown", session_id: str = None) -> dict:
    """Get the full station/segment adjacency graph."""
    provider = _get_provider()
    result = provider.get_route_graph()
    _log_tool_call(agent_id, "get_route_graph", {}, result, session_id)
    return result


@mcp.tool()
def get_platform_occupancy(station_id: str, time_window_minutes: int = 120, agent_id: str = "unknown", session_id: str = None) -> dict:
    """Get trains occupying or scheduled at a station within a time window."""
    provider = _get_provider()
    trains_at_station = []
    for sched in provider.get_schedules():
        for entry in sched.entries:
            seg = provider.get_segment(entry.segment_id)
            if seg and (seg.source_id == station_id or seg.target_id == station_id):
                trains_at_station.append({
                    "train_id": sched.train_id,
                    "segment_id": entry.segment_id,
                    "arrival_time": entry.arrival_time.isoformat(),
                    "departure_time": entry.departure_time.isoformat(),
                })
    result = {"station_id": station_id, "occupants": trains_at_station}
    _log_tool_call(agent_id, "get_platform_occupancy", {"station_id": station_id}, result, session_id)
    return result


if __name__ == "__main__":
    import uvicorn
    app = mcp.sse_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
