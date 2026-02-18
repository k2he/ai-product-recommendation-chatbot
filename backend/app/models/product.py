"""Product data models."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    """Base product model."""

    product_id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0, description="Product price in USD")
    specifications: dict[str, Any] = Field(default_factory=dict)
    image_url: Optional[str] = None
    stock: int = Field(default=0, ge=0, description="Available stock quantity")
    tags: list[str] = Field(default_factory=list)


class Product(ProductBase):
    """Product model with metadata."""

    relevance_score: Optional[float] = Field(
        None, ge=0, le=1, description="Similarity score from vector search"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "product_id": "prod123",
                "name": "Wireless Bluetooth Headphones",
                "description": "High-quality wireless headphones with noise cancellation",
                "category": "Electronics",
                "price": 99.99,
                "specifications": {
                    "color": "Black",
                    "battery_life": "30 hours",
                    "connectivity": "Bluetooth 5.0",
                },
                "image_url": "https://example.com/headphones.jpg",
                "stock": 50,
                "tags": ["bluetooth", "wireless", "noise-cancellation", "audio"],
                "relevance_score": 0.95,
            }
        }


class ProductDocument(BaseModel):
    """Product document for vector storage."""

    product_id: str
    text: str  # Combined searchable text
    metadata: dict[str, Any]

    @classmethod
    def from_product(cls, product: ProductBase) -> "ProductDocument":
        """Create document from product."""
        # Combine searchable fields
        text = f"{product.name}: {product.description}"

        metadata = {
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "price": product.price,
            "stock": product.stock,
            "image_url": product.image_url,
        }

        return cls(product_id=product.product_id, text=text, metadata=metadata)
