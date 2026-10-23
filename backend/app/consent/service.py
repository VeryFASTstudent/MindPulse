from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.consent.schemas import ConsentUpdate


async def read_student_consent(db: AsyncIOMotorDatabase, student_id: ObjectId) -> dict:
    now = datetime.now(timezone.utc)
    await db.consents.update_one(
        {"student_id": student_id},
        {
            "$setOnInsert": {
                "student_id": student_id,
                "share_summary_with_parent": False,
                "share_with_university_support": False,
                "allow_referral_data_share": False,
                "parent_phone": None,
                "parent_name": None,
                "reviewed_at": None,
                "updated_at": now,
            }
        },
        upsert=True,
    )
    return await db.consents.find_one({"student_id": student_id})


async def update_student_consent(
    db: AsyncIOMotorDatabase, student_id: ObjectId, data: ConsentUpdate
) -> dict:
    student = await db.users.find_one({"_id": student_id}, {"is_fast_student": 1})
    if data.share_with_university_support and not (student or {}).get("is_fast_student", False):
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError(detail="Only FAST students can enable university psychologist alerts")
    if data.share_summary_with_parent and not data.parent_phone:
        from app.core.exceptions import ValidationFailedError
        raise ValidationFailedError(detail="Parent phone is required for parent alerts")
    values = data.model_dump()
    values["reviewed_at"] = values.get("reviewed_at") or datetime.now(timezone.utc)
    await db.consents.update_one(
        {"student_id": student_id},
        {"$set": {**values, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return await db.consents.find_one({"student_id": student_id})