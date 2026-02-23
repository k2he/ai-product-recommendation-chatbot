"""Web search tool for the chatbot agent (Tavily integration)."""

import logging

from langchain_core.tools import tool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Import tavily_service to check availability and use the client
# Note: This is a lazy import pattern - the actual service is initialized elsewhere
_tavily_service = None


def _get_tavily_service():
    """Lazy load tavily service to avoid circular imports."""
    global _tavily_service
    if _tavily_service is None:
        from app.services.tavily_service import tavily_service
        _tavily_service = tavily_service
    return _tavily_service


@tool
def search_web(query: str) -> str:
    """Search the web for current information about weather, news, sports, time, or other factual questions.

    Use this tool when you need up-to-date information that isn't about products in the catalog.
    Do NOT use this tool for product searches - use search_products instead.

    Examples of when to use this tool:
    - "what's the weather in Toronto?"
    - "who won the Super Bowl?"
    - "latest tech news"
    - "what time is it in Tokyo?"

    Args:
        query: The search query to look up

    Returns:
        Search results with relevant information
    """
    tavily = _get_tavily_service()

    if not tavily.is_available():
        return "Web search is currently unavailable. I can only help with product-related questions right now."

    try:
        logger.info("search_web tool called with query: %s", query)

        response = tavily.client.search(
            query=query,
            max_results=settings.tavily_max_results,
            search_depth=settings.tavily_search_depth,
        )

        results = response.get("results", [])

        if not results:
            return "No results found for your query."

        # Format top 3 results for the LLM
        formatted = []
        for r in results[:3]:
            title = r.get("title", "")
            content = r.get("content", "")[:300]
            url = r.get("url", "")
            formatted.append(f"**{title}**\n{content}\nSource: {url}")

        logger.info("search_web returning %d results", len(formatted))
        return "\n\n".join(formatted)

    except Exception as e:
        logger.error("search_web tool failed: %s", e)
        return f"Search failed: {str(e)}"


def is_web_search_available() -> bool:
    """Check if web search tool is available."""
    return _get_tavily_service().is_available()

