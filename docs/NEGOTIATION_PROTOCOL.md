# RailMesh Negotiation Protocol

RailMesh trains negotiate schedule adjustments via a multi-turn, round-robin protocol.

## Terminology
- **Coordinator**: The centralized state machine that orchestrates rounds.
- **Participating Trains**: Trains affected by a cascade impact.
- **Round**: A single synchronized step where every participating train submits an `AgentDecision`.

## Valid Actions
Each agent MUST choose one of the following actions every round:
1. `counter_propose`: Used in early rounds to suggest a specific delay/segment adjustment.
2. `accept`: Used when another agent's counter-proposal is workable for this train's schedule.
3. `reject`: Used when a proposal is unworkable (often accompanied by a new counter-proposal).
4. `escalate`: Used when an agent determines no acceptable compromise exists.

## Terminal States
A negotiation session continues up to `MAX_ROUNDS` (default: 5) or until a terminal state is reached:

1. **`consensus_reached`**: All agents submitted `accept` in the same round. The coordinator finalizes the schedule.
2. **`escalated_unresolved`**: Any agent submitted `escalate` (or `reject` after a certain point). The coordinator immediately halts negotiation and flags the disruption for human dispatcher intervention.
3. **`max_rounds_exceeded`**: The max round limit was hit without consensus or escalation. The coordinator will forcibly apply a priority-based deterministic fallback.

## Priority Rules
Trains use priority classes to influence their decisions:
- `express` (Highest)
- `passenger` (Medium)
- `freight` (Lowest)

Lower-priority trains are expected to `accept` delays to yield to higher-priority trains.

## Agent Dropout Handling
If an agent fails to respond (LLM timeout, error, malformed JSON), the Coordinator injects a surrogate `escalate` decision on their behalf with an automated rationale, guaranteeing that the swarm does not hang indefinitely.
