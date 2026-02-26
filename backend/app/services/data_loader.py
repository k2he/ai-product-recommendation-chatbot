"""Data loader service for importing product data."""

import json
import logging
from pathlib import Path
from typing import Any

from app.models.product import ProductBase

logger = logging.getLogger(__name__)

BESTBUY_URL_PREFIX = "https://www.bestbuy.ca"


class DataLoader:
    """Service for loading product data from BestBuy-format JSON files."""

    @staticmethod
    def load_json_file(file_path: str | Path) -> list[dict[str, Any]]:
        """Load data from a single JSON file.

        Supports both:
        - New BestBuy format: { "products": [...] }
        - Legacy format: flat array [...]
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix.lower() != ".json":
            raise ValueError(f"File must be a JSON file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Support BestBuy format: { "products": [...] }
            if isinstance(data, dict) and "products" in data:
                data = data["products"]
            elif isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("JSON must contain a 'products' array, an object, or an array")

            logger.info("Loaded %d records from %s", len(data), file_path)
            return data

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in file %s: %s", file_path, e)
            raise
        except Exception as e:
            logger.error("Error loading file %s: %s", file_path, e)
            raise

    @staticmethod
    def transform_bestbuy_product(raw: dict[str, Any]) -> dict[str, Any]:
        """Transform a raw BestBuy product record into ProductBase-compatible dict.

        Extracts only: sku, name, shortDescription, customerRating, productUrl,
        regularPrice, salePrice, categoryName, highResImage, and derives isOnSale.
        """

        regular_price = float(raw.get("regularPrice", 0.0))
        sale_price = float(raw.get("salePrice", raw.get("regularPrice", 0.0)))
        is_on_sale = sale_price != regular_price

        # Prefix productUrl with BestBuy base URL if it's a relative path
        product_url = raw.get("productUrl", "")
        if product_url and not product_url.startswith("http"):
            product_url = f"{BESTBUY_URL_PREFIX}{product_url}"

        return {
            "sku": str(raw.get("sku", "")),
            "name": raw.get("name", ""),
            "shortDescription": raw.get("shortDescription", ""),
            "customerRating": raw.get("customerRating"),
            "productUrl": product_url,
            "regularPrice": regular_price,
            "salePrice": sale_price,
            "categoryName": raw.get("categoryName", ""),
            "isOnSale": is_on_sale,
            "highResImage": raw.get("highResImage") or None,
        }

    @staticmethod
    def load_directory(directory_path: str | Path) -> list[dict[str, Any]]:
        """Load all JSON files from a directory."""
        directory_path = Path(directory_path)

        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")

        all_data: list[dict[str, Any]] = []
        json_files = list(directory_path.glob("*.json"))

        if not json_files:
            logger.warning("No JSON files found in %s", directory_path)
            return all_data

        for json_file in json_files:
            try:
                data = DataLoader.load_json_file(json_file)
                all_data.extend(data)
            except Exception as e:
                logger.error("Skipping file %s: %s", json_file, e)
                continue

        logger.info("Loaded %d total records from %d files", len(all_data), len(json_files))
        return all_data

    @staticmethod
    def validate_and_parse_products(data: list[dict[str, Any]]) -> list[ProductBase]:
        """Validate and parse raw BestBuy data into ProductBase models."""
        products: list[ProductBase] = []
        errors: list[str] = []

        for idx, item in enumerate(data):
            try:
                transformed = DataLoader.transform_bestbuy_product(item)
                product = ProductBase(**transformed)
                products.append(product)
            except Exception as e:
                errors.append(f"Record {idx}: {e}")
                logger.warning("Invalid product data at index %d: %s", idx, e)

        if errors:
            logger.warning("Failed to parse %d out of %d records", len(errors), len(data))

        logger.info("Successfully validated %d products", len(products))
        return products

    @staticmethod
    def extract_unique_categories(products: list[ProductBase]) -> list[str]:
        """Extract sorted list of unique categoryName values from products."""
        categories = sorted({p.categoryName for p in products if p.categoryName})
        logger.info("Found %d unique categories", len(categories))
        return categories

    @staticmethod
    async def load_products_from_directory(directory_path: str | Path) -> list[ProductBase]:
        """Load and validate products from directory."""
        raw_data = DataLoader.load_directory(directory_path)
        return DataLoader.validate_and_parse_products(raw_data)

    @staticmethod
    async def load_products_from_file(file_path: str | Path) -> list[ProductBase]:
        """Load and validate products from a single file."""
        raw_data = DataLoader.load_json_file(file_path)
        return DataLoader.validate_and_parse_products(raw_data)
