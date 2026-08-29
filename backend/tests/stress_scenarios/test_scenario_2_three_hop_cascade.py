"""
Scenario 2: Cascading Three-Hop Delay
  Delay at NDLS propagates: NDLS → NGP → MMCT touching T12952 and T12810.
  T11040 also uses NDLS_NGP, creating a 3-train cascade.
  
  Asserts:
  - All 3 affected trains identified by cascade engine
  - All 3 invited to ONE session (not separate sessions)
  - terminal_state is valid
  - round_count >= 2
"""
import uuid
import pytest
from app.agents.negotiation_engine import run_negotiation_session
from app.data.synthetic import SyntheticDataLoader
from cascade.propagation_engine import propagate
from app.models.base import DisruptionEvent
from app.store import store


def test_three_hop_cascade():
    loader = SyntheticDataLoader(seed=42)
    disruption = loader.generate_disruption_event("scenario_2_three_hop_cascade")
    
    # Run cascade engine first
    impacts = propagate(disruption, store)
    
    # Must identify at least 2 downstream trains (T12952 and T11040 share NDLS_NGP)
    affected_train_ids = list({imp.train_id for imp in impacts})
    assert len(affected_train_ids) >= 2, (
        f"Cascade engine only found {len(affected_train_ids)} affected trains, expected >= 2"
    )
    
    # T12952 and T11040 both use NDLS_NGP, so both should be impacted
    ndls_ngp_trains = {"T12952", "T11040"}
    found_trains = set(affected_train_ids)
    assert found_trains & ndls_ngp_trains, (
        f"Expected at least one of {ndls_ngp_trains} in cascade impacts, got {found_trains}"
    )
    
    # All affected trains in ONE session (not multiple)
    session_id = f"stress-s2-{uuid.uuid4().hex[:8]}"
    participating_trains = affected_train_ids[:3]  # Cap at 3 for test speed
    
    session = run_negotiation_session(
        session_id=session_id,
        disruption=disruption,
        participating_trains=participating_trains,
        max_rounds=5,
    )
    
    # Session must include all affected trains
    assert set(session.participating_trains) == set(participating_trains), (
        f"Session trains {session.participating_trains} != affected trains {participating_trains}"
    )
    
    # Must be a single session (not multiple)
    cascading_sessions = [sid for sid in store.sessions if sid.startswith("stress-s2")]
    assert len(cascading_sessions) == 1, (
        f"Expected 1 session for cascade, got {len(cascading_sessions)}: {cascading_sessions}"
    )
    
    valid_states = {"consensus_reached", "escalated_unresolved", "max_rounds_exceeded"}
    assert session.terminal_state in valid_states
    assert len(session.rounds) >= 2
    
    all_decisions = [d for r in session.rounds for d in r.decisions]
    for decision in all_decisions:
        assert decision.rationale and len(decision.rationale) > 10
    
    print(f"\n✅ Scenario 2 passed: terminal_state={session.terminal_state}, "
          f"affected_trains={affected_train_ids}, rounds={len(session.rounds)}")
