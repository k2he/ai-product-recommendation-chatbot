"""Utility helper functions."""

import hashlib
import uuid
from datetime import datetime
from typing import Any


def generate_uuid() -> str:
    """Generate a unique UUID."""
    return str(uuid.uuid4())


def generate_hash(text: str) -> str:
    """Generate SHA256 hash of text."""
    return hashlib.sha256(text.encode()).hexdigest()


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat()


def safe_dict_get(d: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary."""
    try:
        return d.get(key, default)
    except (AttributeError, KeyError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
