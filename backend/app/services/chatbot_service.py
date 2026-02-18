"""LangChain-based chatbot workflow."""

import logging
from typing import Any, Optional

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from langchain_community.tools.tavily_search import TavilySearchResults

from app.config import get_settings
from app.database.mongodb import mongodb
from app.database.pinecone_db import pinecone_db
from app.models.product import Product
from app.models.request import ActionType
from app.models.user import UserInDB
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatbotService:
    """LangChain-based chatbot service."""

    def __init__(self) -> None:
        """Initialize the chatbot service."""
        # Initialize LLM
        self.llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
        )

        # Initialize Tavily search
        try:
            if settings.tavily_api_key:
                self.tavily = TavilySearchResults(
                    max_results=settings.tavily_max_results,
                    search_depth=settings.tavily_search_depth,
                )
            else:
                self.tavily = None
        except Exception as e:
            logger.warning(f"Failed to initialize Tavily: {e}")
            self.tavily = None

        # Build chains
        self._build_chains()

    def _build_chains(self) -> None:
        """Build LangChain chains for the workflow."""
        
        # Chain 1: Query Rephrasing
        rephrase_prompt = PromptTemplate.from_template(
            """You are a search query optimizer. Rephrase the user's natural language query 
                into a concise, keyword-rich search query optimized for semantic search in a product database.
                
                Focus on:
                - Product features, specifications, and categories
                - Key attributes the user is looking for
                - Remove conversational filler words
                
                User Query: {query}
                
                Rephrased Query (output only the rephrased query, nothing else):"""
        )

        self.rephrase_chain = rephrase_prompt | self.llm | StrOutputParser()

        # Chain 2: Response Generation
        response_prompt = PromptTemplate.from_template("""You are a helpful product recommendation assistant.
                    
                    User: {user_name}
                    Products Found: {has_results}
                    Source: {source}
                    
                    {products}
                    
                    Generate a friendly, helpful response recommending the products or explaining what was found.
                    If products were found, briefly describe them and ask if the user would like to purchase or receive details via email.
                    If no products were found, politely explain and suggest the user provide more details.
                    
                    Response:"""
        )
        self.response_chain = response_prompt | self.llm | StrOutputParser()


    async def execute_query(
        self, user_query: str, user_id: str, conversation_id: str
    ) -> dict[str, Any]:
        """
        Execute the chatbot workflow using LangChain.
        
        Workflow:
        1. Rephrase query using LLM
        2. Retrieve user information from MongoDB
        3. Search products in Pinecone
        4. Fallback to web search if no results
        5. Generate response using LLM
        """
        try:
            logger.info(f"Starting workflow for query: '{user_query}'")

            # Step 1: Rephrase query
            logger.info("Step 1: Rephrasing user query")
            rephrase_result = await self.rephrase_chain.ainvoke({"query": user_query})
            rephrased_query = rephrase_result.strip()
            logger.info(f"Query rephrased: '{user_query}' -> '{rephrased_query}'")

            # Step 2: Retrieve user information
            logger.info(f"Step 2: Retrieving user info for user_id: {user_id}")
            user_info = await self._get_user_info(user_id)
            user_name = user_info.firstName if user_info else "No Name"

            # Step 3: Vector search
            logger.info("Step 3: Searching vector database")
            products = await self._search_products(rephrased_query)
            search_source = "vector_db" if products else "none"

            # Step 4: Web search fallback
            if not products and self.tavily:
                web_results = await self._web_search(rephrased_query)
                if web_results:
                    return {
                        "message": await self._generate_web_response(user_name, web_results),
                        "products": [],
                        "conversation_id": conversation_id,
                        "has_results": True,
                        "source": "web_search",
                        "error": None,
                    }

            # Step 5: Generate response
            logger.info("Step 5: Generating response")
            response_message = await self._generate_response(
                user_name=user_name,
                products=products,
                has_results=len(products) > 0,
                source=search_source
            )

            result = {
                "message": response_message,
                "products": products,
                "conversation_id": conversation_id,
                "has_results": len(products) > 0,
                "source": search_source,
                "error": None,
            }

            logger.info(f"Workflow completed. Found {len(products)} products")
            return result

        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return {
                "message": "I apologize, but I encountered an error processing your request.",
                "products": [],
                "conversation_id": conversation_id,
                "has_results": False,
                "source": "none",
                "error": str(e),
            }

    async def _get_user_info(self, user_id: str) -> Optional[UserInDB]:
        """Retrieve user information from MongoDB."""
        try:
            user = await mongodb.get_user(user_id)
            return user
        except Exception as e:
            logger.error(f"Error retrieving user info: {e}")
            return None

    async def _search_products(self, query: str) -> list[Product]:
        """Search products in Pinecone vector database."""
        try:
            products = await pinecone_db.search_products(
                query=query,
                top_k=settings.vector_search_top_k,
                threshold=settings.vector_search_threshold,
            )
            logger.info(f"Found {len(products)} products in vector database")
            return products
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []

    async def _web_search(self, query: str) -> list[dict]:
        """Perform web search using Tavily."""
        try:
            if not self.tavily:
                return []
            
            results = await self.tavily.ainvoke({"query": query})
            logger.info(f"Found {len(results)} web search results")
            return results
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []

    async def _generate_response(
        self, user_name: str, products: list[Product], has_results: bool, source: str
    ) -> str:
        """Generate response using LLM."""
        try:
            # Prepare product information
            if products:
                product_list = "\n\n".join([
                    f"Product: {p.name}\n"
                    f"Price: ${p.price:.2f}\n"
                    f"Description: {p.description[:150]}...\n"
                    f"Category: {p.category}"
                    for p in products[:5]
                ])
            else:
                product_list = "No products found in our catalog."

            response = await self.response_chain.ainvoke({
                    "user_name": user_name,
                    "products": product_list,
                    "has_results": str(has_results),
                    "source": source
                }
            )

            return response.strip()

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Fallback response
            if products:
                return (
                    f"Hello {user_name}! I found {len(products)} product(s) that match your request. "
                    f"Would you like to purchase any of these products or receive more details via email?"
                )
            else:
                return (
                    f"Hello {user_name}! I couldn't find any products matching your request. "
                    f"Could you provide more details about what you're looking for?"
                )

    async def _generate_web_response(self, user_name: str, results: list[dict]) -> str:
        """Generate response for web search results."""
        try:
            result_list = "\n\n".join([
                f"Result: {r.get('title', 'N/A')}\n"
                f"Content: {r.get('content', '')[:150]}..."
                for r in results[:3]
            ])

            prompt = PromptTemplate(
                input_variables=["user_name", "results"],
                template="""You are a helpful assistant. The user searched for a product, but we couldn't 
find it in our catalog. However, we found some relevant information online.

User: {user_name}
Web Search Results:
{results}

Generate a helpful response explaining what was found online and suggesting they provide more details 
or try a different search.

Response:"""
            )

            chain = prompt | self.llm
            response = chain.ainvoke(
                {
                    "user_name": user_name,
                    "results": result_list
                }
            )
            return response.strip()

        except Exception as e:
            logger.error(f"Error generating web response: {e}")
            return (
                f"Hello {user_name}! I couldn't find exact matches in our product catalog, "
                f"but I found some related information online. Would you like me to search for something more specific?"
            )

    async def execute_action(
        self, action: ActionType, product_id: str, user_id: str
    ) -> dict[str, Any]:
        """Execute a user action (purchase or email)."""
        try:
            logger.info(f"Executing action: {action} for product: {product_id}")

            # Get user info
            user_info = await self._get_user_info(user_id)
            if not user_info:
                return {
                    "success": False,
                    "message": "User not found",
                    "action": action,
                    "product_id": product_id,
                    "error": "User not found",
                }

            # Get product (search by product_id)
            product = await pinecone_db.get_product_by_id(product_id)

            if not product:
                return {
                    "success": False,
                    "message": "Product not found",
                    "action": action,
                    "product_id": product_id,
                    "error": "Product not found",
                }

            # Execute the appropriate action
            if action == ActionType.PURCHASE:
                result = await self._execute_purchase(user_info, product)
            elif action == ActionType.EMAIL:
                result = await self._execute_email(user_info, product)
            else:
                return {
                    "success": False,
                    "message": f"Unknown action: {action}",
                    "action": action,
                    "product_id": product_id,
                    "error": "Unknown action",
                }

            logger.info(f"Action completed: {action}")
            return {
                "success": result.get("success", False),
                "message": result.get("message", "Action completed"),
                "action": action,
                "product_id": product_id,
                "details": result,
            }

        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return {
                "success": False,
                "message": "Failed to execute action",
                "action": action,
                "product_id": product_id,
                "error": str(e),
            }

    async def _execute_purchase(
        self, user_info: UserInDB, product: Product
    ) -> dict[str, Any]:
        """Execute purchase action."""
        from datetime import datetime

        try:
            # Check stock availability
            if product.stock < 1:
                return {
                    "success": False,
                    "message": f"Insufficient stock. Only {product.stock} units available.",
                    "error": "Insufficient stock",
                }

            # Simulate purchase processing
            quantity = 1
            total_amount = product.price * quantity
            order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            logger.info(
                f"Purchase processed: Order {order_id}, Product {product.product_id}, "
                f"Quantity {quantity}, User {user_info.userId}"
            )

            return {
                "success": True,
                "message": f"Purchase successful! Your order #{order_id} has been placed.",
                "order_id": order_id,
                "product_id": product.product_id,
                "product_name": product.name,
                "quantity": quantity,
                "total_amount": total_amount,
                "user_id": user_info.userId,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing purchase: {e}")
            return {
                "success": False,
                "message": "Failed to process purchase",
                "error": str(e),
            }

    async def _execute_email(
        self, user_info: UserInDB, product: Product
    ) -> dict[str, Any]:
        """Execute email action."""
        from datetime import datetime

        try:
            success = await email_service.send_product_email(
                recipient_email=user_info.email,
                recipient_name=f"{user_info.firstName} {user_info.lastName}",
                product=product,
            )

            if success:
                logger.info(f"Email sent: Product {product.product_id} to {user_info.email}")
                return {
                    "success": True,
                    "message": f"Product details have been sent to {user_info.email}",
                    "product_id": product.product_id,
                    "product_name": product.name,
                    "recipient_email": user_info.email,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to send email",
                    "error": "Email service error",
                }

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                "success": False,
                "message": "Failed to send email",
                "error": str(e),
            }


# Global chatbot service instance
chatbot_service = ChatbotService()
