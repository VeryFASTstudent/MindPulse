"""Create a parent, counselor, or admin account through a trusted operator flow."""

import asyncio
from datetime import datetime, timezone
from getpass import getpass

from bson import ObjectId
from pydantic import EmailStr, TypeAdapter

from app.auth.security import hash_password
from app.core.exceptions import ValidationFailedError
from app.db.indexes import create_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database

VALID_ROLES = {"parent", "counselor", "admin"}


def _prompt_email(prompt: str) -> str:
    value = input(prompt).strip().lower()
    return str(TypeAdapter(EmailStr).validate_python(value))


async def provision() -> None:
    role = input("Account role (parent/counselor/admin): ").strip().lower()
    if role not in VALID_ROLES:
        raise ValueError("Choose parent, counselor, or admin.")

    full_name = input("Full name: ").strip()
    if not full_name:
        raise ValueError("Full name is required.")

    email = _prompt_email("Email: ")
    password = getpass("Temporary password (minimum 8 characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if password != confirmation:
        raise ValueError("Passwords do not match.")

    linked_student_id = None
    counselor_profile = {}
    if role == "parent":
        student_email = _prompt_email("Existing student email to link: ")
    elif role == "counselor":
        counselor_profile = {
            "specialization": input("Specialization: ").strip(),
            "availability": input("Availability: ").strip(),
        }

    await connect_to_mongo()
    db = get_database()
    try:
        await create_indexes(db)
        if await db.users.find_one({"email": email}):
            raise ValidationFailedError(
                detail="An account with this email already exists"
            )

        if role == "parent":
            student = await db.users.find_one(
                {"email": student_email, "role": "student", "is_active": True},
                {"_id": 1},
            )
            if student is None:
                raise ValidationFailedError(
                    detail="No active student account matches that email"
                )
            linked_student_id = student["_id"]

        user_id = ObjectId()
        user = {
            "_id": user_id,
            "role": role,
            "email": email,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "linked_student_ids": (
                [linked_student_id] if linked_student_id is not None else []
            ),
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
        }
        await db.users.insert_one(user)

        if role == "counselor":
            try:
                await db.counselors.insert_one(
                    {
                        "user_id": user_id,
                        "full_name": full_name,
                        "specialization": counselor_profile["specialization"],
                        "contact_email": email,
                        "availability": counselor_profile["availability"],
                        "is_active": True,
                    }
                )
            except Exception:
                await db.users.delete_one({"_id": user_id})
                raise

        print(f"Created {role} account for {full_name} ({email}).")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    try:
        asyncio.run(provision())
    except (ValueError, ValidationFailedError) as error:
        message = getattr(error, "detail", str(error))
        raise SystemExit(message) from error
