"""
Behavior routes.

    POST /behavior/checkin        -- submit/update today's check-in
    GET  /behavior/checkin/today  -- today's check-in, or 404 if not done yet
    GET  /behavior/history        -- last N days of behavioral_signals (default 7)
    GET  /behavior/streak         -- consecutive completed check-in days

All student-only -- a student's own behavioral data. Parent/admin
aggregated views are built in the dashboards module (Phase 10/11), reading
through the consent layer rather than this module directly.
"""

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import require_role
from app.behavior.schemas import CheckinOut, CheckinRequest, StreakOut
from app.behavior.service import get_checkin_streak, get_history, get_today_checkin, submit_checkin
from app.core.exceptions import NotFoundError
from app.db.mongodb import get_database

router = APIRouter()


@router.post("/checkin", response_model=CheckinOut)
async def create_or_update_checkin(
    data: CheckinRequest,
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await submit_checkin(db, user["_id"], data)


@router.get("/checkin/today", response_model=CheckinOut)
async def read_today_checkin(
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    checkin = await get_today_checkin(db, user["_id"])
    if checkin is None:
        raise NotFoundError(detail="No check-in submitted for today yet")
    return checkin


@router.get("/history", response_model=list[CheckinOut])
async def read_history(
    days: int = Query(default=7, ge=1, le=90),
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await get_history(db, user["_id"], days)


@router.get("/streak", response_model=StreakOut)
async def read_streak(
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    streak = await get_checkin_streak(db, user["_id"])
    return StreakOut(streak=streak)
