"""User information tool for the chatbot agent."""

import logging
from typing import Callable

from langchain_core.tools import tool

from app.models.state import AgentState
from app.models.user import UserInDB

logger = logging.getLogger(__name__)


def create_user_info_tool(
    state: AgentState,
    user_info: UserInDB,
) -> Callable:
    """Create a get_user_info tool with injected dependencies.

    Args:
        state: Shared AgentState to store user info for API response
        user_info: Current user's information

    Returns:
        A LangChain tool function
    """

    @tool
    async def get_user_info() -> str:
        """Get the current user's account information including name, email, and phone.

        Use this tool when the user asks for:
        - Account details or account information
        - Profile information
        - Personal information
        - Contact details
        - "What's my email?" or "What's my phone number?"

        Returns:
            Formatted user account information
        """
        try:
            logger.info("get_user_info tool called for user: %s", user_info.userId)

            # Store user info in shared state for API response
            state.user_info = user_info
            state.source = "user_info"
            state.has_results = True

            # Format for LLM to use in response
            return (
                f"User Account Information:\n"
                f"Name: {user_info.firstName} {user_info.lastName}\n"
                f"Email: {user_info.email}\n"
                f"Phone: {user_info.phone}"
            )

        except Exception as e:
            logger.error("get_user_info tool failed: %s", e)
            return f"Failed to retrieve account information: {str(e)}"

    return get_user_info

