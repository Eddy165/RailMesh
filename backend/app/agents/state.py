from typing import Annotated, TypedDict, Sequence, Optional
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_train: str
    target_train: Optional[str]
    session_id: Optional[str]
    delay_event: Optional[dict]
    coordinator_status: Optional[str] # "PENDING", "COMMITTED", "TIMED_OUT"
