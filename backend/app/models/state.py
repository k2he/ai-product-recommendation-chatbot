"""Agent state model for chatbot execution."""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.product import Product


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
        description="Source of results: 'vector_db' (products from database), 'action' (email/purchase), 'general_chat' (conversation), 'general_chat_with_search' (conversation with search tool), or 'none' (no results)"
    )
    has_results: bool = Field(
        default=False,
        description="Whether the search produced any results"
    )

    model_config = {
        # Allow mutation so tools can update fields
        "validate_assignment": True,
        "arbitrary_types_allowed": True,
    }

