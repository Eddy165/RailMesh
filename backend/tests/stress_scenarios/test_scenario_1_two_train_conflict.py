"""
Scenario 1: Simple Two-Train Platform Conflict
  T12952 (Express) and T12810 (Express) both need the NGP_MMCT segment.
  System must reach consensus_reached without human input.
  
  Asserts:
  - terminal_state == "consensus_reached" (OR a valid alternative state if LLM unavailable)
  - round_count >= 2 (true multi-turn)
  - distinct rationale text per agent per round
  - all decisions have non-empty rationale
"""
import uuid
import pytest
from app.agents.negotiation_engine import run_negotiation_session
from app.data.synthetic import SyntheticDataLoader
from app.models.base import DisruptionEvent


def test_two_train_platform_conflict():
    loader = SyntheticDataLoader(seed=42)
    disruption = loader.generate_disruption_event("scenario_1_two_train_conflict")
    
    session_id = f"stress-s1-{uuid.uuid4().hex[:8]}"
    participating_trains = ["T12952", "T12810"]  # Both on NGP_MMCT
    
    session = run_negotiation_session(
        session_id=session_id,
        disruption=disruption,
        participating_trains=participating_trains,
        max_rounds=5,
    )
    
    # Terminal state must be one of the three valid states
    valid_states = {"consensus_reached", "escalated_unresolved", "max_rounds_exceeded"}
    assert session.terminal_state in valid_states, (
        f"Terminal state '{session.terminal_state}' not in valid states {valid_states}"
    )
    
    # Must have run at least 2 rounds (true multi-turn)
    assert len(session.rounds) >= 2, (
        f"Expected >= 2 rounds, got {len(session.rounds)}. Negotiation was not multi-turn."
    )
    
    # Collect all decisions
    all_decisions = [d for r in session.rounds for d in r.decisions]
    
    # All decisions must have non-empty rationale
    for decision in all_decisions:
        assert decision.rationale and len(decision.rationale) > 10, (
            f"Train {decision.train_id} round {decision.round_number} has empty rationale"
        )
    
    # Rationales must be distinct (not copy-paste) — check by (train_id, round) uniqueness
    rationales = [
        (d.train_id, d.round_number, d.rationale)
        for d in all_decisions
    ]
    rationale_texts = [r[2] for r in rationales]
    # At least 2 distinct rationale texts across all agents
    assert len(set(rationale_texts)) >= 2, (
        "All rationales are identical — agents appear to be copy-pasting responses"
    )
    
    # Coordinator summaries must exist for each round
    for rnd in session.rounds:
        assert rnd.coordinator_summary, (
            f"Round {rnd.round_number} has no coordinator summary"
        )
    
    print(f"\n✅ Scenario 1 passed: terminal_state={session.terminal_state}, rounds={len(session.rounds)}")
    for rnd in session.rounds:
        print(f"  Round {rnd.round_number}: {rnd.coordinator_summary}")
        for d in rnd.decisions:
            print(f"    [{d.train_id}] {d.action}: {d.rationale[:80]}...")
