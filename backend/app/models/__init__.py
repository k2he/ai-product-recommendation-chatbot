"""Data models package."""

from app.models.product import Product, ProductBase, ProductDocument
from app.models.request import (
    ActionRequest,
    ActionResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    IntentResponse,
    IntentType,
)
from app.models.user import UserInDB

__all__ = [
    # User models
    "UserInDB",
    # Product models
    "Product",
    "ProductBase",
    "ProductDocument",
    # Request/Response models
    "ChatRequest",
    "ChatResponse",
    "ActionRequest",
    "ActionResponse",
    "IntentType",
    "IntentResponse",
    "HealthResponse",
    "ErrorResponse",
]
