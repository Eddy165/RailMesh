# 🚆 RailMesh

### **When one train falls behind, the network shouldn't.**

**A Swarm-Based Railway Delay Cascade Simulator & Advisory Layer**

> **Tenori × Stateless × LICET Hackathon 2026**
> **Track 02 — Agentic Web, Swarms & Harnesses**

---

## ⚡ The Idea in One Sentence

**RailMesh gives every train its own AI agent and lets those agents negotiate with one another to contain cascading railway delays — before they become network-wide problems.**

---

## 🛤️ The Problem

A railway network doesn't experience delays one train at a time.

A train arrives **8 minutes late**.

That train occupies a platform.

The next train cannot depart.

It misses a crossing.

A junction changes priority.

Another train waits.

And suddenly, a delay that started with **one train** has become a **network problem**.

```text
        🚆 T01
       +8 min
          │
          ▼
   Platform occupied
          │
          ▼
        🚆 T02
     departure delayed
          │
          ▼
      Junction conflict
          │
          ▼
        🚆 T03
     crossing delayed
          │
          ▼
      🌐 CASCADE
```

Today's railway control systems are excellent at showing **what is happening**.

The harder question is:

> **What is about to happen because of it?**

Controllers often have to reason across trains, platforms, junctions and sections manually.

RailMesh explores a different model:

> **What if the railway network could reason about itself?**

---

# 🧠 The RailMesh Approach

Instead of building one giant AI that knows everything, RailMesh distributes intelligence across the network.

### Every train gets an agent.

Each agent understands:

* 📍 Current position
* 🕐 Schedule
* ⏱️ Delay
* 🚦 Local constraints
* 🛤️ Track availability
* 🔀 Junction conflicts
* 🚆 Nearby trains

When disruption occurs, agents don't simply report it.

**They negotiate.**

```text
                 🚆 Train Agent A
                       │
                       │ Proposal
                       ▼
              ┌──────────────────┐
              │   NEGOTIATION     │
              │      LAYER        │
              └──────────────────┘
                 ▲      ▲      ▲
                 │      │      │
                 │      │      │
          🚆 Train B  🔀 Junction  🛤️ Section
             Agent       Agent      Agent
```

The goal isn't to find the mathematically perfect schedule.

The goal is to find a **network-coherent response** that agents can reach through local coordination.

---

# 🌐 Why Now?

Three technologies have converged.

### 01 — Cheap, capable LLM reasoning

LLMs are becoming practical enough to act as **per-entity reasoning units**, rather than only serving as a single centralized intelligence.

RailMesh takes advantage of this by giving individual trains their own lightweight reasoning agents.

---

### 02 — MCP

**Model Context Protocol** makes structured tool access a protocol-level problem.

Instead of hard-wiring every agent to every data source, RailMesh can expose railway information through tools such as:

```text
📅 Schedule
🚦 Signal state
🛤️ Track occupancy
🏢 Platform availability
📊 Historical delays
```

Agents request the information they need when they need it.

---

### 03 — Multi-Agent Coordination

Modern agentic systems are increasingly moving from:

```text
Human → AI
```

toward:

```text
Human
  │
  ▼
AI Agent ↔ AI Agent ↔ AI Agent
```

With A2A patterns and documented multi-agent failure modes such as MAST, there is now a meaningful design space around **agent handoffs, coordination, failure recovery and convergence**.

RailMesh puts those ideas into a concrete real-world problem.

---

# 🚦 What RailMesh Does

RailMesh simulates a railway network in which:

### 🚆 Every train has an agent

Each train maintains its own local view of:

* schedule
* position
* delay
* constraints
* neighboring trains

### 🤝 Agents negotiate

When a disruption occurs, the affected agent can initiate a negotiation with relevant agents.

### 🧩 Agents have different responsibilities

A negotiation may involve:

**Train Agents**

> "I need another 4 minutes before departure."

**Section Controller Agent**

> "That section cannot accommodate both movements simultaneously."

**Junction Agent**

> "Train B has crossing priority."

**Downstream Train Agent**

> "If you take this slot, my arrival moves beyond the threshold."

---

# 🔄 How a Cascade Becomes a Negotiation

```text
                 DELAY EVENT
                     │
                     ▼
             🚆 Affected Train
                  Agent
                     │
                     ▼
          Detect local impact
                     │
                     ▼
          Start negotiation
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
      🚆 Train    🛤️ Section   🔀 Junction
       Agents     Controller     Agent
          │          │            │
          └──────────┼────────────┘
                     ▼
             Exchange proposals
                     │
                     ▼
              Detect conflicts
                     │
                     ▼
             Counter-proposals
                     │
                     ▼
             ┌───────────────┐
             │  CONVERGENCE? │
             └───────┬───────┘
                 YES │ NO
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
      REPLAN              FAIL / ESCALATE
          │                     │
          └──────────┬──────────┘
                     ▼
              👤 HUMAN ADVISORY
```

---

# 🏗️ Architecture

```text
┌───────────────────────────────────────────────────────────┐
│                       RAILMESH                             │
│                                                           │
│   🚆 Train       🚆 Train       🚆 Train       🚆 Train   │
│   Agent          Agent          Agent          Agent      │
│      │              │              │              │       │
│      └──────────────┼──────────────┼──────────────┘       │
│                     ▼                                     │
│          ┌─────────────────────────┐                      │
│          │   NEGOTIATION ENGINE    │                      │
│          │                         │                      │
│          │ Proposal                │                      │
│          │ Counter-proposal        │                      │
│          │ Conflict detection      │                      │
│          │ Priority resolution     │                      │
│          │ Convergence / failure   │                      │
│          └────────────┬────────────┘                      │
│                       ▼                                   │
│          ┌─────────────────────────┐                      │
│          │       MCP LAYER         │                      │
│          │                         │                      │
│          │ 📅 Schedule             │                      │
│          │ 🛤️ Track occupancy      │                      │
│          │ 🚦 Signal state         │                      │
│          │ 📊 Historical delays    │                      │
│          └────────────┬────────────┘                      │
│                       ▼                                   │
│          ┌─────────────────────────┐                      │
│          │   ADVISORY + DASHBOARD  │                      │
│          │                         │                      │
│          │ Cascade visualization   │                      │
│          │ Agent proposals         │                      │
│          │ Conflict timeline       │                      │
│          │ Human-readable reasons  │                      │
│          └─────────────────────────┘                      │
└───────────────────────────────────────────────────────────┘
```

### 🔑 The critical design decision

**There is no single agent with global network state.**

Each agent reasons using:

> **Local knowledge + information received through negotiation**

That makes coordination harder.

And that's precisely the point.

---

# 🤝 The Handoff Test

Track 02 asks a deceptively simple question:

> **"Give the system a real job, involving more than one agent. Then leave it alone. Does the handoff hold?"**

RailMesh treats this as a first-class engineering requirement.

We don't just demonstrate agents talking.

We **stress the coordination system**.

| Scenario                  | What we're testing                          |
| ------------------------- | ------------------------------------------- |
| 🟢 Single delay           | Does the simplest negotiation converge?     |
| 🟡 Multiple delays        | Can agents coordinate concurrently?         |
| 🔴 Conflicting priorities | Can conflicts be resolved without deadlock? |
| ⚫ Agent failure           | Does the network degrade gracefully?        |

Results and failure cases are recorded under:

```text
/tests/handoff-scenarios/
```

**Failure isn't hidden.**

A multi-agent system that only works when everything goes right isn't robust.

---

# 👤 Advisory, Not Autonomous

RailMesh is deliberately **not** an autonomous railway controller.

It is an **advisory layer**.

Instead of:

```text
AI → Change railway operations
```

RailMesh proposes:

```text
NETWORK EVENT
      ↓
AGENT NEGOTIATION
      ↓
PROPOSED REPLAN
      ↓
WHY?
      ↓
👤 HUMAN CONTROLLER
```

The system explains:

* **What is happening**
* **Which trains are affected**
* **Why the cascade is occurring**
* **What agents proposed**
* **Which constraints influenced the proposal**
* **Whether negotiation converged**

The human remains in control.

---

# 🧬 Why a Swarm?

A centralized optimizer might attempt:

```text
NETWORK → CENTRAL AI → DECISION
```

RailMesh explores:

```text
             🚆
              ↕
       🚆 ↔ 🚆 ↔ 🚆
              ↕
          🔀 Junction
              ↕
          🛤️ Section
```

This creates an interesting property:

### Local decisions can produce global behavior.

No train needs to understand the entire railway.

It only needs to understand:

> **"What do I know, what do I need, and who do I need to negotiate with?"**

That is the core experiment behind RailMesh.

---

# 🛠️ Tech Stack

| Layer                  | Technology                                           |
| ---------------------- | ---------------------------------------------------- |
| 🧠 Agent reasoning     | LLM-backed per-train agents                          |
| 🤝 Agent communication | Custom negotiation protocol inspired by A2A patterns |
| 🔌 Data access         | Model Context Protocol (MCP)                         |
| ⚙️ Backend             | Python / Node.js                                     |
| 🖥️ Dashboard          | React                                                |
| 🚆 Simulation          | Synthetic / open railway datasets                    |
| 🧪 Validation          | Automated handoff & stress scenarios                 |

> **The implementation stack will be finalized as the MVP is assembled.**

---

# 📂 Project Structure

```text
railmesh/
│
├── agents/
│   └── Per-train agent logic
│
├── negotiation/
│   └── Proposal / counter / conflict / convergence
│
├── mcp-tools/
│   └── Schedule
│   └── Track occupancy
│   └── Signal state
│   └── Historical data
│
├── dashboard/
│   └── Cascade visualization
│   └── Agent activity
│   └── Advisory output
│
├── tests/
│   └── handoff-scenarios/
│
├── docs/
│   └── architecture.md
│
├── .env.example
├── LICENSE
└── README.md
```

---

# 🚀 Getting Started

```bash
# Clone
git clone https://github.com/<your-org>/railmesh.git

cd railmesh

# Install dependencies
<fill in>

# Configure environment
cp .env.example .env

# Add API keys / MCP configuration
# to .env

# Start simulator
<fill in>

# Start dashboard
<fill in>
```

> **Clean-machine reproducibility is part of the Execution criterion.**

The final submission will target:

```text
git clone
    ↓
install
    ↓
configure
    ↓
run
    ↓
🚆 WATCH THE NETWORK REASON
```

---

# 🎬 Demo

### **One delay. One network. Multiple agents.**

The demo will show:

```text
01  A train falls behind schedule
             ↓
02  Its agent detects a conflict
             ↓
03  Neighboring agents are contacted
             ↓
04  Proposals are exchanged
             ↓
05  Conflicts appear
             ↓
06  Agents negotiate
             ↓
07  A replan converges
             ↓
08  Dashboard explains WHY
```

### Demo narrative

**Problem → Disruption → Cascade → Negotiation → Resolution → Advisory**

📹 **3–4 minute demo / pitch video:**
*Add link once recorded.*

---

# 🗺️ Roadmap

### Phase 01 — Make the Swarm Work

* [ ] Per-train agent architecture
* [ ] Network simulation
* [ ] Delay injection
* [ ] Basic negotiation protocol
* [ ] Proposal / counter-proposal flow
* [ ] Convergence detection

### Phase 02 — Connect the World

* [ ] MCP schedule tools
* [ ] Track occupancy tools
* [ ] Signal state tools
* [ ] Historical delay data
* [ ] Dynamic network state

### Phase 03 — Make It Visible

* [ ] Live cascade visualization
* [ ] Agent activity stream
* [ ] Negotiation timeline
* [ ] Conflict visualization
* [ ] Human-readable advisory output

### Phase 04 — Break It

* [ ] Simultaneous disruptions
* [ ] Conflicting priorities
* [ ] Unresponsive agents
* [ ] Negotiation timeouts
* [ ] Deadlock scenarios
* [ ] Graceful degradation

### Beyond the Hackathon

* Real railway datasets
* Richer operational constraints
* More realistic priority models
* Larger network simulations
* Human-controller evaluation

---

# 🧪 What We Actually Want to Learn

RailMesh isn't only a railway simulator.

It is an experiment in **distributed AI coordination**.

We want to answer:

> Can many small, locally-informed agents coordinate well enough to produce useful global behavior?

And more importantly:

> **What happens when they don't?**

The failures may be just as valuable as the successful negotiations.

---

# 🌐 Why No Web3?

RailMesh deliberately avoids adding crypto or blockchain infrastructure simply to satisfy a "New Internet" narrative.

There is currently no genuine requirement for it.

Our principle is simple:

> **Don't add infrastructure that doesn't solve the problem.**

If a real use case for programmable or decentralized infrastructure emerges during development, we'll evaluate it.

Until then:

**Ship the useful thing.**

**LICET IT Department**
Tenori × Stateless × LICET Hackathon 2026

---

# 🏁 The Bigger Idea

RailMesh starts with railway delays.

But the underlying problem is much broader.

Modern infrastructure is increasingly:

* distributed
* interconnected
* dynamic
* too complex for one decision-maker to model perfectly

RailMesh explores a future where infrastructure isn't controlled by one giant intelligence.

Instead:

> **Many specialized agents understand their local world, communicate, negotiate, recover from failure, and collectively produce a coherent plan.**

For railways, that could mean fewer cascading delays.

For agentic systems, it means something bigger:

### **The network itself becomes part of the intelligence.**

---

## 🚆 RailMesh

**Don't just predict the delay.**

**Understand the cascade.**

**Let the network negotiate.**

---

### License

This project is licensed under the **MIT License**.

Built for **Tenori Labs × Stateless × LICET — 2026**.
