"""LangGraph StateGraph builder for the chatbot ReAct agent.

Provides a single factory function ``build_chatbot_graph`` that wires
agent_node -> (should_continue?) -> tool_node <-> agent_node -> process_results -> END.

The graph is compiled fresh per request because tools are user-specific closures
(they capture user_name, user_email, etc.).
# C1 - Known trade-off: compilation is pure CPU work. A future optimisation
# would inject user context via RunnableConfig at invocation time so the
# graph could be compiled once at startup and reused across requests.
"""

import logging
from functools import partial
from typing import Any, Callable

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.graph.nodes import agent_node, process_results_node, should_continue
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


def build_chatbot_graph(
    llm_with_tools: Any,
    tools: list,
    run_sqr: Callable,
):
    """Build and compile the LangGraph StateGraph for the chatbot workflow.

    Args:
        llm_with_tools: LLM instance already bound to tools via .bind_tools(tools).
        tools: List of LangChain BaseTool instances for ToolNode.
        run_sqr: Async callable that runs the SelfQueryingRetriever.
                 Injected into process_results_node so it can fall back to a
                 Pinecone query when no cached products are found in ToolMessage.

    Returns:
        A compiled CompiledStateGraph ready for .ainvoke().
    """
    workflow = StateGraph(AgentState)

    # Bind dependencies via functools.partial so each node is a plain callable
    bound_agent = partial(agent_node, llm_with_tools=llm_with_tools)
    bound_process_results = partial(process_results_node, run_sqr=run_sqr)

    # Add nodes
    workflow.add_node("agent", bound_agent)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("process_results", bound_process_results)

    # Wire edges
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "process_results": "process_results",
        },
    )
    workflow.add_edge("tools", "agent")       # Loop back after tool execution
    workflow.add_edge("process_results", END)

    compiled = workflow.compile()
    logger.info(
        "LangGraph workflow compiled with %d tool(s): %s",
        len(tools),
        [t.name for t in tools],
    )
    return compiled

