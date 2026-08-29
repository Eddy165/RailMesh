"""
Scenario 4: Agent Dropout / Malformed Response
  T12810 returns malformed/None response on round 2.
  
  Asserts:
  - Session does NOT crash
  - Coordinator handles dropout gracefully (escalate fallback)
  - Session reaches a valid terminal state
  - Dropout is logged with a coordinator-substituted rationale
"""
import uuid
import pytest
from app.agents.negotiation_engine import run_negotiation_session
from app.data.synthetic import SyntheticDataLoader


def test_agent_dropout_handled_gracefully():
    loader = SyntheticDataLoader(seed=42)
    disruption = loader.generate_disruption_event("scenario_4_agent_dropout")
    
    session_id = f"stress-s4-{uuid.uuid4().hex[:8]}"
    participating_trains = ["T12952", "T12810"]
    
    # T12810 drops out on round 2
    session = run_negotiation_session(
        session_id=session_id,
        disruption=disruption,
        participating_trains=participating_trains,
        max_rounds=5,
        dropout_train="T12810",  # This train will return None on round 2
    )
    
    # Must not crash — session must complete
    assert session is not None, "Session object is None — engine crashed"
    
    valid_states = {"consensus_reached", "escalated_unresolved", "max_rounds_exceeded"}
    assert session.terminal_state in valid_states, (
        f"Invalid terminal state: {session.terminal_state}"
    )
    
    # Dropout should be logged with coordinator-substituted rationale
    all_decisions = [d for r in session.rounds for d in r.decisions]
    
    # All decisions (including the dropout substitution) must have rationale
    for decision in all_decisions:
        assert decision.rationale and len(decision.rationale) > 10, (
            f"Missing rationale for {decision.train_id} round {decision.round_number}"
        )
    
    # The dropout substitution for T12810 should mention dropout/coordinator
    if len(session.rounds) >= 2:
        round2_decisions = session.rounds[1].decisions
        t12810_r2 = next((d for d in round2_decisions if d.train_id == "T12810"), None)
        if t12810_r2:
            assert any(word in t12810_r2.rationale.lower() 
                       for word in ["dropout", "failed", "coordinator", "substitut"]), (
                f"Dropout substitution rationale doesn't mention dropout: {t12810_r2.rationale}"
            )
    
    # Session must have run at least 1 round
    assert len(session.rounds) >= 1
    
    print(f"\n✅ Scenario 4 passed: terminal_state={session.terminal_state}, "
          f"rounds={len(session.rounds)} (dropout handled gracefully)")
    for rnd in session.rounds:
        print(f"  Round {rnd.round_number}: {rnd.coordinator_summary}")
        for d in rnd.decisions:
            print(f"    [{d.train_id}] {d.action}: {d.rationale[:80]}...")
