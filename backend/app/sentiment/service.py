"""
Signal extraction from chat messages (blueprint Sections 4, 5B, 6).

This is the privacy boundary for chat content. After a student message is
saved, a background job derives NUMERIC signals from it:

  * sentiment_results  -- sentiment score, dominant emotion, confidence
  * behavioral_signals -- chat_messages_count, avg_response_delay_sec

Neither collection stores the message text. Parent / admin / counselor
features (later phases) only ever read these numeric collections, never
the `messages` collection, so private conversations are not exposed.

The job runs AFTER the chat response has been returned (FastAPI
BackgroundTasks), so a slow or failed model never delays or breaks the
chat. Per blueprint Section 19, failures here are logged and skipped:
missing sentiment is treated downstream as missing data, never as a
fabricated value.
"""

import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from ai.sentiment_model import analyze_sentiment
from app.core.config import settings

logger = logging.getLogger(__name__)

# A gap longer than this between the assistant's reply and the student's
# next message is a break in the conversation, not a "response delay", so
# it is excluded from the average (otherwise one overnight gap would swamp
# the signal).
MAX_RESPONSE_DELAY_SEC = 1800


def _naive(dt: datetime) -> datetime:
    # MongoDB round-trips datetimes as naive UTC (see Phase 5 timezone
    # note), so everything here is compared in naive-UTC form.
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _day_of(dt: datetime) -> datetime:
    d = _naive(dt)
    return datetime(d.year, d.month, d.day)


async def _update_chat_signals(db: AsyncIOMotorDatabase, message: dict, created_at: datetime, day: datetime) -> None:
    student_id = message["student_id"]

    # Response delay = time since the previous message in this session, but
    # only if that previous message was the assistant's reply.
    delay = None
    prev = await db.messages.find_one(
        {"session_id": message["session_id"], "created_at": {"$lt": created_at}},
        # _id is the tie-breaker: Mongo timestamps have millisecond
        # precision, so two messages can share a created_at.
        sort=[("created_at", -1), ("_id", -1)],
    )
    if prev is not None and prev["sender"] == "assistant":
        seconds = (created_at - _naive(prev["created_at"])).total_seconds()
        if 0 <= seconds <= MAX_RESPONSE_DELAY_SEC:
            delay = seconds

    update = {
        "$inc": {"chat_messages_count": 1},
        "$setOnInsert": {"student_id": student_id, "date": day, "checkin_completed": False},
    }

    if delay is not None:
        existing = await db.behavioral_signals.find_one({"student_id": student_id, "date": day})
        samples = (existing or {}).get("response_delay_samples", 0)
        avg = (existing or {}).get("avg_response_delay_sec")
        new_avg = delay if (avg is None or samples == 0) else (avg * samples + delay) / (samples + 1)
        update["$set"] = {
            "avg_response_delay_sec": round(new_avg, 2),
            "response_delay_samples": samples + 1,
        }

    await db.behavioral_signals.update_one({"student_id": student_id, "date": day}, update, upsert=True)


async def process_student_message(db: AsyncIOMotorDatabase, message: dict) -> None:
    """Background job: run once per saved student message."""
    created_at = _naive(message["created_at"])
    day = _day_of(created_at)

    # 1) Behavioral signals never depend on the ML model.
    try:
        await _update_chat_signals(db, message, created_at, day)
    except Exception:
        logger.exception("Failed to update chat behavioral signals")

    # 2) Sentiment (skippable, and allowed to fail safely).
    if not settings.sentiment_enabled:
        return
    try:
        result = await analyze_sentiment(message["text"])
    except Exception:
        logger.exception("Sentiment analysis failed; skipping this message")
        return

    try:
        await db.sentiment_results.insert_one({
            "message_id": message["_id"],
            "student_id": message["student_id"],
            "date": day,
            "sentiment_score": result["sentiment_score"],
            "dominant_emotion": result["dominant_emotion"],
            "confidence": result["confidence"],
            "created_at": created_at,
        })
    except Exception:
        logger.exception("Failed to save sentiment result")


async def get_daily_sentiment(db: AsyncIOMotorDatabase, student_id: ObjectId, days: int) -> list[dict]:
    today = _day_of(datetime.now(timezone.utc))
    since = today - timedelta(days=days - 1)
    cursor = db.sentiment_results.find({"student_id": student_id, "date": {"$gte": since}})

    buckets: dict[datetime, list[float]] = {}
    async for doc in cursor:
        buckets.setdefault(doc["date"], []).append(doc["sentiment_score"])

    return [
        {"date": d, "avg_sentiment": round(sum(v) / len(v), 4), "message_count": len(v)}
        for d, v in sorted(buckets.items())
    ]
