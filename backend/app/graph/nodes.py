"""LangGraph node functions for the chatbot ReAct agent workflow.

Each function is a top-level coroutine (or plain function) so it can be
unit-tested and visualised independently of ChatbotService.

Nodes:
    agent_node           — Calls the LLM with the full message history from state.
    process_results_node — Post-processing: extracts products, source, etc. from
                           message history after the agent loop ends.
    should_continue      — Conditional edge: routes to 'tools' or 'process_results'.
"""

import json
import logging
from typing import Any, Callable, Optional

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.state import AgentState
from app.models.product import Product

logger = logging.getLogger(__name__)


async def agent_node(state: AgentState, llm_with_tools: Any) -> dict:
    """Call the LLM with the full message history from state.

    The LangGraph ``add_messages`` reducer has already merged all previous
    messages into ``state["messages"]``, so we simply pass them to the LLM.

    Args:
        state: Current agent state containing the full message history.
        llm_with_tools: LLM instance with tools bound via ``.bind_tools()``.

    Returns:
        Dict with ``{"messages": [AIMessage]}`` to be merged by the reducer.
    """
    messages = state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def process_results_node(
    state: AgentState,
    run_sqr: Callable,
) -> dict:
    """Post-processing: extract structured data from the message history.

    Examines ``ToolMessage`` entries and AI ``tool_calls`` to populate:
    - ``products``        — Product objects for the API response (re-uses cached
                            results stored in the ToolMessage to avoid a second
                            Pinecone call, falling back to a fresh SQR query only
                            when the cache is absent).
    - ``source``          — One of ``'vector_db'``, ``'action'``,
                            ``'general_chat'``, ``'user_info'``,
                            ``'purchase_history'``, or
                            ``'general_chat_with_search'``.
    - ``has_results``     — Whether the interaction produced any results.
    - ``user_info``       — Reserved; always ``None`` (text in messages).
    - ``purchase_history``— Reserved; always ``[]`` (text in messages).

    Args:
        state:   Current agent state.
        run_sqr: Async callable that executes the SelfQueryingRetriever.
                 Only invoked when no cached products are found in state.

    Returns:
        Dict with the populated result fields.
    """
    messages = state["messages"]
    products: list = []
    source: Optional[str] = None
    has_results = False
    user_info = None
    purchase_history: list = []

    tool_names_called: list[str] = []
    search_query: Optional[str] = None  # query used by search_products tool

    for msg in messages:
        # Collect tool names from AI tool_call messages
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "")
                tool_names_called.append(name)
                if name == "search_products" and not search_query:
                    search_query = tc.get("args", {}).get("query", "")

        # Extract structured data from tool result messages
        if isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            tool_name = getattr(msg, "name", "") or ""

            if tool_name == "search_products":
                # C2 fix: try to parse cached products embedded in the ToolMessage
                # before falling back to a second Pinecone query.
                if "Found" in content and "products" in content:
                    # Attempt to load pre-serialised Product list from JSON block
                    try:
                        json_start = content.index("```json\n") + 8
                        json_end = content.index("\n```", json_start)
                        cached = json.loads(content[json_start:json_end])
                        products = [Product(**p) for p in cached]
                        has_results = True
                    except (ValueError, KeyError, Exception):
                        # No embedded JSON — will fall back to SQR below
                        has_results = True
                    source = "vector_db"
                elif "No products found" in content:
                    source = "none"

            elif tool_name in ("send_product_email", "purchase_product"):
                source = "action"
                has_results = True

            elif tool_name == "get_user_info":
                source = "user_info"
                has_results = True

            elif tool_name == "get_purchase_history":
                source = "purchase_history"
                has_results = True

            elif tool_name == "search_web":
                source = "general_chat_with_search"
                has_results = True

    # If no tools were called it is a pure conversational turn
    if not tool_names_called:
        source = "general_chat"

    # C2 fix: only run a second SQR query when the product list is still empty
    # (i.e., no embedded JSON was found in the ToolMessage).
    if source == "vector_db" and not products and search_query:
        logger.debug(
            "process_results_node: no cached products in ToolMessage — "
            "falling back to SQR for query: %s",
            search_query,
        )
        try:
            products = await run_sqr(search_query)
        except Exception as exc:
            logger.error("process_results_node: SQR fallback failed: %s", exc)

    return {
        "products": products,
        "source": source or "general_chat",
        "has_results": has_results,
        "user_info": user_info,
        "purchase_history": purchase_history,
    }


def should_continue(state: AgentState) -> str:
    """Decide whether to route to the tool executor or post-processing.

    Returns:
        ``"tools"``           — if the last AI message contains tool_calls.
        ``"process_results"`` — otherwise (agent is done calling tools).
    """
    messages = state["messages"]
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "process_results"

