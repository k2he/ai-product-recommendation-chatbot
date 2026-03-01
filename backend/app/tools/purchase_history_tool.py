"""Purchase history tool for the chatbot agent.

No longer mutates external AgentState — returns text only.
"""

import logging
from typing import Callable

from langchain_core.tools import BaseTool, tool

from app.database.mongodb import mongodb

logger = logging.getLogger(__name__)


def create_purchase_history_tool(user_id: str) -> BaseTool:
    """Create a get_purchase_history tool with injected dependencies.

    Args:
        user_id: Current user's ID

    Returns:
        A LangChain tool function
    """

    @tool
    async def get_purchase_history() -> str:
        """Get the user's past purchase and order history.

        Use this tool when the user asks to see:
        - Purchase history
        - Past orders
        - Previous purchases
        - Order history
        - "What have I bought before?"
        - "Show me my orders"

        Returns:
            Formatted list of past orders with summary information
        """
        try:
            logger.info("get_purchase_history tool called for user: %s", user_id)

            # Query MongoDB for user's orders
            orders = await mongodb.get_user_orders(user_id)

            if not orders:
                return "You don't have any purchase history yet."

            # Format summary for LLM to use in response
            summary_lines = [f"I found {len(orders)} order(s) in your purchase history:\n"]

            for idx, order in enumerate(orders[:5], 1):  # Show first 5 orders
                order_date = order.orderDate.strftime("%B %d, %Y")
                item_count = len(order.lineItems)
                item_word = "item" if item_count == 1 else "items"

                summary_lines.append(
                    f"{idx}. Order #{order.orderNumber} on {order_date}: "
                    f"{item_count} {item_word}, ${order.totalPrice:.2f}"
                )

            if len(orders) > 5:
                summary_lines.append(f"\n...and {len(orders) - 5} more order(s)")

            return "\n".join(summary_lines)

        except Exception as e:
            logger.error("get_purchase_history tool failed: %s", e)
            return f"Failed to retrieve purchase history: {str(e)}"

    return get_purchase_history
