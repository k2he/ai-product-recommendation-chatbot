"""Pinecone vector database operations."""

import logging
from typing import Any, Optional

from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
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
            self.client = Pinecone(api_key=settings.pinecone_api_key)

            self.embeddings = OllamaEmbeddings(
                base_url=settings.ollama_base_url,
                model=settings.ollama_embedding_model
            )

            existing_indexes = [idx.name for idx in self.client.list_indexes()]

            if settings.pinecone_index_name in existing_indexes:
                desc = self.client.describe_index(settings.pinecone_index_name)
                if desc.dimension != settings.pinecone_dimension:
                    logger.warning(
                        f"Dimension mismatch! Deleting index {settings.pinecone_index_name}"
                    )
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

            self.vectorstore = PineconeVectorStore(
                index_name=settings.pinecone_index_name,
                embedding=self.embeddings,
                pinecone_api_key=settings.pinecone_api_key,
                namespace=settings.pinecone_namespace,
            )

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
            documents = [ProductDocument.from_product(product) for product in products]
            texts = [doc.text for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            ids = [doc.product_id for doc in documents]

            self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

            logger.info(f"Added {len(products)} products to Pinecone")

        except Exception as e:
            logger.error(f"Failed to add products to Pinecone: {e}")
            raise

    async def search_products(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
        metadata_filter: Optional[dict[str, Any]] = None,
    ) -> list[Product]:
        """Search for products using similarity search with optional metadata filtering.

        Args:
            query: Semantic search query string.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score (0-1) to include a result.
            metadata_filter: Optional Pinecone filter dict, e.g.:
                { "categoryName": { "$in": ["Laptops"] }, "salePrice": { "$lte": 1000 } }
        """
        if not self.vectorstore:
            raise ConnectionError("Vectorstore not initialized")

        try:
            search_kwargs: dict[str, Any] = {"k": top_k}
            if metadata_filter:
                search_kwargs["filter"] = metadata_filter
                logger.info(f"Applying metadata filter: {metadata_filter}")

            results = self.vectorstore.similarity_search_with_score(
                query, **search_kwargs
            )

            products = []
            for doc, score in results:
                if score < threshold:
                    logger.debug(f"Skipping product with low score {score:.3f}")
                    continue

                meta = doc.metadata
                try:
                    product = Product(
                        sku=meta.get("sku", meta.get("product_id", "")),
                        name=meta.get("name", ""),
                        shortDescription=meta.get("shortDescription", doc.page_content),
                        customerRating=meta.get("customerRating"),
                        productUrl=meta.get("productUrl", ""),
                        regularPrice=float(meta.get("regularPrice", 0.0)),
                        salePrice=float(meta.get("salePrice", 0.0)),
                        categoryName=meta.get("categoryName", ""),
                        isOnSale=bool(meta.get("isOnSale", False)),
                        relevance_score=float(score),
                    )
                    products.append(product)
                except Exception as e:
                    logger.warning(f"Failed to parse product from metadata: {e}")
                    continue

            logger.info(f"Found {len(products)} products matching query")
            return products

        except Exception as e:
            logger.error(f"Failed to search products: {e}")
            raise

    async def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Fetch a single product by its SKU/ID from Pinecone."""
        if not self.vectorstore:
            raise ConnectionError("Vectorstore not initialized")

        try:
            fetch_response = self.index.fetch(
                ids=[product_id], namespace=settings.pinecone_namespace
            )
            vectors = fetch_response.vectors
            if product_id not in vectors:
                logger.info(f"Product ID '{product_id}' not found in Pinecone")
                return None

            data = vectors[product_id]
            meta = data.metadata if hasattr(data, "metadata") else {}

            return Product(
                sku=meta.get("sku", meta.get("product_id", "")),
                name=meta.get("name", ""),
                shortDescription=meta.get("shortDescription", ""),
                customerRating=meta.get("customerRating"),
                productUrl=meta.get("productUrl", ""),
                regularPrice=float(meta.get("regularPrice", 0.0)),
                salePrice=float(meta.get("salePrice", 0.0)),
                categoryName=meta.get("categoryName", ""),
                isOnSale=bool(meta.get("isOnSale", False)),
            )

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
