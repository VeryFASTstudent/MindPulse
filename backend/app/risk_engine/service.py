"""Build student baselines and compute persisted, explainable risk status."""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.baseline.service import build_baseline, day_key
from app.dashboards.admin_service import get_risk_configuration
from app.escalations.service import create_sustained_escalations
from app.risk_engine.scoring import (
    RISK_CONFIG,
    consecutive_days_at_level,
    score_risk,
    smooth_risk_score,
)

BASELINE_WINDOW_DAYS = 21
MIN_BASELINE_DAYS = 5
MIN_CONSECUTIVE_DAYS = int(RISK_CONFIG["min_consecutive_days"])


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day)


def _signal_values(row: dict[str, Any], sentiment_by_day: dict[date, list[float]]) -> dict[str, Any]:
    scores = sentiment_by_day.get(day_key(row["date"]), [])
    return {
        "stress": row.get("self_rated_stress"),
        "workload": row.get("workload"),
        "sleep_hours": row.get("sleep_hours"),
        "chat_messages_count": row.get("chat_messages_count", 0),
        "avg_sentiment": sum(scores) / len(scores) if scores else None,
    }


async def get_risk_status(
    db: AsyncIOMotorDatabase,
    student_id: ObjectId,
    as_of: date | None = None,
) -> dict[str, Any]:
    configuration = await get_risk_configuration(db)
    min_consecutive_days = int(configuration["min_consecutive_days"])
    today = as_of or _today_utc()
    start = today - timedelta(days=BASELINE_WINDOW_DAYS - 1)
    rows = await db.behavioral_signals.find(
        {
            "student_id": student_id,
            "date": {"$gte": _midnight(start), "$lt": _midnight(today + timedelta(days=1))},
            "checkin_completed": True,
        }
    ).sort("date", 1).to_list(length=BASELINE_WINDOW_DAYS)

    sentiment_cursor = db.sentiment_results.find(
        {
            "student_id": student_id,
            "date": {"$gte": _midnight(start), "$lt": _midnight(today + timedelta(days=1))},
        },
        {"date": 1, "sentiment_score": 1},
    )
    sentiments_by_day: dict[date, list[float]] = {}
    async for document in sentiment_cursor:
        sentiments_by_day.setdefault(day_key(document["date"]), []).append(
            float(document["sentiment_score"])
        )

    prior_rows = [row for row in rows if day_key(row["date"]) < today]
    today_row = next((row for row in reversed(rows) if day_key(row["date"]) == today), None)

    if today_row is None:
        return {
            "status": "awaiting_checkin",
            "risk_level": "INSUFFICIENT_DATA",
            "sample_size": len(prior_rows),
            "message": "Complete today's check-in to see your well-being status.",
        }

    baseline = build_baseline(prior_rows[-BASELINE_WINDOW_DAYS:], sentiments_by_day)
    if baseline is not None:
        await db.baselines.update_one(
            {"student_id": student_id},
            {"$set": {**baseline, "student_id": student_id, "last_updated": datetime.now(timezone.utc)}},
            upsert=True,
        )

    if baseline is None or baseline["sample_size"] < MIN_BASELINE_DAYS:
        return {
            "status": "insufficient_data",
            "risk_level": "INSUFFICIENT_DATA",
            "sample_size": baseline["sample_size"] if baseline else 0,
            "required_sample_size": MIN_BASELINE_DAYS,
            "message": "Keep checking in; your personal baseline is still building.",
        }

    scored_days: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        prior = rows[max(0, index - BASELINE_WINDOW_DAYS):index]
        if len(prior) < MIN_BASELINE_DAYS:
            continue
        daily_baseline = build_baseline(prior, sentiments_by_day)
        daily_result = score_risk(
            _signal_values(row, sentiments_by_day),
            daily_baseline,
            configuration,
        )
        if daily_result is None or daily_result.get("risk_level") == "INSUFFICIENT_DATA":
            continue
        recent_scores = [
            item.get("raw_weighted_score", item["weighted_score"])
            for item in scored_days[-2:]
        ]
        smoothed_result = smooth_risk_score(
            recent_scores,
            daily_result["weighted_score"],
            configuration,
        )
        daily_result.update(smoothed_result)
        day = day_key(row["date"])
        saved = {
            **daily_result,
            "student_id": student_id,
            "date": _midnight(day),
            "sample_size": daily_baseline["sample_size"],
        }
        await db.risk_scores.update_one(
            {"student_id": student_id, "date": _midnight(day)},
            {"$set": saved},
            upsert=True,
        )
        scored_days.append(saved)

    current = next((item for item in reversed(scored_days) if day_key(item["date"]) == today), None)
    if current is None:
        return {
            "status": "insufficient_data",
            "risk_level": "INSUFFICIENT_DATA",
            "sample_size": baseline["sample_size"],
            "required_sample_size": MIN_BASELINE_DAYS,
            "message": "There is not enough comparable data to calculate today's status.",
        }

    consecutive = consecutive_days_at_level(scored_days, today, current["risk_level"])

    sustained = consecutive >= min_consecutive_days
    escalation_sent = False
    if current["risk_level"] == "HIGH" and sustained:
        trigger_date = today - timedelta(days=consecutive - min_consecutive_days)
        escalation_sent = await create_sustained_escalations(
            db,
            student_id,
            trigger_date,
            consecutive,
        )

    return {
        "status": "sustained" if sustained else "monitoring",
        "risk_level": current["risk_level"] if sustained else "MONITORING",
        "observed_level": current["risk_level"],
        "weighted_score": current["weighted_score"],
        "consecutive_days_at_level": consecutive,
        "sample_size": baseline["sample_size"],
        "required_sample_size": MIN_BASELINE_DAYS,
        "raw_components": current["raw_components"],
        "escalation_sent": escalation_sent,
        "message": (
            f"Your {current['risk_level'].lower()} pattern has continued for {consecutive} days."
            if sustained
            else "Your status is still being monitored; one unusual day does not determine a risk level."
        ),
    }