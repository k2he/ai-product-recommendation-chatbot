"""LangGraph workflow package.

Contains the graph state definition, node functions, and graph builder
for the chatbot's ReAct agent workflow.

Exports:
    AgentState          — TypedDict state for the LangGraph workflow
    build_chatbot_graph — Compile the StateGraph from an LLM + tools
    agent_node          — LLM call node
    process_results_node — Post-processing node (extracts products, source, etc.)
    should_continue     — Conditional edge function
"""

from app.graph.state import AgentState
from app.graph.builder import build_chatbot_graph
from app.graph.nodes import agent_node, process_results_node, should_continue

__all__ = [
    "AgentState",
    "build_chatbot_graph",
    "agent_node",
    "process_results_node",
    "should_continue",
]

