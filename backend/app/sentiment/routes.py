"""
Sentiment routes.

    GET /sentiment/daily?days=7  -- the student's own daily average sentiment

Student-only. Returns numeric trend data only -- never message text.
Sentiment is written by the background job in service.py, not by an API
call, so there is deliberately no POST endpoint here.
"""

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import require_role
from app.db.mongodb import get_database
from app.sentiment.schemas import DailySentimentOut
from app.sentiment.service import get_daily_sentiment

router = APIRouter()


@router.get("/daily", response_model=list[DailySentimentOut])
async def read_daily_sentiment(
    days: int = Query(default=7, ge=1, le=90),
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await get_daily_sentiment(db, user["_id"], days)
