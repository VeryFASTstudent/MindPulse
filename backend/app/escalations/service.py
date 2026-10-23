from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationFailedError
from app.escalations.schemas import EscalationStatus
from app.core.config import settings

ESCALATION_SUMMARY = (
    "A sustained high well-being pattern has been observed. Please follow up "
    "through the approved support process. No chat content or raw scores are shared."
)
_TEMPLATE_PATH = Path(__file__).with_name("message_templates.json")
with _TEMPLATE_PATH.open(encoding="utf-8") as template_file:
    MESSAGE_TEMPLATES = json.load(template_file)
ALLOWED_STATUS_TRANSITIONS = {
    EscalationStatus.new.value: {EscalationStatus.acknowledged.value},
    EscalationStatus.acknowledged.value: {EscalationStatus.closed.value},
}


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day)


async def create_sustained_escalations(
    db: AsyncIOMotorDatabase,
    student_id: ObjectId,
    trigger_date: date,
    consecutive_days: int,
) -> bool:
    consent = await db.consents.find_one({"student_id": student_id})
    if consent is None:
        return False

    if settings.delivery_mode != "outbox_only":
        raise RuntimeError("External alert delivery is disabled unless DELIVERY_MODE=outbox_only")

    student = await db.users.find_one({"_id": student_id}, {"full_name": 1, "email": 1})
    student = student or {"full_name": "Student", "email": ""}

    recipients: list[tuple[str, ObjectId]] = []
    if consent.get("share_with_university_support", False):
        counselors = db.users.find(
            {"role": "counselor", "is_active": True},
            {"_id": 1},
        )
        async for counselor in counselors:
            recipients.append(("counselor", counselor["_id"]))
    if consent.get("share_summary_with_parent", False):
        parents = db.users.find(
            {
                "role": "parent",
                "is_active": True,
                "linked_student_ids": student_id,
            },
            {"_id": 1},
        )
        async for parent in parents:
            recipients.append(("parent", parent["_id"]))

    if not recipients:
        return False

    now = datetime.now(timezone.utc)
    trigger_at = _midnight(trigger_date)
    has_notifications = False
    for recipient_role, recipient_id in recipients:
        event = {
            "student_id": student_id,
            "recipient_id": recipient_id,
            "recipient_role": recipient_role,
            "risk_level": "HIGH",
            "consecutive_days": consecutive_days,
            "summary": ESCALATION_SUMMARY,
            "status": EscalationStatus.new.value,
            "trigger_date": trigger_at,
            "created_at": now,
            "updated_at": now,
        }
        query = {
            "student_id": student_id,
            "recipient_id": recipient_id,
            "trigger_date": trigger_at,
        }
        try:
            result = await db.escalation_events.update_one(
                query,
                {"$setOnInsert": event},
                upsert=True,
            )
        except DuplicateKeyError:
            has_notifications = True
            continue
        if result.upserted_id is None:
            has_notifications = True
            continue

        has_notifications = True
        delivery_collection = getattr(db, "alert_deliveries", None)
        if recipient_role == "counselor":
            delivery = {
                "alert_id": result.upserted_id,
                "student_id": student_id,
                "channel": "email",
                "recipient": settings.university_psychologist_email,
                "message_text": MESSAGE_TEMPLATES["psychologist"].format(
                    student_name=student.get("full_name", "Student"),
                    email=student.get("email", ""),
                    days=consecutive_days,
                ),
                "status": "queued",
                "created_at": now,
            }
            if delivery_collection is not None:
                await delivery_collection.update_one(
                    {"alert_id": result.upserted_id, "channel": "email"},
                    {"$setOnInsert": delivery},
                    upsert=True,
                )
        elif recipient_role == "parent" and consent.get("parent_phone"):
            delivery = {
                "alert_id": result.upserted_id,
                "student_id": student_id,
                "channel": "whatsapp",
                "recipient": consent["parent_phone"],
                "message_text": MESSAGE_TEMPLATES["parent"].format(
                    first_name=student.get("full_name", "Student").split()[0]
                ),
                "status": "queued",
                "created_at": now,
            }
            if delivery_collection is not None:
                await delivery_collection.update_one(
                    {"alert_id": result.upserted_id, "channel": "whatsapp"},
                    {"$setOnInsert": delivery},
                    upsert=True,
                )
        await db.audit_logs.insert_one(
            {
                "actor_type": "system",
                "action": "sustained_risk_escalation_created",
                "student_id": student_id,
                "recipient_id": recipient_id,
                "recipient_role": recipient_role,
                "event_id": result.upserted_id,
                "created_at": now,
            }
        )
    return has_notifications


async def list_parent_escalations(
    db: AsyncIOMotorDatabase, parent_id: ObjectId, student_id: ObjectId
) -> list[dict[str, Any]]:
    consent = await db.consents.find_one(
        {"student_id": student_id, "share_summary_with_parent": True}
    )
    if consent is None:
        return []

    cursor = db.escalation_events.find(
        {
            "student_id": student_id,
            "recipient_id": parent_id,
            "recipient_role": "parent",
        }
    ).sort("trigger_date", -1)
    return await cursor.to_list(length=20)


async def list_counselor_escalations(
    db: AsyncIOMotorDatabase, counselor_id: ObjectId
) -> list[dict[str, Any]]:
    cursor = db.escalation_events.find(
        {
            "recipient_id": counselor_id,
            "recipient_role": "counselor",
        }
    ).sort("trigger_date", -1)
    events = await cursor.to_list(length=100)
    if not events:
        return []

    student_ids = list({event["student_id"] for event in events})
    consents = db.consents.find(
        {
            "student_id": {"$in": student_ids},
            "share_with_university_support": True,
        },
        {"student_id": 1},
    )
    consented_ids = {consent["student_id"] async for consent in consents}
    visible_events = [event for event in events if event["student_id"] in consented_ids]
    if not visible_events:
        return []

    users = db.users.find(
        {
            "_id": {"$in": [event["student_id"] for event in visible_events]},
            "role": "student",
            "is_active": True,
        },
        {"full_name": 1},
    )
    names_by_id = {user["_id"]: user["full_name"] async for user in users}
    for event in visible_events:
        event["student_name"] = names_by_id.get(event["student_id"])
    return [event for event in visible_events if event.get("student_name")]


async def update_counselor_escalation(
    db: AsyncIOMotorDatabase,
    counselor_id: ObjectId,
    event_id: ObjectId,
    new_status: EscalationStatus,
) -> dict[str, Any]:
    event = await db.escalation_events.find_one(
        {
            "_id": event_id,
            "recipient_id": counselor_id,
            "recipient_role": "counselor",
        }
    )
    if event is None:
        raise NotFoundError(detail="Escalation notice not found")

    consent = await db.consents.find_one(
        {
            "student_id": event["student_id"],
            "share_with_university_support": True,
        }
    )
    if consent is None:
        raise ForbiddenError(detail="The student has withdrawn university sharing")

    if new_status.value not in ALLOWED_STATUS_TRANSITIONS.get(event["status"], set()):
        raise ValidationFailedError(
            detail=f"Cannot change an escalation from {event['status']} to {new_status.value}"
        )

    now = datetime.now(timezone.utc)
    await db.escalation_events.update_one(
        {"_id": event_id, "recipient_id": counselor_id},
        {"$set": {"status": new_status.value, "updated_at": now}},
    )
    await db.audit_logs.insert_one(
        {
            "actor_type": "counselor",
            "actor_id": counselor_id,
            "action": "sustained_risk_escalation_status_updated",
            "student_id": event["student_id"],
            "event_id": event_id,
            "status": new_status.value,
            "created_at": now,
        }
    )
    event["status"] = new_status.value
    event["updated_at"] = now
    return event
