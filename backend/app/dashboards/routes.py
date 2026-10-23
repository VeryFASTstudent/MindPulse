from bson import ObjectId
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import require_role
from app.core.exceptions import ValidationFailedError
from app.dashboards.admin_service import (
    get_risk_configuration,
    list_admin_audit_events,
    list_admin_external_resources,
    list_admin_users,
    create_admin_external_resource,
    set_admin_external_resource_active,
    set_admin_user_active,
    update_risk_configuration,
)
from app.dashboards.schemas import (
    AdminOverview,
    AdminUserOut,
    AdminUserStatusUpdate,
    AuditEventOut,
    ParentStudentSummary,
    RiskConfiguration,
    StudentAlertDeliveryOut,
)
from app.dashboards.service import get_admin_overview, get_parent_summaries
from app.db.mongodb import get_database
from app.escalations.schemas import EscalationOut, EscalationStatusUpdate
from app.escalations.service import (
    list_counselor_escalations,
    update_counselor_escalation,
)
from app.referral.schemas import (
    ExternalResourceStatusUpdate,
    ExternalSupportResourceCreate,
    ExternalSupportResourceOut,
)

router = APIRouter()


def _object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ValidationFailedError(detail="Invalid identifier")
    return ObjectId(value)


@router.get("/parent/students", response_model=list[ParentStudentSummary])
async def read_linked_student_summaries(
    parent: dict = Depends(require_role(["parent"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await get_parent_summaries(db, parent)


@router.get("/student/alerts", response_model=list[StudentAlertDeliveryOut])
async def read_student_alert_deliveries(
    student: dict = Depends(require_role(["student"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await db.alert_deliveries.find(
        {"student_id": student["_id"]},
        {"_id": 0, "channel": 1, "recipient": 1, "message_text": 1, "status": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(length=50)


@router.get("/counselor/escalations", response_model=list[EscalationOut])
async def read_counselor_escalations(
    counselor: dict = Depends(require_role(["counselor"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await list_counselor_escalations(db, counselor["_id"])


@router.patch(
    "/counselor/escalations/{event_id}",
    response_model=EscalationOut,
)
async def update_escalation_status(
    event_id: str,
    data: EscalationStatusUpdate,
    counselor: dict = Depends(require_role(["counselor"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await update_counselor_escalation(
        db, counselor["_id"], _object_id(event_id), data.status
    )


@router.get("/admin/overview", response_model=AdminOverview)
async def read_admin_overview(
    _: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await get_admin_overview(db)


@router.get("/admin/users", response_model=list[AdminUserOut])
async def read_admin_users(
    _: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await list_admin_users(db)


@router.patch("/admin/users/{user_id}", response_model=AdminUserOut)
async def update_admin_user_status(
    user_id: str,
    data: AdminUserStatusUpdate,
    admin: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await set_admin_user_active(
        db, _object_id(user_id), data.is_active, admin["_id"]
    )


@router.get("/admin/audit", response_model=list[AuditEventOut])
async def read_admin_audit_events(
    _: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await list_admin_audit_events(db)


@router.get("/admin/risk-configuration", response_model=RiskConfiguration)
async def read_admin_risk_configuration(
    _: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await get_risk_configuration(db)


@router.put("/admin/risk-configuration", response_model=RiskConfiguration)
async def write_admin_risk_configuration(
    data: RiskConfiguration,
    admin: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await update_risk_configuration(db, data, admin["_id"])


@router.get(
    "/admin/support-resources",
    response_model=list[ExternalSupportResourceOut],
)
async def read_admin_support_resources(
    _: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await list_admin_external_resources(db)


@router.post(
    "/admin/support-resources",
    response_model=ExternalSupportResourceOut,
    status_code=201,
)
async def create_admin_support_resource(
    data: ExternalSupportResourceCreate,
    admin: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await create_admin_external_resource(db, data, admin["_id"])


@router.patch(
    "/admin/support-resources/{resource_id}",
    response_model=ExternalSupportResourceOut,
)
async def update_admin_support_resource(
    resource_id: str,
    data: ExternalResourceStatusUpdate,
    admin: dict = Depends(require_role(["admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await set_admin_external_resource_active(
        db, _object_id(resource_id), data.is_active, admin["_id"]
    )
