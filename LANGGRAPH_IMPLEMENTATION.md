# LangGraph Implementation Guide

## 🔄 Architecture: LangGraph StateGraph + ToolNode

This project uses **LangGraph** with an explicit `StateGraph` implementing the **ReAct agent pattern**. The LLM (`ChatOllama`) decides which tools to call, and a `ToolNode` automatically dispatches tool calls and collects results.

## 🎯 Why LangGraph?

| Feature | Benefit |
|---------|---------|
| **Explicit state machine** | Nodes and edges define the workflow visually |
| **`ToolNode`** (prebuilt) | Automatic tool dispatch — no manual parsing of `tool_calls` |
| **TypedDict state** | `AgentState` with `Annotated[list, add_messages]` manages messages cleanly |
| **Post-processing node** | Extracts structured data (products, source) from message history |
| **LangSmith tracing** | Full graph execution with node-by-node detail |
| **Future-ready** | Supports checkpointing, streaming, and human-in-the-loop (purchase confirmation) |

## 📋 Implementation Overview

### Core Component: `ChatbotService`


Located at: `backend/app/services/chatbot_service.py`

```python
class ChatbotService:
    """LangGraph-based chatbot service using explicit StateGraph."""

    def __init__(self):
        self.llm = ChatOllama(...)          # LLM (gpt-oss:20b)
        self.sqr = None                     # SelfQueryRetriever (lazy init)

    def _build_graph(self, tools):
        """Build: __start__ → agent → (should_continue?) → tools ↻ agent → process_results → __end__"""
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_node("process_results", process_results_node)
        ...
        return workflow.compile()
```

### State Model: `AgentState`

Located at: `backend/app/models/state.py`

```python
from typing import Annotated, Any, Optional, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # Full chat history (managed by LangGraph)
    products: list                            # Populated by process_results node
    source: Optional[str]                     # 'vector_db', 'action', 'general_chat', etc.
    has_results: bool
    user_info: Optional[Any]
    purchase_history: list
```

## 🔄 Workflow Graph

```
                    ┌──────────────┐
                    │   __start__  │
                    └──────┬───────┘
                           ↓
                ┌──────────────────────┐
                │    agent (LLM call)  │ ← ChatOllama only
                │  (decides which tool │   (messages passed directly
                │   to call, if any)   │    from state)
                └──────────┬───────────┘
                           ↓
                ┌──────────────────────┐
          ┌─────┤   should_continue?   ├─────┐
          │     └──────────────────────┘     │
          ↓                                  ↓
┌─────────────────┐               ┌──────────────────────┐
│   tool_node     │               │   process_results    │
│  (ToolNode w/   │               │  (extract products,  │
│   all 6 tools,  │               │   source, etc. from  │
│   incl. search_ │               │   message history)   │
│   products w/   │               └──────────┬───────────┘
│   SQR→Pinecone) │                          ↓
└────────┬────────┘               ┌──────────────────────┐
         │                        │      __end__         │
         ↓ (loop back)            └──────────────────────┘
┌──────────────────────┐
│    agent (LLM call)  │ ← sees tool results, decides next action
└──────────────────────┘
```

## 🛠️ Tools (6 Total)

All tools use the `@tool` decorator from `langchain_core.tools`. They **do not mutate state** — they return text results, and the `process_results` node extracts structured data.

| Tool | File | Purpose |
|------|------|---------|
| `search_products` | `tools/search_tool.py` | SQR → Pinecone vector search with metadata filtering |
| `send_product_email` | `tools/email_tool.py` | Send product details via SMTP email |
| `purchase_product` | `tools/purchase_tool.py` | Place an order for a product |
| `get_user_info` | `tools/user_info_tool.py` | Display user account information from MongoDB |
| `get_purchase_history` | `tools/purchase_history_tool.py` | Display past orders from MongoDB |
| `search_web` | `tools/web_search_tool.py` | Tavily web search for factual questions |

### Tool Dependency Injection

Tools are created via factory functions that inject dependencies through closures:

```python
# In ChatbotService._build_tools():
search_tool = create_search_products_tool(run_sqr=self._run_sqr)
email_tool = create_email_tool(email_service=email_service, ...)
purchase_tool = create_purchase_tool(get_product_by_id=..., user_name=..., ...)
```

## 🔑 Key Design Decisions

### 1. Messages as the Source of Truth

The `messages` field in `AgentState` carries the full conversation:
- `SystemMessage` — system prompt with behavior guidelines
- `HumanMessage` — user's query
- `AIMessage` — LLM responses (may contain `tool_calls`)
- `ToolMessage` — tool execution results

The LLM sees the **entire message history** on every call, enabling natural pronoun resolution ("buy **it**" → refers to last discussed product).

### 2. Post-Processing Node Instead of State Mutation

Previously, tools mutated a shared `AgentState` Pydantic object as a side-effect. Now:
- Tools return **text only**
- The `process_results` node runs **after** the agent loop ends
- It walks the message history, identifies which tools were called, and populates `products`, `source`, `has_results`, etc.
- For `search_products`, it re-runs the SQR to get `Product` objects for the API response

### 3. ToolNode for Automatic Dispatch

`ToolNode` from `langgraph.prebuilt` handles:
1. Reading `tool_calls` from the last `AIMessage`
2. Executing the matching tool function
3. Returning `ToolMessage` results into the state message list

No manual tool dispatch code needed.

### 4. Conditional Routing

The `should_continue` function provides two-way routing:
- **`tool_calls` present** → route to `tools` node (execute tools, loop back to agent)
- **No `tool_calls`** → route to `process_results` node (extract data, end)

## 📊 API Contract (Unchanged)

The REST API contract remains identical:

### POST /api/v1/chat
```json
// Request
{
    "query": "show me wireless headphones",
    "conversation_id": "conv_123",
    "last_product_ids": []
}

// Response
{
    "message": "I found 3 wireless headphones...",
    "products": [{ "sku": "...", "name": "...", ... }],
    "conversation_id": "conv_123",
    "has_results": true,
    "source": "vector_db"
}
```

### POST /api/v1/actions
```json
// Request
{ "action": "email", "product_id": "18470962" }

// Response
{ "success": true, "message": "Product details sent..." }
```

## 🗂️ File Changes from LangChain → LangGraph

| File | Change |
|------|--------|
| `app/models/state.py` | Pydantic `BaseModel` → `TypedDict` with `Annotated[list, add_messages]` |
| `app/models/__init__.py` | Removed `AgentState.model_rebuild()` call |
| `app/services/chatbot_service.py` | Replaced `create_agent` with `StateGraph` + `ToolNode` + `process_results` node |
| `app/tools/search_tool.py` | Removed `state` parameter; returns text only |
| `app/tools/email_tool.py` | Removed `state` parameter; returns text only |
| `app/tools/purchase_tool.py` | Removed `state` dict parameter (was `dict[str, Any]`); returns text only |
| `app/tools/user_info_tool.py` | Removed `state` parameter; returns text only |
| `app/tools/purchase_history_tool.py` | Removed `state` parameter; returns text only |
| `app/tools/web_search_tool.py` | No changes (never had state mutation) |
| `app/api/routes.py` | No changes (API contract identical) |

## 🚀 Future Enhancements (Ready to Implement)

These are enabled by the LangGraph architecture but not yet implemented:

1. **Checkpointing with `MemorySaver`** — True multi-turn conversation memory
2. **Purchase Confirmation (`interrupt_before`)** — Human-in-the-loop before purchase
3. **Streaming (`graph.astream()`)** — Real-time intermediate step updates
4. **Graph Visualization (`graph.get_graph()`)** — Auto-generated Mermaid diagrams
5. **`StructuredTool.from_function`** — Explicit Pydantic input schemas per tool

