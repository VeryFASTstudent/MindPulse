"""
Behavioral data collection (Section 6 of the blueprint).

One behavioral_signals document per student per calendar day (UTC). A
student can submit/update today's check-in as many times as they want --
it's an upsert keyed on (student_id, date-at-midnight) -- but there's only
ever one row per day, which is what the baseline/risk engine (Phase 7/8)
will read from.

chat_messages_count and avg_response_delay_sec (also part of
behavioral_signals per the DB design) are populated by the sentiment/signal
extraction pipeline in Phase 6, not here -- this module only owns the
self-reported fields.
"""

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.behavior.schemas import CheckinRequest

# Streak calculation walks backwards day by day from today; capping the
# lookback keeps the query bounded instead of scanning a student's entire
# history every time the dashboard loads.
MAX_STREAK_LOOKBACK_DAYS = 60


def _today_utc_midnight() -> datetime:
    """
    Returns a naive UTC datetime (no tzinfo attached) at midnight today.

    Naive on purpose: PyMongo/Motor round-trips datetimes as naive UTC by
    default, so a tz-aware value written here would come back naive on
    read and silently fail equality/set-membership checks against a
    freshly-constructed aware value (Python doesn't raise on aware vs.
    naive `==`, it just returns False). Keeping everything naive-but-UTC
    throughout this module avoids that trap entirely.
    """
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day)


async def submit_checkin(
    db: AsyncIOMotorDatabase,
    student_id: ObjectId,
    data: CheckinRequest,
    as_of: datetime | None = None,
) -> dict:
    today = (
        datetime(as_of.year, as_of.month, as_of.day)
        if as_of is not None
        else _today_utc_midnight()
    )
    await db.behavioral_signals.update_one(
        {"student_id": student_id, "date": today},
        {
            "$set": {
                "self_rated_stress": data.self_rated_stress,
                "workload": data.workload,
                "sleep_hours": data.sleep_hours,
                "activity_score": data.activity_score,
                "checkin_completed": True,
            },
            "$setOnInsert": {"student_id": student_id, "date": today},
        },
        upsert=True,
    )
    return await db.behavioral_signals.find_one({"student_id": student_id, "date": today})


async def get_today_checkin(db: AsyncIOMotorDatabase, student_id: ObjectId) -> dict | None:
    today = _today_utc_midnight()
    # Since Phase 6 the chat pipeline can create today's row before the
    # student checks in, so only a row with checkin_completed counts here.
    return await db.behavioral_signals.find_one(
        {"student_id": student_id, "date": today, "checkin_completed": True}
    )


async def get_history(db: AsyncIOMotorDatabase, student_id: ObjectId, days: int = 7) -> list[dict]:
    since = _today_utc_midnight() - timedelta(days=days - 1)
    cursor = db.behavioral_signals.find(
        {"student_id": student_id, "date": {"$gte": since}, "checkin_completed": True}
    ).sort("date", 1)
    return await cursor.to_list(length=days)


async def get_checkin_streak(db: AsyncIOMotorDatabase, student_id: ObjectId) -> int:
    """
    Counts consecutive completed check-in days ending today. Missing even
    one day (including today, if not yet checked in) breaks the streak --
    intentionally simple and easy to explain to a student, unlike the
    more forgiving trend logic used inside the risk engine itself.
    """
    today = _today_utc_midnight()
    since = today - timedelta(days=MAX_STREAK_LOOKBACK_DAYS)

    cursor = db.behavioral_signals.find(
        {"student_id": student_id, "date": {"$gte": since}, "checkin_completed": True},
        {"date": 1},
    )
    completed_dates = {doc["date"] async for doc in cursor}

    streak = 0
    cursor_date = today
    while cursor_date in completed_dates:
        streak += 1
        cursor_date -= timedelta(days=1)
    return streak
