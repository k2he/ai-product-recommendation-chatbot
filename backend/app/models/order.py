"""Order and purchase history data models."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """Line item in an order."""

    name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Product SKU")
    quantity: int = Field(..., ge=1, description="Quantity ordered")
    total: float = Field(..., ge=0, description="Total price for this line item")
    imgUrl: str = Field(..., description="Product image URL")


class OrderInDB(BaseModel):
    """Order model as stored in database."""

    userId: str = Field(..., description="User who placed the order")
    orderNumber: str = Field(..., description="Order number")
    orderDate: datetime = Field(..., description="Order date and time")
    totalPrice: float = Field(..., ge=0, description="Total order price")
    status: str = Field(..., description="Order status")
    lineItems: list[LineItem] = Field(..., description="Items in the order")
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "json_schema_extra": {
            "example": {
                "userId": "user_001",
                "orderNumber": "1019026365",
                "orderDate": "2024-09-06T03:28:26Z",
                "totalPrice": 282.47,
                "status": "InProcess",
                "lineItems": [
                    {
                        "name": "Logitech Pebble 2 M350s Mouse",
                        "sku": "17242194",
                        "quantity": 1,
                        "total": 29.99,
                        "imgUrl": "https://example.com/image.jpg",
                    }
                ],
                "createdAt": "2024-02-22T00:00:00Z",
                "updatedAt": "2024-02-22T00:00:00Z",
            }
        }
    }


