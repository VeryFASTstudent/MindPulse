import unittest
from datetime import datetime, timedelta, timezone

from app.dashboards.service import get_admin_overview, get_parent_summaries


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
    def __init__(self, documents):
        self.documents = documents

    def find(self, query, projection=None):
        return FakeCursor(
            document
            for document in self.documents
            if _matches(document, query)
        )

    async def find_one(self, query, projection=None, sort=None):
        documents = [
            document
            for document in self.documents
            if _matches(document, query)
        ]
        if sort:
            for field, direction in reversed(sort):
                documents.sort(
                    key=lambda document: document.get(field),
                    reverse=direction < 0,
                )
        return documents[0] if documents else None


class FakeDatabase:
    def __init__(
        self,
        *,
        users=(),
        consents=(),
        behavioral_signals=(),
        risk_scores=(),
        escalation_events=(),
    ):
        self.users = FakeCollection(list(users))
        self.consents = FakeCollection(list(consents))
        self.behavioral_signals = FakeCollection(list(behavioral_signals))
        self.risk_scores = FakeCollection(list(risk_scores))
        self.escalation_events = FakeCollection(list(escalation_events))


def _matches(document, query):
    for field, expected in query.items():
        actual = document.get(field)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$gte" in expected:
                if actual is None:
                    return False
                actual_date = _as_utc(actual)
                expected_date = _as_utc(expected["$gte"])
                if actual_date < expected_date:
                    return False
        elif actual != expected:
            return False
    return True


def _as_utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class DashboardServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_parent_summaries_only_include_linked_students_who_consent(self):
        now = datetime.now(timezone.utc)
        db = FakeDatabase(
            users=[
                {"_id": "linked-consented", "role": "student", "is_active": True, "full_name": "A Student"},
                {"_id": "linked-private", "role": "student", "is_active": True, "full_name": "B Student"},
                {"_id": "unlinked", "role": "student", "is_active": True, "full_name": "C Student"},
            ],
            consents=[
                {"student_id": "linked-consented", "share_summary_with_parent": True},
            ],
            behavioral_signals=[
                {
                    "student_id": "linked-consented",
                    "checkin_completed": True,
                    "date": now,
                    "self_rated_stress": 4,
                    "sleep_hours": 7,
                },
                {
                    "student_id": "linked-consented",
                    "checkin_completed": True,
                    "date": now - timedelta(days=1),
                    "self_rated_stress": 8,
                    "sleep_hours": 5,
                },
                {
                    "student_id": "linked-private",
                    "checkin_completed": True,
                    "date": now,
                    "self_rated_stress": 10,
                    "sleep_hours": 2,
                },
            ],
            risk_scores=[
                {
                    "student_id": "linked-consented",
                    "date": now,
                    "risk_level": "MEDIUM",
                },
            ],
        )

        summaries = await get_parent_summaries(
            db,
            {
                "_id": "parent-1",
                "linked_student_ids": [
                    "linked-consented",
                    "linked-private",
                    "unlinked",
                ],
            },
        )

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["student_id"], "linked-consented")
        self.assertEqual(summaries[0]["average_stress"], 6)
        self.assertEqual(summaries[0]["average_sleep_hours"], 6)
        self.assertEqual(summaries[0]["latest_wellbeing_status"], "MEDIUM")

    async def test_admin_overview_suppresses_cohorts_below_five_students(self):
        now = datetime.now(timezone.utc)
        students = [f"student-{index}" for index in range(4)]
        db = FakeDatabase(
            consents=[
                {"student_id": student, "share_with_university_support": True}
                for student in students
            ],
            risk_scores=[
                {"student_id": student, "date": now, "risk_level": "LOW"}
                for student in students
            ],
        )

        overview = await get_admin_overview(db)

        self.assertTrue(overview["suppressed"])
        self.assertFalse(overview["available"])
        self.assertIsNone(overview["cohort_size"])
        self.assertEqual(overview["risk_distribution"], {})

    async def test_admin_overview_counts_only_latest_score_per_consented_student(self):
        now = datetime.now(timezone.utc)
        students = [f"student-{index}" for index in range(5)]
        scores = [
            {"student_id": student, "date": now, "risk_level": "LOW"}
            for student in students
        ]
        scores.extend(
            [
                {
                    "student_id": students[0],
                    "date": now - timedelta(days=1),
                    "risk_level": "HIGH",
                },
                {
                    "student_id": "not-consented",
                    "date": now,
                    "risk_level": "HIGH",
                },
            ]
        )
        db = FakeDatabase(
            consents=[
                {"student_id": student, "share_with_university_support": True}
                for student in students
            ],
            risk_scores=scores,
        )

        overview = await get_admin_overview(db)

        self.assertTrue(overview["available"])
        self.assertFalse(overview["suppressed"])
        self.assertEqual(overview["cohort_size"], 5)
        self.assertEqual(
            overview["risk_distribution"],
            {"LOW": 5, "MEDIUM": 0, "HIGH": 0},
        )


if __name__ == "__main__":
    unittest.main()
