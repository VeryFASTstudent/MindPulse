from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import require_role
from app.consent.schemas import ConsentOut, ConsentUpdate
from app.consent.service import read_student_consent, update_student_consent
from app.db.mongodb import get_database

router = APIRouter()


@router.get("/me", response_model=ConsentOut)
async def get_my_consent(
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await read_student_consent(db, user["_id"])


@router.put("/me", response_model=ConsentOut)
async def put_my_consent(
    data: ConsentUpdate,
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await update_student_consent(db, user["_id"], data)