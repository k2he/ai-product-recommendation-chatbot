"""Pinecone vector database operations."""

import logging
from typing import Any, Optional

from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.models.product import Product, ProductBase, ProductDocument

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Static metadata field definitions for SelfQueryingRetriever ───────────────
# categoryName is omitted here — it is built dynamically in build_sqr()
# because its allowed values come from categories.json at runtime.
_STATIC_METADATA_FIELDS = [
    AttributeInfo(
        name="salePrice",
        description=(
            "Current selling price of the product in CAD. "
            "Use for queries like 'under $500', 'less than 200 dollars', 'over $1000'."
        ),
        type="float",
    ),
    AttributeInfo(
        name="regularPrice",
        description="Original non-sale price of the product in CAD.",
        type="float",
    ),
    AttributeInfo(
        name="customerRating",
        description=(
            "Average customer rating from 0 to 5. "
            "Use for queries like 'highly rated', '4 stars or more', 'top rated'."
        ),
        type="float",
    ),
    AttributeInfo(
        name="isOnSale",
        description=(
            "Boolean — true if the product currently has an active sale. "
            "Use for queries like 'on sale', 'discounted', 'deals'."
        ),
        type="boolean",
    ),
]

_DOCUMENT_CONTENT_DESCRIPTION = (
    "Product name and short description."
    "Contains product type, brand, key features, and specifications."
)


class PineconeDB:
    """Pinecone vector database manager."""

    def __init__(self) -> None:
        self.client: Optional[Pinecone] = None
        self.index = None
        self.embeddings: Optional[OllamaEmbeddings] = None
        self.vectorstore: Optional[PineconeVectorStore] = None

    async def connect(self) -> None:
        """Connect to Pinecone and initialise the vectorstore."""
        try:
            self.client = Pinecone(api_key=settings.pinecone_api_key)

            self.embeddings = OllamaEmbeddings(
                base_url=settings.ollama_base_url,
                model=settings.ollama_embedding_model,
            )

            existing_indexes = [idx.name for idx in self.client.list_indexes()]

            if settings.pinecone_index_name in existing_indexes:
                desc = self.client.describe_index(settings.pinecone_index_name)
                if desc.dimension != settings.pinecone_dimension:
                    logger.warning(
                        "Dimension mismatch — deleting index: %s",
                        settings.pinecone_index_name,
                    )
                    self.client.delete_index(settings.pinecone_index_name)
                    existing_indexes.remove(settings.pinecone_index_name)

            if settings.pinecone_index_name not in existing_indexes:
                logger.info("Creating Pinecone index: %s", settings.pinecone_index_name)
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
            logger.info("Connected to Pinecone index: %s", settings.pinecone_index_name)

        except Exception as e:
            logger.error("Failed to connect to Pinecone: %s", e)
            raise

    async def disconnect(self) -> None:
        """Release Pinecone resources (no persistent connection to close)."""
        self.client = None
        self.index = None
        self.vectorstore = None
        logger.info("Pinecone connection closed")

    # ── Self-Querying Retriever factory ────────────────────────────────────────

    def build_sqr(self, llm: Any, categories: list[str]) -> SelfQueryRetriever:
        """Build a SelfQueryingRetriever wired to this Pinecone vectorstore.

        SQR replaces both the rephrase chain and the manual metadata filter
        construction. Given a raw natural language query it:
          1. Calls the LLM once to decompose the query into a semantic search
             string + a structured filter expression (LangChain query language).
          2. Translates that filter automatically into Pinecone filter syntax.
          3. Runs the vector search with the filter applied in one round trip.

        This method is called once during ChatbotService.__init__(), after
        Pinecone has connected and categories.json has been loaded.

        Args:
            llm:        Any LangChain-compatible LLM (ChatOllama in production).
            categories: List of unique categoryName strings from categories.json.
                        Injected into the AttributeInfo description so the LLM
                        knows exactly which values are valid to filter on.

        Returns:
            Configured SelfQueryingRetriever instance.
        """
        if not self.vectorstore:
            raise ConnectionError("Vectorstore not initialised — call connect() first.")

        # Build the dynamic categoryName field using the loaded category list
        category_values = ", ".join(f'"{c}"' for c in categories)
        category_field = AttributeInfo(
            name="categoryName",
            description=(
                f"Product category. Only filter using exact values from this list: "
                f"{category_values}. "
                "Use when the user mentions a product type like 'laptop', 'headphones', "
                "'earbuds', 'MacBook Air', etc."
            ),
            type="string",
        )

        metadata_field_info = _STATIC_METADATA_FIELDS + [category_field]

        retriever = SelfQueryRetriever.from_llm(
            llm=llm,
            vectorstore=self.vectorstore,
            document_contents=_DOCUMENT_CONTENT_DESCRIPTION,
            metadata_field_info=metadata_field_info,
            search_kwargs={"k": settings.vector_search_top_k},
            # When SQR cannot parse a filter it falls back to unfiltered search
            enable_limit=False,
            verbose=True,
        )

        logger.info(
            "SelfQueryingRetriever built — %d metadata fields, %d categories.",
            len(metadata_field_info),
            len(categories),
        )
        return retriever

    # ── Product ingestion ──────────────────────────────────────────────────────

    async def add_products(self, products: list[ProductBase]) -> None:
        """Embed and upsert products into Pinecone."""
        if not self.vectorstore:
            raise ConnectionError("Vectorstore not initialised.")
        try:
            documents = [ProductDocument.from_product(p) for p in products]
            self.vectorstore.add_texts(
                texts=[d.text for d in documents],
                metadatas=[d.metadata for d in documents],
                ids=[d.product_id for d in documents],
            )
            logger.info("Added %d products to Pinecone", len(products))
        except Exception as e:
            logger.error("Failed to add products to Pinecone: %s", e)
            raise

    # ── Point lookup ───────────────────────────────────────────────────────────

    async def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Fetch a single product by SKU directly from the Pinecone index."""
        if not self.index:
            raise ConnectionError("Index not initialised.")
        try:
            fetch_response = self.index.fetch(
                ids=[product_id], namespace=settings.pinecone_namespace
            )
            vectors = fetch_response.vectors
            if product_id not in vectors:
                logger.info("Product '%s' not found in Pinecone", product_id)
                return None

            meta = vectors[product_id].metadata or {}
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
                highResImage=meta.get("highResImage") or None,
                relevance_score=None,
            )
        except Exception as e:
            logger.error("Failed to fetch product by ID: %s", e)
            return None

    # ── Admin helpers ──────────────────────────────────────────────────────────

    async def delete_products(self, product_ids: list[str]) -> None:
        """Delete specific products from the Pinecone index by their IDs."""
        if not self.index:
            raise ConnectionError("Index not initialised.")
        try:
            self.index.delete(ids=product_ids, namespace=settings.pinecone_namespace)
            logger.info("Deleted %d products from Pinecone", len(product_ids))
        except Exception as e:
            logger.error("Failed to delete products: %s", e)
            raise

    async def clear_index(self) -> None:
        """Delete all vectors from the configured namespace."""
        if not self.index:
            raise ConnectionError("Index not initialised.")
        try:
            self.index.delete(delete_all=True, namespace=settings.pinecone_namespace)
            logger.info("Cleared all products from Pinecone index")
        except Exception as e:
            logger.error("Failed to clear index: %s", e)
            raise

    async def get_stats(self) -> dict[str, Any]:
        """Return index statistics (total vectors, dimension, namespaces)."""
        if not self.index:
            raise ConnectionError("Index not initialised.")
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", 0),
                "namespaces": stats.get("namespaces", {}),
            }
        except Exception as e:
            logger.error("Failed to get index stats: %s", e)
            return {}


# Global Pinecone instance
pinecone_db = PineconeDB()
