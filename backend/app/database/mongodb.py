"""MongoDB database connection and operations."""

import logging
from datetime import UTC, datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from app.config import get_settings
from app.models.user import UserCreate, UserInDB, UserUpdate

logger = logging.getLogger(__name__)
settings = get_settings()


class MongoDB:
    """MongoDB connection manager."""

    def __init__(self) -> None:
        """Initialize MongoDB connection."""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size,
            )
            self.db = self.client[settings.mongodb_database]

            # Test connection
            await self.client.admin.command("ping")
            logger.info("Connected to MongoDB: %s", settings.mongodb_database)

            # Create indexes
            await self._create_indexes()

        except ConnectionFailure as e:
            logger.error("Failed to connect to MongoDB: %s", e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def _create_indexes(self) -> None:
        """Create database indexes."""
        if self.db is not None:
            # Unique index on userId
            await self.db[settings.mongodb_user_collection].create_index(
                "userId", unique=True, name="userId_unique"
            )
            # Index on email
            await self.db[settings.mongodb_user_collection].create_index(
                "email", name="email_index"
            )
            logger.info("MongoDB indexes created")

    async def create_user(self, user: UserCreate) -> UserInDB:
        """Create a new user."""
        if self.db is None:
            raise ConnectionError("Database not connected")

        try:
            user_data = user.model_dump()
            user_data["createdAt"] = datetime.now(UTC)
            user_data["updatedAt"] = datetime.now(UTC)

            result = await self.db[settings.mongodb_user_collection].insert_one(user_data)

            if result.inserted_id:
                created_user = await self.get_user(user.userId)
                if created_user:
                    return created_user

            raise ValueError("Failed to create user")

        except DuplicateKeyError:
            raise ValueError(f"User with userId '{user.userId}' already exists")

    async def get_user(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID."""
        if self.db is None:
            raise ConnectionError("Database not connected")

        user_data = await self.db[settings.mongodb_user_collection].find_one(
            {"userId": user_id}, {"_id": 0}
        )

        if user_data:
            return UserInDB(**user_data)
        return None

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email."""
        if self.db is None:
            raise ConnectionError("Database not connected")

        user_data = await self.db[settings.mongodb_user_collection].find_one(
            {"email": email}, {"_id": 0}
        )

        if user_data:
            return UserInDB(**user_data)
        return None

    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """Update user information."""
        if not self.db:
            raise ConnectionError("Database not connected")

        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_user(user_id)

        update_data["updatedAt"] = datetime.now(UTC)

        result = await self.db[settings.mongodb_user_collection].update_one(
            {"userId": user_id}, {"$set": update_data}
        )

        if result.modified_count:
            return await self.get_user(user_id)
        return None

    async def delete_user(self, user_id: str) -> bool:
        """Delete user by ID."""
        if not self.db:
            raise ConnectionError("Database not connected")

        result = await self.db[settings.mongodb_user_collection].delete_one({"userId": user_id})
        return result.deleted_count > 0

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[UserInDB]:
        """List all users with pagination."""
        if not self.db:
            raise ConnectionError("Database not connected")

        cursor = self.db[settings.mongodb_user_collection].find({}, {"_id": 0}).skip(skip).limit(
            limit
        )
        users = await cursor.to_list(length=limit)
        return [UserInDB(**user) for user in users]


# Global MongoDB instance
mongodb = MongoDB()
