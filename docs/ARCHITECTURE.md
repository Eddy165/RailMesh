# RailMesh Architecture

## Core Principles
1. **Advisory Only:** This system only simulates cascades and proposes new schedules. It has no integration with critical safety systems.
2. **True Multi-Turn:** Each agent invokes an LLM separately during each round of negotiation.
3. **Provable Rationale:** Every decision must include an English explanation (`rationale` field) that is written to a verifiable audit log.

## Components

### 1. The MCP Servers (Tools)
The backend runs two local MCP (Model Context Protocol 2.0) servers that the agents consume:
- **`schedule_position_server.py`**: Read-only tools for world state (`get_schedule`, `get_position`, `get_route_graph`, `get_platform_occupancy`).
- **`delay_disruption_server.py`**: State-modifying and analysis tools (`report_delay`, `get_active_disruptions`, `propose_reschedule`).

These use the native `mcp.server.mcpserver` package.

### 2. The Deterministic Cascade Engine (`cascade/`)
A graph-based (NetworkX) engine that takes an initial disruption and traverses the schedule to find all downstream effects:
- Segment blocks
- Platform contention (multiple trains arriving at once)
- Connecting service delays (trains waiting for passengers/crew)

### 3. The Negotiation Engine (`app/agents/`)
The coordinator creates a `NegotiationSession`. In a loop (up to `MAX_ROUNDS`):
- Each train agent evaluates the prior round's decisions and current state.
- The agent calls Gemini 2.5 Flash to generate a structured `AgentDecision`.
- The coordinator evaluates if consensus is reached, if it's deadlocked, or if more rounds are needed.
- If the LLM is down (or `GOOGLE_API_KEY` is missing), a deterministic fallback provides decisions to ensure resilience.

### 4. Event Store & Audit Log (`app/store.py`)
All sessions are stored in memory and flushed to disk as append-only JSONL files (`logs/sessions/{session_id}/audit.jsonl`).

### 5. FastAPI Backend (`api/`)
Provides REST endpoints to:
- Inject disruptions
- Poll active sessions and network snapshots
- SSE stream updates (for real-time dashboard)

### 6. React Dashboard (`frontend/`)
Visualizes the network map, live negotiation log, and schedule impact.
