from mcp.server.mcpserver import MCPServer
from typing import List, Optional
from app.store import store

# Create the WorldState MCPServer
# Read-mostly: train status, segment occupancy, network snapshot, dependency graph.

mcp = MCPServer("WorldState")

@mcp.tool()
def get_train_status(train_id: str) -> dict:
    """Fetch the current schedule and status for a specific train."""
    sched = store.get_train_status(train_id)
    if sched:
        return sched.model_dump(mode="json")
    return {"error": f"Train {train_id} not found."}

@mcp.tool()
def get_segment_occupancy(segment_id: str) -> dict:
    """Get a list of trains that are scheduled to occupy a specific track segment."""
    occupants = store.get_segment_occupancy(segment_id)
    return {"segment_id": segment_id, "occupants": [s.model_dump(mode="json") for s in occupants]}

@mcp.tool()
def get_network_snapshot() -> dict:
    """Retrieve the current snapshot of the entire railway network."""
    return store.get_network_snapshot()

@mcp.tool()
def get_dependency_graph(train_id: str) -> dict:
    """Get the dependency graph (which trains affect which) starting from a specific train."""
    return store.get_dependency_graph(train_id)
