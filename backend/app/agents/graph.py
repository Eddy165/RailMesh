from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from app.agents.state import AgentState
from app.agents.train_agent import make_train_agent
from app.agents.coordinator import coordinator_tick
from app.mcp import negotiation
import json


def train_node(state: AgentState):
    current_train = state["current_train"]
    agent = make_train_agent(current_train)
    inputs = {"messages": state["messages"]}
    result = agent.invoke(inputs)
    return {
        "messages": result["messages"],
        "current_train": current_train,
    }


def coordinator_node(state: AgentState):
    session_id = state.get("session_id")
    is_timeout = state.get("delay_event", {}).get("timeout", False)
    status = coordinator_tick(session_id, is_timeout=is_timeout)
    return {"coordinator_status": status}


def should_continue(state: AgentState):
    if state.get("coordinator_status") in ["COMMITTED_AGREEMENT", "COMMITTED_FALLBACK"]:
        return END

    if state.get("delay_event", {}).get("timeout", False):
        return "coordinator"

    session_id = state.get("session_id")
    if not session_id:
        return END

    logs = negotiation.get_log(session_id)
    if not logs:
        return "train"

    last_action = logs[-1]["action"]

    if last_action in ["PROPOSE", "COUNTER"]:
        state["current_train"] = logs[-1]["receiver_id"]
        return "train"
    elif last_action == "ACCEPT":
        return "coordinator"
    elif last_action in ["REJECT", "ESCALATE"]:
        return END

    return END


# Build the graph
workflow = StateGraph(AgentState)

workflow.add_node("train", train_node)
workflow.add_node("coordinator", coordinator_node)

workflow.set_entry_point("train")

workflow.add_conditional_edges("train", should_continue, {
    "train": "train",
    "coordinator": "coordinator",
    END: END,
})

workflow.add_edge("coordinator", END)

negotiation_graph = workflow.compile()
