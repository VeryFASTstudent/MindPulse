from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import ForbiddenError, NotFoundError
from app.dashboards.schemas import RiskConfiguration
from app.referral.schemas import ExternalSupportResourceCreate
from app.risk_engine.scoring import RISK_CONFIG

RISK_CONFIG_ID = "active-risk-configuration"


def default_risk_configuration() -> dict[str, Any]:
    return {
        **{
            key: float(value)
            for key, value in RISK_CONFIG.items()
            if key not in {"thresholds", "min_consecutive_days"}
        },
        "low_max": float(RISK_CONFIG["thresholds"]["low_max"]),
        "medium_max": float(RISK_CONFIG["thresholds"]["medium_max"]),
        "min_consecutive_days": int(RISK_CONFIG["min_consecutive_days"]),
        "min_signal_coverage": float(RISK_CONFIG["min_signal_coverage"]),
    }


async def get_risk_configuration(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    stored = await db.system_settings.find_one({"_id": RISK_CONFIG_ID})
    if stored is None:
        return default_risk_configuration()
    return {key: value for key, value in stored.items() if key != "_id"}


async def update_risk_configuration(
    db: AsyncIOMotorDatabase,
    config: RiskConfiguration,
    actor_id: ObjectId,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    values = config.model_dump()
    await db.system_settings.update_one(
        {"_id": RISK_CONFIG_ID},
        {
            "$set": {**values, "updated_at": now, "updated_by": actor_id},
        },
        upsert=True,
    )
    await db.audit_logs.insert_one(
        {
            "actor_type": "admin",
            "actor_id": actor_id,
            "action": "risk_configuration_updated",
            "created_at": now,
        }
    )
    return values


async def list_admin_users(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    cursor = db.users.find(
        {},
        {
            "full_name": 1,
            "email": 1,
            "role": 1,
            "is_active": 1,
            "created_at": 1,
        },
    ).sort("created_at", -1)
    return await cursor.to_list(length=200)


async def set_admin_user_active(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    is_active: bool,
    admin_id: ObjectId,
) -> dict[str, Any]:
    user = await db.users.find_one(
        {"_id": user_id},
        {
            "full_name": 1,
            "email": 1,
            "role": 1,
            "is_active": 1,
            "created_at": 1,
        },
    )
    if user is None:
        raise NotFoundError(detail="Account not found")
    if user_id == admin_id and not is_active:
        raise ForbiddenError(detail="You cannot deactivate your own admin account")
    if user["role"] == "admin" and user.get("is_active", True) and not is_active:
        active_admins = await db.users.count_documents(
            {"role": "admin", "is_active": True}
        )
        if active_admins <= 1:
            raise ForbiddenError(detail="The last active admin cannot be deactivated")

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_active": is_active}},
    )
    await db.audit_logs.insert_one(
        {
            "actor_type": "admin",
            "actor_id": admin_id,
            "action": "account_status_updated",
            "status": "active" if is_active else "inactive",
            "created_at": now,
        }
    )
    user["is_active"] = is_active
    return user


async def list_admin_audit_events(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    cursor = db.audit_logs.find(
        {},
        {
            "actor_type": 1,
            "actor_id": 1,
            "action": 1,
            "status": 1,
            "created_at": 1,
        },
    ).sort("created_at", -1)
    return await cursor.to_list(length=100)


async def list_admin_external_resources(
    db: AsyncIOMotorDatabase,
) -> list[dict[str, Any]]:
    cursor = db.external_support_resources.find(
        {},
        {
            "name": 1,
            "specialization": 1,
            "contact_email": 1,
            "website_url": 1,
            "cost_description": 1,
            "is_active": 1,
        },
    ).sort("name", 1)
    return await cursor.to_list(length=200)


async def create_admin_external_resource(
    db: AsyncIOMotorDatabase,
    resource: ExternalSupportResourceCreate,
    admin_id: ObjectId,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    document = {
        **resource.model_dump(mode="json"),
        "is_active": True,
        "created_at": now,
        "created_by": admin_id,
    }
    result = await db.external_support_resources.insert_one(document)
    document["_id"] = result.inserted_id
    await db.audit_logs.insert_one(
        {
            "actor_type": "admin",
            "actor_id": admin_id,
            "action": "external_support_resource_created",
            "created_at": now,
        }
    )
    return document


async def set_admin_external_resource_active(
    db: AsyncIOMotorDatabase,
    resource_id: ObjectId,
    is_active: bool,
    admin_id: ObjectId,
) -> dict[str, Any]:
    resource = await db.external_support_resources.find_one(
        {"_id": resource_id},
        {
            "name": 1,
            "specialization": 1,
            "contact_email": 1,
            "website_url": 1,
            "cost_description": 1,
            "is_active": 1,
        },
    )
    if resource is None:
        raise NotFoundError(detail="Support resource not found")
    await db.external_support_resources.update_one(
        {"_id": resource_id},
        {"$set": {"is_active": is_active}},
    )
    await db.audit_logs.insert_one(
        {
            "actor_type": "admin",
            "actor_id": admin_id,
            "action": "external_support_resource_status_updated",
            "status": "active" if is_active else "inactive",
            "created_at": datetime.now(timezone.utc),
        }
    )
    resource["is_active"] = is_active
    return resource
