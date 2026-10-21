"""
Chat routes.

    POST /chat/message                     -- send a message, get the AI's reply
    GET  /chat/sessions                    -- list the student's own chat sessions
    GET  /chat/sessions/{session_id}/messages -- full message history for one session

All three are student-only. A student can only ever see their own
sessions/messages -- there is no endpoint here that lets a parent, admin,
or counselor read chat content, matching the privacy boundary in the
blueprint (Section 10: parents/admins never see raw conversations).
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import require_role
from app.chat.schemas import ChatMessageRequest, ChatReplyResponse, CheckinConfirmRequest, MessageOut, SessionOut
from app.core.config import settings
from app.chat.service import handle_student_message
from app.behavior.schemas import CheckinRequest
from app.behavior.service import submit_checkin
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.mongodb import get_database
from app.sentiment.service import process_student_message

router = APIRouter()
_RATE_BUCKETS: dict[ObjectId, deque[datetime]] = defaultdict(deque)


def _check_rate_limit(user_id: ObjectId) -> None:
    now = datetime.now(timezone.utc)
    bucket = _RATE_BUCKETS[user_id]
    while bucket and bucket[0] < now - timedelta(days=1):
        bucket.popleft()
    minute_count = sum(item >= now - timedelta(minutes=1) for item in bucket)
    if minute_count >= settings.chat_rate_limit_per_minute or len(bucket) >= settings.chat_rate_limit_per_day:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Chat rate limit exceeded")
    bucket.append(now)


@router.post("/message", response_model=ChatReplyResponse)
async def send_message(
    data: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    _check_rate_limit(user["_id"])
    student_message, assistant_message, response_mode = await handle_student_message(
        db, user["_id"], data.text
    )
    # Signal extraction (sentiment + chat behavior) runs AFTER the response
    # is sent, so it can never slow down or break the chat itself.
    background_tasks.add_task(process_student_message, db, student_message)
    return ChatReplyResponse(
        session_id=str(student_message["session_id"]),
        student_message=student_message,
        assistant_message=assistant_message,
        response_mode=response_mode,
        checkin_state=(
            (await db.chat_sessions.find_one({"_id": student_message["session_id"]}) or {})
            .get("checkin_draft", {})
            .get("status")
        ),
        checkin_draft=(
            (await db.chat_sessions.find_one({"_id": student_message["session_id"]}) or {})
            .get("checkin_draft")
        ),
    )


@router.post("/checkin/confirm")
async def confirm_checkin(
    data: CheckinConfirmRequest,
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    session = await db.chat_sessions.find_one({"_id": data.session_id, "student_id": user["_id"]})
    if session is None or session.get("checkin_draft", {}).get("status") != "awaiting_confirmation":
        raise HTTPException(status_code=400, detail="No check-in is awaiting confirmation")
    draft = session["checkin_draft"]
    if data.action == "cancel":
        await db.chat_sessions.update_one({"_id": data.session_id}, {"$set": {"checkin_draft.status": "cancelled"}})
        return {"status": "cancelled"}
    if data.action == "edit":
        draft["status"] = "collecting"
        draft["field"] = "stress"
        draft["values"] = {}
        await db.chat_sessions.update_one({"_id": data.session_id}, {"$set": {"checkin_draft": draft}})
        return {"status": "collecting", "message": "Let's edit your check-in. What is your stress level from 1 to 10?"}
    saved = await submit_checkin(db, user["_id"], CheckinRequest(**draft["values"]))
    await db.chat_sessions.update_one({"_id": data.session_id}, {"$set": {"checkin_draft.status": "saved"}})
    return {"status": "saved", "checkin": saved}


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    cursor = db.chat_sessions.find({"student_id": user["_id"]}).sort("last_message_at", -1)
    return await cursor.to_list(length=50)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def get_session_messages(
    session_id: str,
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    session = await db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    if session is None:
        raise NotFoundError(detail="Chat session not found")
    if session["student_id"] != user["_id"]:
        raise ForbiddenError(detail="You cannot access another student's chat session")

    cursor = db.messages.find({"session_id": ObjectId(session_id)}).sort("created_at", 1)
    return await cursor.to_list(length=500)
