"""Database initialization script.

Creates MongoDB indexes and seeds sample users for development.
"""

import asyncio
import logging

from app.database.mongodb import mongodb
from app.models.user import UserInDB
from app.services.user_service import user_service
from app.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def init_databases() -> None:
    """Initialize databases and create sample users."""
    try:
        logger.info("Initializing databases...")

        await mongodb.connect()
        logger.info("Database connected successfully")

        # Create sample users
        sample_users = [
            UserInDB(
                userId="user_001",
                firstName="Kai",
                lastName="He",
                email="kai.he@example.com",
                phone="+1234567890",
            ),
            UserInDB(
                userId="user_002",
                firstName="Jane",
                lastName="Smith",
                email="jane.smith@example.com",
                phone="+1234567891",
            ),
            UserInDB(
                userId="user_003",
                firstName="Bob",
                lastName="Johnson",
                email="bob.johnson@example.com",
                phone="+1234567892",
            ),
        ]

        for user in sample_users:
            try:
                await user_service.create_user(user)
                logger.info("Created user: %s", user.userId)
            except ValueError as e:
                logger.warning("User %s already exists: %s", user.userId, e)

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error("Error initializing databases: %s", e)
        raise

    finally:
        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(init_databases())
