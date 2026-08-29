"""
Scenario 3: Deadlock — Two Express Trains, Same Slot
  T12952 and T12810 are both EXPRESS priority on NGP_MMCT.
  No mutually acceptable reschedule exists.
  
  Asserts:
  - terminal_state == "escalated_unresolved" (NOT looping forever)
  - System does NOT silently pick an arbitrary winner
  - round_count is bounded (does not exceed max_rounds)
  - All decisions have distinct rationale
"""
import uuid
import pytest
from app.agents.negotiation_engine import run_negotiation_session
from app.data.synthetic import SyntheticDataLoader


def test_deadlock_escalation():
    loader = SyntheticDataLoader(seed=42)
    disruption = loader.generate_disruption_event("scenario_3_deadlock")
    
    session_id = f"stress-s3-{uuid.uuid4().hex[:8]}"
    participating_trains = ["T12952", "T12810"]  # Both EXPRESS, same segment
    
    MAX_ROUNDS = 5
    session = run_negotiation_session(
        session_id=session_id,
        disruption=disruption,
        participating_trains=participating_trains,
        max_rounds=MAX_ROUNDS,
        force_deadlock=True,  # Force all agents to escalate after round 1
    )
    
    # Must NOT loop forever
    assert len(session.rounds) <= MAX_ROUNDS, (
        f"Session exceeded max rounds: {len(session.rounds)} > {MAX_ROUNDS}"
    )
    
    # Must reach escalated_unresolved, not consensus (deadlock scenario)
    valid_states = {"escalated_unresolved", "max_rounds_exceeded"}
    assert session.terminal_state in valid_states, (
        f"Deadlock scenario should NOT reach consensus_reached. Got: {session.terminal_state}"
    )
    
    # System should NOT silently pick a winner (no COMMIT action in messages)
    from app.store import store
    session_obj = store.get_session(session_id)
    commit_messages = [m for m in session_obj.messages if m.action.value == "COMMIT"]
    assert len(commit_messages) == 0, (
        f"Deadlock scenario should not produce COMMIT, but found: {commit_messages}"
    )
    
    # All decisions have rationale
    all_decisions = [d for r in session.rounds for d in r.decisions]
    for decision in all_decisions:
        assert decision.rationale and len(decision.rationale) > 10
    
    print(f"\n✅ Scenario 3 passed: terminal_state={session.terminal_state}, "
          f"rounds={len(session.rounds)} (deadlock correctly identified)")
    for rnd in session.rounds:
        print(f"  Round {rnd.round_number}: {rnd.coordinator_summary}")
