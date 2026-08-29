from typing import Annotated, TypedDict, Sequence, Optional, List
from langchain_core.messages import BaseMessage
from app.models.base import AgentDecision
import operator


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_train: str
    target_train: Optional[str]
    session_id: Optional[str]
    delay_event: Optional[dict]
    coordinator_status: Optional[str]
    round_number: int
    participating_trains: List[str]
    decisions: Annotated[List[AgentDecision], operator.add]
    terminal_state: Optional[str]
