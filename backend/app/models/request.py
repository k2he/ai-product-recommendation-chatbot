"""API request and response models."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.product import Product


class IntentType(str, Enum):
    """Valid intent types for intent classification."""

    SEARCH = "search"
    EMAIL = "email"
    PURCHASE = "purchase"
    GENERAL_CHAT = "general_chat"


class IntentResponse(BaseModel):
    """Structured output model for intent classification."""

    intent: IntentType = Field(
        description="The classified intent: 'search', 'email', 'purchase', or 'general_chat'"
    )
    product_hint: Optional[str] = Field(
        default=None,
        description="The product name mentioned by the user, or null if none"
    )


class ChatRequest(BaseModel):
    """Chat request model."""

    query: str = Field(..., min_length=1, max_length=1000, description="User's product query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    last_product_ids: list[str] = Field(
        default_factory=list,
        description="SKUs of products shown in the most recent assistant response. "
                    "Used for intent detection (email/purchase) without repeating search.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "I need wireless headphones with good battery life",
                "conversation_id": "conv_123",
                "last_product_ids": [],
            }
        }
    }


class ActionRequest(BaseModel):
    """Action request model for tool execution."""

    action: IntentType
    product_id: str = Field(..., description="Product SKU for the action")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "action": "email",
                "product_id": "18470962",
                "conversation_id": "conv_123",
            }
        }
    }


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str = Field(..., description="Assistant's response message")
    products: list[Product] = Field(default_factory=list, description="Recommended products")
    conversation_id: str = Field(..., description="Conversation identifier")
    has_results: bool = Field(..., description="Whether products were found")
    source: str = Field(
        ...,
        description="Source of results: 'vector_db' (products from database), 'action' (email/purchase), 'general_chat' (conversation), 'general_chat_with_search' (conversation with search tool), 'user_info' (account details), 'purchase_history' (past orders), or 'none' (no results)",
    )
    user_info: Optional[dict[str, Any]] = Field(
        default=None,
        description="User account information when displaying account details"
    )
    purchase_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="User's purchase history when displaying past orders"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "I found 3 wireless headphones that match your requirements...",
                "products": [
                    {
                        "sku": "18470962",
                        "name": "Apple AirPods 4",
                        "shortDescription": "Exceptional comfort and audio performance.",
                        "customerRating": 4.0,
                        "productUrl": "https://www.bestbuy.ca/en-ca/product/18470962",
                        "regularPrice": 179.99,
                        "salePrice": 149.99,
                        "categoryName": "Wireless Earbuds & Earphones",
                        "isOnSale": True,
                        "relevance_score": 0.92,
                    }
                ],
                "conversation_id": "conv_123",
                "has_results": True,
                "source": "vector_db",
            }
        }
    }


class ActionResponse(BaseModel):
    """Action response model."""

    success: bool = Field(..., description="Whether the action succeeded")
    message: str = Field(..., description="Result message")
    action: IntentType = Field(..., description="Action that was executed")
    product_id: str = Field(..., description="Product SKU that was acted on")
    details: Optional[dict[str, Any]] = Field(None, description="Additional action details")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Product details sent to user@example.com",
                "action": "email",
                "product_id": "18470962",
                "details": {"email": "user@example.com"},
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    services: dict[str, str]
