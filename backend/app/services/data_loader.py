"""Data loader service for importing product data."""

import json
import logging
from pathlib import Path
from typing import Any

from app.models.product import ProductBase

logger = logging.getLogger(__name__)


class DataLoader:
    """Service for loading product data from JSON files."""

    @staticmethod
    def load_json_file(file_path: str | Path) -> list[dict[str, Any]]:
        """Load data from a single JSON file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.suffix.lower() == ".json":
            raise ValueError(f"File must be a JSON file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both single object and array
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("JSON must contain an object or array")

            logger.info(f"Loaded {len(data)} records from {file_path}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise

    @staticmethod
    def load_directory(directory_path: str | Path) -> list[dict[str, Any]]:
        """Load all JSON files from a directory."""
        directory_path = Path(directory_path)

        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")

        all_data = []
        json_files = list(directory_path.glob("*.json"))

        if not json_files:
            logger.warning(f"No JSON files found in {directory_path}")
            return all_data

        for json_file in json_files:
            try:
                data = DataLoader.load_json_file(json_file)
                all_data.extend(data)
            except Exception as e:
                logger.error(f"Skipping file {json_file}: {e}")
                continue

        logger.info(f"Loaded {len(all_data)} total records from {len(json_files)} files")
        return all_data

    @staticmethod
    def validate_and_parse_products(data: list[dict[str, Any]]) -> list[ProductBase]:
        """Validate and parse raw data into Product models."""
        products = []
        errors = []

        for idx, item in enumerate(data):
            try:
                product = ProductBase(**item)
                products.append(product)
            except Exception as e:
                errors.append(f"Record {idx}: {str(e)}")
                logger.warning(f"Invalid product data at index {idx}: {e}")

        if errors:
            logger.warning(f"Failed to parse {len(errors)} out of {len(data)} records")

        logger.info(f"Successfully validated {len(products)} products")
        return products

    @staticmethod
    async def load_products_from_directory(directory_path: str | Path) -> list[ProductBase]:
        """Load and validate products from directory."""
        raw_data = DataLoader.load_directory(directory_path)
        products = DataLoader.validate_and_parse_products(raw_data)
        return products

    @staticmethod
    async def load_products_from_file(file_path: str | Path) -> list[ProductBase]:
        """Load and validate products from a single file."""
        raw_data = DataLoader.load_json_file(file_path)
        products = DataLoader.validate_and_parse_products(raw_data)
        return products
