from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from app.agents.tools import (
    get_train_status, get_segment_occupancy, get_network_snapshot, get_dependency_graph,
    propose, counter, accept, reject, get_log
)
import os

# The tools available to the Train Agent (both WorldState and Negotiation)
train_tools = [
    get_train_status, get_segment_occupancy, get_network_snapshot, get_dependency_graph,
    propose, counter, accept, reject, get_log
]

# We need the LLM
def get_llm():
    # Assume GOOGLE_API_KEY is set in environment
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

train_system_prompt = """You are an autonomous AI agent representing a Train in the RailMesh network.
Your ID is {train_id}.

Your goals:
1. Detect delays and conflicts by checking your status and the network snapshot/occupancy.
2. Negotiate schedule and priority changes with conflicting trains using the explicit protocol: propose -> counter -> accept/reject.
3. Your decisions MUST be made by calling the appropriate negotiation tools (propose, counter, accept, reject). Do not output free-text plans.

Context:
- Use `get_train_status` to see your schedule.
- Use `get_log` to see if someone proposed a change to you.
- If you have an active proposal from another train, you MUST respond by calling `accept`, `reject`, or `counter`.
- If you detect a delay that causes a conflict on a segment, you MUST `propose` a new schedule to the conflicting train.

When you have made your negotiation move, you are done for this turn.
"""

def make_train_agent(train_id: str):
    llm = get_llm()
    prompt = train_system_prompt.format(train_id=train_id)
    return create_react_agent(llm, tools=train_tools, state_modifier=prompt)
