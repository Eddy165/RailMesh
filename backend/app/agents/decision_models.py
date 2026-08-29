from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class AgentDecision(BaseModel):
    action: str = Field(description="One of: PROPOSE, COUNTER, ACCEPT, REJECT, WAIT")
    target_train_id: Optional[str] = Field(description="The train ID to negotiate with, if applicable")
    proposed_schedule: Optional[Dict[str, Any]] = Field(description="The proposed schedule, if PROPOSE or COUNTER")
    reason: Optional[str] = Field(description="Reason for rejection, if REJECT")
    original_proposal_id: Optional[str] = Field(description="The message_id of the proposal being responded to")

class CoordinatorDecision(BaseModel):
    action: str = Field(description="One of: COMMIT, TIMEOUT_FALLBACK, WAIT")
    final_schedule: Optional[Dict[str, Any]] = Field(description="The final schedule to commit")
    session_id: Optional[str] = Field(description="The session ID to commit or timeout")
