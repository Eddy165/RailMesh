from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from app.agents.state import AgentState
from app.agents.train_agent import make_train_agent
from app.agents.coordinator import coordinator_tick
import json

def train_node(state: AgentState):
    current_train = state["current_train"]
    agent = make_train_agent(current_train)
    
    # We pass the messages and optionally a prompt describing the event
    inputs = {"messages": state["messages"]}
    result = agent.invoke(inputs)
    
    # The react agent will append its thoughts and tool calls to the messages
    return {"messages": result["messages"]}

def coordinator_node(state: AgentState):
    session_id = state.get("session_id")
    # In tests, we might set delay_event["timeout"] = True to force timeout
    is_timeout = state.get("delay_event", {}).get("timeout", False)
    
    status = coordinator_tick(session_id, is_timeout=is_timeout)
    return {"coordinator_status": status}

def should_continue(state: AgentState):
    # If coordinator has committed, we end.
    if state.get("coordinator_status") in ["COMMITTED_AGREEMENT", "COMMITTED_FALLBACK"]:
        return END
        
    if state.get("delay_event", {}).get("timeout", False):
        return "coordinator"
        
    messages = state["messages"]
    last_message = messages[-1]
    
    # Check if the last action was a tool call for negotiation
    # Since we are using create_react_agent, tool calls are in the AIMessage or ToolMessage.
    # To simplify, we can parse the negotiation logs directly to see the state.
    from app.mcp import negotiation
    session_id = state.get("session_id")
    if not session_id:
        return END
        
    logs = negotiation.get_log(session_id)
    if not logs:
        # No negotiation started yet, maybe train is still thinking
        return "train"
        
    last_action = logs[-1]["action"]
    
    if last_action in ["PROPOSE", "COUNTER"]:
        # Swap current train to receiver
        state["current_train"] = logs[-1]["receiver_id"]
        return "train"
    elif last_action == "ACCEPT":
        return "coordinator"
    elif last_action == "REJECT":
        # Maybe go to coordinator for resolution, or END
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
    END: END
})

workflow.add_edge("coordinator", END)

negotiation_graph = workflow.compile()
