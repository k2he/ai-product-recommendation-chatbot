"""LangGraph-based chatbot service — orchestrates requests through the agent graph.

Responsibilities:
  1. LLM initialisation (ChatOllama)
  2. SelfQueryingRetriever lazy init and product retrieval (_get_or_build_sqr)
  3. Build per-request tools with injected user context (_build_tools)
  4. Build the system prompt (_build_system_prompt)
  5. Delegate graph compilation to app.graph.builder.build_chatbot_graph
  6. Run graph.ainvoke() and format the API response (process_chat_interaction)
  7. Execute direct email / purchase actions for the /actions endpoint (execute_action)

Graph structure (defined in app/graph/builder.py):
  __start__ → agent → (should_continue?) → tools ↻ agent → process_results → __end__
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_ollama import ChatOllama

from app.config import get_settings
from app.database.mongodb import mongodb
from app.database.pinecone_db import pinecone_db
from app.graph.builder import build_chatbot_graph
from app.graph.state import AgentState
from app.models import UserInDB
from app.models.product import Product
from app.models.request import IntentType
from app.services.email_service import email_service
from app.tools import (
    create_search_products_tool,
    create_email_tool,
    create_purchase_tool,
    search_web,
    is_web_search_available,
    create_user_info_tool,
    create_purchase_history_tool,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatbotService:
    """LangGraph-based chatbot service using explicit StateGraph."""

    def __init__(self) -> None:
        """Initialize the chatbot service.

        Build order:
          1. LLM
          2. SQR is lazily initialized on first use

        The vectorstore is already connected by the time this constructor runs
        because pinecone_db.connect() is called in main.py's lifespan handler
        before the ChatbotService singleton is first used.
        """
        self.llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
        )

        # SQR is lazily initialized on first use so that the service module can
        # be imported before Pinecone has connected (e.g. during test collection).
        self.sqr: Optional[SelfQueryRetriever] = None

    # ── SQR Construction ───────────────────────────────────────────────────────

    def _get_or_build_sqr(self) -> SelfQueryRetriever:
        """Return the SQR, building it on first call.

        Lazy initialization lets the module load before Pinecone connects,
        and ensures categories.json is read after load_products.py has written it.
        """
        if self.sqr is not None:
            return self.sqr

        categories = self._load_categories()
        self.sqr = pinecone_db.build_sqr(llm=self.llm, categories=categories)
        return self.sqr

    def _load_categories(self) -> list[str]:
        """Read category list from categories.json written by load_products.py."""
        categories_file = (
            Path(__file__).parent.parent.parent / "data" / "categories.json"
        )
        try:
            with open(categories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            categories = data.get("categories", [])
            logger.info("Loaded %d categories from %s", len(categories), categories_file)
            return categories
        except FileNotFoundError:
            logger.warning(
                "categories.json not found — SQR will have no category filter. "
                "Run load_products.py to generate it."
            )
            return []
        except Exception as e:
            logger.warning("Failed to load categories.json: %s", e)
            return []

    # ── Core Methods ───────────────────────────────────────────────────────────

    async def _run_sqr(self, query: str) -> list[Product]:
        """Run the SelfQueryingRetriever and map Documents → Product models.

        SQR handles both query decomposition and the Pinecone vector search
        with metadata filtering in a single call.
        """
        retriever = self._get_or_build_sqr()
        try:
            docs = await retriever.ainvoke(query)
        except Exception as e:
            logger.error("SQR retrieval failed: %s", e)
            return []

        products: list[Product] = []
        for doc in docs:
            meta = doc.metadata
            try:
                products.append(
                    Product(
                        sku=meta.get("sku", meta.get("product_id", "")),
                        name=meta.get("name", ""),
                        shortDescription=meta.get("shortDescription", doc.page_content),
                        customerRating=meta.get("customerRating"),
                        productUrl=meta.get("productUrl", ""),
                        regularPrice=float(meta.get("regularPrice", 0.0)),
                        salePrice=float(meta.get("salePrice", 0.0)),
                        categoryName=meta.get("categoryName", ""),
                        isOnSale=bool(meta.get("isOnSale", False)),
                        highResImage=meta.get("highResImage") or None,
                        relevance_score=None,
                    )
                )
            except Exception as e:
                logger.warning("Skipping malformed product document: %s", e)
        return products

    async def _get_user_info(self, user_id: str) -> Optional[UserInDB]:
        """Retrieve user document from MongoDB."""
        try:
            return await mongodb.get_user(user_id)
        except Exception as e:
            logger.warning("Failed to retrieve user %s: %s", user_id, e)
            return None

    def _build_tools(
        self,
        user_name: str,
        user_email: str,
        user_id: str,
        user_info: UserInDB,
    ) -> list:
        """Build the tools list with injected context.

        Tools no longer receive an AgentState parameter — they return text
        and the post-processing node extracts structured data from the
        message history.

        Args:
            user_name: User's first name
            user_email: User's email address
            user_id: User's ID
            user_info: Full user information object

        Returns:
            List of LangChain tool functions
        """
        tools = []

        # Tool 1: Search products (SQR runs inside this tool)
        search_tool = create_search_products_tool(
            run_sqr=self._run_sqr,
        )
        tools.append(search_tool)

        # Tool 2: Send product email
        email_tool = create_email_tool(
            email_service=email_service,
            get_product_by_id=pinecone_db.get_product_by_id,
            user_name=user_name,
            user_email=user_email,
        )
        tools.append(email_tool)

        # Tool 3: Purchase product
        purchase_tool = create_purchase_tool(
            get_product_by_id=pinecone_db.get_product_by_id,
            user_name=user_name,
            user_email=user_email,
            user_id=user_id,
        )
        tools.append(purchase_tool)

        # Tool 4: Get user information
        user_info_tool = create_user_info_tool(
            user_info=user_info,
        )
        tools.append(user_info_tool)

        # Tool 5: Get purchase history
        purchase_history_tool = create_purchase_history_tool(
            user_id=user_id,
        )
        tools.append(purchase_history_tool)

        # Tool 6: Web search (only if available)
        if is_web_search_available():
            tools.append(search_web)

        return tools

    def _build_system_prompt(self, user_name: str) -> str:
        """Build the system prompt for the agent.

        Context from previous turns is carried in the LangGraph message history,
        so we no longer need last_product_ids or last_product_names in the prompt.

        Args:
            user_name: User's first name

        Returns:
            System prompt string
        """
        return f"""You are a friendly e-commerce shopping assistant chatting with {user_name}.

BEHAVIOR GUIDELINES:
• Be warm, conversational, and helpful
• For greetings or small talk, respond naturally WITHOUT mentioning email or purchase options
• When showing products, provide a concise description to help the user understand their options
• When user asks for account info or purchase history, use the appropriate tool
• Keep responses concise (3-5 sentences)

CONTEXT HANDLING:
• When the user says "it", "that", or "the product" without specifying, refer to the conversation history for the most recently discussed product
• For email/purchase actions, you MUST provide a valid product SKU from search results or conversation history"""

    # ── LangGraph Construction ─────────────────────────────────────────────────

    def _build_graph(self, tools: list):
        """Build and compile the LangGraph StateGraph.

        Delegates to ``app.graph.builder.build_chatbot_graph`` which owns
        the node/edge wiring.  The graph is compiled per-request because
        tools capture user-specific context (name, email, id).
        See ``graph/builder.py`` for the C1 trade-off note.

        Args:
            tools: List of LangChain BaseTool instances.

        Returns:
            Compiled LangGraph graph.
        """
        llm_with_tools = self.llm.bind_tools(tools)
        return build_chatbot_graph(
            llm_with_tools=llm_with_tools,
            tools=tools,
            run_sqr=self._run_sqr,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def process_chat_interaction(
        self,
        user_query: str,
        user_info: UserInDB,
        conversation_id: str,
        last_product_ids: list[str],
    ) -> dict:
        """Execute the chatbot workflow using a LangGraph StateGraph.

        Args:
            user_query: User's query message
            user_info: User information (required, must be pre-fetched by caller)
            conversation_id: Conversation identifier
            last_product_ids: Product SKUs from previous assistant response
                              (kept for API compatibility; context is now in message history)

        Returns:
            Response dict with message, products, and metadata
        """
        try:
            logger.info("Starting LangGraph workflow for query: '%s'", user_query)

            # Validate user info
            if not user_info:
                raise ValueError("user_info is required but was not provided")

            logger.info("Processing request for user: %s", user_info.userId)

            # Extract user details
            user_name = user_info.firstName if user_info.firstName else "there"
            user_email = str(user_info.email)
            user_id = user_info.userId

            # Build tools with injected context (no state parameter)
            tools = self._build_tools(
                user_name=user_name,
                user_email=user_email,
                user_id=user_id,
                user_info=user_info,
            )

            # Build and compile the graph
            graph = self._build_graph(tools)

            # Build system prompt
            system_prompt = self._build_system_prompt(user_name=user_name)

            # Prepare initial messages with system prompt + user query
            # LangGraph initial messages: system prompt + user query
            initial_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query),
            ]

            # Execute the graph
            result = await graph.ainvoke({
                "messages": initial_messages,
                "products": [],
                "source": None,
                "has_results": False,
                "user_info": None,
                "purchase_history": [],
            })

            # Extract response from the last AI message
            response_text = self._extract_response(result)
            products = result.get("products", [])
            source = result.get("source", "general_chat")
            has_results = result.get("has_results", False)

            logger.info(
                "LangGraph workflow complete — source: %s, products: %d",
                source,
                len(products),
            )

            return {
                "message": response_text.strip(),
                "products": products,
                "conversation_id": conversation_id,
                "has_results": has_results,
                "source": source,
                "error": None,
            }

        except Exception as e:
            logger.error("LangGraph workflow error: %s", e)
            return {
                "message": "I apologize, but I encountered an error. Please try again.",
                "products": [],
                "conversation_id": conversation_id,
                "has_results": False,
                "source": "none",
                "user_info": None,
                "purchase_history": [],
                "error": str(e),
            }

    def _extract_response(self, result: dict) -> str:
        """Extract the final AI response text from graph result."""
        messages = result.get("messages", [])
        # Walk backwards to find the last AIMessage (not a ToolMessage)
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                return msg.content if msg.content else ""
            if isinstance(msg, AIMessage) and msg.content:
                # AIMessage with tool_calls but also content (some models do this)
                return msg.content
        return "I apologize, but I couldn't generate a response."

    async def execute_action(
        self,
        action: IntentType,
        product_id: str,
        user_info: UserInDB,
    ) -> dict[str, Any]:
        """Execute an email or purchase action for a specific product.

        This method is kept for backward compatibility with the /action endpoint.

        Args:
            action: The action to perform (IntentType.EMAIL or IntentType.PURCHASE)
            product_id: Product SKU
            user_info: User information

        Returns:
            Action result dict with success status, message, and optional details
        """
        try:
            if not user_info:
                raise ValueError("user_info is required but was not provided")

            # Validate product exists
            product = await pinecone_db.get_product_by_id(product_id)
            if not product:
                return {
                    "success": False,
                    "message": f"Product '{product_id}' not found.",
                    "error": "product_not_found",
                }

            user_name = user_info.firstName if user_info.firstName else "there"
            user_email = str(user_info.email)

            # Execute action
            if action == IntentType.EMAIL:
                await email_service.send_product_email(
                    recipient_email=user_email,
                    recipient_name=user_name,
                    product=product,
                )

                return {
                    "success": True,
                    "message": (
                        f"Done, {user_name}! I've sent the details for "
                        f"**{product.name}** to {user_email}. Check your inbox! 📧"
                    ),
                    "details": {"email": user_email, "product_name": product.name},
                }

            elif action == IntentType.PURCHASE:
                order_id = f"ORD-{product_id}-{user_info.userId[-4:]}"

                return {
                    "success": True,
                    "message": (
                        f"Great choice, {user_name}! Your order for **{product.name}** "
                        f"has been placed. Order ID: `{order_id}`. "
                        f"Total: ${product.salePrice:.2f} CAD. "
                        f"A confirmation will be sent to {user_email}. 🛒"
                    ),
                    "details": {
                        "order_id": order_id,
                        "product_name": product.name,
                        "price": product.salePrice,
                    },
                }

            else:
                return {
                    "success": False,
                    "message": f"Unknown action: {action.value}",
                    "error": "unknown_action",
                }

        except Exception as e:
            logger.error("Action error (%s): %s", action.value, e)
            return {
                "success": False,
                "message": "Failed to execute action. Please try again.",
                "error": str(e),
            }


# Global singleton — constructed at import time, SQR built lazily on first query
chatbot_service = ChatbotService()
