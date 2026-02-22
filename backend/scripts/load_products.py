"""Product data loading script.

Loads BestBuy-format JSON files from backend/data/products/ into Pinecone.

After loading it writes backend/data/categories.json which contains the list
of unique categoryName values.  This file serves two purposes:
  1. It is read at runtime by ChatbotService._load_categories() to build the
     SelfQueryingRetriever's dynamic AttributeInfo for the categoryName field.
  2. It gives operators a quick audit of what categories are in the index.

Re-run this script whenever product JSON files are added or changed.

Usage:
    python -m scripts.load_products           # prompts before clearing
    python -m scripts.load_products --clear    # clears index without prompting
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from app.database.pinecone_db import pinecone_db
from app.services.data_loader import DataLoader
from app.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load product data into Pinecone")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing products from Pinecone before loading",
    )
    return parser.parse_args()


async def load_products(*, clear: bool = False) -> None:
    """Load products from BestBuy JSON files into Pinecone and save categories."""
    try:
        logger.info("Starting product data loading...")

        await pinecone_db.connect()

        data_dir = Path(__file__).parent.parent / "data" / "products"
        if not data_dir.exists():
            logger.error("Products directory not found: %s", data_dir)
            return

        logger.info("Loading products from: %s", data_dir)
        products = await DataLoader.load_products_from_directory(data_dir)

        if not products:
            logger.warning("No products found to load")
            return

        logger.info("Loaded %d products from JSON files", len(products))

        # ── Save unique categories ─────────────────────────────────────────────
        categories = DataLoader.extract_unique_categories(products)
        categories_file = Path(__file__).parent.parent / "data" / "categories.json"
        categories_file.parent.mkdir(parents=True, exist_ok=True)

        with open(categories_file, "w", encoding="utf-8") as f:
            json.dump({"categories": categories, "total": len(categories)}, f, indent=2)

        logger.info("Saved %d unique categories to %s", len(categories), categories_file)
        logger.info("Categories: %s", categories)
        logger.info(
            "SelfQueryingRetriever will use these categories as allowed filter values "
            "when the application next starts."
        )

        # ── Upsert into Pinecone ───────────────────────────────────────────────
        should_clear = clear
        if not should_clear and sys.stdin.isatty():
            should_clear = input("Clear existing products in Pinecone? (y/n): ").lower() == "y"

        if should_clear:
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
        logger.info("Pinecone stats: %s", stats)
        logger.info("Product loading completed successfully!")

    except Exception as e:
        logger.error("Error loading products: %s", e)
        raise
    finally:
        await pinecone_db.disconnect()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(load_products(clear=args.clear))
