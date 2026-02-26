"""Purchase history loading script.

Loads purchase history from JSON files into MongoDB.

This script:
1. Reads purchase_history.json files for each user
2. Filters out environmental fees (items with parentSku)
3. Saves orders to MongoDB purchase_orders collection

Usage:
    python -m scripts.load_purchase_history
    python -m scripts.load_purchase_history --clear
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from app.database.mongodb import mongodb
from app.models.order import OrderInDB, LineItem
from app.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load purchase history into MongoDB")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing orders from MongoDB before loading",
    )
    return parser.parse_args()


async def load_purchase_history(*, clear: bool = False) -> None:
    """Load purchase history from JSON files into MongoDB."""
    try:
        logger.info("Starting purchase history loading...")

        await mongodb.connect()

        # Map of JSON files to user IDs
        data_dir = Path(__file__).parent.parent / "data" / "purchase_history"
        purchase_files = {
            "user_001": data_dir / "purchase_history_user_001.json",
            "user_002": data_dir / "purchase_history_user_002.json",
            "user_003": data_dir / "purchase_history_user_003.json",
        }

        # Clear existing orders if requested
        should_clear = clear
        if not should_clear and sys.stdin.isatty():
            should_clear = input("Clear existing orders in MongoDB? (y/n): ").lower() == "y"

        if should_clear and mongodb.db:
            logger.info("Clearing existing orders...")
            from app.config import get_settings
            settings = get_settings()
            result = await mongodb.db[settings.mongodb_purchase_orders_collection].delete_many({})
            logger.info("Deleted %d existing orders", result.deleted_count)

        total_orders_loaded = 0

        # Load orders for each user
        for user_id, file_path in purchase_files.items():
            if not file_path.exists():
                logger.warning("Purchase history file not found: %s", file_path)
                continue

            logger.info("Loading purchase history for %s from %s", user_id, file_path)

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            orders = data.get("orders", [])
            logger.info("Found %d orders for %s", len(orders), user_id)

            # Process each order
            for order_data in orders:
                try:
                    # Filter out environmental fees (items with parentSku)
                    filtered_line_items = [
                        item for item in order_data.get("lineItems", [])
                        if item.get("parentSku") is None or item.get("parentSku") == ""
                    ]

                    # Skip orders with no valid line items
                    if not filtered_line_items:
                        logger.warning(
                            "Skipping order %s - no valid line items after filtering",
                            order_data.get("orderNumber")
                        )
                        continue

                    # Recalculate total price based on filtered items
                    recalculated_total = sum(item.get("total", 0) for item in filtered_line_items)

                    # Parse datetime
                    order_date = datetime.fromisoformat(
                        order_data["datetime"].replace("Z", "+00:00")
                    )

                    # Create LineItem models
                    line_items = [
                        LineItem(
                            name=item["name"],
                            sku=item["sku"],
                            quantity=item["quantity"],
                            total=item["total"],
                            imgUrl=item["imgUrl"],
                        )
                        for item in filtered_line_items
                    ]

                    # Create OrderInDB model
                    order = OrderInDB(
                        userId=user_id,
                        orderNumber=order_data["orderNumber"],
                        orderDate=order_date,
                        totalPrice=recalculated_total,
                        status=order_data["status"],
                        lineItems=line_items,
                    )

                    # Save to MongoDB
                    await mongodb.create_order(order)
                    total_orders_loaded += 1
                    logger.info(
                        "Loaded order %s for %s: %d items, $%.2f",
                        order.orderNumber,
                        user_id,
                        len(line_items),
                        recalculated_total,
                    )

                except Exception as e:
                    logger.error(
                        "Failed to load order %s: %s",
                        order_data.get("orderNumber", "unknown"),
                        e,
                    )
                    continue

        logger.info("Purchase history loading completed! Total orders loaded: %d", total_orders_loaded)

    except Exception as e:
        logger.error("Purchase history loading failed: %s", e)
        raise
    finally:
        await mongodb.disconnect()


def main() -> None:
    """Entry point for the script."""
    args = _parse_args()
    asyncio.run(load_purchase_history(clear=args.clear))


if __name__ == "__main__":
    main()

