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

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from ai.llm_client import generate_chat_reply

# A session is considered "active" if the last message was within this
# window; otherwise a new session starts. This keeps chat_sessions
# meaningfully grouped by conversation rather than one giant session per
# student forever.
SESSION_IDLE_TIMEOUT = timedelta(hours=2)

# How many prior messages to send back to the LLM as context. Kept small
# on purpose -- enough for a coherent reply, not so much that every
# message balloons token usage/cost.
HISTORY_WINDOW = 10


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
    db: AsyncIOMotorDatabase, session_id: ObjectId, student_id: ObjectId, sender: str, text: str
) -> dict:
    doc = {
        "session_id": session_id,
        "student_id": student_id,
        "sender": sender,
        "text": text,
        "created_at": datetime.now(timezone.utc),
    }
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
) -> tuple[dict, dict]:
    session = await get_or_create_active_session(db, student_id)
    student_message = await save_message(db, session["_id"], student_id, "student", text)

    history_docs = await get_recent_history(db, session["_id"])
    conversation = [
        {"role": "user" if m["sender"] == "student" else "assistant", "content": m["text"]}
        for m in history_docs
    ]

    reply_text = await generate_chat_reply(conversation)
    assistant_message = await save_message(db, session["_id"], student_id, "assistant", reply_text)

    return student_message, assistant_message
