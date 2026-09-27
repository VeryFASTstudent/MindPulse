"""
Auth routes.

    POST /auth/register   -- create a new user (+ student_profile if role=student)
    POST /auth/login       -- exchange email+password for access+refresh tokens
    POST /auth/refresh     -- exchange a valid refresh token for a new access token
    GET  /auth/me          -- return the currently authenticated user
"""

from bson import ObjectId
from fastapi import APIRouter, Depends
from jose import JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.auth.schemas import RefreshRequest, Token, UserLogin, UserOut, UserRegister
from app.auth.security import create_access_token, create_refresh_token, decode_token
from app.auth.service import authenticate_user, register_user
from app.core.exceptions import UnauthorizedError
from app.db.mongodb import get_database

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: UserRegister, db: AsyncIOMotorDatabase = Depends(get_database)):
    user = await register_user(db, data)
    return user


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncIOMotorDatabase = Depends(get_database)):
    user = await authenticate_user(db, data.email, data.password)
    user_id = str(user["_id"])
    return Token(
        access_token=create_access_token(user_id, user["role"]),
        refresh_token=create_refresh_token(user_id, user["role"]),
    )


@router.post("/refresh", response_model=Token)
async def refresh(data: RefreshRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        payload = decode_token(data.refresh_token)
    except JWTError:
        raise UnauthorizedError(detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError(detail="A valid refresh token is required")

    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if user is None or not user.get("is_active", True):
        raise UnauthorizedError(detail="User not found or inactive")

    user_id = str(user["_id"])
    return Token(
        access_token=create_access_token(user_id, user["role"]),
        refresh_token=create_refresh_token(user_id, user["role"]),
    )


@router.get("/me", response_model=UserOut)
async def read_current_user(user: dict = Depends(get_current_user)):
    return user
