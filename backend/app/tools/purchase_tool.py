"""Purchase product tool for the chatbot agent.

No longer mutates external state — returns a text result.
The inconsistent dict-based state access (state["source"]) is removed.
"""

import logging
from typing import Callable, Optional

from langchain_core.tools import BaseTool, tool

from app.models.product import Product

logger = logging.getLogger(__name__)


def create_purchase_tool(
    get_product_by_id: Callable,
    user_name: str,
    user_email: str,
    user_id: str,
) -> BaseTool:
    """Create a purchase_product tool with injected dependencies.

    Args:
        get_product_by_id: Async function to fetch product by SKU
        user_name: User's first name for personalization
        user_email: User's email address for confirmation
        user_id: User's ID for generating order ID

    Returns:
        A LangChain tool function
    """

    @tool
    async def purchase_product(product_id: str) -> str:
        """Place an order for a product.

        Use this tool when the user wants to buy, order, or purchase a specific product.

        Examples of when to use this tool:
        - "I'll take it"
        - "buy the Sony headphones"
        - "order that laptop"
        - "I want to purchase this"

        Args:
            product_id: SKU of the product to purchase (use SKU from search results)

        Returns:
            Order confirmation with order ID and total
        """
        try:
            logger.info("purchase_product tool called for product: %s", product_id)

            # Fetch the product
            product: Optional[Product] = await get_product_by_id(product_id)
            if not product:
                return f"Product with SKU '{product_id}' not found. Please check the product ID and try again."

            # Generate order ID
            order_id = f"ORD-{product_id}-{user_id[-4:]}"

            logger.info("Purchase completed for product %s, order ID: %s", product_id, order_id)
            return (
                f"Great choice! Your order for **{product.name}** has been placed. "
                f"Order ID: `{order_id}`. "
                f"Total: ${product.salePrice:.2f} CAD. "
                f"A confirmation will be sent to {user_email}. 🛒"
            )

        except Exception as e:
            logger.error("purchase_product tool failed: %s", e)
            return f"Failed to place order: {str(e)}. Please try again."

    return purchase_product
