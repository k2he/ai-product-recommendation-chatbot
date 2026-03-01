"""LangGraph agent tools for the chatbot workflow.

This module exports tools that the chatbot agent can invoke:
- search_products: Search the product catalog via SelfQueryingRetriever
- send_product_email: Email product details to the user
- purchase_product: Place an order for a product
- search_web: Search the web for factual information (via Tavily)
- get_user_info: Display user account information
- get_purchase_history: Display user's past orders
"""

from app.tools.search_tool import create_search_products_tool
from app.tools.email_tool import create_email_tool
from app.tools.purchase_tool import create_purchase_tool
from app.tools.web_search_tool import search_web, is_web_search_available
from app.tools.user_info_tool import create_user_info_tool
from app.tools.purchase_history_tool import create_purchase_history_tool

__all__ = [
    "create_search_products_tool",
    "create_email_tool",
    "create_purchase_tool",
    "search_web",
    "is_web_search_available",
    "create_user_info_tool",
    "create_purchase_history_tool",
]

