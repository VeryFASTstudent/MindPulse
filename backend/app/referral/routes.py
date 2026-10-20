from bson import ObjectId
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import require_role
from app.core.exceptions import ValidationFailedError
from app.db.mongodb import get_database
from app.referral.schemas import (
    CounselorOut,
    ExternalSupportResourceOut,
    ReferralOut,
    ReferralRequestCreate,
    ReferralStatusUpdate,
)
from app.referral.service import (
    create_referral_request,
    list_counselor_requests,
    list_counselors,
    list_external_support_resources,
    list_student_requests,
    update_counselor_request,
)

router = APIRouter()


def _object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ValidationFailedError(detail="Invalid identifier")
    return ObjectId(value)


@router.get("/counselors", response_model=list[CounselorOut])
async def read_counselors(
    _: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await list_counselors(db)


@router.get(
    "/external-resources",
    response_model=list[ExternalSupportResourceOut],
)
async def read_external_support_resources(
    _: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await list_external_support_resources(db)


@router.post("/requests", response_model=ReferralOut, status_code=201)
async def request_counselor_support(
    data: ReferralRequestCreate,
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await create_referral_request(
        db, user, _object_id(data.counselor_id), data.student_confirmed
    )


@router.get("/requests/mine", response_model=list[ReferralOut])
async def read_my_requests(
    user: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await list_student_requests(db, user["_id"])


@router.get("/requests/inbox", response_model=list[ReferralOut])
async def read_counselor_inbox(
    user: dict = Depends(require_role(["counselor"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await list_counselor_requests(db, user["_id"])


@router.patch("/requests/{request_id}", response_model=ReferralOut)
async def update_request(
    request_id: str,
    data: ReferralStatusUpdate,
    user: dict = Depends(require_role(["counselor"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await update_counselor_request(
        db, user["_id"], _object_id(request_id), data.status
    )
