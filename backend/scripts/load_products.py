"""Product data loading script.

Loads BestBuy-format JSON files from backend/data/products/ into Pinecone.

After loading it writes backend/data/categories.json which contains the list
of unique categoryName values. This file serves two purposes:
  1. It is read at runtime by ChatbotService._load_categories() to build the
     SelfQueryingRetriever's dynamic AttributeInfo for the categoryName field.
  2. It gives operators a quick audit of what categories are in the index.

Re-run this script whenever product JSON files are added or changed.
"""

import asyncio
import json
import logging
from pathlib import Path

from app.database.pinecone_db import pinecone_db
from app.services.data_loader import DataLoader
from app.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def load_products():
    """Load products from BestBuy JSON files into Pinecone and save categories."""
    try:
        logger.info("Starting product data loading...")

        await pinecone_db.connect()

        data_dir = Path(__file__).parent.parent / "data" / "products"
        if not data_dir.exists():
            logger.error(f"Products directory not found: {data_dir}")
            return

        logger.info(f"Loading products from: {data_dir}")
        products = await DataLoader.load_products_from_directory(data_dir)

        if not products:
            logger.warning("No products found to load")
            return

        logger.info(f"Loaded {len(products)} products from JSON files")

        # ── Save unique categories ─────────────────────────────────────────────
        # categories.json is consumed by ChatbotService at startup to build the
        # SelfQueryingRetriever's categoryName AttributeInfo description.
        # Always regenerate it here so SQR stays in sync with the index.
        categories = DataLoader.extract_unique_categories(products)
        categories_file = Path(__file__).parent.parent / "data" / "categories.json"
        categories_file.parent.mkdir(parents=True, exist_ok=True)

        with open(categories_file, "w", encoding="utf-8") as f:
            json.dump({"categories": categories, "total": len(categories)}, f, indent=2)

        logger.info(f"Saved {len(categories)} unique categories to {categories_file}")
        logger.info(f"Categories: {categories}")
        logger.info(
            "SelfQueryingRetriever will use these categories as allowed filter values "
            "when the application next starts."
        )

        # ── Upsert into Pinecone ───────────────────────────────────────────────
        clear_existing = input("Clear existing products in Pinecone? (y/n): ").lower()
        if clear_existing == "y":
            logger.info("Clearing existing products...")
            await pinecone_db.clear_index()

        # Fit BM25 encoder on the full corpus for domain-specific keyword matching
        # This learns IDF weights from all products, providing better hybrid search results
        # than using the generic BM25Encoder.default()
        from app.models.product import ProductDocument
        texts = [ProductDocument.from_product(p).text for p in products]
        pinecone_db.fit_bm25_encoder(texts)

        logger.info("Adding products to Pinecone...")
        await pinecone_db.add_products(products)

        stats = await pinecone_db.get_stats()
        logger.info(f"Pinecone stats: {stats}")
        logger.info("Product loading completed successfully!")

    except Exception as e:
        logger.error(f"Error loading products: {e}")
        raise
    finally:
        await pinecone_db.disconnect()


if __name__ == "__main__":
    asyncio.run(load_products())
