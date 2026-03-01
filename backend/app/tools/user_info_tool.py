"""User information tool for the chatbot agent.

Retrieves a fresh UserInDB from UserService.get_user() at call time
so the tool always reflects the latest data in MongoDB.
"""

import json
import logging

from langchain_core.tools import BaseTool, tool

from app.models.user import UserInDB
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


def create_user_info_tool(user_id: str) -> BaseTool:
    """Create a get_user_info tool that fetches live data from UserService.

    Args:
        user_id: The ID of the current user (injected at request time).

    Returns:
        A LangGraph-compatible BaseTool whose return value is a JSON-serialised
        UserInDB so that process_results_node can reconstruct the object from
        the ToolMessage without an extra MongoDB call.
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
            Formatted user account information with an embedded JSON block
            containing the full UserInDB data for structured rendering.
        """
        try:
            logger.info("get_user_info tool called for user_id: %s", user_id)

            user: UserInDB | None = await UserService.get_user(user_id)
            if not user:
                return f"No account found for user ID '{user_id}'."

            # Human-readable text for the LLM to build its response
            human_text = (
                f"User Account Information:\n"
                f"Name: {user.firstName} {user.lastName}\n"
                f"Email: {user.email}\n"
                f"Phone: {user.phone}"
            )

            # Embedded JSON block for process_results_node to reconstruct
            # the UserInDB without a second MongoDB call.
            json_block = f"\n```json\n{user.model_dump_json()}\n```"

            return human_text + json_block

        except Exception as e:
            logger.error("get_user_info tool failed: %s", e)
            return f"Failed to retrieve account information: {str(e)}"

    return get_user_info
