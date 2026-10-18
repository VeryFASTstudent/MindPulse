"""Rolling baseline calculations from completed daily check-ins."""

from datetime import date, datetime
from statistics import mean
from typing import Any


def day_key(value: datetime | date) -> date:
    return value.date() if isinstance(value, datetime) else value


def build_baseline(rows: list[dict[str, Any]], sentiments_by_day: dict[date, list[float]]) -> dict[str, Any] | None:
    if not rows:
        return None

    sentiments = [
        score
        for row in rows
        for score in sentiments_by_day.get(day_key(row["date"]), [])
    ]
    return {
        "typical_stress": round(mean(row["self_rated_stress"] for row in rows), 4),
        "typical_workload": round(mean(row["workload"] for row in rows), 4),
        "typical_sleep": round(mean(row["sleep_hours"] for row in rows), 4),
        "typical_engagement": round(mean(row.get("chat_messages_count", 0) for row in rows), 4),
        "typical_sentiment": round(mean(sentiments), 4) if sentiments else None,
        "sample_size": len(rows),
        "sentiment_sample_size": len(sentiments),
    }