"""LangGraph agent state definition for the chatbot workflow.

Uses TypedDict with Annotated[list, add_messages] for LangGraph's
built-in message tracking.  The remaining fields are populated by
the process_results node after the agent loop ends.
"""

from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph state container for the chatbot workflow.

    ``messages`` is the canonical message list managed by LangGraph's
    ``add_messages`` reducer — every node that returns
    ``{"messages": [...]}`` will have those messages *appended*
    automatically.

    The remaining fields are populated by the ``process_results`` node
    after the agent loop ends.  Tools do not mutate state directly.
    """

    # ── Core message list (managed by LangGraph) ──────────────────────────
    messages: Annotated[list, add_messages]

    # ── Populated by process_results node from tool outputs ───────────────
    products: list                  # List[Product] objects for the API response
    source: Optional[str]           # 'vector_db', 'action', 'general_chat', etc.
    has_results: bool               # Whether the interaction produced any results
    user_info: Optional[Any]        # UserInDB when displaying account details
    purchase_history: list          # List[OrderInDB] when displaying past orders

