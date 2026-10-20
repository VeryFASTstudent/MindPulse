import unittest
from unittest.mock import AsyncMock

from app.auth.schemas import UserRegister, UserRole
from app.auth.service import register_user
from app.core.exceptions import ForbiddenError


class RegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_self_registration_rejects_privileged_roles(self):
        db = _Database()
        request = UserRegister(
            email="counselor@example.edu",
            password="long-enough-password",
            full_name="Unauthorized Counselor",
            role=UserRole.counselor,
        )

        with self.assertRaises(ForbiddenError):
            await register_user(db, request)

        db.users.find_one.assert_not_awaited()
        db.users.insert_one.assert_not_awaited()


class _Users:
    def __init__(self):
        self.find_one = AsyncMock()
        self.insert_one = AsyncMock()


class _Database:
    def __init__(self):
        self.users = _Users()


if __name__ == "__main__":
    unittest.main()
