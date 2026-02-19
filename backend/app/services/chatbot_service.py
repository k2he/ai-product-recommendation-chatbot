"""LangChain-based chatbot workflow.

Chains:
  1. intent_chain     — LLM classifies user message as 'search', 'email', or 'purchase'
  2. rephrase_chain   — LLM optimises the query for vector search AND emits a Pinecone
                        metadata filter (categoryName, salePrice, customerRating)
  3. response_chain   — LLM generates a friendly recommendation response with a CTA
                        asking the user if they want email or purchase
"""

import json
import logging
import re
from typing import Any, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_community.tools.tavily_search import TavilySearchResults

from app.config import get_settings
from app.database.mongodb import mongodb
from app.database.pinecone_db import pinecone_db
from app.models.product import Product
from app.models.request import ActionType
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatbotService:
    """LangChain-based chatbot service."""

    def __init__(self) -> None:
        """Initialize the chatbot service."""
        self.llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
        )

        try:
            if settings.tavily_api_key:
                self.tavily = TavilySearchResults(
                    max_results=settings.tavily_max_results,
                    search_depth=settings.tavily_search_depth,
                )
            else:
                self.tavily = None
        except Exception as e:
            logger.warning(f"Failed to initialize Tavily: {e}")
            self.tavily = None

        self._build_chains()

    def _build_chains(self) -> None:
        """Build all LangChain chains used in the workflow."""

        # ── Chain 1: Intent Detection ──────────────────────────────────────
        # Runs first on every message to decide which workflow branch to take.
        intent_prompt = PromptTemplate.from_template(
            """You are an intent classifier for a product recommendation chatbot.

            Classify the user's message into EXACTLY one of these intents:
            - "search"   : The user is looking for products, asking questions, or browsing.
            - "email"    : The user wants to receive product details via email
                           (e.g. "send it to me", "email me that", "shoot it to my inbox").
            - "purchase" : The user wants to buy or order a product
                           (e.g. "I'll take it", "buy the Sony ones", "purchase that laptop").
            
            Rules:
            - If the message is ambiguous between email/purchase and search, choose "search".
            - Return ONLY a JSON object with two fields and nothing else:
              {{"intent": "<search|email|purchase>", "product_hint": "<product name or null>"}}
            
            Previously shown products (may be referenced): {last_product_names}
            User message: {query}
            
            JSON response:"""
        )
        self.intent_chain = intent_prompt | self.llm | StrOutputParser()

        # ── Chain 2: Query Rephrasing + Metadata Filter ────────────────────
        # Produces a rephrased query string AND an optional Pinecone filter dict.
        rephrase_prompt = PromptTemplate.from_template(
            """You are a search query optimizer for a BestBuy Canada product catalogue.

            Your job is to:
            1. Rephrase the user's query into a concise, keyword-rich semantic search string.
            2. Extract any metadata filters the user explicitly mentioned.
            
            Supported filter fields (use Pinecone filter syntax):
            - categoryName  : Use {{"$in": [...]}} with the most relevant category names from:
              {available_categories}
            - salePrice     : Use {{"$lte": <number>}} for "under $X", {{"$gte": <number>}} for "over $X"
            - customerRating: Use {{"$gte": <number>}} for "4 stars+", "highly rated", "top rated" etc.
            - isOnSale      : Use true for "on sale", "discounted", "deals"
            
            Rules:
            - Only add a filter field if the user explicitly mentioned it.
            - If no filters apply, return an empty object for "filter".
            - Return ONLY valid JSON and nothing else.
            
            User query: {query}
            
            Respond with exactly this JSON shape:
            {{"rephrased": "<optimised search string>", "filter": {{}}}}"""
        )
        self.rephrase_chain = rephrase_prompt | self.llm | StrOutputParser()

        # ── Chain 3: Response Generation ───────────────────────────────────
        # Generates the final user-facing message with a CTA.
        response_prompt = PromptTemplate.from_template(
            """You are a friendly and helpful product recommendation assistant for BestBuy Canada.

            User name: {user_name}
            Products found: {has_results}
            Source: {source}
            
            {products}
            
            Instructions:
            - Greet the user by first name and summarise what you found in a warm, conversational tone.
            - Highlight key selling points (price, rating, sale status) for up to 3 products.
            - At the end of your response, always add this call-to-action on a new line:
              "Would you like me to **send these product details to your email**, or would you like to **purchase** one of them? Just let me know!"
            - If no products were found, apologise and suggest the user try different keywords.
            - Keep the response concise — 3 to 5 sentences before the CTA.
            
            Response:"""
        )
        self.response_chain = response_prompt | self.llm | StrOutputParser()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _load_available_categories(self) -> str:
        """Load categories from categories.json for use in the rephrase prompt."""
        import json
        from pathlib import Path
        categories_file = Path(__file__).parent.parent.parent / "data" / "categories.json"
        try:
            with open(categories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ", ".join(data.get("categories", []))
        except Exception:
            return "(categories unavailable)"

    def _parse_json_from_llm(self, raw: str) -> dict:
        """Extract a JSON object from LLM output, stripping markdown fences."""
        raw = raw.strip()
        # Remove ```json ... ``` or ``` ... ``` fences
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
        # Find first { ... } block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"No JSON object found in LLM output: {raw}")

    async def _get_user_info(self, user_id: str):
        """Retrieve user from MongoDB."""
        try:
            return await mongodb.get_user(user_id)
        except Exception as e:
            logger.warning(f"Failed to retrieve user {user_id}: {e}")
            return None

    async def _search_products(
        self,
        query: str,
        metadata_filter: Optional[dict] = None,
    ) -> list[Product]:
        """Search Pinecone with optional metadata filter."""
        try:
            return await pinecone_db.search_products(
                query,
                top_k=settings.vector_search_top_k,
                threshold=settings.vector_search_threshold,
                metadata_filter=metadata_filter or None,
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _web_search(self, query: str) -> list[dict]:
        """Fallback Tavily web search."""
        if not self.tavily:
            return []
        try:
            return await self.tavily.ainvoke(query)
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def _generate_response(
        self,
        user_name: str,
        products: list[Product],
        has_results: bool,
        source: str,
    ) -> str:
        """Run the response generation chain."""
        product_text = ""
        if products:
            lines = []
            for i, p in enumerate(products[:5], 1):
                sale_tag = " 🏷️ ON SALE" if p.isOnSale else ""
                rating = f" | ⭐ {p.customerRating}/5" if p.customerRating else ""
                lines.append(
                    f"{i}. {p.name}{sale_tag}{rating}\n"
                    f"   Price: ${p.salePrice:.2f} CAD{' (was $' + f'{p.regularPrice:.2f}' + ')' if p.isOnSale else ''}\n"
                    f"   Category: {p.categoryName}\n"
                    f"   {p.shortDescription[:180]}..."
                )
            product_text = "\n\n".join(lines)
        else:
            product_text = "No products found."

        result = await self.response_chain.ainvoke({
            "user_name": user_name,
            "has_results": str(has_results),
            "source": source,
            "products": product_text,
        })
        return result.strip()

    async def _generate_web_response(self, user_name: str, web_results: list[dict]) -> str:
        """Generate a response from Tavily web search results."""
        summary = "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
            for r in web_results[:3]
        )
        result = await self.response_chain.ainvoke({
            "user_name": user_name,
            "has_results": "True (web search)",
            "source": "web_search",
            "products": f"Web search results:\n{summary}",
        })
        return result.strip()

    # ── Public API ─────────────────────────────────────────────────────────

    async def execute_query(
        self,
        user_query: str,
        user_id: str,
        conversation_id: str,
        last_product_ids: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Execute the chatbot workflow.

        Workflow:
          Step 0 — Intent detection (LLM)
                   → 'email' or 'purchase': skip search, trigger action directly
                   → 'search': continue to Steps 1-5
          Step 1 — Rephrase query + extract metadata filter (LLM)
          Step 2 — Retrieve user info (MongoDB)
          Step 3 — Vector search with optional filter (Pinecone)
          Step 4 — Web search fallback if no results (Tavily)
          Step 5 — Generate response with CTA (LLM)
        """
        try:
            logger.info(f"Starting workflow for query: '{user_query}'")

            # ── Step 0: Intent Detection ───────────────────────────────────
            logger.info("Step 0: Detecting intent")
            last_product_ids = last_product_ids or []

            # Resolve last product names for context (best-effort)
            last_product_names = "none"
            if last_product_ids:
                fetched = []
                for pid in last_product_ids[:3]:
                    p = await pinecone_db.get_product_by_id(pid)
                    if p:
                        fetched.append(p.name)
                if fetched:
                    last_product_names = ", ".join(fetched)

            intent_raw = await self.intent_chain.ainvoke({
                "query": user_query,
                "last_product_names": last_product_names,
            })

            try:
                intent_data = self._parse_json_from_llm(intent_raw)
                intent = intent_data.get("intent", "search").lower()
                product_hint = intent_data.get("product_hint")
            except Exception as e:
                logger.warning(f"Intent parsing failed, defaulting to 'search': {e}")
                intent = "search"
                product_hint = None

            logger.info(f"Detected intent: '{intent}', product_hint: '{product_hint}'")

            # ── Intent branch: email or purchase ──────────────────────────
            if intent in ("email", "purchase") and last_product_ids:
                # Use the first product from last shown products, or match by hint
                target_id = last_product_ids[0]
                if product_hint and len(last_product_ids) > 1:
                    # Try to find the best matching product by hint
                    for pid in last_product_ids:
                        p = await pinecone_db.get_product_by_id(pid)
                        if p and product_hint.lower() in p.name.lower():
                            target_id = pid
                            break

                action_result = await self.execute_action(
                    action=ActionType(intent),
                    product_id=target_id,
                    user_id=user_id,
                )
                return {
                    "message": action_result["message"],
                    "products": [],
                    "conversation_id": conversation_id,
                    "has_results": False,
                    "source": "action",
                    "error": None if action_result["success"] else action_result.get("error"),
                }

            # ── Step 1: Rephrase + filter ──────────────────────────────────
            logger.info("Step 1: Rephrasing query and extracting metadata filter")
            available_categories = self._load_available_categories()

            rephrase_raw = await self.rephrase_chain.ainvoke({
                "query": user_query,
                "available_categories": available_categories,
            })

            try:
                rephrase_data = self._parse_json_from_llm(rephrase_raw)
                rephrased_query = rephrase_data.get("rephrased", user_query).strip()
                metadata_filter = rephrase_data.get("filter") or None
                # Sanitise: empty dict → None
                if metadata_filter == {}:
                    metadata_filter = None
            except Exception as e:
                logger.warning(f"Rephrase parsing failed, using original query: {e}")
                rephrased_query = user_query
                metadata_filter = None

            logger.info(f"Rephrased: '{user_query}' → '{rephrased_query}'")
            logger.info(f"Metadata filter: {metadata_filter}")

            # ── Step 2: User info ──────────────────────────────────────────
            logger.info(f"Step 2: Retrieving user info for user_id: {user_id}")
            user_info = await self._get_user_info(user_id)
            user_name = user_info.firstName if user_info else "there"

            # ── Step 3: Vector search ──────────────────────────────────────
            logger.info("Step 3: Searching vector database")
            products = await self._search_products(rephrased_query, metadata_filter)
            search_source = "vector_db" if products else "none"

            # ── Step 4: Web search fallback ────────────────────────────────
            if not products and self.tavily:
                logger.info("Step 4: Falling back to web search")
                web_results = await self._web_search(rephrased_query)
                if web_results:
                    return {
                        "message": await self._generate_web_response(user_name, web_results),
                        "products": [],
                        "conversation_id": conversation_id,
                        "has_results": True,
                        "source": "web_search",
                        "error": None,
                    }

            # ── Step 5: Generate response ──────────────────────────────────
            logger.info("Step 5: Generating response")
            response_message = await self._generate_response(
                user_name=user_name,
                products=products,
                has_results=len(products) > 0,
                source=search_source,
            )

            logger.info(f"Workflow completed. Found {len(products)} products")
            return {
                "message": response_message,
                "products": products,
                "conversation_id": conversation_id,
                "has_results": len(products) > 0,
                "source": search_source,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return {
                "message": "I apologise, but I encountered an error processing your request. Please try again.",
                "products": [],
                "conversation_id": conversation_id,
                "has_results": False,
                "source": "none",
                "error": str(e),
            }

    async def execute_action(
        self,
        action: ActionType,
        product_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Execute an email or purchase action for a specific product."""
        try:
            user_info = await self._get_user_info(user_id)
            if not user_info:
                return {
                    "success": False,
                    "message": "User not found.",
                    "error": "user_not_found",
                }

            product = await pinecone_db.get_product_by_id(product_id)
            if not product:
                return {
                    "success": False,
                    "message": f"Product '{product_id}' not found.",
                    "error": "product_not_found",
                }

            user_name = user_info.firstName if user_info.firstName else "there"
            if action == ActionType.EMAIL:
                try:
                    await email_service.send_product_email(
                        to_email=user_info.email,
                        user_name=user_name,
                        product=product,
                    )
                    return {
                        "success": True,
                        "message": (
                            f"Done, {user_name}! I've sent the details for **{product.name}** "
                            f"to {user_email}. Check your inbox! 📧"
                        ),
                        "details": {"email": user_email, "product_name": product.name},
                    }
                except Exception as e:
                    logger.error(f"Email sending failed: {e}")
                    return {
                        "success": False,
                        "message": "Failed to send email. Please try again.",
                        "error": str(e),
                    }

            elif action == ActionType.PURCHASE:
                # Simulate purchase — replace with real payment integration
                order_id = f"ORD-{product_id}-{user_id[-4:]}"
                return {
                    "success": True,
                    "message": (
                        f"Great choice, {user_name}! Your order for **{product.name}** "
                        f"has been placed. Order ID: `{order_id}`. "
                        f"Total: ${product.salePrice:.2f} CAD. "
                        f"You'll receive a confirmation at {user_email}. 🛒"
                    ),
                    "details": {
                        "order_id": order_id,
                        "product_name": product.name,
                        "price": product.salePrice,
                    },
                }

            return {
                "success": False,
                "message": f"Unknown action: {action}",
                "error": "unknown_action",
            }

        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            return {
                "success": False,
                "message": "Failed to execute action. Please try again.",
                "error": str(e),
            }


# Global chatbot service instance
chatbot_service = ChatbotService()
