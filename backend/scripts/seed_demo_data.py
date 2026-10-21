"""Seed guarded, synthetic MindPulse demo data.

Run from backend with ALLOW_DEMO_SEED=true:
    python -m scripts.seed_demo_data
    python -m scripts.seed_demo_data --reset
"""

import argparse
import asyncio
import json
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId

from app.auth.security import hash_password
from app.auth.schemas import UserRegister, UserRole
from app.behavior.schemas import CheckinRequest
from app.behavior.service import submit_checkin
from app.baseline.service import build_baseline
from app.db.indexes import create_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.escalations.service import create_sustained_escalations
from app.risk_engine.service import get_risk_status
from app.chat.guardrails import CRISIS_PATTERN, normalize_text

PASSWORD = "Demo@12345"
DOMAIN = "@mindpulse.com"
DATA_PATH = Path(__file__).with_name("demo_chats.json")
STUDENT_EMAILS = [
    "aisha@mindpulse.com",
    "bilal@mindpulse.com",
    "hamza@mindpulse.com",
    "sana@mindpulse.com",
    "zainab@mindpulse.com",
]
ALL_EMAILS = STUDENT_EMAILS + [
    "parent@mindpulse.com",
    "counselor@mindpulse.com",
    "admin@mindpulse.com",
    "live@mindpulse.com",
]

CHECKINS: dict[str, list[dict[str, Any] | None]] = {
    "aisha@mindpulse.com": [
        {"self_rated_stress": 3, "workload": 4, "sleep_hours": 8, "activity_score": 6},
    ] * 10,
    "bilal@mindpulse.com": [
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 4, "workload": 5, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 5, "workload": 6, "sleep_hours": 6.5, "activity_score": 4},
        {"self_rated_stress": 5, "workload": 6, "sleep_hours": 6.5, "activity_score": 4},
        {"self_rated_stress": 5, "workload": 6, "sleep_hours": 6, "activity_score": 4},
        {"self_rated_stress": 5, "workload": 6, "sleep_hours": 6, "activity_score": 4},
        {"self_rated_stress": 5, "workload": 6, "sleep_hours": 6, "activity_score": 4},
        {"self_rated_stress": 10, "workload": 10, "sleep_hours": 0, "activity_score": 0},
        {"self_rated_stress": 10, "workload": 10, "sleep_hours": 0, "activity_score": 0},
        {"self_rated_stress": 10, "workload": 10, "sleep_hours": 0, "activity_score": 0},
    ],
    "hamza@mindpulse.com": [
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 4, "workload": 5, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 9, "workload": 9, "sleep_hours": 3, "activity_score": 1},
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
        {"self_rated_stress": 4, "workload": 4, "sleep_hours": 7, "activity_score": 5},
    ],
    "sana@mindpulse.com": [
        None,
        {"self_rated_stress": 5, "workload": 5, "sleep_hours": 7, "activity_score": 4},
        None,
        None,
        {"self_rated_stress": 5, "workload": 6, "sleep_hours": 6, "activity_score": 4},
        None,
        None,
        None,
        {"self_rated_stress": 6, "workload": 6, "sleep_hours": 6, "activity_score": 3},
        {"self_rated_stress": 5, "workload": 5, "sleep_hours": 7, "activity_score": 4},
    ],
    "zainab@mindpulse.com": [
        {"self_rated_stress": 7, "workload": 8, "sleep_hours": 6, "activity_score": 5},
    ] * 10,
}


def _load_chats() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))["students"]


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min)


def _account(email: str, role: str, name: str, **extra: Any) -> dict[str, Any]:
    return {
        "_id": ObjectId(),
        "role": role,
        "email": email,
        "password_hash": hash_password(PASSWORD),
        "full_name": name,
        "linked_student_ids": extra.pop("linked_student_ids", []),
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
        "synthetic": True,
        **extra,
    }


async def _delete_demo_data(db: Any) -> None:
    demo_users = await db.users.find(
        {"email": {"$in": ALL_EMAILS}}, {"_id": 1}
    ).to_list(length=100)
    demo_ids = [user["_id"] for user in demo_users]
    await db.users.delete_many({"email": {"$in": ALL_EMAILS}})
    for collection in (
        "student_profiles", "consents", "baselines", "behavioral_signals",
        "sentiment_results", "risk_scores", "chat_sessions", "messages",
        "escalation_events", "audit_logs", "counselors",
    ):
        filters = [{"synthetic": True}]
        if demo_ids:
            if collection in {"student_profiles", "counselors"}:
                filters.append({"user_id": {"$in": demo_ids}})
            elif collection in {
                "consents", "baselines", "behavioral_signals", "sentiment_results",
                "risk_scores", "chat_sessions", "messages", "escalation_events",
            }:
                filters.append({"student_id": {"$in": demo_ids}})
        await db[collection].delete_many({"$or": filters})


async def _seed_accounts(db: Any) -> dict[str, dict[str, Any]]:
    students: dict[str, dict[str, Any]] = {}
    for email in STUDENT_EMAILS:
        name = email.split(".")[0].title()
        user = _account(email, "student", name)
        await db.users.insert_one(user)
        students[email] = user
        await db.student_profiles.insert_one({
            "user_id": user["_id"], "university_id": "DEMO", "program": "Synthetic Study",
            "semester": 5, "created_at": datetime.now(timezone.utc), "synthetic": True,
        })
        await db.consents.insert_one({
            "student_id": user["_id"], "share_summary_with_parent": email == "bilal@mindpulse.com",
            "share_with_university_support": True,
            "allow_referral_data_share": email == "bilal@mindpulse.com",
            "updated_at": datetime.now(timezone.utc), "synthetic": True,
        })
    bilal_id = students["bilal@mindpulse.com"]["_id"]
    parent = _account("parent@mindpulse.com", "parent", "Demo Parent", linked_student_ids=[bilal_id])
    counselor = _account("counselor@mindpulse.com", "counselor", "Demo Counselor")
    admin = _account("admin@mindpulse.com", "admin", "Demo Admin")
    live = _account("live@mindpulse.com", "student", "Live Demo Student")
    await db.users.insert_many([parent, counselor, admin, live])
    await db.student_profiles.insert_one({"user_id": live["_id"], "university_id": "DEMO", "program": "Live Demo", "semester": 1, "created_at": datetime.now(timezone.utc), "synthetic": True})
    await db.consents.insert_one({"student_id": live["_id"], "share_summary_with_parent": True, "share_with_university_support": True, "allow_referral_data_share": True, "updated_at": datetime.now(timezone.utc), "synthetic": True})
    await db.counselors.insert_one({"user_id": counselor["_id"], "full_name": counselor["full_name"], "specialization": "Student well-being", "contact_email": counselor["email"], "availability": "Demo hours", "is_active": True, "synthetic": True})
    return students


async def _seed_student(db: Any, email: str, user: dict[str, Any], chats: dict[str, Any], today: date) -> None:
    days = chats[email]["days"]
    targets = chats[email]["sentiments"]
    checkins = CHECKINS[email]
    for index, scripted in enumerate(days):
        day = today - timedelta(days=9 - index)
        start = _day_start(day)
        count = len(scripted) // 2
        if count:
            session_id = ObjectId()
            await db.chat_sessions.insert_one({"_id": session_id, "student_id": user["_id"], "started_at": start, "last_message_at": start, "status": "closed", "synthetic": True})
            for message_index, text in enumerate(scripted):
                message_result = await db.messages.insert_one({"session_id": session_id, "student_id": user["_id"], "sender": "student" if message_index % 2 == 0 else "assistant", "text": text, "created_at": start + timedelta(hours=14, minutes=message_index * 3), "response_mode": "guided" if message_index % 2 else None, "synthetic": True})
                if message_index % 2 == 0:
                    if CRISIS_PATTERN.search(normalize_text(text)):
                        raise ValueError(f"Crisis phrase in demo corpus: {email} day {index + 1}")
                    target = targets[index] if index < len(targets) else 0.0
                    await db.sentiment_results.insert_one({"message_id": message_result.inserted_id, "student_id": user["_id"], "date": start, "sentiment_score": target, "dominant_emotion": "joy" if target > 0.2 else "sadness" if target < -0.2 else "neutral", "confidence": 0.9, "synthetic": True})
        row = checkins[index]
        if row is not None:
            data = CheckinRequest(**row)
            saved = await submit_checkin(db, user["_id"], data, as_of=start)
            daily_scores = [
                result["sentiment_score"]
                async for result in db.sentiment_results.find(
                    {"student_id": user["_id"], "date": start},
                    {"sentiment_score": 1},
                )
            ]
            await db.behavioral_signals.update_one(
                {"_id": saved["_id"]},
                {"$set": {
                    "chat_messages_count": count,
                    "avg_sentiment": (
                        sum(daily_scores) / len(daily_scores) if daily_scores else None
                    ),
                    "synthetic": True,
                }},
            )
        elif count:
            daily_scores = [
                result["sentiment_score"]
                async for result in db.sentiment_results.find(
                    {"student_id": user["_id"], "date": start},
                    {"sentiment_score": 1},
                )
            ]
            await db.behavioral_signals.update_one(
                {"student_id": user["_id"], "date": start},
                {"$set": {
                    "chat_messages_count": count,
                    "avg_sentiment": (
                        sum(daily_scores) / len(daily_scores) if daily_scores else None
                    ),
                    "synthetic": True,
                }, "$setOnInsert": {
                    "student_id": user["_id"], "date": start, "checkin_completed": False,
                }},
                upsert=True,
            )


async def seed(reset: bool) -> None:
    if os.getenv("ALLOW_DEMO_SEED", "").lower() != "true":
        raise SystemExit("Refusing demo seed: set ALLOW_DEMO_SEED=true explicitly.")
    await connect_to_mongo()
    db = get_database()
    try:
        await create_indexes(db)
        conflicts = await db.users.find(
            {"email": {"$in": ALL_EMAILS}, "synthetic": {"$ne": True}},
            {"email": 1},
        ).to_list(length=100)
        if conflicts:
            emails = ", ".join(item["email"] for item in conflicts)
            raise SystemExit(f"Refusing to mix demo data with real accounts: {emails}")
        existing_demo = await db.users.find_one({"email": {"$in": ALL_EMAILS}, "synthetic": True})
        if reset or existing_demo is not None:
            await _delete_demo_data(db)
        students = await _seed_accounts(db)
        chats = _load_chats()
        today = datetime.now(timezone.utc).date()
        for email, user in students.items():
            await _seed_student(db, email, user, chats, today)
        results = {}
        for email, user in students.items():
            for index in range(10):
                result = await get_risk_status(db, user["_id"], as_of=today - timedelta(days=9 - index))
                if result["risk_level"] == "INSUFFICIENT_DATA":
                    await db.risk_scores.update_one({"student_id": user["_id"], "date": _day_start(today - timedelta(days=9 - index))}, {"$set": {"risk_level": result["risk_level"], "student_id": user["_id"], "date": _day_start(today - timedelta(days=9 - index)), "synthetic": True}}, upsert=True)
            latest = await get_risk_status(db, user["_id"], as_of=today)
            results[email] = latest
        student_ids = [user["_id"] for user in students.values()]
        await db.baselines.update_many(
            {"student_id": {"$in": student_ids}}, {"$set": {"synthetic": True}}
        )
        await db.risk_scores.update_many(
            {"student_id": {"$in": student_ids}}, {"$set": {"synthetic": True}}
        )
        bilal = students["bilal@mindpulse.com"]
        bilal_result = results["bilal@mindpulse.com"]
        if bilal_result["risk_level"] == "HIGH" and bilal_result["consecutive_days_at_level"] >= 3:
            await create_sustained_escalations(db, bilal["_id"], today - timedelta(days=bilal_result["consecutive_days_at_level"] - 3), bilal_result["consecutive_days_at_level"])
            await db.escalation_events.update_many(
                {"student_id": bilal["_id"]}, {"$set": {"synthetic": True}}
            )
            await db.audit_logs.update_many(
                {"student_id": bilal["_id"]}, {"$set": {"synthetic": True}}
            )
        print("role\temail\tpassword\tresult")
        for email in STUDENT_EMAILS:
            result = results[email]
            print(f"student\t{email}\t{PASSWORD}\t{result['risk_level']} / alert={'yes' if result.get('escalation_sent') else 'no'}")
        print(f"parent\tparent@mindpulse.com\t{PASSWORD}\tlinked to Bilal only")
        print(f"counselor\tcounselor@mindpulse.com\t{PASSWORD}\tdemo counselor profile")
        print(f"admin\tadmin@mindpulse.com\t{PASSWORD}\taggregate dashboard")
        print(f"student\tlive@mindpulse.com\t{PASSWORD}\tempty live-demo account")
        for email, result in results.items():
            if email == "bilal@mindpulse.com" and result["risk_level"] != "HIGH":
                print(f"WARNING: Bilal actual result was {result}; adjust persona values, not the engine.")
            if email == "hamza@mindpulse.com" and result.get("escalation_sent"):
                print(f"WARNING: Hamza unexpectedly escalated: {result}; adjust persona values, not the engine.")
            if email == "zainab@mindpulse.com" and result["risk_level"] == "HIGH":
                print(f"WARNING: Zainab actual result was HIGH: {result}; adjust persona values, not the engine.")
    finally:
        await close_mongo_connection()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete synthetic demo data before recreating it")
    args = parser.parse_args()
    asyncio.run(seed(args.reset))


if __name__ == "__main__":
    main()
