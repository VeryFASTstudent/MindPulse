from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.escalations.service import list_parent_escalations

ADMIN_MINIMUM_COHORT_SIZE = 5
ADMIN_OVERVIEW_DAYS = 7


def _utc_midnight() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day)


async def get_parent_summaries(
    db: AsyncIOMotorDatabase, parent: dict[str, Any]
) -> list[dict[str, Any]]:
    linked_ids = parent.get("linked_student_ids", [])
    if not linked_ids:
        return []

    students_cursor = db.users.find(
        {"_id": {"$in": linked_ids}, "role": "student", "is_active": True},
        {"full_name": 1},
    ).sort("full_name", 1)
    students = await students_cursor.to_list(length=100)
    if not students:
        return []

    student_ids = [student["_id"] for student in students]
    consent_cursor = db.consents.find(
        {
            "student_id": {"$in": student_ids},
            "share_summary_with_parent": True,
        },
        {"student_id": 1},
    )
    consented_ids = {doc["student_id"] async for doc in consent_cursor}
    since = _utc_midnight() - timedelta(days=6)
    summaries = []

    for student in students:
        student_id = student["_id"]
        if student_id not in consented_ids:
            continue

        checkins = await db.behavioral_signals.find(
            {
                "student_id": student_id,
                "checkin_completed": True,
                "date": {"$gte": since},
            },
            {"date": 1, "self_rated_stress": 1, "sleep_hours": 1},
        ).sort("date", -1).to_list(length=7)
        risk = await db.risk_scores.find_one(
            {"student_id": student_id},
            {"risk_level": 1, "date": 1},
            sort=[("date", -1)],
        )

        summaries.append(
            {
                "student_id": student_id,
                "full_name": student["full_name"],
                "last_checkin_at": checkins[0]["date"] if checkins else None,
                "average_stress": (
                    round(
                        sum(item["self_rated_stress"] for item in checkins)
                        / len(checkins),
                        1,
                    )
                    if checkins
                    else None
                ),
                "average_sleep_hours": (
                    round(
                        sum(item["sleep_hours"] for item in checkins) / len(checkins),
                        1,
                    )
                    if checkins
                    else None
                ),
                "latest_wellbeing_status": risk.get("risk_level") if risk else None,
                "escalations": await list_parent_escalations(
                    db, parent["_id"], student_id
                ),
            }
        )
    return summaries


async def get_admin_overview(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    since = _utc_midnight() - timedelta(days=ADMIN_OVERVIEW_DAYS - 1)
    consent_cursor = db.consents.find(
        {"share_with_university_support": True},
        {"student_id": 1},
    )
    consented_student_ids = [doc["student_id"] async for doc in consent_cursor]
    if not consented_student_ids:
        return _suppressed_overview(
            "No students have opted in to aggregate university support reporting."
        )

    score_cursor = db.risk_scores.find(
        {
            "student_id": {"$in": consented_student_ids},
            "date": {"$gte": since},
        },
        {"student_id": 1, "date": 1, "risk_level": 1},
    ).sort("date", -1)
    latest_by_student: dict[Any, str] = {}
    async for score in score_cursor:
        latest_by_student.setdefault(score["student_id"], score["risk_level"])

    if len(latest_by_student) < ADMIN_MINIMUM_COHORT_SIZE:
        return _suppressed_overview(
            "Aggregate results are hidden until at least five opted-in students have recent data."
        )

    distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for level in latest_by_student.values():
        if level in distribution:
            distribution[level] += 1

    return {
        "available": True,
        "suppressed": False,
        "period_days": ADMIN_OVERVIEW_DAYS,
        "cohort_size": len(latest_by_student),
        "risk_distribution": distribution,
        "message": "Aggregate well-being indicators for opted-in students only.",
    }


def _suppressed_overview(message: str) -> dict[str, Any]:
    return {
        "available": False,
        "suppressed": True,
        "period_days": ADMIN_OVERVIEW_DAYS,
        "cohort_size": None,
        "risk_distribution": {},
        "message": message,
    }
