"""Purchase history tool for the chatbot agent.

Retrieves orders from MongoDB at call time and embeds a JSON block so
process_results_node can reconstruct the full OrderInDB list for the UI
without a second database call.
"""

import json
import logging

from langchain_core.tools import BaseTool, tool

from app.database.mongodb import mongodb

logger = logging.getLogger(__name__)


def create_purchase_history_tool(user_id: str) -> BaseTool:
    """Create a get_purchase_history tool with injected user_id.

    Args:
        user_id: Current user's ID (injected at request time).

    Returns:
        A LangGraph-compatible BaseTool whose return value contains a
        JSON block of serialised OrderInDB objects so that
        process_results_node can render them as structured UI cards.
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
            Formatted order summary with an embedded JSON block containing
            the full order list for structured UI rendering.
        """
        try:
            logger.info("get_purchase_history tool called for user: %s", user_id)

            orders = await mongodb.get_user_orders(user_id)

            if not orders:
                return "You don't have any purchase history yet."

            # Human-readable summary for the LLM to build its response
            summary_lines = [f"Found {len(orders)} order(s) in your purchase history:\n"]
            for idx, order in enumerate(orders[:5], 1):
                order_date = order.orderDate.strftime("%B %d, %Y")
                item_count = len(order.lineItems)
                item_word = "item" if item_count == 1 else "items"
                summary_lines.append(
                    f"{idx}. Order #{order.orderNumber} on {order_date}: "
                    f"{item_count} {item_word}, ${order.totalPrice:.2f}"
                )
            if len(orders) > 5:
                summary_lines.append(f"\n...and {len(orders) - 5} more order(s)")

            human_text = "\n".join(summary_lines)

            # Embedded JSON block so process_results_node can reconstruct
            # OrderInDB objects for the UI without a second MongoDB call.
            orders_data = [
                json.loads(order.model_dump_json()) for order in orders
            ]
            json_block = f"\n```json\n{json.dumps(orders_data)}\n```"

            logger.info("get_purchase_history returning %d orders", len(orders))
            return human_text + json_block

        except Exception as e:
            logger.error("get_purchase_history tool failed: %s", e)
            return f"Failed to retrieve purchase history: {str(e)}"

    return get_purchase_history
