"""User service for business logic."""

import logging
from typing import Optional

from app.database.mongodb import mongodb
from app.models.user import UserInDB

logger = logging.getLogger(__name__)


class UserService:
    """User service for handling user-related operations."""

    @staticmethod
    async def create_user(user: UserInDB) -> UserInDB:
        """Create a new user."""
        try:
            return await mongodb.create_user(user)
        except ValueError as e:
            logger.error("Error creating user: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error creating user: %s", e)
            raise

    @staticmethod
    async def get_user(user_id: str) -> Optional[UserInDB]:
        """Get user by ID."""
        try:
            return await mongodb.get_user(user_id)
        except Exception as e:
            logger.error("Error getting user %s: %s", user_id, e)
            return None

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[UserInDB]:
        """Get user by email."""
        try:
            return await mongodb.get_user_by_email(email)
        except Exception as e:
            logger.error("Error getting user by email %s: %s", email, e)
            return None

    @staticmethod
    async def update_user(user_id: str, user_update: UserInDB) -> Optional[UserInDB]:
        """Update user information."""
        try:
            return await mongodb.update_user(user_id, user_update)
        except Exception as e:
            logger.error("Error updating user %s: %s", user_id, e)
            return None

    @staticmethod
    async def delete_user(user_id: str) -> bool:
        """Delete user."""
        try:
            return await mongodb.delete_user(user_id)
        except Exception as e:
            logger.error("Error deleting user %s: %s", user_id, e)
            return False

    @staticmethod
    async def list_users(skip: int = 0, limit: int = 100) -> list[UserInDB]:
        """List all users with pagination."""
        try:
            return await mongodb.list_users(skip, limit)
        except Exception as e:
            logger.error("Error listing users: %s", e)
            return []


# Global user service instance
user_service = UserService()
