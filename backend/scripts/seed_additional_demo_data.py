"""Add the Hira/Usman/Rida evaluation accounts without replacing existing demos."""
import argparse
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone, time
from pathlib import Path
from bson import ObjectId
from app.auth.security import hash_password
from app.behavior.schemas import CheckinRequest
from app.behavior.service import submit_checkin
from app.chat.guardrails import CRISIS_PATTERN, normalize_text
from app.db.indexes import create_indexes
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.risk_engine.service import get_risk_status
from app.escalations.service import create_sustained_escalations, MESSAGE_TEMPLATES

DATA = Path(__file__).with_name("hira_usman_rida_chats.json")
STUDENT_KEYS = {"hira", "usman", "rida"}
EXTRA_EMAILS = {
    "hira.imtiaz22@gmail.com", "usman.farooq21@gmail.com", "rida.siddiqui23@gmail.com",
    "imtiaz.hussain58@gmail.com", "farooq.ahmed60@gmail.com", "shabana.siddiqui@gmail.com",
    "psychologist@gmail.com", "admin.mindpulse@gmail.com", "live.demo@gmail.com",
    "maryam.anwar22@gmail.com", "talha.mehmood21@gmail.com", "areeba.khan23@gmail.com",
}

async def remove_existing(db):
    users = await db.users.find({"email": {"$in": list(EXTRA_EMAILS)}}, {"_id": 1}).to_list(length=100)
    ids = [u["_id"] for u in users]
    await db.users.delete_many({"email": {"$in": list(EXTRA_EMAILS)}})
    for name in ("student_profiles", "consents", "baselines", "behavioral_signals", "sentiment_results", "risk_scores", "chat_sessions", "messages", "escalation_events", "alert_deliveries", "audit_logs", "counselors"):
        query = {"synthetic": True}
        if ids and name in {"student_profiles", "counselors"}: query = {"user_id": {"$in": ids}}
        elif ids and name not in {"audit_logs", "alert_deliveries"}: query = {"student_id": {"$in": ids}}
        await db[name].delete_many(query)

async def add_user(db, email, name, role, password, **extra):
    user = {"_id": ObjectId(), "email": email, "full_name": name, "role": role, "password_hash": hash_password(password), "linked_student_ids": extra.pop("linked_student_ids", []), "created_at": datetime.now(timezone.utc), "is_active": True, "synthetic": True, **extra}
    await db.users.insert_one(user)
    return user

async def force_hira_demo_alert(db, hira):
    """Presentation-only synthetic alert; never used for real students."""
    consent = await db.consents.find_one({"student_id": hira["_id"]})
    if not consent:
        return
    now = datetime.now(timezone.utc)
    trigger = datetime.combine(now.date(), time.min)
    counselor = await db.users.find_one({"role": "counselor", "is_active": True}, {"_id": 1})
    parent = await db.users.find_one({"role": "parent", "linked_student_ids": hira["_id"], "is_active": True}, {"_id": 1})
    targets = []
    if consent.get("share_with_university_support") and counselor:
        targets.append(("counselor", counselor["_id"], "email", "psychologist@gmail.com", MESSAGE_TEMPLATES["psychologist"].format(student_name=hira["full_name"], email=hira["email"], days=3)))
    if consent.get("share_summary_with_parent") and parent and consent.get("parent_phone"):
        targets.append(("parent", parent["_id"], "whatsapp", consent["parent_phone"], MESSAGE_TEMPLATES["parent"].format(first_name=hira["full_name"].split()[0])))
    for role, recipient_id, channel, recipient, text in targets:
        event = {"student_id": hira["_id"], "recipient_id": recipient_id, "recipient_role": role, "risk_level": "HIGH", "consecutive_days": 3, "summary": "Synthetic demo alert only. No chat content or raw scores are shared.", "status": "new", "trigger_date": trigger, "created_at": now, "updated_at": now, "synthetic": True, "demo_forced": True}
        result = await db.escalation_events.update_one({"student_id": hira["_id"], "recipient_id": recipient_id, "trigger_date": trigger}, {"$setOnInsert": event}, upsert=True)
        alert_id = result.upserted_id or (await db.escalation_events.find_one({"student_id": hira["_id"], "recipient_id": recipient_id, "trigger_date": trigger}, {"_id": 1}))["_id"]
        await db.alert_deliveries.update_one({"alert_id": alert_id, "channel": channel}, {"$setOnInsert": {"alert_id": alert_id, "student_id": hira["_id"], "channel": channel, "recipient": recipient, "message_text": text, "status": "queued", "created_at": now, "synthetic": True, "demo_forced": True}}, upsert=True)

async def seed(reset=False):
    if os.getenv("ALLOW_DEMO_SEED", "").lower() != "true":
        raise SystemExit("Set ALLOW_DEMO_SEED=true before running this additive seed.")
    await connect_to_mongo(); db = get_database()
    try:
        await create_indexes(db)
        if reset or await db.users.find_one({"email": {"$in": list(EXTRA_EMAILS)}}): await remove_existing(db)
        corpus = json.loads(DATA.read_text(encoding="utf-8"))
        today = datetime.now(timezone.utc).date()
        students = {}
        for item in corpus["students"]:
            user = await add_user(db, item["email"], item["full_name"], "student", item["password"], is_fast_student=item["is_fast_student"])
            students[item["key"]] = user
            await db.student_profiles.insert_one({"user_id": user["_id"], "is_fast_student": item["is_fast_student"], "created_at": datetime.now(timezone.utc), "synthetic": True})
            await db.consents.insert_one({"student_id": user["_id"], "share_with_university_support": item["psychologist"], "share_summary_with_parent": item["parent"], "allow_referral_data_share": item["parent"], "parent_name": item.get("parent_name"), "parent_phone": item.get("parent_phone"), "reviewed_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc), "synthetic": True})
            for index, day in enumerate(item["days"]):
                day_date = today - timedelta(days=9-index); start = datetime.combine(day_date, time(20, 0))
                saved = await submit_checkin(db, user["_id"], CheckinRequest(self_rated_stress=day["checkin"]["stress"], workload=day["checkin"]["workload"], sleep_hours=day["checkin"]["sleep_hours"], activity_score=day["checkin"]["activity"]), as_of=start)
                count = len(day["messages"])
                await db.behavioral_signals.update_one({"_id": saved["_id"]}, {"$set": {"chat_messages_count": count, "avg_sentiment": day["avg_sentiment"], "synthetic": True}})
                session = ObjectId()
                await db.chat_sessions.insert_one({"_id": session, "student_id": user["_id"], "started_at": start, "last_message_at": start, "status": "closed", "synthetic": True})
                for msg_index, pair in enumerate(day["messages"]):
                    student_text, assistant_text = pair
                    if CRISIS_PATTERN.search(normalize_text(student_text)): raise ValueError(f"Crisis phrase in {item['key']} day {index+1}")
                    created = start + timedelta(minutes=msg_index * 3)
                    student_message = await db.messages.insert_one({"session_id": session, "student_id": user["_id"], "sender": "student", "text": student_text, "created_at": created, "synthetic": True})
                    await db.sentiment_results.insert_one({"message_id": student_message.inserted_id, "student_id": user["_id"], "date": datetime.combine(day_date, time.min), "sentiment_score": day["avg_sentiment"], "dominant_emotion": day["emotion"], "confidence": 0.9, "synthetic": True})
                    await db.messages.insert_one({"session_id": session, "student_id": user["_id"], "sender": "assistant", "text": assistant_text, "created_at": created + timedelta(minutes=2), "response_mode": "guided", "synthetic": True})
        await add_user(db, "psychologist@gmail.com", "University Psychologist", "counselor", "Psych@2026Pulse")
        await db.counselors.insert_one({"user_id": (await db.users.find_one({"email":"psychologist@gmail.com"}))["_id"], "full_name":"University Psychologist", "specialization":"Student well-being", "contact_email":"psychologist@gmail.com", "availability":"Demo hours", "is_active":True, "synthetic":True})
        for key, student_email in {"hira":"hira.imtiaz22@gmail.com", "usman":"usman.farooq21@gmail.com", "rida":"rida.siddiqui23@gmail.com"}.items():
            student = students[key]
            parent_email = {"hira":"imtiaz.hussain58@gmail.com", "usman":"farooq.ahmed60@gmail.com", "rida":"shabana.siddiqui@gmail.com"}[key]
            parent = await add_user(db, parent_email, f"{key.title()} Parent", "parent", "Parent@2026Pulse", linked_student_ids=[student["_id"]])
        await add_user(db, "admin.mindpulse@gmail.com", "MindPulse Admin", "admin", "Admin@2026Pulse")
        live = await add_user(db, "live.demo@gmail.com", "Live Demo", "student", "Live@2026Pulse", is_fast_student=True)
        await db.student_profiles.insert_one({"user_id":live["_id"],"is_fast_student":True,"synthetic":True})
        await db.consents.insert_one({"student_id":live["_id"],"share_with_university_support":True,"share_summary_with_parent":True,"allow_referral_data_share":True,"reviewed_at":datetime.now(timezone.utc),"updated_at":datetime.now(timezone.utc),"synthetic":True})
        for email, user in students.items():
            result = None
            for offset in range(10):
                result = await get_risk_status(db, user["_id"], as_of=today - timedelta(days=9-offset))
                if result.get("observed_level") == "HIGH" and result.get("consecutive_days_at_level", 0) >= 3:
                    await create_sustained_escalations(
                        db,
                        user["_id"],
                        today - timedelta(days=9-offset + result["consecutive_days_at_level"] - 3),
                        result["consecutive_days_at_level"],
                    )
            result = await get_risk_status(db, user["_id"], as_of=today)
            print(f"{email}: {result['risk_level']} observed={result.get('observed_level')} consecutive={result.get('consecutive_days_at_level')} alert={result.get('escalation_sent')}")
        await force_hira_demo_alert(db, students["hira"])
        print("hira demo_forced alert: HIGH, psychologist + parent deliveries queued")
        print("Additional Hira/Usman/Rida accounts seeded.")
    finally: await close_mongo_connection()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--reset", action="store_true"); args = parser.parse_args(); asyncio.run(seed(args.reset))
