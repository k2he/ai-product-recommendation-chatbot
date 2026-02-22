"""LangChain-based chatbot workflow.

Chains / retrievers:
  1. intent_chain  — LLM classifies user message as 'search', 'email', or 'purchase'
  2. sqr           — SelfQueryingRetriever: decomposes the query into a semantic
                     search string + Pinecone metadata filter in one LLM call,
                     then runs the vector search. Replaces the old rephrase_chain
                     + manual metadata_filter plumbing entirely.
  3. response_chain — LLM generates a friendly recommendation response with a CTA
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama

from app.config import get_settings
from app.database.mongodb import mongodb
from app.database.pinecone_db import pinecone_db
from app.models import UserInDB
from app.models.product import Product
from app.models.request import IntentResponse, IntentType
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatbotService:
    """LangChain-based chatbot service using SelfQueryingRetriever."""

    def __init__(self) -> None:
        """Initialise the chatbot service.

        Build order:
          1. LLM
          2. intent_chain and response_chain (no external deps)
          3. Load categories.json → build SQR (needs vectorstore + LLM + categories)

        The vectorstore is already connected by the time this constructor runs
        because pinecone_db.connect() is called in main.py's lifespan handler
        before the ChatbotService singleton is first used.
        """
        self.llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
        )

        # sqr is lazily initialised on first use so that the service module can
        # be imported before Pinecone has connected (e.g. during test collection).
        self.sqr: Optional[SelfQueryRetriever] = None

        self._build_chains()

    # ── Chain / retriever construction ─────────────────────────────────────────

    def _build_chains(self) -> None:
        """Build intent_chain and response_chain."""

        # ── Chain 1: Intent Detection (with Structured Output) ────────────────
        intent_prompt = PromptTemplate.from_template(
            """Classify the user's intent for a product recommendation chatbot.

INTENT MEANINGS:
• Browsing/searching for products or asking questions
• Requesting product details via email (e.g. "send it to me", "email that")
• Wanting to purchase/order a product (e.g. "I'll take it", "buy the Sony ones")

CONTEXT:
Previously shown products: {last_product_names}

INSTRUCTIONS:
- Choose the most appropriate intent (default to the first if ambiguous)
- Extract any specific product name mentioned, or leave blank if none

USER MESSAGE: {query}"""
        )
        # Use structured output - returns IntentResponse directly
        self.intent_chain = intent_prompt | self.llm.with_structured_output(
            IntentResponse
        )

        # ── Chain 2: Response Generation ───────────────────────────────────────
        response_prompt = PromptTemplate.from_template(
            """Generate a friendly product recommendation response for BestBuy Canada.

USER: {user_name}
FOUND: {has_results}
SOURCE: {source}

PRODUCTS:
{products}

RESPONSE GUIDELINES:
• Greet {user_name} by first name with a warm, conversational tone
• Summarize findings and highlight key selling points (price, rating, sales) for top 3 products
• Keep it concise: 3-5 sentences maximum

IF PRODUCTS FOUND, end with exactly:
---CTA---
📬 Want to go further? **Send these product details to your email** or **purchase one right now** — just let me know!

IF NO PRODUCTS FOUND:
• Apologize politely and suggest trying different keywords
• Omit the CTA section

Generate response:"""
        )
        self.response_chain = response_prompt | self.llm | StrOutputParser()

    def _get_or_build_sqr(self) -> SelfQueryRetriever:
        """Return the SQR, building it on first call.

        Lazy initialisation lets the module load before Pinecone connects,
        and ensures categories.json is read after load_products.py has written it.
        """
        if self.sqr is not None:
            return self.sqr

        categories = self._load_categories()
        self.sqr = pinecone_db.build_sqr(llm=self.llm, categories=categories)
        return self.sqr

    # ── Helpers ────────────────────────────────────────────────────────────────

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


    async def _get_user_info(self, user_id: str) -> Optional[UserInDB]:
        """Retrieve user document from MongoDB."""
        try:
            return await mongodb.get_user(user_id)
        except Exception as e:
            logger.warning("Failed to retrieve user %s: %s", user_id, e)
            return None

    async def _run_sqr(self, query: str) -> list[Product]:
        """Run the SelfQueryingRetriever and map Documents → Product models.

        SQR handles both query decomposition and the Pinecone vector search
        with metadata filtering in a single call. The LLM inside SQR interprets
        the query, extracts any filters, and translates them to Pinecone syntax
        automatically.
        """
        retriever = self._get_or_build_sqr()
        try:
            # SQR.ainvoke returns a list of LangChain Document objects
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
                        relevance_score=None,  # SQR does not expose scores
                    )
                )
            except Exception as e:
                logger.warning("Skipping malformed product document: %s", e)
        return products


    async def _generate_response(
        self,
        user_name: str,
        products: list[Product],
        has_results: bool,
        source: str,
    ) -> str:
        """Run the response generation chain."""
        if products:
            lines = []
            for i, p in enumerate(products[:5], 1):
                sale_tag = " 🏷️ ON SALE" if p.isOnSale else ""
                rating = f" | ⭐ {p.customerRating}/5" if p.customerRating else ""
                lines.append(
                    f"{i}. {p.name}{sale_tag}{rating}\n"
                    f"   Price: ${p.salePrice:.2f} CAD"
                    + (f" (was ${p.regularPrice:.2f})" if p.isOnSale else "")
                    + f"\n   Category: {p.categoryName}\n"
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


    async def _detect_intent(
        self,
        user_query: str,
        last_product_ids: list[str],
    ) -> tuple[IntentType, Optional[str]]:
        """Detect user intent and extract product hint.

        Returns:
            Tuple of (intent_enum, product_hint)
        """
        # Resolve product names for the intent prompt context
        last_product_names = "none"
        if last_product_ids:
            fetched_names = []
            for pid in last_product_ids[:3]:
                p = await pinecone_db.get_product_by_id(pid)
                if p:
                    fetched_names.append(p.name)
            if fetched_names:
                last_product_names = ", ".join(fetched_names)

        try:
            intent_response = await self.intent_chain.ainvoke({
                "query": user_query,
                "last_product_names": last_product_names,
            })
            # Use intent_response.intent directly (already IntentType)
            intent_enum = intent_response.intent
            product_hint = intent_response.product_hint
        except Exception as e:
            logger.warning("Intent detection failed, defaulting to 'search': %s", e)
            intent_enum, product_hint = IntentType.SEARCH, None

        logger.info("Intent: '%s' | product_hint: '%s'", intent_enum, product_hint)
        return intent_enum, product_hint

    async def _resolve_target_product_id(
        self,
        last_product_ids: list[str],
        product_hint: Optional[str],
    ) -> str:
        """Resolve which product ID to use for email/purchase actions.

        If product_hint is provided and matches one of the last products,
        use that. Otherwise, use the first product.
        """
        target_id = last_product_ids[0]

        if product_hint and len(last_product_ids) > 1:
            for pid in last_product_ids:
                p = await pinecone_db.get_product_by_id(pid)
                if p and product_hint.lower() in p.name.lower():
                    target_id = pid
                    break

        return target_id

    async def _handle_action_intent(
        self,
        intent: IntentType,
        product_hint: Optional[str],
        last_product_ids: list[str],
        user_info: Optional[UserInDB],
        conversation_id: str,
    ) -> Optional[dict[str, Any]]:
        """Handle email or purchase intent.

        Args:
            intent: Detected intent (EMAIL or PURCHASE)
            product_hint: Product name hint extracted from query
            last_product_ids: Product SKUs from previous response
            user_info: Pre-fetched user info to avoid duplicate DB call
            conversation_id: Conversation identifier

        Returns:
            Response dict if action was executed, None if intent is not email/purchase
        """
        if intent not in (IntentType.EMAIL, IntentType.PURCHASE) or not last_product_ids:
            return None

        target_id = await self._resolve_target_product_id(last_product_ids, product_hint)

        action_result = await self.execute_action(
            action=intent,
            product_id=target_id,
            user_info=user_info,
        )

        return {
            "message": action_result["message"],
            "products": [],
            "conversation_id": conversation_id,
            "has_results": False,
            "source": "action",
            "error": None if action_result["success"] else action_result.get("error"),
        }

    async def _handle_search_workflow(
        self,
        user_query: str,
        user_info: UserInDB,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Handle the search workflow (Steps 1-4).

        Args:
            user_query: User's search query
            user_info: User information (required, must be pre-fetched by caller)
            conversation_id: Conversation identifier

        Returns:
            Response dict with search results and generated message
        """
        # ── Step 1: User info validation ───────────────────────────────────
        if not user_info:
            raise ValueError("user_info is required but was not provided")

        logger.info("Step 1: Using user info for: %s", user_info.userId)
        user_name = user_info.firstName if user_info.firstName else "there"

        # ── Step 2: SelfQueryingRetriever ─────────────────────────────────
        logger.info("Step 2: Running SelfQueryingRetriever")
        products = await self._run_sqr(user_query)
        search_source = "vector_db" if products else "none"
        logger.info("SQR returned %d products", len(products))

        # ── Step 3: Generate response ──────────────────────────────────────
        logger.info("Step 3: Generating response")
        response_message = await self._generate_response(
            user_name=user_name,
            products=products,
            has_results=bool(products),
            source=search_source,
        )

        logger.info("Workflow complete — %d products returned", len(products))
        return {
            "message": response_message,
            "products": products,
            "conversation_id": conversation_id,
            "has_results": bool(products),
            "source": search_source,
            "error": None,
        }

    async def _execute_email_action(
        self,
        user_name: str,
        user_email: str,
        product: Product,
    ) -> dict[str, Any]:
        """Execute email action - send product details to user.

        Returns:
            Action result dict with success status and message
        """
        try:
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
        except Exception as e:
            logger.error("Email sending failed: %s", e)
            return {
                "success": False,
                "message": "Failed to send email. Please try again.",
                "error": str(e),
            }

    async def _execute_purchase_action(
        self,
        user_name: str,
        user_email: str,
        product: Product,
        product_id: str,
        user_info: UserInDB,
    ) -> dict[str, Any]:
        """Execute purchase action - place order for product.

        Args:
            user_name: User's first name
            user_email: User's email address
            product: Product to purchase
            product_id: Product SKU
            user_info: User information for generating order ID

        Returns:
            Action result dict with success status and message
        """
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

    # ── Public API ─────────────────────────────────────────────────────────────

    async def process_chat_interaction(
        self,
        user_query: str,
        user_info: UserInDB,
        conversation_id: str,
        last_product_ids: list[str],
    ) -> dict:
        """Execute the full chatbot workflow.

        Args:
            user_query: User's query message
            user_info: User information (required, must be pre-fetched by caller)
            conversation_id: Conversation identifier
            last_product_ids: Product SKUs from previous assistant response

        Workflow:
          Step 0 — intent_chain (LLM)
                   → 'email' or 'purchase': resolve product, call execute_action, return
                   → 'search': continue
          Step 1 — User validation
          Step 2 — SelfQueryingRetriever (single LLM call)
                   Decomposes query into semantic string + metadata filter,
                   runs Pinecone search with filter applied.
          Step 3 — response_chain (LLM) generates friendly reply + CTA
        """
        try:
            logger.info("Starting workflow for query: '%s'", user_query)

            # ── Validate user info ─────────────────────────────────────────────
            if not user_info:
                raise ValueError("user_info is required but was not provided")

            logger.info("Processing request for user: %s", user_info.userId)

            # ── Step 0: Intent Detection ───────────────────────────────────────
            logger.info("Step 0: Detecting intent")
            last_product_ids = last_product_ids or []

            intent, product_hint = await self._detect_intent(user_query, last_product_ids)

            # ── Intent branch: email or purchase ───────────────────────────────
            action_response = await self._handle_action_intent(
                intent, product_hint, last_product_ids, user_info, conversation_id
            )
            if action_response:
                return action_response

            # ── Search workflow ────────────────────────────────────────────────
            return await self._handle_search_workflow(
                user_query, user_info, conversation_id
            )

        except Exception as e:
            logger.error("Workflow error: %s", e)
            return {
                "message": "I apologise, but I encountered an error. Please try again.",
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

        Args:
            action: The action to perform (EMAIL or PURCHASE)
            product_id: Product SKU
            user_info: User information (required, must be pre-fetched by caller)

        Returns:
            Action result dict with success status, message, and optional details
        """
        try:
            # Validate user info
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

            # Extract user info
            user_name = user_info.firstName if user_info.firstName else "there"
            user_email = str(user_info.email)

            # Execute action based on intent
            if action == IntentType.EMAIL:
                return await self._execute_email_action(user_name, user_email, product)

            elif action == IntentType.PURCHASE:
                return await self._execute_purchase_action(
                    user_name, user_email, product, product_id, user_info
                )

            else:
                return {
                    "success": False,
                    "message": f"Unknown action: {action}",
                    "error": "unknown_action"
                }

        except Exception as e:
            logger.error("Action error (%s): %s", action, e)
            return {
                "success": False,
                "message": "Failed to execute action. Please try again.",
                "error": str(e),
            }


# Global singleton — constructed at import time, SQR built lazily on first query
chatbot_service = ChatbotService()
