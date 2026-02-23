"""LangChain-based chatbot workflow using Tool-Calling Agent.

Architecture:
  Single Agent with 4 Tools:
    1. search_products  — Search product catalog via SelfQueryingRetriever
    2. send_product_email — Email product details to user
    3. purchase_product — Place an order for a product
    4. search_web — Search the web for factual questions (via Tavily)

  The LLM decides which tool(s) to call based on the user's message.
  No explicit intent classification - the agent handles routing directly.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_ollama import ChatOllama
from langchain.agents import create_agent

from app.config import get_settings
from app.database.mongodb import mongodb
from app.database.pinecone_db import pinecone_db
from app.models import UserInDB, AgentState
from app.models.product import Product
from app.models.request import IntentType
from app.services.email_service import email_service
from app.tools import (
    create_search_products_tool,
    create_email_tool,
    create_purchase_tool,
    search_web,
    is_web_search_available,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatbotService:
    """LangChain-based chatbot service using Tool-Calling Agent."""

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
        state: AgentState,
        user_name: str,
        user_email: str,
        user_id: str,
    ) -> list:
        """Build the tools list with injected context.

        Args:
            state: Shared AgentState for tools to store results
            user_name: User's first name
            user_email: User's email address
            user_id: User's ID

        Returns:
            List of LangChain tool functions
        """
        tools = []

        # Tool 1: Search products
        search_tool = create_search_products_tool(
            run_sqr=self._run_sqr,
            state=state,
        )
        tools.append(search_tool)

        # Tool 2: Send product email
        email_tool = create_email_tool(
            email_service=email_service,
            get_product_by_id=pinecone_db.get_product_by_id,
            state=state,
            user_name=user_name,
            user_email=user_email,
        )
        tools.append(email_tool)

        # Tool 3: Purchase product
        purchase_tool = create_purchase_tool(
            get_product_by_id=pinecone_db.get_product_by_id,
            state=state,
            user_name=user_name,
            user_email=user_email,
            user_id=user_id,
        )
        tools.append(purchase_tool)

        # Tool 4: Web search (only if available)
        if is_web_search_available():
            tools.append(search_web)

        return tools

    def _build_system_prompt(
        self,
        user_name: str,
        last_product_ids: list[str],
        last_product_names: str,
    ) -> str:
        """Build the system prompt for the agent.

        Args:
            user_name: User's first name
            last_product_ids: Product SKUs from previous response
            last_product_names: Formatted string of product names

        Returns:
            System prompt string
        """
        context_section = ""
        if last_product_ids:
            context_section = f"""
CONVERSATION CONTEXT:
Previously shown products: {last_product_names}
Product SKUs for reference: {', '.join(last_product_ids[:3])}
If the user refers to "it", "that", or "the product", use the first SKU: {last_product_ids[0]}
"""

        return f"""You are a friendly e-commerce shopping assistant chatting with {user_name}.
{context_section}
BEHAVIOR GUIDELINES:
• Be warm, conversational, and helpful
• For greetings or small talk, respond naturally then guide toward shopping
• After showing products, end with: "📬 Want to go further? **Send these product details to your email** or **purchase one right now** — just let me know!"
• Keep responses concise (3-5 sentences)

CONTEXT HANDLING:
• When the user says "it", "that", or "the product" without specifying, use the first product SKU from context above
• For email/purchase actions, you MUST provide a valid product SKU from search results or conversation context"""

    async def _resolve_product_names(self, product_ids: list[str]) -> str:
        """Resolve product IDs to names for context."""
        if not product_ids:
            return "none"

        names = []
        for pid in product_ids[:3]:
            product = await pinecone_db.get_product_by_id(pid)
            if product:
                names.append(f"{product.name} (SKU: {pid})")

        return ", ".join(names) if names else "none"

    def _extract_response_from_agent(self, result: dict) -> str:
        """Extract the final response text from agent result."""
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, 'content'):
                return last_msg.content
            return str(last_msg)
        return "I apologize, but I couldn't generate a response."

    def _determine_source(self, result: dict, state: AgentState) -> str:
        """Determine the source based on agent execution and state."""
        # If state has explicit source from tools, use it
        if state.source:
            return state.source

        # Check if any tool was called
        messages = result.get("messages", [])
        tool_used = any(
            hasattr(msg, 'tool_calls') and msg.tool_calls
            for msg in messages
            if hasattr(msg, 'tool_calls')
        )

        if tool_used:
            # Check for web search specifically
            for msg in messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.get("name") == "search_web":
                            return "general_chat_with_search"
            return "vector_db"  # Default for other tools

        return "general_chat"

    # ── Public API ─────────────────────────────────────────────────────────────

    async def process_chat_interaction(
        self,
        user_query: str,
        user_info: UserInDB,
        conversation_id: str,
        last_product_ids: list[str],
    ) -> dict:
        """Execute the chatbot workflow using a tool-calling agent.

        Args:
            user_query: User's query message
            user_info: User information (required, must be pre-fetched by caller)
            conversation_id: Conversation identifier
            last_product_ids: Product SKUs from previous assistant response

        Returns:
            Response dict with message, products, and metadata
        """
        try:
            logger.info("Starting agent workflow for query: '%s'", user_query)

            # Validate user info
            if not user_info:
                raise ValueError("user_info is required but was not provided")

            logger.info("Processing request for user: %s", user_info.userId)

            # Extract user details
            user_name = user_info.firstName if user_info.firstName else "there"
            user_email = str(user_info.email)
            user_id = user_info.userId

            # Resolve product names for context
            last_product_ids = last_product_ids or []
            last_product_names = await self._resolve_product_names(last_product_ids)

            # Create shared state for tools to populate
            state = AgentState()

            # Build tools with injected context
            tools = self._build_tools(
                state=state,
                user_name=user_name,
                user_email=user_email,
                user_id=user_id,
            )

            # Build system prompt
            system_prompt = self._build_system_prompt(
                user_name=user_name,
                last_product_ids=last_product_ids,
                last_product_names=last_product_names,
            )

            # Create and execute agent
            logger.info("Creating agent with %d tools", len(tools))
            agent_executor = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=system_prompt,
            )

            result = await agent_executor.ainvoke({
                "messages": [("user", user_query)]
            })

            # Extract response
            response_text = self._extract_response_from_agent(result)
            source = self._determine_source(result, state)
            products = state.products
            has_results = state.has_results

            logger.info(
                "Agent workflow complete — source: %s, products: %d",
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
            logger.error("Agent workflow error: %s", e)
            return {
                "message": "I apologize, but I encountered an error. Please try again.",
                "products": [],
                "conversation_id": conversation_id,
                "has_results": False,
                "source": "none",
                "error": str(e),
            }

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
                # Should never happen with enum validation, but good to have
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
