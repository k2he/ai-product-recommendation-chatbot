"""Product data loading script."""

import asyncio
import logging
from pathlib import Path

from app.database.pinecone_db import pinecone_db
from app.services.data_loader import DataLoader
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


async def load_products():
    """Load products from JSON files into Pinecone."""
    try:
        logger.info("Starting product data loading...")

        # Connect to Pinecone
        await pinecone_db.connect()

        # Get products directory
        data_dir = Path(__file__).parent.parent / "data" / "products"

        if not data_dir.exists():
            logger.error(f"Products directory not found: {data_dir}")
            return

        # Load products from directory
        logger.info(f"Loading products from: {data_dir}")
        products = await DataLoader.load_products_from_directory(data_dir)

        if not products:
            logger.warning("No products found to load")
            return

        logger.info(f"Loaded {len(products)} products from JSON files")

        # Clear existing data (optional)
        clear_existing = input("Clear existing products in Pinecone? (y/n): ").lower()
        if clear_existing == "y":
            logger.info("Clearing existing products...")
            await pinecone_db.clear_index()

        # Add products to Pinecone
        logger.info("Adding products to Pinecone...")
        await pinecone_db.add_products(products)

        # Get stats
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
