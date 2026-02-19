"""Product data loading script.

Loads BestBuy-format JSON files from backend/data/products/ into Pinecone.
Saves all unique categoryName values to backend/data/categories.json for use
in metadata filtering at query time.
"""

import asyncio
import json
import logging
from pathlib import Path

from app.database.pinecone_db import pinecone_db
from app.services.data_loader import DataLoader
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


async def load_products():
    """Load products from BestBuy JSON files into Pinecone and save categories."""
    try:
        logger.info("Starting product data loading...")

        # Connect to Pinecone
        await pinecone_db.connect()

        # Get products directory
        data_dir = Path(__file__).parent.parent / "data" / "products"

        if not data_dir.exists():
            logger.error(f"Products directory not found: {data_dir}")
            return

        # Load and transform products from directory
        logger.info(f"Loading products from: {data_dir}")
        products = await DataLoader.load_products_from_directory(data_dir)

        if not products:
            logger.warning("No products found to load")
            return

        logger.info(f"Loaded {len(products)} products from JSON files")

        # ── Step 2: Extract and save unique categories ──────────────────────
        categories = DataLoader.extract_unique_categories(products)
        categories_file = Path(__file__).parent.parent / "data" / "categories.json"
        categories_file.parent.mkdir(parents=True, exist_ok=True)

        with open(categories_file, "w", encoding="utf-8") as f:
            json.dump({"categories": categories, "total": len(categories)}, f, indent=2)

        logger.info(f"Saved {len(categories)} unique categories to {categories_file}")
        logger.info(f"Categories: {categories}")

        # ── Step 3: Load into Pinecone ───────────────────────────────────────
        clear_existing = input("Clear existing products in Pinecone? (y/n): ").lower()
        if clear_existing == "y":
            logger.info("Clearing existing products...")
            await pinecone_db.clear_index()

        logger.info("Adding products to Pinecone...")
        await pinecone_db.add_products(products)

        # Stats
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
