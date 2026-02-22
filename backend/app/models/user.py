"""User data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user model."""

    userId: str = Field(..., description="Unique user identifier")
    firstName: str = Field(..., min_length=1, max_length=100)
    lastName: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?1?\d{9,15}$")


class UserCreate(UserBase):
    """User creation model."""

    pass


class UserUpdate(BaseModel):
    """User update model."""

    firstName: Optional[str] = Field(None, min_length=1, max_length=100)
    lastName: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?1?\d{9,15}$")


class UserInDB(UserBase):
    """User model as stored in database."""

    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    firstName: str
    lastName: str
    email: EmailStr
    phone: str

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "userId": "user123",
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": "2024-01-01T00:00:00",
            }
        }


class UserResponse(UserBase):
    """User response model."""

    createdAt: datetime
    updatedAt: datetime
