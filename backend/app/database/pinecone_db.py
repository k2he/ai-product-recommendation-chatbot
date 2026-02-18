"""Pinecone vector database operations."""

import logging
from typing import Any, Optional, Coroutine

from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.models import Product
from app.models.product import Product, ProductBase, ProductDocument

logger = logging.getLogger(__name__)
settings = get_settings()


class PineconeDB:
    """Pinecone vector database manager."""

    def __init__(self) -> None:
        """Initialize Pinecone connection."""
        self.client: Optional[Pinecone] = None
        self.index = None
        self.embeddings: Optional[OllamaEmbeddings] = None
        self.vectorstore: Optional[PineconeVectorStore] = None

    async def connect(self) -> None:
        """Connect to Pinecone and initialize index."""
        try:
            # Initialize Pinecone
            self.client = Pinecone(api_key=settings.pinecone_api_key)

            # Initialize embeddings
            self.embeddings = OllamaEmbeddings(
                base_url=settings.ollama_base_url,
                model=settings.ollama_embedding_model
            )

            # Check if index exists, create if not
            existing_indexes = [idx.name for idx in self.client.list_indexes()]

            if settings.pinecone_index_name in existing_indexes:
                desc = self.client.describe_index(settings.pinecone_index_name)
                # Check for dimension mismatch
                if desc.dimension != settings.pinecone_dimension:
                    logger.warning(f"Dimension mismatch! Deleting index {settings.pinecone_index_name}")
                    self.client.delete_index(settings.pinecone_index_name)
                    existing_indexes.remove(settings.pinecone_index_name)

            if settings.pinecone_index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {settings.pinecone_index_name}")
                self.client.create_index(
                    name=settings.pinecone_index_name,
                    dimension=settings.pinecone_dimension,
                    metric=settings.pinecone_metric,
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )

            # Initialize vectorstore
            self.vectorstore = PineconeVectorStore(
                index_name=settings.pinecone_index_name,
                embedding=self.embeddings,
                pinecone_api_key=settings.pinecone_api_key,
                namespace=settings.pinecone_namespace,
            )

            # Keep a reference to the raw index for delete/stats operations
            self.index = self.client.Index(settings.pinecone_index_name)

            logger.info(f"Connected to Pinecone index: {settings.pinecone_index_name}")

        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Pinecone."""
        logger.info("Pinecone connection closed")

    async def add_products(self, products: list[ProductBase]) -> None:
        """Add products to vector database."""
        if not self.vectorstore:
            raise ConnectionError("Vectorstore not initialized")

        try:
            # Convert products to documents
            documents = [ProductDocument.from_product(product) for product in products]

            # Extract texts and metadatas
            texts = [doc.text for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            ids = [doc.product_id for doc in documents]

            # Add to vectorstore
            self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

            logger.info(f"Added {len(products)} products to Pinecone")

        except Exception as e:
            logger.error(f"Failed to add products to Pinecone: {e}")
            raise

    async def search_products(
        self, query: str, top_k: int = 5, threshold: float = 0.7
    ) -> list[Product]:
        """Search for products using similarity search."""
        if not self.vectorstore:
            raise ConnectionError("Vectorstore not initialized")

        try:
            # Perform similarity search with scores
            results = self.vectorstore.similarity_search_with_score(query, k=top_k)
            # results = self.vectorstore.search(query, search_type="similarity", k=top_k)

            products = []
            for doc, score in results:
                # Pinecone returns distance, convert to similarity (1 - distance for cosine)
                # similarity = 1 - score if score < 1 else 0

                # Filter by threshold
                if score >= threshold:
                    metadata = doc.metadata
                    product = Product(
                        product_id=metadata.get("product_id", ""),
                        name=metadata.get("name", ""),
                        description=doc.page_content,
                        category=metadata.get("category", ""),
                        price=metadata.get("price", 0.0),
                        specifications=metadata.get("specifications", {}),
                        image_url=metadata.get("image_url"),
                        stock=metadata.get("stock", 0),
                        tags=metadata.get("tags", []),
                        relevance_score=score,
                    )
                    products.append(product)

            logger.info(f"Found {len(products)} products matching query: '{query}'")
            return products

        except Exception as e:
            logger.error(f"Failed to search products: {e}")
            return []

    async def get_product_by_id(
        self, product_id: str, top_k: int = 5, threshold: float = 0.7
    ) -> Product | None:
        """Search for products using similarity search."""
        if not self.vectorstore:
            raise ConnectionError("Vectorstore not initialized")

        try:
            # Perform similarity search with scores
            fetch_response = self.index.fetch(ids=[product_id], namespace=settings.pinecone_namespace)
            vectors = fetch_response.vectors
            if product_id not in vectors:
                logger.info(f"Product ID '{product_id}' not found in Pinecone")
                return None

            data = vectors[product_id]
            metadata = data.metadata if hasattr(data, 'metadata') else {}

            product = Product(
                product_id=metadata.get("product_id", ""),
                name=metadata.get("name", ""),
                description=metadata.get("text", ""),
                category=metadata.get("category", ""),
                price=metadata.get("price", 0.0),
                specifications=metadata.get("specifications", {}),
                image_url=metadata.get("image_url"),
                stock=metadata.get("stock", 0),
                tags=metadata.get("tags", [])
            )

            return product
        except Exception as e:
            logger.error(f"Failed to fetch product by ID: {e}")
            return None

    async def delete_products(self, product_ids: list[str]) -> None:
        """Delete products from vector database."""
        if not self.index:
            raise ConnectionError("Index not initialized")

        try:
            self.index.delete(ids=product_ids, namespace=settings.pinecone_namespace)
            logger.info(f"Deleted {len(product_ids)} products from Pinecone")

        except Exception as e:
            logger.error(f"Failed to delete products: {e}")
            raise

    async def clear_index(self) -> None:
        """Clear all vectors from the index."""
        if not self.index:
            raise ConnectionError("Index not initialized")

        try:
            self.index.delete(delete_all=True, namespace=settings.pinecone_namespace)
            logger.info("Cleared all products from Pinecone index")

        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            raise

    async def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        if not self.index:
            raise ConnectionError("Index not initialized")

        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", 0),
                "namespaces": stats.get("namespaces", {}),
            }

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}


# Global Pinecone instance
pinecone_db = PineconeDB()
