"""
Request/response models for the auth module.

Kept separate from the risk/behavior/chat schemas added in later phases so
each module stays independently readable.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field

from app.core.object_id import PyObjectId


class UserRole(str, Enum):
    student = "student"
    parent = "parent"
    counselor = "counselor"
    admin = "admin"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole
    # Only meaningful when role == student; ignored otherwise.
    university_id: str | None = None
    program: str | None = None
    semester: int | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"populate_by_name": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # user_id
    role: UserRole
    exp: int
    type: str  # "access" | "refresh"


class RefreshRequest(BaseModel):
    refresh_token: str
