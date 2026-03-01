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
    - ``products``        — Product objects for the API response.  Accumulated
                            across ALL ``search_products`` tool calls so that
                            multi-category queries (e.g. "monitors and wearables")
                            return the full combined product list.
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
                 Only invoked as a fallback when no embedded JSON is found
                 in a ToolMessage.

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
    # Collect ALL search queries in call order so the SQR fallback can
    # replay every search that had no embedded JSON.
    search_queries: list[str] = []

    # Map tool_call_id → query so each ToolMessage can be matched to its query
    call_id_to_query: dict[str, str] = {}

    for msg in messages:
        # Collect tool names and map call IDs → query strings
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "")
                tool_names_called.append(name)
                if name == "search_products":
                    query = tc.get("args", {}).get("query", "")
                    call_id = tc.get("id", "")
                    if query:
                        search_queries.append(query)
                        if call_id:
                            call_id_to_query[call_id] = query

        # Extract structured data from tool result messages
        if isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            tool_name = getattr(msg, "name", "") or ""

            if tool_name == "search_products":
                if "Found" in content and "products" in content:
                    source = "vector_db"
                    has_results = True
                    # Try to parse the embedded JSON block written by search_tool.py.
                    # Each ToolMessage carries the products from its own SQR call,
                    # so we EXTEND (not replace) the accumulator to support
                    # multi-category queries.
                    try:
                        json_start = content.index("```json\n") + 8
                        json_end = content.index("\n```", json_start)
                        cached = json.loads(content[json_start:json_end])
                        new_products = [Product(**p) for p in cached]
                        # Deduplicate by SKU before extending
                        existing_skus = {p.sku for p in products}
                        products.extend(
                            p for p in new_products if p.sku not in existing_skus
                        )
                        # Remove this query from the fallback list — it was resolved
                        tool_call_id = getattr(msg, "tool_call_id", "")
                        resolved_query = call_id_to_query.get(tool_call_id)
                        if resolved_query and resolved_query in search_queries:
                            search_queries.remove(resolved_query)
                        logger.debug(
                            "process_results_node: parsed %d products from ToolMessage "
                            "(total so far: %d)",
                            len(new_products),
                            len(products),
                        )
                    except (ValueError, KeyError, Exception) as exc:
                        logger.debug(
                            "process_results_node: no embedded JSON in ToolMessage (%s) "
                            "— will use SQR fallback",
                            exc,
                        )
                elif "No products found" in content:
                    if source != "vector_db":   # don't downgrade if another call succeeded
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

    # SQR fallback: run for any search query whose ToolMessage had no embedded JSON.
    # This covers both the single-query and multi-query cases.
    if source == "vector_db" and search_queries:
        for query in search_queries:
            logger.debug(
                "process_results_node: SQR fallback for query: %s", query
            )
            try:
                fallback_products = await run_sqr(query)
                existing_skus = {p.sku for p in products}
                products.extend(
                    p for p in fallback_products if p.sku not in existing_skus
                )
            except Exception as exc:
                logger.error(
                    "process_results_node: SQR fallback failed for query '%s': %s",
                    query,
                    exc,
                )

    logger.info(
        "process_results_node: source=%s, total products=%d",
        source or "general_chat",
        len(products),
    )

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

