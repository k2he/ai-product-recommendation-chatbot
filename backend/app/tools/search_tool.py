"""Search products tool for the chatbot agent."""

import logging
from typing import Callable

from langchain_core.tools import tool

from app.models.state import AgentState

logger = logging.getLogger(__name__)


def create_search_products_tool(
    run_sqr: Callable,
    state: AgentState,
) -> Callable:
    """Create a search_products tool with injected dependencies.

    Args:
        run_sqr: Async function to run the SelfQueryingRetriever
        state: Shared AgentState to store products for API response

    Returns:
        A LangChain tool function
    """

    @tool
    async def search_products(query: str) -> str:
        """Search the product catalog for items matching the user's request.

        Use this tool when the user is looking for products, asking about
        product availability, comparing items, or requesting recommendations.

        Examples of when to use this tool:
        - "show me laptops under $1000"
        - "do you have wireless headphones?"
        - "I need a gaming monitor"
        - "what TVs do you recommend?"

        Args:
            query: Natural language search query describing what the user wants

        Returns:
            Formatted list of matching products with names, prices, and ratings
        """
        try:
            logger.info("search_products tool called with query: %s", query)

            # Run the SelfQueryingRetriever
            products = await run_sqr(query)

            # Append products to shared state for API response (accumulate across multiple searches)
            state.products.extend(products)
            state.source = "vector_db" if products else "none"
            state.has_results = bool(products)

            if not products:
                return "No products found matching your search. Try different keywords or browse our categories."

            # Format products for LLM to use in response
            lines = []
            for i, p in enumerate(products[:5], 1):
                sale_tag = " 🏷️ ON SALE" if p.isOnSale else ""
                rating = f" | ⭐ {p.customerRating}/5" if p.customerRating else ""
                lines.append(
                    f"{i}. **{p.name}** (SKU: {p.sku}){sale_tag}{rating}\n"
                    f"   Price: ${p.salePrice:.2f} CAD"
                    + (f" (was ${p.regularPrice:.2f})" if p.isOnSale else "")
                    + f"\n   Category: {p.categoryName}\n"
                    f"   {p.shortDescription[:150]}..."
                )

            result = f"Found {len(products)} products:\n\n" + "\n\n".join(lines)
            logger.info("search_products returning %d products", len(products))
            return result

        except Exception as e:
            logger.error("search_products tool failed: %s", e)
            state.products = []
            state.source = "none"
            state.has_results = False
            return f"Search failed: {str(e)}. Please try again."

    return search_products
