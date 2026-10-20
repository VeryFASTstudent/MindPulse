"""
Auth business logic: registration and login.

Registration also creates a `student_profiles` document when the role is
"student", matching the blueprint's collection relationship
(student_profiles.user_id -> users._id). Other roles don't get a profile
document in Phase 2 -- parent/counselor/admin-specific fields are added
alongside their respective dashboards in later phases.
"""

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.schemas import UserRegister, UserRole
from app.auth.security import hash_password, verify_password
from app.core.exceptions import ForbiddenError, UnauthorizedError, ValidationFailedError


async def register_user(db: AsyncIOMotorDatabase, data: UserRegister) -> dict:
    if data.role is not UserRole.student:
        raise ForbiddenError(detail="Only student self-registration is permitted")

    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise ValidationFailedError(detail="An account with this email already exists")

    user_doc = {
        "role": data.role.value,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "full_name": data.full_name,
        "linked_student_ids": [],
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    if data.role.value == "student":
        await db.student_profiles.insert_one({
            "user_id": result.inserted_id,
            "university_id": data.university_id,
            "program": data.program,
            "semester": data.semester,
            "created_at": datetime.now(timezone.utc),
        })

    return user_doc


async def authenticate_user(db: AsyncIOMotorDatabase, email: str, password: str) -> dict:
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(password, user["password_hash"]):
        raise UnauthorizedError(detail="Incorrect email or password")
    if not user.get("is_active", True):
        raise UnauthorizedError(detail="This account has been deactivated")
    return user
