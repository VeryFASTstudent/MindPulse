import unittest
from unittest.mock import AsyncMock

from bson import ObjectId

from app.core.exceptions import ForbiddenError, ValidationFailedError
from app.referral.schemas import ReferralStatus
from app.referral.service import create_referral_request, update_counselor_request


class ReferralWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_requires_explicit_student_confirmation(self):
        db = _Database()

        with self.assertRaises(ValidationFailedError):
            await create_referral_request(
                db,
                {"_id": ObjectId()},
                ObjectId(),
                student_confirmed=False,
            )

        db.counselors.find_one.assert_not_awaited()

    async def test_request_requires_current_referral_consent(self):
        student_id = ObjectId()
        counselor_id = ObjectId()
        db = _Database()
        db.counselors.find_one.return_value = {
            "_id": counselor_id,
            "user_id": ObjectId(),
            "is_active": True,
        }
        db.consents.find_one.return_value = {
            "student_id": student_id,
            "allow_referral_data_share": False,
        }

        with self.assertRaises(ForbiddenError):
            await create_referral_request(
                db,
                {"_id": student_id},
                counselor_id,
                student_confirmed=True,
            )

        db.appointments.insert_one.assert_not_awaited()

    async def test_request_stores_only_student_initiated_minimal_record(self):
        student_id = ObjectId()
        counselor_id = ObjectId()
        counselor_user_id = ObjectId()
        db = _Database()
        db.counselors.find_one.return_value = {
            "_id": counselor_id,
            "user_id": counselor_user_id,
            "is_active": True,
        }
        db.consents.find_one.return_value = {
            "student_id": student_id,
            "allow_referral_data_share": True,
        }
        db.appointments.insert_one.return_value = _InsertResult(ObjectId())

        result = await create_referral_request(
            db,
            {"_id": student_id},
            counselor_id,
            student_confirmed=True,
        )

        saved = db.appointments.insert_one.await_args.args[0]
        self.assertEqual(result["status"], "requested")
        self.assertEqual(saved["student_id"], student_id)
        self.assertEqual(saved["counselor_id"], counselor_user_id)
        self.assertTrue(saved["student_consent_confirmed"])
        self.assertNotIn("message", saved)
        self.assertNotIn("risk_score", saved)

    async def test_counselor_cannot_update_after_consent_is_withdrawn(self):
        student_id = ObjectId()
        request_id = ObjectId()
        counselor_id = ObjectId()
        db = _Database()
        db.appointments.find_one.return_value = {
            "_id": request_id,
            "student_id": student_id,
            "counselor_id": counselor_id,
            "status": "requested",
        }
        db.consents.find_one.return_value = None

        with self.assertRaises(ForbiddenError):
            await update_counselor_request(
                db,
                counselor_id,
                request_id,
                ReferralStatus.accepted,
            )

        db.appointments.update_one.assert_not_awaited()

    async def test_request_status_cannot_skip_or_reverse_workflow(self):
        db = _Database()
        db.appointments.find_one.return_value = {
            "_id": ObjectId(),
            "student_id": ObjectId(),
            "counselor_id": ObjectId(),
            "status": "declined",
        }
        db.consents.find_one.return_value = {"allow_referral_data_share": True}

        with self.assertRaises(ValidationFailedError):
            await update_counselor_request(
                db,
                db.appointments.find_one.return_value["counselor_id"],
                db.appointments.find_one.return_value["_id"],
                ReferralStatus.accepted,
            )

        db.appointments.update_one.assert_not_awaited()


class _InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _Database:
    def __init__(self):
        self.counselors = _Collection()
        self.consents = _Collection()
        self.appointments = _Collection()
        self.users = _Collection()


class _Collection:
    def __init__(self):
        self.find_one = AsyncMock()
        self.insert_one = AsyncMock()
        self.update_one = AsyncMock()


if __name__ == "__main__":
    unittest.main()
