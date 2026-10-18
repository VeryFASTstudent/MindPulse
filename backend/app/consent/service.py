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
                "updated_at": now,
            }
        },
        upsert=True,
    )
    return await db.consents.find_one({"student_id": student_id})


async def update_student_consent(
    db: AsyncIOMotorDatabase, student_id: ObjectId, data: ConsentUpdate
) -> dict:
    await db.consents.update_one(
        {"student_id": student_id},
        {"$set": {**data.model_dump(), "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return await db.consents.find_one({"student_id": student_id})