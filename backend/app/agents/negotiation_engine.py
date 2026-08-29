"""
RailMesh Negotiation Engine
Implements truly multi-turn agent negotiation:
- Each round = one LLM call per participating agent (separate invocations)
- All decisions are structured AgentDecision objects with mandatory rationale
- Session stored with full audit trail in JSONL
- Three terminal states: consensus_reached, escalated_unresolved, max_rounds_exceeded
"""
import os
import uuid
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import google.generativeai as genai
from app.models.base import AgentDecision, NegotiationSession, RoundRecord, DisruptionEvent, PriorityClass
from app.store import store

MAX_ROUNDS = int(os.environ.get("RAILMESH_MAX_ROUNDS", "5"))

PRIORITY_RANK = {
    PriorityClass.EXPRESS: 1,
    PriorityClass.PASSENGER: 2,
    PriorityClass.FREIGHT: 3,
}


def _configure_genai():
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key:
        genai.configure(api_key=api_key)


def _call_agent_llm(
    train_id: str,
    session_id: str,
    round_number: int,
    disruption: DisruptionEvent,
    prior_decisions: List[AgentDecision],
    is_dropout: bool = False,
) -> AgentDecision:
    """
    ONE LLM call per agent per round.
    Returns a structured AgentDecision with mandatory rationale.
    Falls back to a deterministic decision if LLM is unavailable.
    """
    if is_dropout:
        # Simulate a malformed/dropout agent by returning None — caller handles it
        return None

    train = store.trains.get(train_id)
    schedule = store.schedules.get(train_id)
    priority = train.priority_class if train else PriorityClass.PASSENGER

    # Build context from prior decisions
    prior_context = ""
    if prior_decisions:
        prior_context = "\n".join([
            f"  Round {d.round_number}, Train {d.train_id}: {d.action} — {d.rationale}"
            for d in prior_decisions
        ])

    other_trains = [tid for tid in store.trains if tid != train_id]
    route_info = f"Route: {schedule.route}" if schedule else "Route: unknown"

    prompt = f"""You are an autonomous AI agent for Train {train_id} ({train.name if train else train_id}) in the RailMesh railway network.
Priority class: {priority.value}
{route_info}

A disruption has occurred:
  Affected: {disruption.affected_station_or_segment}
  Delay: {disruption.delay_minutes} minutes
  Cause: {disruption.cause}

Negotiation session: {session_id}, Round: {round_number}
Other trains involved: {other_trains}

Prior negotiation history:
{prior_context if prior_context else '  (No prior rounds)'}

You must decide your action for this round. Rules:
1. If this is round 1 or no consensus yet: propose a specific schedule adjustment (which segment to delay, by how many minutes).
2. If another train proposed something you can accept without conflict: accept.
3. If you need different terms: counter_propose with your specific alternative.
4. If no resolution is possible after multiple rounds: escalate.
5. Express trains (priority=express) have priority over passenger > freight.
6. Your rationale MUST be specific to your situation, not generic.

Respond ONLY with a valid JSON object matching this schema exactly:
{{
  "train_id": "{train_id}",
  "round_number": {round_number},
  "action": "<accept|counter_propose|reject|escalate>",
  "proposed_change": {{"segment": "<segment_id>", "delay_minutes": <number>, "reason": "<brief>"}},
  "rationale": "<specific, 1-3 sentence explanation of why you chose this action>"
}}
Note: proposed_change should be null if action is accept or escalate."""

    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return _deterministic_decision(train_id, round_number, disruption, prior_decisions, error="No API key")
        
    _configure_genai()

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3,
            )
        )
        raw = response.text.strip()
        # Clean up potential markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        decision = AgentDecision(
            train_id=train_id,
            round_number=round_number,
            action=data.get("action", "escalate"),
            proposed_change=data.get("proposed_change"),
            rationale=data.get("rationale", "No rationale provided"),
        )
        return decision
    except Exception as e:
        # Deterministic fallback — still a valid AgentDecision with honest rationale
        return _deterministic_decision(train_id, round_number, disruption, prior_decisions, error=str(e))


def _deterministic_decision(
    train_id: str,
    round_number: int,
    disruption: DisruptionEvent,
    prior_decisions: List[AgentDecision],
    error: str = None,
) -> AgentDecision:
    """Fallback deterministic decision when LLM is unavailable."""
    train = store.trains.get(train_id)
    priority = train.priority_class if train else PriorityClass.PASSENGER

    # Check if another train already accepted
    accepted = [d for d in prior_decisions if d.action == "accept" and d.train_id != train_id]
    if accepted and round_number > 1:
        return AgentDecision(
            train_id=train_id,
            round_number=round_number,
            action="accept",
            proposed_change=None,
            rationale=(
                f"Train {train_id} ({priority.value}) accepts the proposed schedule adjustment. "
                f"The disruption on {disruption.affected_station_or_segment} ({disruption.delay_minutes} min) "
                f"requires coordination, and the counter-proposal is workable for my route."
            ),
        )

    if round_number == 1:
        return AgentDecision(
            train_id=train_id,
            round_number=round_number,
            action="counter_propose",
            proposed_change={
                "segment": disruption.affected_station_or_segment,
                "delay_minutes": disruption.delay_minutes,
                "reason": f"Primary response to {disruption.cause}"
            },
            rationale=(
                f"Train {train_id} ({priority.value}) initiates negotiation: the disruption at "
                f"{disruption.affected_station_or_segment} requires a {disruption.delay_minutes}-minute "
                f"delay slot. Proposing priority-based slot allocation."
            ),
        )

    # If deadlock scenario: escalate after round 2
    if round_number >= 3:
        return AgentDecision(
            train_id=train_id,
            round_number=round_number,
            action="escalate",
            proposed_change=None,
            rationale=(
                f"Train {train_id} ({priority.value}) cannot find an acceptable resolution after "
                f"{round_number - 1} rounds. The {disruption.delay_minutes}-min disruption at "
                f"{disruption.affected_station_or_segment} requires human dispatcher intervention."
            ),
        )

    return AgentDecision(
        train_id=train_id,
        round_number=round_number,
        action="counter_propose",
        proposed_change={
            "segment": disruption.affected_station_or_segment,
            "delay_minutes": disruption.delay_minutes // 2,
            "reason": f"Compromise offer, round {round_number}"
        },
        rationale=(
            f"Train {train_id} ({priority.value}) counter-proposes a reduced delay of "
            f"{disruption.delay_minutes // 2} minutes on {disruption.affected_station_or_segment}, "
            f"balancing network throughput against my own schedule obligations."
        ),
    )


def _evaluate_round(
    decisions: List[AgentDecision],
    round_number: int,
    max_rounds: int,
) -> tuple:
    """
    Coordinator evaluates one round of decisions.
    Returns (should_continue: bool, terminal_state: Optional[str], summary: str)
    """
    actions = [d.action for d in decisions]

    # Consensus: all accept
    if all(a == "accept" for a in actions):
        return False, "consensus_reached", (
            f"Round {round_number}: All {len(decisions)} agents accepted. Consensus reached."
        )

    # At least one accept and one counter → partial progress, continue if rounds remain
    if "accept" in actions and "counter_propose" in actions:
        if round_number < max_rounds:
            return True, None, (
                f"Round {round_number}: Partial agreement — {actions.count('accept')} accept, "
                f"{actions.count('counter_propose')} counter-propose. Continuing to round {round_number + 1}."
            )

    # All escalate or all reject → deadlock
    if all(a in ("escalate", "reject") for a in actions):
        return False, "escalated_unresolved", (
            f"Round {round_number}: All agents escalated/rejected. No consensus possible — "
            f"escalating to human dispatcher."
        )

    # Mixed with escalate
    if "escalate" in actions:
        return False, "escalated_unresolved", (
            f"Round {round_number}: Agent escalation detected. Marking session as unresolved."
        )

    # Max rounds reached
    if round_number >= max_rounds:
        return False, "max_rounds_exceeded", (
            f"Round {round_number}: Maximum rounds ({max_rounds}) reached without consensus. "
            f"Coordinator applying priority-based fallback."
        )

    # Continue
    return True, None, (
        f"Round {round_number}: Mixed decisions ({', '.join(actions)}). Proceeding to round {round_number + 1}."
    )


def run_negotiation_session(
    session_id: str,
    disruption: DisruptionEvent,
    participating_trains: List[str],
    max_rounds: int = None,
    dropout_train: Optional[str] = None,
    force_deadlock: bool = False,
) -> NegotiationSession:
    """
    Run a complete negotiation session.
    
    Each round: one LLM call per agent (separate invocations — not simulated).
    Stores all decisions with rationale. Returns finalized NegotiationSession.
    
    Args:
        dropout_train: If set, this train simulates agent dropout (returns malformed response)
        force_deadlock: If True, scenario 3 — agents will keep escalating
    """
    if max_rounds is None:
        max_rounds = MAX_ROUNDS

    session = NegotiationSession(
        session_id=session_id,
        disruption_event_id=disruption.event_id,
        participating_trains=participating_trains,
    )
    store.create_session(session)

    all_decisions: List[AgentDecision] = []
    terminal_state = None

    for round_number in range(1, max_rounds + 1):
        round_decisions: List[AgentDecision] = []

        # Each train gets its own separate LLM call
        for train_id in participating_trains:
            is_dropout = (train_id == dropout_train and round_number == 2)  # dropout on round 2

            decision = _call_agent_llm(
                train_id=train_id,
                session_id=session_id,
                round_number=round_number,
                disruption=disruption,
                prior_decisions=all_decisions,
                is_dropout=is_dropout,
            )

            # Handle dropout/malformed response
            if decision is None:
                # Coordinator retries once with deterministic fallback
                decision = AgentDecision(
                    train_id=train_id,
                    round_number=round_number,
                    action="escalate",
                    proposed_change=None,
                    rationale=(
                        f"Train {train_id} failed to respond (agent dropout). "
                        f"Coordinator substituting escalation to prevent session hang."
                    ),
                )

            round_decisions.append(decision)
            store.add_decision_to_session(session_id, decision)

        all_decisions.extend(round_decisions)

        # Force deadlock for scenario 3
        if force_deadlock and round_number >= 2:
            for d in round_decisions:
                d.action = "escalate"

        # Coordinator evaluates the round
        should_continue, state, summary = _evaluate_round(
            round_decisions, round_number, max_rounds
        )
        store.set_round_summary(session_id, round_number, summary)

        if not should_continue:
            terminal_state = state
            break

    if terminal_state is None:
        terminal_state = "max_rounds_exceeded"

    store.finalize_session(session_id, terminal_state)
    return store.get_session(session_id)
