"""Agent state model for chatbot execution."""

from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

from app.models.product import Product

if TYPE_CHECKING:
    from app.models.user import UserInDB
    from app.models.order import OrderInDB


class AgentState(BaseModel):
    """Type-safe state container for agent tool execution.

    This state is populated by tools during agent execution and used
    to construct the API response with structured data (products, metadata).
    """

    products: list[Product] = Field(
        default_factory=list,
        description="Products found by search_products tool or affected by actions"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of results: 'vector_db', 'action', 'general_chat', 'general_chat_with_search', 'user_info', 'purchase_history', or 'none'"
    )
    has_results: bool = Field(
        default=False,
        description="Whether the search produced any results"
    )
    user_info: Optional["UserInDB"] = Field(
        default=None,
        description="User information when displaying account details"
    )
    purchase_history: list["OrderInDB"] = Field(
        default_factory=list,
        description="User's purchase history when displaying past orders"
    )

    model_config = {
        # Allow mutation so tools can update fields
        "validate_assignment": True,
        "arbitrary_types_allowed": True,
    }

