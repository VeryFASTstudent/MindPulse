import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.exceptions import ForbiddenError
from app.dashboards.admin_service import (
    create_admin_external_resource,
    default_risk_configuration,
    get_risk_configuration,
    set_admin_external_resource_active,
    set_admin_user_active,
    update_risk_configuration,
)
from app.dashboards.schemas import RiskConfiguration
from app.referral.schemas import ExternalSupportResourceCreate
from app.risk_engine.scoring import score_risk
from pydantic import ValidationError


class AdminControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_risk_configuration_defaults_to_repository_policy(self):
        db = SimpleNamespace(
            system_settings=SimpleNamespace(
                find_one=AsyncMock(return_value=None),
            )
        )

        config = await get_risk_configuration(db)

        self.assertEqual(config, default_risk_configuration())
        self.assertEqual(config["min_consecutive_days"], 3)

    async def test_risk_weights_must_sum_to_one(self):
        values = default_risk_configuration()
        values["stress_deviation"] += 0.1

        with self.assertRaises(ValidationError):
            RiskConfiguration(**values)

    async def test_admin_configuration_controls_future_risk_thresholds(self):
        values = default_risk_configuration()
        baseline = {"typical_stress": 1.0}
        today = {"stress": 5.5}

        default_result = score_risk(today, baseline)
        values["low_max"] = 0.6
        updated_result = score_risk(today, baseline, values)

        self.assertEqual(default_result["risk_level"], "MEDIUM")
        self.assertEqual(updated_result["risk_level"], "LOW")

    async def test_admin_cannot_deactivate_the_last_active_admin(self):
        admin_id = "admin-1"
        db = SimpleNamespace(
            users=SimpleNamespace(
                find_one=AsyncMock(
                    return_value={
                        "_id": admin_id,
                        "role": "admin",
                        "is_active": True,
                    }
                ),
                count_documents=AsyncMock(return_value=1),
                update_one=AsyncMock(),
            )
        )

        with self.assertRaises(ForbiddenError):
            await set_admin_user_active(db, admin_id, False, "admin-2")

        db.users.update_one.assert_not_awaited()

    async def test_risk_configuration_updates_are_audited(self):
        config = RiskConfiguration(**default_risk_configuration())
        db = SimpleNamespace(
            system_settings=SimpleNamespace(update_one=AsyncMock()),
            audit_logs=SimpleNamespace(insert_one=AsyncMock()),
        )

        result = await update_risk_configuration(db, config, "admin-1")

        self.assertEqual(result["min_consecutive_days"], 3)
        db.system_settings.update_one.assert_awaited_once()
        db.audit_logs.insert_one.assert_awaited_once()

    async def test_admin_created_external_resource_is_active_and_audited(self):
        resource_id = "resource-1"
        db = SimpleNamespace(
            external_support_resources=SimpleNamespace(
                insert_one=AsyncMock(
                    return_value=SimpleNamespace(inserted_id=resource_id)
                )
            ),
            audit_logs=SimpleNamespace(insert_one=AsyncMock()),
        )
        resource = ExternalSupportResourceCreate(
            name="Campus Wellness",
            specialization="Student counseling",
            website_url="https://example.org",
            cost_description="Free",
        )

        result = await create_admin_external_resource(db, resource, "admin-1")

        self.assertEqual(result["_id"], resource_id)
        self.assertTrue(result["is_active"])
        self.assertEqual(result["name"], "Campus Wellness")
        db.audit_logs.insert_one.assert_awaited_once()

    async def test_admin_can_deactivate_external_support_resource(self):
        resource_id = "resource-1"
        db = SimpleNamespace(
            external_support_resources=SimpleNamespace(
                find_one=AsyncMock(
                    return_value={
                        "_id": resource_id,
                        "name": "Campus Wellness",
                        "specialization": "Student counseling",
                        "contact_email": "support@example.org",
                        "website_url": None,
                        "cost_description": "Free",
                        "is_active": True,
                    }
                ),
                update_one=AsyncMock(),
            ),
            audit_logs=SimpleNamespace(insert_one=AsyncMock()),
        )

        result = await set_admin_external_resource_active(
            db, resource_id, False, "admin-1"
        )

        self.assertFalse(result["is_active"])
        db.external_support_resources.update_one.assert_awaited_once()
        db.audit_logs.insert_one.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
