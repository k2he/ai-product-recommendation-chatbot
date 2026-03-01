"""Search products tool for the chatbot agent.

Returns formatted text followed by an embedded JSON block so that
``process_results_node`` can reconstruct the full ``Product`` list from the
``ToolMessage`` without issuing a second Pinecone query — even when the tool
is called multiple times in one turn (e.g. "show me monitors and wearables").
"""

import json
import logging
from typing import Callable

from langchain_core.tools import BaseTool, tool

logger = logging.getLogger(__name__)


def create_search_products_tool(run_sqr: Callable) -> BaseTool:
    """Create a search_products tool with injected SQR dependency.

    Args:
        run_sqr: Async function to run the SelfQueryingRetriever

    Returns:
        A LangGraph-compatible BaseTool
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
            Formatted list of matching products with names, prices, and ratings,
            followed by an embedded JSON block for structured processing.
        """
        try:
            logger.info("search_products tool called with query: %s", query)

            products = await run_sqr(query)

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

            human_text = f"Found {len(products)} products:\n\n" + "\n\n".join(lines)

            # Embed serialised Product list so process_results_node can
            # reconstruct Product objects for the API response without a
            # second Pinecone call.  The LLM ignores the JSON block.
            product_dicts = [p.model_dump() for p in products[:5]]
            json_block = f"\n```json\n{json.dumps(product_dicts)}\n```"

            logger.info("search_products returning %d products for query: %s", len(products), query)
            return human_text + json_block

        except Exception as e:
            logger.error("search_products tool failed: %s", e)
            return f"Search failed: {str(e)}. Please try again."

    return search_products
