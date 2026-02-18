"""API request and response models."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.product import Product


class ActionType(str, Enum):
    """Available user actions."""

    PURCHASE = "purchase"
    EMAIL = "email"
    NONE = "none"


class ChatRequest(BaseModel):
    """Chat request model."""

    query: str = Field(..., min_length=1, max_length=1000, description="User's product query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "query": "I need wireless headphones with good battery life",
                "conversation_id": "conv_123",
            }
        }


class ActionRequest(BaseModel):
    """Action request model for tool execution."""

    action: ActionType
    product_id: str = Field(..., description="Product ID for the action")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "action": "email",
                "product_id": "prod123",
                "conversation_id": "conv_123",
            }
        }


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str = Field(..., description="Assistant's response message")
    products: list[Product] = Field(default_factory=list, description="Recommended products")
    conversation_id: str = Field(..., description="Conversation identifier")
    has_results: bool = Field(..., description="Whether products were found")
    source: str = Field(
        ..., description="Source of results: 'vector_db', 'web_search', or 'none'"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "message": "I found 3 wireless headphones that match your requirements...",
                "products": [
                    {
                        "product_id": "prod123",
                        "name": "Wireless Headphones Pro",
                        "description": "Premium wireless headphones",
                        "category": "Electronics",
                        "price": 149.99,
                        "specifications": {"battery_life": "40 hours"},
                        "image_url": "https://example.com/image.jpg",
                        "stock": 25,
                        "tags": ["wireless", "bluetooth"],
                        "relevance_score": 0.92,
                    }
                ],
                "conversation_id": "conv_123",
                "has_results": True,
                "source": "vector_db",
            }
        }


class ActionResponse(BaseModel):
    """Action response model."""

    success: bool = Field(..., description="Whether action was successful")
    message: str = Field(..., description="Action result message")
    action: ActionType = Field(..., description="Action that was performed")
    product_id: str = Field(..., description="Product ID")
    details: Optional[dict[str, Any]] = Field(None, description="Additional action details")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Product details have been sent to your email",
                "action": "email",
                "product_id": "prod123",
                "details": {"email": "user@example.com", "sent_at": "2024-01-01T12:00:00"},
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    message: str
    details: Optional[dict[str, Any]] = None
