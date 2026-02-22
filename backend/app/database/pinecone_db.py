"""Pinecone vector database operations."""

import logging
from typing import Any, Optional

from langchain.chains.query_constructor.base import AttributeInfo
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from pinecone_text.sparse import BM25Encoder

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
    """Pinecone vector database manager with hybrid search support."""

    def __init__(self) -> None:
        self.client: Optional[Pinecone] = None
        self.index = None
        self.embeddings: Optional[OllamaEmbeddings] = None
        self.vectorstore: Optional[PineconeVectorStore] = None
        self.bm25_encoder: Optional[BM25Encoder] = None

    async def connect(self) -> None:
        """Connect to Pinecone and initialise the vectorstore with hybrid search support."""
        try:
            self.client = Pinecone(api_key=settings.pinecone_api_key)

            self.embeddings = OllamaEmbeddings(
                base_url=settings.ollama_base_url,
                model=settings.ollama_embedding_model,
            )

            # Initialize BM25 encoder for sparse vectors (hybrid search)
            self.bm25_encoder = BM25Encoder()
            logger.info("Initialized BM25Encoder for hybrid search")

            existing_indexes = [idx.name for idx in self.client.list_indexes()]

            if settings.pinecone_index_name in existing_indexes:
                desc = self.client.describe_index(settings.pinecone_index_name)
                if desc.dimension != settings.pinecone_dimension:
                    logger.warning(
                        f"Dimension mismatch — deleting index: {settings.pinecone_index_name}"
                    )
                    self.client.delete_index(settings.pinecone_index_name)
                    existing_indexes.remove(settings.pinecone_index_name)

            if settings.pinecone_index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index with hybrid search support: {settings.pinecone_index_name}")
                self.client.create_index(
                    name=settings.pinecone_index_name,
                    dimension=settings.pinecone_dimension,
                    metric=settings.pinecone_metric,
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    ),
                )

            self.vectorstore = PineconeVectorStore(
                index_name=settings.pinecone_index_name,
                embedding=self.embeddings,
                pinecone_api_key=settings.pinecone_api_key,
                namespace=settings.pinecone_namespace,
                sparse_encoder=self.bm25_encoder,  # Enable automatic hybrid search
            )

            self.index = self.client.Index(settings.pinecone_index_name)
            logger.info(f"Connected to Pinecone index with hybrid search: {settings.pinecone_index_name}")

        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            raise

    async def disconnect(self) -> None:
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
            f"SelfQueryingRetriever built — "
            f"{len(metadata_field_info)} metadata fields, "
            f"{len(categories)} categories."
        )
        return retriever

    # ── Product ingestion ──────────────────────────────────────────────────────

    def fit_bm25_encoder(self, texts: list[str]) -> None:
        """Fit the BM25 encoder on a corpus of texts.

        This calculates IDF (Inverse Document Frequency) weights based on the
        provided corpus, enabling domain-specific keyword matching.

        Args:
            texts: List of text documents to train on (typically all product descriptions)

        Note:
            - Should be called ONCE on the full product corpus before adding products
            - Alternative: Use BM25Encoder.default() for generic pre-trained weights
            - Custom fitting provides better results for domain-specific data
        """
        if not self.bm25_encoder:
            logger.warning("BM25Encoder not initialized, skipping fit")
            return

        if hasattr(self.bm25_encoder, 'idf_'):
            logger.info("BM25Encoder already fitted, skipping")
            return

        logger.info(f"Fitting BM25Encoder on {len(texts)} documents...")
        self.bm25_encoder.fit(texts)
        logger.info("BM25Encoder fitted successfully with domain-specific IDF weights")

    async def add_products(self, products: list[ProductBase]) -> None:
        """Embed and upsert products into Pinecone with hybrid search support.

        Since sparse_encoder is set on the vectorstore, it automatically generates
        both dense (semantic) and sparse (BM25) vectors during upsert.

        Note:
            BM25 encoder must be fitted before calling this method. You can either:
            1. Call fit_bm25_encoder() explicitly with the full corpus
            2. Let this method auto-fit on the current batch (not ideal for multiple batches)
        """
        if not self.vectorstore or not self.index:
            raise ConnectionError("Vectorstore not initialised.")

        try:
            documents = [ProductDocument.from_product(p) for p in products]
            texts = [d.text for d in documents]
            metadatas = [d.metadata for d in documents]
            ids = [d.product_id for d in documents]

            # Auto-fit BM25 encoder if not already fitted (convenience fallback)
            # For best results, call fit_bm25_encoder() explicitly on the full corpus
            if self.bm25_encoder and not hasattr(self.bm25_encoder, 'idf_'):
                logger.warning(
                    "BM25Encoder not fitted yet - auto-fitting on current batch. "
                    "For optimal results, call fit_bm25_encoder() on the full corpus first."
                )
                self.fit_bm25_encoder(texts)

            # Use vectorstore.add_texts() which automatically handles hybrid search
            # when sparse_encoder is configured
            await self.vectorstore.aadd_texts(
                texts=texts,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(f"Added {len(products)} products to Pinecone with hybrid search vectors")

        except Exception as e:
            logger.error(f"Failed to add products to Pinecone: {e}")
            raise

    async def hybrid_search(
        self,
        query: str,
        filter: Optional[dict] = None,
        top_k: int = 5,
        alpha: Optional[float] = None,
    ) -> list[dict]:
        """Perform hybrid search combining dense and sparse vectors.

        Args:
            query: Search query text
            filter: Pinecone metadata filter
            top_k: Number of results to return
            alpha: Weight for dense vs sparse (0.0=sparse only, 1.0=dense only)
                   If None, uses settings.hybrid_search_alpha

        Returns:
            List of search results with metadata
        """
        if not self.index or not self.embeddings:
            raise ConnectionError("Index not initialised.")

        try:
            # Use configured alpha if not provided
            if alpha is None:
                alpha = settings.hybrid_search_alpha

            # Generate dense vector (semantic embedding)
            dense_vector = await self.embeddings.aembed_query(query)

            # Generate sparse vector (BM25/keyword)
            sparse_vector = None
            if self.bm25_encoder:
                sparse_dict = self.bm25_encoder.encode_queries([query])[0]
                sparse_vector = {
                    "indices": sparse_dict["indices"],
                    "values": sparse_dict["values"]
                }

            # Perform hybrid search
            search_kwargs = {
                "namespace": settings.pinecone_namespace,
                "top_k": top_k,
                "include_metadata": True,
            }

            # Add filter if provided
            if filter:
                search_kwargs["filter"] = filter

            # Query with both dense and sparse vectors
            if sparse_vector:
                results = self.index.query(
                    vector=dense_vector,
                    sparse_vector=sparse_vector,
                    **search_kwargs
                )
                logger.info(f"Hybrid search returned {len(results.matches)} results (alpha={alpha})")
            else:
                # Fallback to dense-only if sparse not available
                results = self.index.query(
                    vector=dense_vector,
                    **search_kwargs
                )
                logger.info(f"Dense-only search returned {len(results.matches)} results")

            # Convert results to list of dicts
            matches = []
            for match in results.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata or {},
                })

            return matches

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

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
                logger.info(f"Product '{product_id}' not found in Pinecone")
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
            )
        except Exception as e:
            logger.error(f"Failed to fetch product by ID: {e}")
            return None

    # ── Admin helpers ──────────────────────────────────────────────────────────

    async def delete_products(self, product_ids: list[str]) -> None:
        if not self.index:
            raise ConnectionError("Index not initialised.")
        try:
            self.index.delete(ids=product_ids, namespace=settings.pinecone_namespace)
            logger.info(f"Deleted {len(product_ids)} products from Pinecone")
        except Exception as e:
            logger.error(f"Failed to delete products: {e}")
            raise

    async def clear_index(self) -> None:
        if not self.index:
            raise ConnectionError("Index not initialised.")
        try:
            self.index.delete(delete_all=True, namespace=settings.pinecone_namespace)
            logger.info("Cleared all products from Pinecone index")
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            raise

    async def get_stats(self) -> dict[str, Any]:
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
            logger.error(f"Failed to get index stats: {e}")
            return {}


# Global Pinecone instance
pinecone_db = PineconeDB()
