"""Product data models."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    """Base product model aligned with BestBuy Canada product structure."""

    sku: str = Field(..., description="Unique product SKU identifier")
    name: str = Field(..., min_length=1, max_length=500)
    shortDescription: str = Field(..., min_length=1)
    customerRating: Optional[float] = Field(None, ge=0, le=5, description="Customer rating out of 5")
    productUrl: str = Field(..., description="Full product URL including https://www.bestbuy.ca")
    regularPrice: float = Field(..., ge=0, description="Regular (non-sale) price in CAD")
    salePrice: float = Field(..., ge=0, description="Current sale or regular price in CAD")
    categoryName: str = Field(..., min_length=1, max_length=200)
    isOnSale: bool = Field(..., description="True if product currently has an active sale end date")
    highResImage: Optional[str] = Field(None, description="High resolution product image URL")


class Product(ProductBase):
    """Product model with search metadata."""

    relevance_score: Optional[float] = Field(
        None, ge=0, le=1, description="Similarity score from vector search"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "sku": "18470962",
                "name": "Apple AirPods 4 In-Ear True Wireless Earbuds with USB-C Charging Case",
                "shortDescription": "Apple AirPods 4 is rebuilt for exceptional comfort and audio performance.",
                "customerRating": 4.0,
                "productUrl": "https://www.bestbuy.ca/en-ca/product/apple-airpods-4/18470962",
                "regularPrice": 179.99,
                "salePrice": 149.99,
                "categoryName": "Wireless Earbuds & Earphones",
                "isOnSale": True,
                "highResImage": "https://multimedia.bbycastatic.ca/multimedia/products/1500x1500/184/18470/18470962.jpg",
                "relevance_score": 0.95,
            }
        }


class ProductDocument(BaseModel):
    """Product document for vector storage."""

    product_id: str
    text: str  # Combined searchable text: name + shortDescription
    metadata: dict[str, Any]

    @classmethod
    def from_product(cls, product: ProductBase) -> "ProductDocument":
        """Create a Pinecone document from a product."""
        # Searchable text is name + shortDescription
        text = f"{product.name} {product.shortDescription}"

        metadata = {
            "product_id": product.sku,
            "sku": product.sku,
            "name": product.name,
            "shortDescription": product.shortDescription,
            "customerRating": product.customerRating if product.customerRating is not None else 0.0,
            "productUrl": product.productUrl,
            "regularPrice": product.regularPrice,
            "salePrice": product.salePrice,
            "categoryName": product.categoryName,
            "isOnSale": product.isOnSale,
            "highResImage": product.highResImage or "",
        }

        return cls(product_id=product.sku, text=text, metadata=metadata)
