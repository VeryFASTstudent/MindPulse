import unittest
from datetime import date
from types import SimpleNamespace

from app.core.exceptions import ForbiddenError, ValidationFailedError
from app.escalations.schemas import EscalationStatus
from app.escalations.service import (
    create_sustained_escalations,
    list_counselor_escalations,
    update_counselor_escalation,
)


class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, field, direction=1):
        self.documents.sort(
            key=lambda document: document.get(field),
            reverse=direction < 0,
        )
        return self

    async def to_list(self, length=None):
        return self.documents[:length]

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for document in self.documents:
            yield document


class FakeCollection:
    def __init__(self, documents=()):
        self.documents = list(documents)
        self.next_id = 1

    def find(self, query, projection=None):
        return FakeCursor(
            document
            for document in self.documents
            if _matches(document, query)
        )

    async def find_one(self, query, projection=None):
        return next(
            (
                document
                for document in self.documents
                if _matches(document, query)
            ),
            None,
        )

    async def update_one(self, query, update, upsert=False):
        document = await self.find_one(query)
        if document is not None:
            document.update(update.get("$set", {}))
            return SimpleNamespace(upserted_id=None)
        if not upsert:
            return SimpleNamespace(upserted_id=None)

        inserted = dict(update.get("$setOnInsert", {}))
        inserted["_id"] = f"event-{self.next_id}"
        self.next_id += 1
        self.documents.append(inserted)
        return SimpleNamespace(upserted_id=inserted["_id"])

    async def insert_one(self, document):
        inserted = dict(document)
        inserted["_id"] = f"audit-{self.next_id}"
        self.next_id += 1
        self.documents.append(inserted)
        return SimpleNamespace(inserted_id=inserted["_id"])


class FakeDatabase:
    def __init__(self, consents=(), users=()):
        self.consents = FakeCollection(consents)
        self.users = FakeCollection(users)
        self.escalation_events = FakeCollection()
        self.audit_logs = FakeCollection()


def _matches(document, query):
    for key, expected in query.items():
        actual = document.get(key)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
        elif isinstance(actual, list):
            if expected not in actual:
                return False
        elif actual != expected:
            return False
    return True


class EscalationWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_alerts_require_consent_and_include_only_summary_fields(self):
        db = FakeDatabase(
            consents=[
                {
                    "student_id": "student-1",
                    "share_with_university_support": True,
                    "share_summary_with_parent": True,
                }
            ],
            users=[
                {
                    "_id": "counselor-1",
                    "role": "counselor",
                    "is_active": True,
                },
                {
                    "_id": "parent-1",
                    "role": "parent",
                    "is_active": True,
                    "linked_student_ids": ["student-1"],
                },
            ],
        )

        created = await create_sustained_escalations(
            db, "student-1", date(2026, 10, 20), 3
        )

        self.assertTrue(created)
        self.assertEqual(len(db.escalation_events.documents), 2)
        self.assertEqual(len(db.audit_logs.documents), 2)
        event = db.escalation_events.documents[0]
        self.assertEqual(event["risk_level"], "HIGH")
        self.assertNotIn("text", event)
        self.assertNotIn("weighted_score", event)
        self.assertIn("No chat content", event["summary"])

    async def test_alert_creation_is_idempotent_for_the_same_trigger_day(self):
        db = FakeDatabase(
            consents=[
                {
                    "student_id": "student-1",
                    "share_with_university_support": True,
                }
            ],
            users=[
                {
                    "_id": "counselor-1",
                    "role": "counselor",
                    "is_active": True,
                }
            ],
        )

        first = await create_sustained_escalations(
            db, "student-1", date(2026, 10, 20), 3
        )
        second = await create_sustained_escalations(
            db, "student-1", date(2026, 10, 20), 4
        )

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertEqual(len(db.escalation_events.documents), 1)
        self.assertEqual(len(db.audit_logs.documents), 1)

    async def test_counselor_alert_is_hidden_after_consent_is_withdrawn(self):
        db = FakeDatabase(
            consents=[
                {
                    "student_id": "student-1",
                    "share_with_university_support": False,
                }
            ],
            users=[
                {
                    "_id": "student-1",
                    "role": "student",
                    "is_active": True,
                    "full_name": "Student",
                }
            ],
        )
        db.escalation_events.documents.append(
            {
                "_id": "event-1",
                "student_id": "student-1",
                "recipient_id": "counselor-1",
                "recipient_role": "counselor",
                "status": "new",
            }
        )

        events = await list_counselor_escalations(db, "counselor-1")

        self.assertEqual(events, [])

    async def test_counselor_status_transition_requires_current_consent(self):
        db = FakeDatabase(
            consents=[
                {
                    "student_id": "student-1",
                    "share_with_university_support": False,
                }
            ]
        )
        db.escalation_events.documents.append(
            {
                "_id": "event-1",
                "student_id": "student-1",
                "recipient_id": "counselor-1",
                "recipient_role": "counselor",
                "status": "new",
            }
        )

        with self.assertRaises(ForbiddenError):
            await update_counselor_escalation(
                db,
                "counselor-1",
                "event-1",
                EscalationStatus.acknowledged,
            )

    async def test_status_cannot_skip_acknowledgement(self):
        db = FakeDatabase(
            consents=[
                {
                    "student_id": "student-1",
                    "share_with_university_support": True,
                }
            ]
        )
        db.escalation_events.documents.append(
            {
                "_id": "event-1",
                "student_id": "student-1",
                "recipient_id": "counselor-1",
                "recipient_role": "counselor",
                "status": "new",
            }
        )

        with self.assertRaises(ValidationFailedError):
            await update_counselor_escalation(
                db,
                "counselor-1",
                "event-1",
                EscalationStatus.closed,
            )


if __name__ == "__main__":
    unittest.main()
