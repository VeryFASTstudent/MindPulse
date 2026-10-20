from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationFailedError
from app.referral.schemas import ReferralStatus

COUNSELOR_STATUSES = {
    ReferralStatus.accepted.value,
    ReferralStatus.declined.value,
    ReferralStatus.completed.value,
}
ALLOWED_TRANSITIONS = {
    ReferralStatus.requested.value: {
        ReferralStatus.accepted.value,
        ReferralStatus.declined.value,
    },
    ReferralStatus.accepted.value: {ReferralStatus.completed.value},
}


async def list_counselors(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    cursor = db.counselors.find(
        {"is_active": True},
        {
            "user_id": 1,
            "full_name": 1,
            "specialization": 1,
            "contact_email": 1,
            "availability": 1,
        },
    ).sort("full_name", 1)
    profiles = await cursor.to_list(length=100)
    user_ids = [profile["user_id"] for profile in profiles if profile.get("user_id")]
    if not user_ids:
        return []

    active_counselors = db.users.find(
        {
            "_id": {"$in": user_ids},
            "role": "counselor",
            "is_active": True,
        },
        {"_id": 1},
    )
    valid_user_ids = {user["_id"] async for user in active_counselors}
    return [profile for profile in profiles if profile.get("user_id") in valid_user_ids]


async def list_external_support_resources(
    db: AsyncIOMotorDatabase,
) -> list[dict[str, Any]]:
    cursor = db.external_support_resources.find(
        {"is_active": True},
        {
            "name": 1,
            "specialization": 1,
            "contact_email": 1,
            "website_url": 1,
            "cost_description": 1,
            "is_active": 1,
        },
    ).sort("name", 1)
    return await cursor.to_list(length=100)


async def create_referral_request(
    db: AsyncIOMotorDatabase,
    student: dict[str, Any],
    counselor_id: ObjectId,
    student_confirmed: bool,
) -> dict[str, Any]:
    if not student_confirmed:
        raise ValidationFailedError(detail="Confirm that you want to send this support request")

    counselor = await db.counselors.find_one({"_id": counselor_id, "is_active": True})
    if counselor is None:
        raise NotFoundError(detail="Counselor not found or unavailable")

    counselor_user = await db.users.find_one(
        {
            "_id": counselor.get("user_id"),
            "role": "counselor",
            "is_active": True,
        }
    )
    if counselor_user is None:
        raise NotFoundError(detail="Counselor not found or unavailable")

    consent = await db.consents.find_one({"student_id": student["_id"]})
    if consent is None or not consent.get("allow_referral_data_share", False):
        raise ForbiddenError(
            detail="Enable referral data sharing in Privacy settings before sending a request"
        )

    now = datetime.now(timezone.utc)
    request = {
        "student_id": student["_id"],
        "counselor_id": counselor["user_id"],
        "counselor_profile_id": counselor["_id"],
        "status": ReferralStatus.requested.value,
        "requested_at": now,
        "updated_at": now,
        "student_consent_confirmed": True,
    }
    result = await db.appointments.insert_one(request)
    request["_id"] = result.inserted_id
    return request


async def list_student_requests(
    db: AsyncIOMotorDatabase, student_id: ObjectId
) -> list[dict[str, Any]]:
    cursor = db.appointments.find({"student_id": student_id}).sort("requested_at", -1)
    return await cursor.to_list(length=100)


async def list_counselor_requests(
    db: AsyncIOMotorDatabase, counselor_id: ObjectId
) -> list[dict[str, Any]]:
    cursor = db.appointments.find(
        {
            "counselor_id": counselor_id,
            "status": {"$in": [status.value for status in ReferralStatus]},
        }
    ).sort("requested_at", 1)
    requests = await cursor.to_list(length=100)
    if not requests:
        return []

    student_ids = list({request["student_id"] for request in requests})
    consents = db.consents.find(
        {
            "student_id": {"$in": student_ids},
            "allow_referral_data_share": True,
        },
        {"student_id": 1},
    )
    allowed_students = {consent["student_id"] async for consent in consents}
    visible_requests = [
        request for request in requests if request["student_id"] in allowed_students
    ]
    if not visible_requests:
        return []

    users = db.users.find(
        {"_id": {"$in": list(allowed_students)}},
        {"full_name": 1},
    )
    names_by_id = {user["_id"]: user["full_name"] async for user in users}
    for request in visible_requests:
        request["student_name"] = names_by_id.get(request["student_id"])
    return visible_requests


async def update_counselor_request(
    db: AsyncIOMotorDatabase,
    counselor_id: ObjectId,
    request_id: ObjectId,
    status: ReferralStatus,
) -> dict[str, Any]:
    if status.value not in COUNSELOR_STATUSES:
        raise ValidationFailedError(detail="Counselors can only update request status")

    request = await db.appointments.find_one(
        {"_id": request_id, "counselor_id": counselor_id}
    )
    if request is None:
        raise NotFoundError(detail="Referral request not found")
    if status.value not in ALLOWED_TRANSITIONS.get(request["status"], set()):
        raise ValidationFailedError(
            detail=f"Cannot change a request from {request['status']} to {status.value}"
        )

    consent = await db.consents.find_one(
        {"student_id": request["student_id"], "allow_referral_data_share": True}
    )
    if consent is None:
        raise ForbiddenError(detail="The student has withdrawn referral data sharing")

    now = datetime.now(timezone.utc)
    await db.appointments.update_one(
        {"_id": request_id, "counselor_id": counselor_id},
        {"$set": {"status": status.value, "updated_at": now}},
    )
    request["status"] = status.value
    request["updated_at"] = now
    return request
