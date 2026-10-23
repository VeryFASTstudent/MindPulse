"""
Index creation, run once at startup.

Collections referenced here don't need to exist yet -- MongoDB creates a
collection implicitly the first time an index (or a document) is written
to it, so this is safe to run before Phase 2's auth module creates any
users.

Indexes match the design in the blueprint's Database Design section:
- users: unique email
- behavioral_signals / sentiment_results / risk_scores: (student_id, date)
  since virtually every trend query is "latest N days for this student"
- messages: (session_id, created_at) for chronological chat retrieval
- appointments: (student_id, status) and (counselor_id, status)
"""

from motor.motor_asyncio import AsyncIOMotorDatabase


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("email", unique=True)
    await db.consents.create_index("student_id", unique=True)
    await db.alert_deliveries.create_index([("student_id", 1), ("created_at", -1)])

    await db.behavioral_signals.create_index([("student_id", 1), ("date", -1)])
    await db.sentiment_results.create_index([("student_id", 1), ("date", -1)])
    await db.risk_scores.create_index([("student_id", 1), ("date", -1)])
    await db.baselines.create_index("student_id", unique=True)

    await db.messages.create_index([("session_id", 1), ("created_at", 1)])

    await db.appointments.create_index([("student_id", 1), ("status", 1)])
    await db.appointments.create_index([("counselor_id", 1), ("status", 1)])
    await db.counselors.create_index("user_id", unique=True)
    await db.external_support_resources.create_index(
        [("is_active", 1), ("name", 1)]
    )
    await db.escalation_events.create_index(
        [("student_id", 1), ("recipient_id", 1), ("trigger_date", 1)],
        unique=True,
    )
    await db.escalation_events.create_index(
        [("recipient_id", 1), ("status", 1), ("trigger_date", -1)]
    )
