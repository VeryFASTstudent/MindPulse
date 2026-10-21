"""
Chat business logic.

Message flow (matches the blueprint's sequence diagram):
Student -> POST /chat/message -> this module ->
    1. get_or_create_active_session
    2. save the student's message
    3. build recent conversation history
    4. ai/llm_client.generate_chat_reply()
    5. save the assistant's reply
    6. return both messages

Signal extraction (turning this into sentiment_results / behavioral_signals)
is deliberately NOT done here -- that's Phase 6 (sentiment analysis) and
hooks in as an async step after save_message, without changing this flow.
"""

from datetime import datetime, timedelta, timezone
import re

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from ai.llm_client import generate_chat_reply
from app.chat.guardrails import classify_input, normalize_text
from app.behavior.schemas import CheckinRequest

# A session is considered "active" if the last message was within this
# window; otherwise a new session starts. This keeps chat_sessions
# meaningfully grouped by conversation rather than one giant session per
# student forever.
SESSION_IDLE_TIMEOUT = timedelta(hours=2)

# How many prior messages to send back to the LLM as context. Kept small
# on purpose -- enough for a coherent reply, not so much that every
# message balloons token usage/cost.
HISTORY_WINDOW = 8
CHECKIN_FIELDS = ("stress", "workload", "sleep_hours", "activity")
CHECKIN_PROMPTS = {
    "stress": "What is your stress level today from 1 to 10?",
    "workload": "What is your workload today from 1 to 10?",
    "sleep_hours": "How many hours did you sleep? You can use a number from 0 to 24.",
    "activity": "What is your activity level today from 0 to 10?",
}


def _checkin_number(text: str) -> float | None:
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", normalize_text(text))
    return float(match.group(1)) if match else None


def _validate_checkin_value(field: str, value: float | None) -> bool:
    if value is None:
        return False
    if field in {"stress", "workload"}:
        return value.is_integer() and 1 <= value <= 10
    if field == "activity":
        return value.is_integer() and 0 <= value <= 10
    return 0 <= value <= 24


def _checkin_prompt(state: dict) -> str:
    return CHECKIN_PROMPTS[state["field"]]


async def _handle_checkin_message(db: AsyncIOMotorDatabase, session: dict, student_id: ObjectId, text: str) -> str | None:
    normalized = normalize_text(text).lower()
    if normalized in {"skip", "cancel", "stop", "no"}:
        await db.chat_sessions.update_one(
            {"_id": session["_id"]}, {"$set": {"checkin_draft.status": "cancelled"}}
        )
        return "Your check-in draft was cancelled. You can start another one anytime."
    draft = session.get("checkin_draft")
    if not draft:
        if normalized in {"check in", "daily check-in", "start check-in", "checkin"}:
            draft = {"field": CHECKIN_FIELDS[0], "status": "collecting", "values": {}}
            await db.chat_sessions.update_one({"_id": session["_id"]}, {"$set": {"checkin_draft": draft}})
            return CHECKIN_PROMPTS[CHECKIN_FIELDS[0]]
        return None
    if draft.get("status") != "collecting":
        return None
    field = draft["field"]
    value = _checkin_number(text)
    if not _validate_checkin_value(field, value):
        return f"That value is outside the allowed range. {_checkin_prompt(draft)}"
    draft["values"][field] = int(value) if value.is_integer() else value
    next_index = CHECKIN_FIELDS.index(field) + 1
    if next_index < len(CHECKIN_FIELDS):
        draft["field"] = CHECKIN_FIELDS[next_index]
        await db.chat_sessions.update_one({"_id": session["_id"]}, {"$set": {"checkin_draft": draft}})
        return CHECKIN_PROMPTS[draft["field"]]
    draft["status"] = "awaiting_confirmation"
    await db.chat_sessions.update_one({"_id": session["_id"]}, {"$set": {"checkin_draft": draft}})
    values = draft["values"]
    return (
        f"Here is your check-in: stress {values['stress']}/10, workload {values['workload']}/10, "
        f"sleep {values['sleep_hours']} hours, activity {values['activity']}/10. "
        "Please confirm it in the app, edit it, or cancel."
    )


async def get_or_create_active_session(db: AsyncIOMotorDatabase, student_id: ObjectId) -> dict:
    session = await db.chat_sessions.find_one({"student_id": student_id, "status": "active"})
    now = datetime.now(timezone.utc)

    if session:
        last = session["last_message_at"]
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now - last < SESSION_IDLE_TIMEOUT:
            return session
        await db.chat_sessions.update_one({"_id": session["_id"]}, {"$set": {"status": "closed"}})

    new_session = {
        "student_id": student_id,
        "started_at": now,
        "last_message_at": now,
        "status": "active",
    }
    result = await db.chat_sessions.insert_one(new_session)
    new_session["_id"] = result.inserted_id
    return new_session


async def save_message(
    db: AsyncIOMotorDatabase,
    session_id: ObjectId,
    student_id: ObjectId,
    sender: str,
    text: str,
    response_mode: str | None = None,
) -> dict:
    doc = {
        "session_id": session_id,
        "student_id": student_id,
        "sender": sender,
        "text": text,
        "created_at": datetime.now(timezone.utc),
    }
    if response_mode is not None:
        doc["response_mode"] = response_mode
    result = await db.messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.chat_sessions.update_one(
        {"_id": session_id}, {"$set": {"last_message_at": doc["created_at"]}}
    )
    return doc


async def get_recent_history(db: AsyncIOMotorDatabase, session_id: ObjectId, limit: int = HISTORY_WINDOW) -> list[dict]:
    cursor = db.messages.find({"session_id": session_id}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    docs.reverse()  # oldest first, for correct conversational order
    return docs


async def handle_student_message(
    db: AsyncIOMotorDatabase, student_id: ObjectId, text: str
) -> tuple[dict, dict, str]:
    session = await get_or_create_active_session(db, student_id)
    student_message = await save_message(db, session["_id"], student_id, "student", text)

    input_mode, guarded_reply = classify_input(text)
    if guarded_reply is not None:
        assistant_message = await save_message(
            db, session["_id"], student_id, "assistant", guarded_reply, response_mode=input_mode
        )
        return student_message, assistant_message, input_mode

    checkin_reply = await _handle_checkin_message(db, session, student_id, text)
    if checkin_reply is not None:
        assistant_message = await save_message(
            db, session["_id"], student_id, "assistant", checkin_reply, response_mode="checkin"
        )
        return student_message, assistant_message, "checkin"

    history_docs = await get_recent_history(db, session["_id"])
    conversation = [
        {"role": "user" if m["sender"] == "student" else "assistant", "content": m["text"]}
        for m in history_docs
    ]

    reply_text, response_mode = await generate_chat_reply(conversation)
    assistant_message = await save_message(
        db,
        session["_id"],
        student_id,
        "assistant",
        reply_text,
        response_mode=response_mode,
    )

    return student_message, assistant_message, response_mode
