# RailMesh 🚂

A Swarm-Based Railway Delay Cascade Simulator & Advisory Layer built for the Tenori Stateless Hackathon \u00d7 LICET 2026.

## Overview
RailMesh is a multi-agent decision-support system that simulates cascading delays across a railway network (modeled after Indian Railways). Given a disruption, a swarm of LLM agents (one per affected train) detects the issue, models the cascade, and genuinely negotiates rescheduling priorities with each other in a verifiable, multi-turn loop.

> **Note:** RailMesh is an **advisory layer and simulator only**. It never interfaces with real signaling (CTC) or safety infrastructure (KAVACH).

## Core Architecture
- **Backend**: Python 3.11+, FastAPI, LangGraph, MCP (Model Context Protocol 2.0).
- **Agents**: Gemini 2.5 Flash via `google-genai` SDK.
- **Frontend**: React + TypeScript + Vite.

For detailed architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
For the negotiation rules, see [docs/NEGOTIATION_PROTOCOL.md](docs/NEGOTIATION_PROTOCOL.md).

## Quick Start (Demo)
Run the automated demo script, which starts the backend, the frontend, and injects a disruption to show the agents working live.

1. Rename `.env.example` to `.env` in `backend/` and add your `GOOGLE_API_KEY`.
2. Run the demo script from PowerShell:
   ```powershell
   .\scripts\run_demo.ps1
   ```
3. Open `http://localhost:5173` to view the dashboard!

## Running Tests
RailMesh comes with robust tests, including stress tests for deadlock and dropout recovery.
```powershell
cd backend
.venv\Scripts\python -m pytest tests/ -v
```
Stress tests use a deterministic fallback mechanism, allowing them to pass even without an API key!
