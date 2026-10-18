from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import require_role
from app.db.mongodb import get_database
from app.risk_engine.schemas import RiskStatusOut
from app.risk_engine.service import get_risk_status

router = APIRouter()


@router.get("/status", response_model=RiskStatusOut)
async def read_risk_status(
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await get_risk_status(db, user["_id"])