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
from app.models.order import OrderInDB, LineItem
from app.models.state import AgentState

# Rebuild AgentState after all forward-referenced models are imported
# This resolves the Pydantic forward reference issue
AgentState.model_rebuild()

__all__ = [
    # User models
    "UserInDB",
    # Product models
    "Product",
    "ProductBase",
    "ProductDocument",
    # Agent state model
    "AgentState",
    # Order models
    "OrderInDB",
    "LineItem",
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
