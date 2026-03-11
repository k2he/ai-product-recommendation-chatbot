# LangChain → LangGraph Migration Analysis

## 📋 Current Architecture Summary

Your project is an **AI-powered e-commerce chatbot** with this architecture:

```
Frontend (React + Vite)
    ↓ REST API (FastAPI)
Backend:
    ├── ChatbotService (LangChain Agent via create_agent)
    │     ├── ChatOllama LLM (gpt-oss:20b)
    │     ├── SelfQueryRetriever (Pinecone + metadata filtering)
    │     └── 6 Tools:
    │           1. search_products — SQR → Pinecone vector search
    │           2. send_product_email — SMTP email
    │           3. purchase_product — Order creation
    │           4. get_user_info — MongoDB user lookup
    │           5. get_purchase_history — MongoDB order query
    │           6. search_web — Tavily web search
    ├── MongoDB (users, purchase_orders)
    ├── Pinecone (product embeddings + metadata)
    └── Shared AgentState (Pydantic model, populated by tools)
```

**Key observation:** Despite the docs saying "LangChain sequential chains", the **actual code** already uses `create_agent` from `langchain.agents` — a **tool-calling agent** pattern, NOT sequential chains. The agent gets all 6 tools, and the LLM decides which to call. State is shared via a mutable `AgentState` Pydantic object passed into tool closures.

---

## 🔍 Feature Research — LangGraph Capabilities Applicable to This Project

Before defining the migration phases, the following four LangGraph / LangChain features were evaluated for applicability:

### 1. `MessagesPlaceholder` for Chat History ✅ APPLICABLE

**What it is:** `MessagesPlaceholder` (from `langchain_core.prompts`) is a slot inside a `ChatPromptTemplate` that accepts a variable-length list of messages at runtime. It is the standard way to inject conversation history into a prompt.

**How it applies to this project:**
- The current code passes only the latest user message: `{"messages": [("user", user_query)]}`. There is **no chat history** carried between turns.
- With LangGraph, the state carries `messages: Annotated[list, add_messages]` which **accumulates** all messages (system, human, AI, tool) across the agent loop.
- `MessagesPlaceholder` is used inside the `ChatPromptTemplate` to inject that full message list into every LLM call:

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt_text),
    MessagesPlaceholder(variable_name="messages"),  # ← injects full chat history
])
```

**Benefits for this project:**
- Replaces the fragile `last_product_ids` / `last_product_names` context mechanism in the current system prompt
- The LLM sees the **full conversation** (including prior tool calls and results), enabling better "it" / "that" pronoun resolution
- Combined with `MemorySaver` checkpointing, provides true multi-turn memory without frontend state management

**No new dependencies required** — `MessagesPlaceholder` is part of `langchain_core` which is already installed (`langchain-core>=1.2.3` in `pyproject.toml`).

---

### 2. `graph.get_graph()` for Workflow Visualization ✅ APPLICABLE

**What it is:** Every compiled LangGraph `CompiledGraph` exposes a `.get_graph()` method that returns a `Graph` object representing the node/edge structure. This can be rendered in multiple formats:

```python
compiled_graph = workflow.compile(checkpointer=memory)

# Mermaid diagram (text) — paste into GitHub markdown or Mermaid Live Editor
print(compiled_graph.get_graph().draw_mermaid())

# Mermaid PNG (bytes) — save to file or display in notebook
png_bytes = compiled_graph.get_graph().draw_mermaid_png()
with open("workflow_graph.png", "wb") as f:
    f.write(png_bytes)

# ASCII art — quick terminal debugging
compiled_graph.get_graph().print_ascii()
```

**How it applies to this project:**
- Add a **dev/debug endpoint** (`GET /api/v1/graph`) that returns the Mermaid diagram string — useful for documentation and verifying the graph structure after changes
- Auto-generate the architecture diagram for `LANGGRAPH_IMPLEMENTATION.md` instead of maintaining it manually
- Use `print_ascii()` during startup logging so the graph structure is visible in Docker logs
- Use `draw_mermaid_png()` in a build script to auto-generate `docs/workflow_graph.png`

**No new dependencies required** — `get_graph()` and `draw_mermaid()` are built into `langgraph`. `draw_mermaid_png()` optionally requires the `pyppeteer` or `playwright` package for PNG rendering, but the Mermaid text output works out of the box.

---

### 3. `ToolNode` + `StructuredTool.from_function` ✅ APPLICABLE

**What they are:**

- **`ToolNode`** (from `langgraph.prebuilt`) — A prebuilt LangGraph node that automatically:
  1. Reads `tool_calls` from the last AI message in state
  2. Executes the matching tool function
  3. Returns `ToolMessage` results back into the state's message list
  This replaces manual tool dispatch logic entirely.

- **`StructuredTool.from_function`** (from `langchain_core.tools`) — Creates a LangChain tool with an **explicit Pydantic input schema**, giving full control over argument names, types, descriptions, and validation. This is an alternative to the `@tool` decorator.

**How they apply to this project:**

The current tools use a **factory-function + closure pattern** for dependency injection (e.g., `create_search_products_tool(run_sqr, state)` returns an inner `@tool` function). This works but is opaque — the tool's input schema is inferred from the inner function signature, and the closure hides dependencies.

`StructuredTool.from_function` makes this explicit:

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class SearchProductsInput(BaseModel):
    query: str = Field(description="Natural language search query")

search_products_tool = StructuredTool.from_function(
    coroutine=_search_products_impl,   # async implementation
    name="search_products",
    description="Search the product catalog for items matching the user's request.",
    args_schema=SearchProductsInput,
)
```

Combined with `ToolNode`:

```python
from langgraph.prebuilt import ToolNode

tools = [search_products_tool, email_tool, purchase_tool, ...]
tool_node = ToolNode(tools)  # auto-dispatches based on tool_calls in AI message

workflow.add_node("tools", tool_node)
```

**Benefits for this project:**
- **Explicit input schemas** — Pydantic models for each tool's arguments; better validation, clearer docs
- **Cleaner dependency injection** — dependencies can be passed via `functools.partial` or class methods instead of nested closures
- **`ToolNode` eliminates boilerplate** — no need to manually parse `tool_calls`, invoke the right function, and construct `ToolMessage` responses
- **Purchase tool fix** — the `purchase_tool.py` dict/AgentState inconsistency disappears because tools no longer mutate external state; they just return data, and `ToolNode` handles message plumbing

**No new dependencies required** — both are in packages already installed (`langgraph>=1.0.9`, `langchain-core>=1.2.3`).

---

### 4. Purchase Confirmation Step (Human-in-the-Loop) ✅ APPLICABLE

**What it is:** LangGraph supports `interrupt_before` and `interrupt_after` on any node. When the graph reaches an interrupted node, execution **pauses** and returns the current state to the caller. The caller (API layer) can then present the state to the user for confirmation. Once confirmed, the graph is **resumed** from the checkpoint using `Command(resume=user_response)`.

**How it applies to this project:**

Currently, the `purchase_product` tool executes **immediately** with no confirmation — the LLM decides to buy and it's done. This is risky for an e-commerce bot.

The proposed approach adds a **dedicated `purchase_confirmation` node** with `interrupt_before`:

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()

workflow.add_node("purchase_confirmation", purchase_confirmation_node)

# Interrupt BEFORE purchase_confirmation runs — return to user for approval
compiled_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["purchase_confirmation"],
)
```

**Proposed purchase confirmation flow:**

```
User: "Buy the Sony headphones"
    ↓
agent_node → LLM calls purchase_product tool
    ↓
should_route_to_confirmation? → YES (detected purchase tool_call)
    ↓
── INTERRUPT ── (graph pauses, returns to API)
    ↓
API returns to frontend:
  { "requires_confirmation": true,
    "confirmation_message": "Please confirm: Purchase Sony WH-1000XM5 for $349.99 CAD?",
    "product": { ... },
    "thread_id": "abc-123" }
    ↓
User clicks "Confirm" → Frontend sends POST /api/v1/chat/confirm
    ↓
API resumes graph: graph.ainvoke(Command(resume="confirmed"), config={"configurable": {"thread_id": "abc-123"}})
    ↓
purchase_confirmation_node → executes the actual purchase
    ↓
agent_node → generates confirmation message
    ↓
__end__
```

**Implementation details:**
- Add a `pending_purchase` field to the LangGraph state (`Optional[dict]` with product_id, product details, user_id)
- The `should_continue` conditional edge gains a third route: if the tool call is `purchase_product`, route to `purchase_confirmation` instead of the generic `tool_node`
- `purchase_confirmation` node is interrupted before execution — the product details are returned to the user
- On resume, the node checks the user's response (`"confirmed"` / `"cancelled"`) and either completes the purchase or cancels
- **Requires checkpointing** (`MemorySaver` at minimum) — the graph state must persist between the interrupt and resume calls

**Frontend changes needed:**
- Handle a new `requires_confirmation` field in the `ChatResponse`
- Show a confirmation UI (product card + Confirm/Cancel buttons)
- Send a resume/confirm request to a new endpoint (`POST /api/v1/chat/confirm`)

**Benefits for this project:**
- **Safety guardrail** — prevents accidental purchases from ambiguous user messages
- **User trust** — the user sees exactly what they're buying before committing
- **Reversible** — user can cancel before any order is created
- **Auditable** — the checkpoint stores the full decision trail

---

## ⚖️ Pros & Cons Comparison

### LangChain (Current — Tool-Calling Agent)

| ✅ Pros | ❌ Cons |
|---------|---------|
| Simple single-agent setup; easy to reason about | **No explicit control flow** — the LLM decides everything, which can lead to unpredictable tool calling sequences |
| Minimal boilerplate — `create_agent` + tools list | **No state graph** — mutable `AgentState` object is a workaround; tools mutate shared state as a side-effect |
| Works out of the box for straightforward Q&A | **No human-in-the-loop** — cannot pause execution for user confirmation (e.g., before purchase) |
| Easier onboarding for new developers | **No conditional routing** — can't define explicit "if search returns 0 results → try web search" logic; must rely on LLM judgment |
| Good enough for a single turn-based interaction | **No checkpointing/persistence** — can't resume a multi-step conversation or replay from a mid-point |
| LangSmith tracing works natively | **No streaming of intermediate steps** — user sees nothing until the full response is ready |
| | **No chat history** — only the latest user message is passed; no `MessagesPlaceholder` for multi-turn context |
| | **Fragile tool orchestration** — purchase_tool uses `state["source"]` (dict), while others use `state.source` (AgentState); inconsistency suggests this pattern is brittle |
| | **No retry/fallback graph** — if SQR fails, there's no structured fallback to web search; it depends entirely on LLM behavior |
| | **`langchain.agents.create_agent`** is a thin wrapper; limited configurability for timeout, max iterations, error recovery |
| | **No workflow visualization** — cannot inspect the agent's decision graph; debugging is opaque |

### LangGraph (Proposed)

| ✅ Pros | ❌ Cons |
|---------|---------|
| **Explicit state machine** — define nodes (search, email, purchase, respond) and edges with clear transitions | More upfront code to define the graph structure |
| **TypedDict/Pydantic state** — LangGraph's `StateGraph` manages state officially; no side-effect mutation | Steeper learning curve for graph concepts (nodes, edges, conditional edges) |
| **Conditional routing** — e.g., "if 0 products found AND web search available → route to web_search node" | Requires refactoring `chatbot_service.py` significantly |
| **Human-in-the-loop** — `interrupt_before` on purchase node for user confirmation before order is placed | Slightly more complex debugging compared to linear flow |
| **Built-in checkpointing** — `MemorySaver` or async checkpointers allow conversation persistence and replay | Need to manage checkpointer lifecycle |
| **`MessagesPlaceholder`** — full chat history injected into every LLM call; replaces fragile `last_product_ids` context | |
| **Streaming support** — stream intermediate node outputs (e.g., "Searching products..." → "Found 3 results" → final response) | |
| **Retry & error handling** — nodes can have fallback edges; graph can route to error-recovery nodes | |
| **`ToolNode` + `StructuredTool.from_function`** — prebuilt tool dispatch node with explicit Pydantic input schemas per tool | |
| **`graph.get_graph()` visualization** — auto-generate Mermaid diagrams, PNGs, or ASCII art of the workflow for docs and debugging | |
| **LangSmith tracing** — LangGraph traces show the full graph execution with node-by-node detail | |
| **Already a dependency** — `langgraph>=1.0.9` is already in `pyproject.toml`! No new packages needed | |
| **Future-proof** — LangGraph is LangChain's recommended approach for agents going forward; `create_agent` in LangChain actually delegates to LangGraph internally | |
| **Sub-graphs** — can compose e.g., a "product action sub-graph" (email/purchase) separate from the main conversation graph | |

---

## 🏗️ Proposed LangGraph Architecture

```
                        ┌──────────────┐
                        │   __start__  │
                        └──────┬───────┘
                               ↓
                    ┌──────────────────────┐
                    │    agent (LLM call)  │ ← ChatPromptTemplate with
                    │    ChatOllama only   │   MessagesPlaceholder("messages")
                    │  (decides which tool │   for full chat history
                    │   to call, if any)   │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
              ┌─────┤   should_continue?   ├──────────────┐
              │     └──────────┬───────────┘              │
              │                │                          │
              ↓                ↓                          ↓
    ┌─────────────────┐  ┌────────────────────┐  ┌──────────────────┐
    │   tool_node     │  │ purchase_confirm   │  │     __end__      │
    │  (ToolNode w/   │  │  ── INTERRUPT ──   │  │  (final answer)  │
    │  StructuredTool │  │ (user confirms or  │  └──────────────────┘
    │  tools, incl.   │  │  cancels purchase) │
    │  search_products│  └────────┬───────────┘
    │  which uses SQR │           │
    │  → Pinecone)    │           │
    └────────┬────────┘           │
             │                    │
             ↓                    ↓
    ┌──────────────────────────────────────────┐
    │         agent (LLM call)                 │  ← sees tool results
    │         loops back for next action       │    or confirmation result
    └──────────────────────────────────────────┘
```

**Key changes from original plan:**
- **`agent_node` is LLM-only** (`ChatOllama`) — it decides which tool to call but does NOT run the SelfQueryRetriever itself
- **SQR lives inside `tool_node`** — when the LLM calls `search_products`, the `ToolNode` executes that tool, which internally invokes the SQR → Pinecone vector search
- `MessagesPlaceholder` in the prompt template gives the agent **full chat history** on every LLM call
- `ToolNode` with `StructuredTool`-based tools handles **automatic tool dispatch**
- **Three-way routing** from `should_continue`: → `tool_node` (normal tools), → `purchase_confirmation` (purchase with interrupt), → `__end__`
- `graph.get_graph().draw_mermaid()` auto-generates this diagram at build/startup time

This is the **ReAct agent pattern** implemented explicitly as a graph, with a **human-in-the-loop purchase confirmation** step, giving you full control over the loop.

---

## 📝 Migration Plan (9 Phases)

### Phase 1: Foundation — Define LangGraph State
**Files:** `backend/app/models/state.py`

- Replace the current `AgentState` Pydantic model with a LangGraph-compatible `TypedDict` (or `Annotated` state)
- Add `messages: Annotated[list, add_messages]` for LangGraph's message tracking (used by `MessagesPlaceholder`)
- Keep existing fields: `products`, `source`, `has_results`, `user_info`, `purchase_history`
- **NEW:** Add `pending_purchase: Optional[dict]` field to hold product details during purchase confirmation interrupt

```python
from typing import Annotated, Optional, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # ← full chat history
    products: list                           # populated by post-processing
    source: Optional[str]
    has_results: bool
    user_info: Optional[dict]
    purchase_history: list
    pending_purchase: Optional[dict]         # ← NEW: for purchase confirmation
```

### Phase 2: Create the Graph with `MessagesPlaceholder` and `ToolNode` — Replace `create_agent`
**Files:** `backend/app/services/chatbot_service.py` (major refactor)

- Import `StateGraph`, `ToolNode`, `add_messages` from `langgraph`
- **Use `MessagesPlaceholder`** in the `ChatPromptTemplate` to inject the full `state["messages"]` chat history into every LLM call:

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", self._build_system_prompt(user_name)),
    MessagesPlaceholder(variable_name="messages"),
])
agent_with_prompt = prompt | self.llm.bind_tools(tools)
```

- **Use `ToolNode`** as the prebuilt tool execution node — no manual tool dispatch:

```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode(tools)  # auto-handles tool_calls → ToolMessage
workflow.add_node("tools", tool_node)
```

- Define the `agent_node` function that calls `agent_with_prompt.ainvoke({"messages": state["messages"]})`
- Define a `should_continue` conditional edge function with **three-way routing**:
  - If last message has `tool_calls` with `purchase_product` → route to `purchase_confirmation`
  - If last message has other `tool_calls` → route to `tool_node`
  - Otherwise → route to `END`
- Wire up: `__start__` → `agent_node` → (conditional) → `tool_node` / `purchase_confirmation` → `agent_node` (loop)
- Compile the graph: `graph = workflow.compile(checkpointer=memory, interrupt_before=["purchase_confirmation"])`
- Replace `agent_executor.ainvoke()` with `graph.ainvoke()`
- **Remove `last_product_ids` context workaround** — `MessagesPlaceholder` provides full history, so the LLM already knows what products were discussed

### Phase 3: Refactor Tools with `StructuredTool.from_function` — Clean Up State Mutation
**Files:** All files in `backend/app/tools/`

- **Convert factory-function tools to `StructuredTool.from_function`** with explicit Pydantic input schemas
- Remove direct `AgentState` mutation from tools — instead, tools return structured data (JSON strings)
- The graph's post-processing node will extract structured data from tool outputs and update state
- Fix the `purchase_tool.py` inconsistency (uses `state["source"]` dict, while others use `state.source` AgentState)

**Example conversion for `search_products`:**

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import functools

class SearchProductsInput(BaseModel):
    query: str = Field(description="Natural language search query describing what the user wants")

async def _search_products_impl(query: str, *, run_sqr) -> str:
    """Search the product catalog for items matching the user's request."""
    products = await run_sqr(query)
    if not products:
        return json.dumps({"products": [], "source": "none"})
    return json.dumps({"products": [p.model_dump() for p in products], "source": "vector_db"})

# In _build_tools():
search_tool = StructuredTool.from_function(
    coroutine=functools.partial(_search_products_impl, run_sqr=self._run_sqr),
    name="search_products",
    description="Search the product catalog for items matching the user's request.",
    args_schema=SearchProductsInput,
)
```

**Tools to convert:**
| Current Factory Function | → `StructuredTool.from_function` | Input Schema |
|---|---|---|
| `create_search_products_tool()` | `search_products` | `SearchProductsInput(query: str)` |
| `create_email_tool()` | `send_product_email` | `EmailProductInput(product_id: str)` |
| `create_purchase_tool()` | `purchase_product` | `PurchaseProductInput(product_id: str)` |
| `create_user_info_tool()` | `get_user_info` | `UserInfoInput()` (no args) |
| `create_purchase_history_tool()` | `get_purchase_history` | `PurchaseHistoryInput()` (no args) |
| `search_web` (already `@tool`) | Keep as-is or convert | `WebSearchInput(query: str)` |

### Phase 4: Add Purchase Confirmation Node (Human-in-the-Loop)
**Files:** `backend/app/services/chatbot_service.py`, `backend/app/api/routes.py`, `backend/app/models/request.py`

This phase implements the **purchase confirmation interrupt** flow:

**Backend — Graph node:**
- Add `purchase_confirmation` node to the graph
- The `should_continue` conditional edge detects when the LLM's tool call is `purchase_product` and routes to `purchase_confirmation` instead of `tool_node`
- Before executing, the node populates `state["pending_purchase"]` with product details (name, price, SKU)
- The graph is compiled with `interrupt_before=["purchase_confirmation"]` — execution **pauses** here and returns to the API

```python
def purchase_confirmation_node(state: AgentState) -> dict:
    """Execute the purchase after user confirmation."""
    pending = state["pending_purchase"]
    if pending and pending.get("confirmed"):
        # Proceed with purchase — create order
        order_id = f"ORD-{pending['product_id']}-{pending['user_id'][-4:]}"
        return {
            "messages": [ToolMessage(content=f"Order placed! Order ID: {order_id}", tool_call_id=pending["tool_call_id"])],
            "pending_purchase": None,
        }
    else:
        # User cancelled
        return {
            "messages": [ToolMessage(content="Purchase cancelled by user.", tool_call_id=pending["tool_call_id"])],
            "pending_purchase": None,
        }
```

**Backend — API endpoint:**
- Add `POST /api/v1/chat/confirm` endpoint that accepts `{ thread_id, confirmed: bool }`
- On confirm: updates state with `pending_purchase.confirmed = True`, then resumes graph via `graph.ainvoke(Command(resume="confirmed"), config={"configurable": {"thread_id": thread_id}})`
- On cancel: resumes with `Command(resume="cancelled")`

**Backend — Response model:**
- Add `requires_confirmation: bool` and `pending_purchase: Optional[dict]` to `ChatResponse`

**Frontend changes:**
- When `requires_confirmation == true` in response, show a confirmation card:
  - Product name, image, price
  - "Confirm Purchase" / "Cancel" buttons
- On button click, `POST /api/v1/chat/confirm` with the `thread_id`

**Flow summary:**
```
1. User: "Buy the Sony headphones"
2. agent_node: LLM calls purchase_product(product_id="SKU123")
3. should_continue: detects purchase tool → routes to purchase_confirmation
4. INTERRUPT: graph pauses, API returns { requires_confirmation: true, product: {...} }
5. Frontend: shows confirmation card
6. User: clicks "Confirm"
7. API: graph.ainvoke(Command(resume="confirmed"), config={thread_id})
8. purchase_confirmation_node: executes purchase, returns order details
9. agent_node: generates "Your order has been placed!" response
10. __end__: final response returned to frontend
```

### Phase 5: Add Post-Processing Node
**Files:** `backend/app/services/chatbot_service.py`

- Add a `process_results` node that runs after the agent loop ends
- This node examines the message history to:
  - Extract products from `search_products` tool output → populate `state["products"]`
  - Detect source type → populate `state["source"]`
  - Extract user_info / purchase_history from tool outputs
- This replaces the current `_determine_source()` and manual state inspection

### Phase 6: Add Checkpointing (Required for Purchase Confirmation)
**Files:** `backend/app/services/chatbot_service.py`, `backend/app/main.py`

- **NOTE:** This phase is now **required** (not optional) because the purchase confirmation interrupt depends on checkpointing to persist state between the interrupt and resume calls
- Add `MemorySaver` checkpointer for in-memory conversation persistence (development/MVP)
- Or use `AsyncSqliteSaver` / `AsyncPostgresSaver` for durable persistence (production)
- Pass `thread_id=conversation_id` in config to enable multi-turn memory
- This also gives the chatbot true conversation memory — combined with `MessagesPlaceholder`, the chatbot remembers the **entire conversation** without the frontend passing `last_product_ids`

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
compiled_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["purchase_confirmation"],
)

# Invoke with thread_id for conversation persistence
result = await compiled_graph.ainvoke(
    {"messages": [HumanMessage(content=user_query)]},
    config={"configurable": {"thread_id": conversation_id}},
)
```

### Phase 7: Add Graph Visualization with `graph.get_graph()`
**Files:** `backend/app/services/chatbot_service.py`, `backend/app/api/routes.py`, `backend/scripts/`

- **Startup logging:** Log the ASCII graph on service initialization for quick verification:

```python
compiled_graph = workflow.compile(checkpointer=memory, interrupt_before=["purchase_confirmation"])
logger.info("LangGraph workflow compiled:\n%s", compiled_graph.get_graph().print_ascii())
```

- **Debug/dev API endpoint:** Add `GET /api/v1/graph` that returns the Mermaid diagram:

```python
@router.get("/graph")
async def get_workflow_graph():
    graph = chatbot_service.compiled_graph.get_graph()
    return {"mermaid": graph.draw_mermaid()}
```

- **Documentation script:** Add `backend/scripts/generate_graph.py` that writes:
  - `docs/workflow_graph.mmd` (Mermaid text for GitHub rendering)
  - `docs/workflow_graph.png` (PNG image, requires `pyppeteer` — optional dev dependency)

- **Auto-update docs:** The generated Mermaid diagram replaces the manually maintained ASCII art in the migration/implementation docs

### Phase 8: Enable Streaming (Optional Enhancement)
**Files:** `backend/app/api/routes.py`, `backend/app/services/chatbot_service.py`

- Use `graph.astream()` instead of `graph.ainvoke()`
- Add a `StreamingResponse` SSE endpoint for real-time updates
- Frontend can show "Searching products..." → "Found 3 results" → final response

### Phase 9: Update Documentation & Tests
**Files:** `LANGCHAIN_IMPLEMENTATION.md` → rename to `LANGGRAPH_IMPLEMENTATION.md`, tests

- Update architecture documentation with auto-generated Mermaid diagram from `graph.get_graph()`
- Update workflow diagrams
- Document the purchase confirmation flow (API contract, frontend integration)
- Document `MessagesPlaceholder` chat history behavior
- Add/update integration tests for:
  - The new graph (basic flow)
  - Purchase confirmation interrupt/resume flow
  - `StructuredTool` input validation
  - Graph visualization output

---

## 📊 Effort Estimate

| Phase | Effort | Risk | Priority |
|-------|--------|------|----------|
| Phase 1: State model | Small (1-2 hrs) | Low | Required |
| Phase 2: Graph + MessagesPlaceholder + ToolNode | Medium (3-4 hrs) | Medium | Required |
| Phase 3: StructuredTool.from_function refactor | Medium (2-3 hrs) | Low | Required |
| Phase 4: Purchase confirmation (human-in-the-loop) | Medium-Large (4-5 hrs) | Medium | Required |
| Phase 5: Post-processing node | Small (1-2 hrs) | Low | Required |
| Phase 6: Checkpointing (required for Phase 4) | Medium (2-3 hrs) | Low | Required |
| Phase 7: Graph visualization | Small (1-2 hrs) | Low | Recommended |
| Phase 8: Streaming | Medium (3-4 hrs) | Medium | Optional |
| Phase 9: Docs & Tests | Medium (3-4 hrs) | Low | Required |

**Total estimated effort:** ~13-17 hours (core, Phases 1-6), +4-6 hours (recommended, Phase 7) +6-8 hours (optional enhancements, Phases 8-9)

---

## ⚠️ Key Risks & Mitigations

1. **SelfQueryRetriever compatibility** — SQR is from `langchain_classic` and works as a retriever, not a graph node. **Mitigation:** Keep SQR as-is inside the `search_products` `StructuredTool`; it's invoked normally within the tool function.

2. **Tool interface transition** — Moving from `@tool` decorator with closures to `StructuredTool.from_function` requires rewriting tool files. **Mitigation:** The tool *logic* stays identical; only the wrapping changes. Test each tool individually before integrating into the graph.

3. **`langgraph` already installed** — It's in `pyproject.toml` (`langgraph>=1.0.9`), so no new dependency. `MessagesPlaceholder`, `StructuredTool`, and `ToolNode` are all in already-installed packages.

4. **Frontend impact: MINIMAL for most phases, MODERATE for Phase 4** — The REST API contract (`ChatRequest`/`ChatResponse`) stays identical for Phases 1-3. Phase 4 (purchase confirmation) requires:
   - New `requires_confirmation` / `pending_purchase` fields in `ChatResponse`
   - New `POST /api/v1/chat/confirm` endpoint
   - Frontend confirmation UI (product card + confirm/cancel buttons)

5. **Checkpointing is now required** — The purchase confirmation interrupt requires `MemorySaver` (or equivalent) to persist state between interrupt and resume. **Mitigation:** `MemorySaver` (in-memory) is zero-config for development; can upgrade to `AsyncSqliteSaver` for production durability later.

6. **`graph.get_graph().draw_mermaid_png()`** requires `pyppeteer` or `playwright` for PNG rendering. **Mitigation:** Use `draw_mermaid()` (text) by default; add PNG rendering as an optional dev dependency only.

---

## 🎯 Recommendation

**I recommend migrating to LangGraph** for these reasons:

1. You already have `langgraph` as a dependency
2. LangChain's `create_agent` actually uses LangGraph internally — you're already running LangGraph without the benefits
3. The current `AgentState` side-effect mutation pattern is fragile (evidenced by the dict/Pydantic inconsistency in `purchase_tool.py`)
4. LangGraph gives you explicit control flow, which is critical for an e-commerce bot where actions like **purchase** should have clear guardrails
5. **`MessagesPlaceholder`** provides true multi-turn chat history, replacing the fragile `last_product_ids` workaround
6. **`ToolNode` + `StructuredTool.from_function`** give cleaner tool definitions with explicit schemas and automatic dispatch
7. **`graph.get_graph()`** provides self-documenting workflow visualization — the architecture diagram stays in sync with the code
8. **Purchase confirmation via `interrupt_before`** is a critical safety feature for an e-commerce bot — prevents accidental purchases and builds user trust

---

## 📦 Summary of New LangGraph Features Incorporated

| Feature | Import | Used In | Purpose |
|---------|--------|---------|---------|
| `MessagesPlaceholder` | `langchain_core.prompts` | Phase 1 (state), Phase 2 (prompt) | Inject full chat history into every LLM call |
| `graph.get_graph()` | `langgraph` (built-in) | Phase 7 | Auto-generate Mermaid/ASCII workflow diagrams |
| `ToolNode` | `langgraph.prebuilt` | Phase 2 | Prebuilt node for automatic tool dispatch |
| `StructuredTool.from_function` | `langchain_core.tools` | Phase 3 | Explicit Pydantic input schemas for tools |
| `interrupt_before` | `langgraph` (compile option) | Phase 4 | Pause graph for purchase confirmation |
| `MemorySaver` | `langgraph.checkpoint.memory` | Phase 6 | Checkpointing for interrupt/resume + memory |
| `Command(resume=...)` | `langgraph.types` | Phase 4 | Resume graph after user confirmation |

**All features are available in the already-installed packages** (`langgraph>=1.0.9`, `langchain-core>=1.2.3`). No new dependencies required.

---

**Please review this updated plan and let me know if you'd like me to proceed with the implementation, or if you'd like to adjust any phase.**
