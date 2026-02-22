"""Tavily web search service."""

import logging
from typing import Optional

from tavily import TavilyClient
from langchain_core.tools import tool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TavilyService:
    """Service for web search using Tavily API."""

    def __init__(self) -> None:
        """Initialize Tavily search client."""
        try:
            if settings.tavily_api_key:
                self.client = TavilyClient(api_key=settings.tavily_api_key)
                logger.info("Tavily service initialized successfully")
            else:
                self.client = None
                logger.warning("Tavily API key not provided - web search disabled")
        except Exception as e:
            logger.error("Failed to initialize Tavily service: %s", e)
            self.client = None

    def is_available(self) -> bool:
        """Check if Tavily service is available."""
        return self.client is not None

    async def search(self, query: str, max_results: Optional[int] = None) -> list[dict]:
        """Execute web search using Tavily.

        Args:
            query: Search query string
            max_results: Optional override for max results

        Returns:
            List of search result dicts with title, content, url
        """
        if not self.client:
            logger.warning("Tavily search called but service not available")
            return []

        try:
            logger.info("Executing Tavily search for: %s", query)

            # Use TavilyClient's search method
            response = self.client.search(
                query=query,
                max_results=max_results or settings.tavily_max_results,
                search_depth=settings.tavily_search_depth,
            )

            # Extract results from response
            results = response.get("results", [])
            logger.info("Tavily returned %d results", len(results))
            return results
        except Exception as e:
            logger.error("Tavily search failed: %s", e)
            return []


# Global service instance
tavily_service = TavilyService()


# ── LangChain Tool Definition ──────────────────────────────────────────────

@tool
def search_web(query: str) -> str:
    """Search the web for current information about weather, news, sports, time, or other factual questions.

    Use this tool when you need up-to-date information that you don't have in your training data.

    Args:
        query: The search query to look up

    Returns:
        Search results as JSON string with title, content, and url for each result
    """
    if not tavily_service.is_available():
        return "Web search is currently unavailable."

    try:
        response = tavily_service.client.search(
            query=query,
            max_results=settings.tavily_max_results,
            search_depth=settings.tavily_search_depth,
        )

        results = response.get("results", [])

        if not results:
            return "No results found for your query."

        # # Return only first 3 results
        return str(results[:3])

    except Exception as e:
        logger.error("Search tool failed: %s", e)
        return f"Search failed: {str(e)}"

