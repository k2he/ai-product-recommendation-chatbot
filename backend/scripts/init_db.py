"""Database initialization script."""

import asyncio
import logging

from app.database.mongodb import mongodb
from app.database.pinecone_db import pinecone_db
from app.models.user import UserCreate
from app.services.user_service import user_service
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


async def init_databases():
    """Initialize databases and create sample users."""
    try:
        logger.info("Initializing databases...")

        # Connect to databases
        await mongodb.connect()
        # await pinecone_db.connect()

        logger.info("Databases connected successfully")

        # Create sample users
        sample_users = [
            UserCreate(
                userId="user_001",
                firstName="Kai",
                lastName="He",
                email="kai.he@example.com",
                phone="+1234567890",
            ),
            UserCreate(
                userId="user_002",
                firstName="Jane",
                lastName="Smith",
                email="jane.smith@example.com",
                phone="+1234567891",
            ),
            UserCreate(
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
                logger.info(f"Created user: {user.userId}")
            except ValueError as e:
                logger.warning(f"User {user.userId} already exists: {e}")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Error initializing databases: {e}")
        raise

    finally:
        await mongodb.disconnect()
        # await pinecone_db.disconnect()


if __name__ == "__main__":
    asyncio.run(init_databases())
