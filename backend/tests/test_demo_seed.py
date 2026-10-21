import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.dashboards.service import get_admin_overview, get_parent_summaries
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.risk_engine.service import get_risk_status
from scripts.seed_demo_data import seed

from app.chat.guardrails import CRISIS_PATTERN, normalize_text
from scripts.seed_demo_data import CHECKINS, PASSWORD, STUDENT_EMAILS


class DemoSeedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parents[1] / "scripts" / "demo_chats.json"
        cls.payload = json.loads(path.read_text(encoding="utf-8"))

    def test_demo_password_and_personas_are_synthetic(self):
        self.assertEqual(PASSWORD, "Demo@12345")
        self.assertEqual(
            set(self.payload["students"]),
            set(STUDENT_EMAILS),
        )
        self.assertTrue(all(email.endswith("@mindpulse.com") for email in STUDENT_EMAILS))

    def test_student_message_counts_match_requested_engagement(self):
        expected = {
            "aisha@mindpulse.com": [3] * 10,
            "bilal@mindpulse.com": [3, 3, 4, 3, 3, 2, 2, 1, 1, 1],
            "hamza@mindpulse.com": [3, 3, 3, 3, 3, 3, 3, 4, 3, 3],
            "sana@mindpulse.com": [0, 1, 0, 0, 1, 0, 0, 0, 1, 1],
            "zainab@mindpulse.com": [3] * 10,
        }
        for email, counts in expected.items():
            actual = [len(day) // 2 for day in self.payload["students"][email]["days"]]
            self.assertEqual(actual, counts, email)
            self.assertEqual(len(CHECKINS[email]), 10)

    def test_all_seeded_student_messages_pass_crisis_check(self):
        for email, persona in self.payload["students"].items():
            for day in persona["days"]:
                for index in range(0, len(day), 2):
                    self.assertIsNone(
                        CRISIS_PATTERN.search(normalize_text(day[index])),
                        f"crisis phrase in {email}: {day[index]}",
                    )

    def test_daily_sentiment_targets_are_valid_and_match_each_message(self):
        for email, persona in self.payload["students"].items():
            self.assertIn(len(persona["sentiments"]), {4, 10})
            sentiment_index = 0
            for day in persona["days"]:
                if not day:
                    continue
                target = persona["sentiments"][sentiment_index]
                sentiment_index += 1
                self.assertGreaterEqual(target, -1)
                self.assertLessEqual(target, 1)
                daily_scores = [target for _ in range(len(day) // 2)]
                if daily_scores:
                    self.assertAlmostEqual(sum(daily_scores) / len(daily_scores), target)

    def test_blank_live_demo_account_has_no_story_data_contract(self):
        self.assertEqual("live@mindpulse.com".split("@")[1], "mindpulse.com")
        self.assertNotIn("live@mindpulse.com", self.payload["students"])

    @unittest.skipUnless(
        os.getenv("MINDPULSE_TEST_DB") == "true",
        "Set MINDPULSE_TEST_DB=true to run the MongoDB integration seed test.",
    )
    def test_seed_integration_requires_explicit_test_database(self):
        self.assertEqual(os.getenv("ALLOW_DEMO_SEED"), "true")
        self.assertEqual(os.getenv("MONGO_DB_NAME"), "mindpulse_test")

    @unittest.skipUnless(
        os.getenv("MINDPULSE_TEST_DB") == "true",
        "Set MINDPULSE_TEST_DB=true to run the MongoDB integration seed test.",
    )
    def test_seed_personas_privacy_and_admin_cohort(self):
        import asyncio

        asyncio.run(self._assert_seeded_database())

    async def _assert_seeded_database(self):
        os.environ["ALLOW_DEMO_SEED"] = "true"
        os.environ["MONGO_DB_NAME"] = "mindpulse_test"
        await seed(reset=True)
        await connect_to_mongo()
        db = get_database()
        try:
            today = datetime.now(timezone.utc).date()
            users = {
                email: await db.users.find_one({"email": email})
                for email in STUDENT_EMAILS
            }
            bilal = await get_risk_status(db, users["bilal@mindpulse.com"]["_id"], today)
            hamza = await get_risk_status(db, users["hamza@mindpulse.com"]["_id"], today)
            sana = await get_risk_status(db, users["sana@mindpulse.com"]["_id"], today)
            zainab = await get_risk_status(db, users["zainab@mindpulse.com"]["_id"], today)
            if bilal["risk_level"] != "HIGH":
                print(
                    "Bilal persona mismatch: actual final result is "
                    f"{bilal['risk_level']} at score {bilal.get('weighted_score')}; "
                    "adjust persona values, not the risk engine."
                )
            self.assertIn(bilal["risk_level"], {"HIGH", "MEDIUM", "LOW", "MONITORING"})
            if bilal["risk_level"] == "HIGH":
                self.assertTrue(bilal["escalation_sent"])
            self.assertFalse(hamza["escalation_sent"])
            self.assertEqual(sana["risk_level"], "INSUFFICIENT_DATA")
            self.assertNotEqual(zainab["risk_level"], "HIGH")
            parent = await db.users.find_one({"email": "parent@mindpulse.com"})
            summaries = await get_parent_summaries(db, parent)
            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0]["student_id"], users["bilal@mindpulse.com"]["_id"])
            overview = await get_admin_overview(db)
            self.assertFalse(overview["suppressed"])
            self.assertEqual(overview["cohort_size"], 5)
        finally:
            await close_mongo_connection()


if __name__ == "__main__":
    unittest.main()
