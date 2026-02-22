"""API routes for the chatbot."""

import logging
import uuid

from fastapi import APIRouter, Header, HTTPException, status

from app.config import get_settings
from app.database.mongodb import mongodb
from app.database.pinecone_db import pinecone_db
from app.models.request import (
    ActionRequest,
    ActionResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
)
from app.services.chatbot_service import chatbot_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix=settings.api_prefix)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        mongodb_status = "connected" if mongodb.db else "disconnected"
        pinecone_status = "connected" if pinecone_db.client else "disconnected"

        return HealthResponse(
            status="healthy" if all([
                mongodb_status == "connected",
                pinecone_status == "connected",
            ]) else "degraded",
            version=settings.app_version,
            services={
                "mongodb": mongodb_status,
                "pinecone": pinecone_status,
                "ollama": "configured" if settings.ollama_base_url else "not_configured",
            },
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy",
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Header(..., alias="X-User-ID"),
) -> ChatResponse:
    """Main chat endpoint for product recommendations.

    The workflow has three phases:
    1. Intent detection — LLM determines if the user wants to search, email, or purchase.
    2. If 'email'/'purchase' and last_product_ids are provided, executes the action directly.
    3. Otherwise, runs SelfQueryingRetriever to search Pinecone with auto-extracted filters.

    Headers:
        X-User-ID: User identifier

    Body:
        query: User's product search query
        conversation_id: Optional conversation ID
        last_product_ids: SKUs from the most recent assistant response (for action detection)
    """
    try:
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}",
            )

        conversation_id = request.conversation_id or str(uuid.uuid4())

        result = await chatbot_service.process_chat_interaction(
            user_query=request.query,
            user_id=user_id,
            conversation_id=conversation_id,
            last_product_ids=request.last_product_ids,
        )

        if result.get("error"):
            logger.warning("Workflow error: %s", result["error"])

        return ChatResponse(
            message=result["message"],
            products=result["products"],
            conversation_id=result["conversation_id"],
            has_results=result["has_results"],
            source=result["source"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat request",
        )


@router.post("/actions", response_model=ActionResponse)
async def execute_action(
    request: ActionRequest,
    user_id: str = Header(..., alias="X-User-ID"),
) -> ActionResponse:
    """Execute a user action (purchase or email) on a specific product.

    This endpoint is triggered by the UI's action buttons on product cards.
    For free-text action intents ("email me that"), the /chat endpoint
    handles them automatically via intent detection.

    Headers:
        X-User-ID: User identifier

    Body:
        action: 'purchase' or 'email'
        product_id: Product SKU
        conversation_id: Optional conversation ID
    """
    try:
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}",
            )

        result = await chatbot_service.execute_action(
            action=request.action,
            product_id=request.product_id,
            user_id=user_id,
        )

        if not result["success"]:
            logger.warning("Action failed: %s", result.get("error", "Unknown error"))

        return ActionResponse(
            success=result["success"],
            message=result["message"],
            action=request.action,
            product_id=request.product_id,
            details=result.get("details"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Action error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute action",
        )
