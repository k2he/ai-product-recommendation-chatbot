"""Email product tool for the chatbot agent."""

import logging
from typing import Any, Callable, Optional

from langchain_core.tools import tool

from app.models.product import Product
from app.models.state import AgentState

logger = logging.getLogger(__name__)


def create_email_tool(
    email_service: Any,
    get_product_by_id: Callable,
    state: AgentState,
    user_name: str,
    user_email: str,
) -> Callable:
    """Create a send_product_email tool with injected dependencies.

    Args:
        email_service: Email service instance for sending emails
        get_product_by_id: Async function to fetch product by SKU
        state: Shared AgentState for tracking action results
        user_name: User's first name for personalization
        user_email: User's email address to send to

    Returns:
        A LangChain tool function
    """

    @tool
    async def send_product_email(product_id: str) -> str:
        """Send product details to the user's email address.

        Use this tool when the user wants product information emailed to them.
        The user's email address is already known from their profile.

        Examples of when to use this tool:
        - "email me that laptop"
        - "send the product details to my email"
        - "can you email me info about the Sony headphones?"

        Args:
            product_id: SKU of the product to email (use SKU from search results)

        Returns:
            Confirmation message indicating email was sent
        """
        try:
            logger.info("send_product_email tool called for product: %s", product_id)

            # Fetch the product
            product: Optional[Product] = await get_product_by_id(product_id)
            if not product:
                return f"Product with SKU '{product_id}' not found. Please check the product ID and try again."

            # Send the email
            await email_service.send_product_email(
                recipient_email=user_email,
                recipient_name=user_name,
                product=product,
            )

            # Update state for API response (source indicates an action was taken)
            state.source = "action"

            logger.info("Email sent successfully for product %s to %s", product_id, user_email)
            return (
                f"Done! I've sent the details for **{product.name}** to {user_email}. "
                f"Check your inbox! 📧"
            )

        except Exception as e:
            logger.error("send_product_email tool failed: %s", e)
            return f"Failed to send email: {str(e)}. Please try again."

    return send_product_email

