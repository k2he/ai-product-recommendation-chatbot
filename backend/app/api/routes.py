"""API routes for the chatbot."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

from app.config import get_settings
from app.database.mongodb import mongodb
from app.database.pinecone_db import pinecone_db
from app.models.request import (
    ActionRequest,
    ActionResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
)
from app.models.user import UserCreate, UserResponse
from app.services.chatbot_service import chatbot_service
from app.services.user_service import user_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Create router
router = APIRouter(prefix=settings.api_prefix)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        # Check MongoDB
        mongodb_status = "connected" if mongodb.db else "disconnected"

        # Check Pinecone
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
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy",
        )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate) -> UserResponse:
    """Create a new user."""
    try:
        created_user = await user_service.create_user(user)
        return UserResponse(**created_user.model_dump())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """Get user by ID."""
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {user_id}",
        )
    return UserResponse(**user.model_dump())


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Header(..., alias="X-User-ID"),
) -> ChatResponse:
    """
    Main chat endpoint for product recommendations.

    Headers:
        X-User-ID: User identifier

    Body:
        query: User's product search query
        conversation_id: Optional conversation ID
    """
    try:
        # Validate user exists
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}",
            )

        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Execute chatbot workflow using LangChain
        result = await chatbot_service.execute_query(
            user_query=request.query,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        # Handle errors from workflow
        if result.get("error"):
            logger.warning(f"Workflow error: {result['error']}")

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
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat request",
        )


@router.post("/actions", response_model=ActionResponse)
async def execute_action(
    request: ActionRequest,
    user_id: str = Header(..., alias="X-User-ID"),
) -> ActionResponse:
    """
    Execute user action (purchase or email).

    Headers:
        X-User-ID: User identifier

    Body:
        action: Action type ('purchase' or 'email')
        product_id: Product identifier
        conversation_id: Optional conversation ID
    """
    try:
        # Validate user exists
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}",
            )

        # Execute action using LangChain service
        result = await chatbot_service.execute_action(
            action=request.action,
            product_id=request.product_id,
            user_id=user_id,
        )

        if not result["success"]:
            logger.warning(f"Action failed: {result.get('error', 'Unknown error')}")

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
        logger.error(f"Action error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute action",
        )
