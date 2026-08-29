RailMesh
A Swarm-Based Railway Delay Cascade Simulator & Advisory Layer

Built for the Tenori × Stateless × LICET Hackathon 2026 — Track 02: Agentic Web, Swarms & Harnesses

  


Table of Contents
The Problem
Why Now
What RailMesh Does
How It Works
Architecture
The Handoff Test
Tech Stack
Getting Started
Project Structure
Demo
Roadmap
Team
License


The Problem
A single delayed train rarely stays a single problem. On a shared network, one late arrival can hold up a platform, which delays the next train's departure, which cascades into a crossing conflict three stations down — all within minutes, and all invisible to any one dispatcher watching their own section of track.

Today, this kind of cross-network reasoning is done manually, reactively, and locally — a controller reacts to what's in front of them, not what's about to happen two junctions away because of a decision they just made. There is no system that lets the network reason about itself.

RailMesh asks: what if every train had an agent, and those agents had to negotiate with each other in real time to keep the network coherent?
Why Now
This class of system wasn't practically buildable a few years ago, for three converging reasons:

LLM reasoning is now cheap enough to run per-entity, not just per-system. Instead of one centralized optimizer trying to model an entire network, each train can have its own lightweight reasoning agent — closer to how the real system actually works (distributed, local decision-makers).
MCP (Model Context Protocol) standardized tool access. Wiring an agent into live schedule, signal, and track-occupancy data used to mean bespoke integration work per data source. MCP turns that into a protocol-level problem, not a plumbing problem.
Multi-agent negotiation patterns have matured. With A2A (Agent-to-Agent) protocol reaching v1.0 in 2026, and a growing body of documented failure modes (see MAST taxonomy) for how agent handoffs break, there's now a known design space to build in — rather than uncharted research territory.

Put together: the reasoning is affordable, the data access is standardized, and the coordination patterns are known. That combination is what makes RailMesh a 2026 project, not a 2023 one.
What RailMesh Does
RailMesh simulates a railway network where:

Each train is represented by its own LLM-backed agent, aware of its own schedule, position, and constraints.
When a delay occurs, the affected agent doesn't just report the delay — it negotiates with neighboring train agents and junction/section controllers to find a network-coherent replan.
The system produces an advisory layer: a human-readable explanation of what's about to happen, why, and what the agents propose to do about it — not a black-box auto-decision.
A dashboard visualizes the cascade in real time: which trains are affected, what the agents proposed, and whether the negotiation converged.

RailMesh is explicitly advisory, not autonomous — it's designed to make cascading failure visible and explainable to a human controller, not to replace one.
How It Works
Delay Event

    │

    ▼

Affected Train Agent detects impact

    │

    ▼

Negotiation Protocol initiated with neighboring agents

    │

    ├── Section Controller Agent (track/platform availability)

    ├── Downstream Train Agents (schedule conflicts)

    └── Junction Agent (crossing priority)

    │

    ▼

Proposals exchanged → conflicts flagged → replan converges (or fails)

    │

    ▼

Advisory Output: human-readable cascade explanation + recommended replan

Each agent reasons only over what it locally knows and what it receives from other agents during negotiation — there is no single agent with global network state. This is intentional: it's the harder, more realistic version of the problem, and it's the version Track 02 asks for.
Architecture
┌─────────────────────────────────────────────────────────┐

│                     RailMesh System                      │

│                                                         │

│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │

│  │ Train Agent  │◄─►│ Train Agent  │◄─►│ Train Agent  │ │

│  │   (per unit) │   │   (per unit) │   │   (per unit) │ │

│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘ │

│         │                  │                  │          │

│         └──────────┬───────┴──────────┬───────┘          │

│                     ▼                  ▼                  │

│           ┌──────────────────────────────────┐            │

│           │   Negotiation Protocol Layer      │            │

│           │  (proposal / counter / converge)  │            │

│           └────────────────┬───────────────────┘           │

│                             │                               │

│                             ▼                               │

│           ┌──────────────────────────────────┐            │

│           │        MCP Tool Layer             │            │

│           │  (schedule data, track occupancy, │            │

│           │   signal state, historical delays)│            │

│           └────────────────┬───────────────────┘           │

│                             │                               │

│                             ▼                               │

│           ┌──────────────────────────────────┐            │

│           │   Advisory / Dashboard Layer      │            │

│           │  (cascade viz + human-readable    │            │

│           │   explanation of agent decisions) │            │

│           └──────────────────────────────────┘            │

└─────────────────────────────────────────────────────────┘

Key design decision: Web3/crypto infrastructure is deliberately excluded from this build unless a genuine use case emerges during development — the problem doesn't currently require it, and we'd rather ship something real than force a "New Internet" primitive in that doesn't earn its place.
The Handoff Test
Track 02's brief sets an explicit bar: "Give the system a real job, involving more than one agent. Then leave it alone. Does the handoff hold?"

RailMesh is tested against this directly with unattended stress scenarios:

Scenario
What it tests
Single delay, low network density
Baseline — does the simplest handoff converge cleanly?
Multiple simultaneous delays
Do agents correctly prioritize when several negotiations run concurrently?
Conflicting agent priorities
Does the protocol have a resolution mechanism, or does it deadlock?
One agent unresponsive/failing
Does the system degrade gracefully, or does the whole negotiation stall?


Results — including honestly documented failure modes — are logged in /tests/handoff-scenarios/ and referenced in the demo video.
Tech Stack
Layer
Technology
Agent reasoning
LLM-backed per-train agents (Claude / configurable)
Agent communication
Custom negotiation protocol, informed by A2A patterns
Data access
MCP (Model Context Protocol)
Backend
(fill in: e.g. Node/Python)
Frontend / Dashboard
(fill in: e.g. React)
Simulation data
(fill in: synthetic / open rail dataset source)

Getting Started
# Clone the repository

git clone https://github.com/<your-org>/railmesh.git

cd railmesh

# Install dependencies

<fill in>

# Set up environment variables

cp .env.example .env

# Add your API keys / MCP server config to .env

# Run the simulator

<fill in>

# Run the dashboard

<fill in>

Note: Replace the placeholders above once the setup scripts are finalized. A working git clone → run path is part of the Execution criterion — test this on a clean machine before submission.
Project Structure
railmesh/

├── agents/              # Per-train agent logic

├── negotiation/         # Negotiation protocol implementation

├── mcp-tools/           # MCP server integrations (schedule, track, signal data)

├── dashboard/           # Visualization layer

├── tests/

│   └── handoff-scenarios/   # Unattended stress test results

├── docs/

│   └── architecture.md

├── .env.example

├── LICENSE

└── README.md
Demo
📹 [Link to 3-4 minute demo/pitch video — add once recorded]

The demo walks through: the problem → why now → a live cascading delay negotiation → what we'd build next.
Roadmap
Core negotiation protocol (MVP)
MCP integration for live/simulated schedule data
Dashboard visualization of cascade + agent reasoning
Stress-test suite (handoff scenarios)
Post-hackathon: real dataset integration, richer priority/conflict rules
Team
Name
Role
Edwin Mario A (Eddy)
(fill in role)
(teammate)
(fill in role)
(teammate)
(fill in role)


LICET IT Department — Tenori × Stateless × LICET Hackathon 2026
License
This project is licensed under the MIT License — see LICENSE for details.



Built for Tenori Labs × Stateless × LICET, 2026.

