"""Rolling baseline calculations from completed daily check-ins."""

from datetime import date, datetime
from typing import Any


RECENCY_DECAY = 0.85


def day_key(value: datetime | date) -> date:
    return value.date() if isinstance(value, datetime) else value


def _recency_weighted_mean(values: list[float]) -> float:
    weights = [RECENCY_DECAY ** (len(values) - index - 1) for index in range(len(values))]
    return sum(value * weight for value, weight in zip(values, weights)) / sum(weights)


def build_baseline(rows: list[dict[str, Any]], sentiments_by_day: dict[date, list[float]]) -> dict[str, Any] | None:
    if not rows:
        return None

    ordered_rows = sorted(rows, key=lambda row: day_key(row["date"]))
    daily_sentiments = [
        sum(scores) / len(scores)
        for row in ordered_rows
        if (scores := sentiments_by_day.get(day_key(row["date"]), []))
    ]
    return {
        "typical_stress": round(
            _recency_weighted_mean([row["self_rated_stress"] for row in ordered_rows]), 4
        ),
        "typical_workload": round(
            _recency_weighted_mean([row["workload"] for row in ordered_rows]), 4
        ),
        "typical_sleep": round(
            _recency_weighted_mean([row["sleep_hours"] for row in ordered_rows]), 4
        ),
        "typical_engagement": round(
            _recency_weighted_mean(
                [row.get("chat_messages_count", 0) for row in ordered_rows]
            ),
            4,
        ),
        "typical_sentiment": (
            round(_recency_weighted_mean(daily_sentiments), 4)
            if daily_sentiments
            else None
        ),
        "sample_size": len(ordered_rows),
        "sentiment_sample_size": sum(
            len(sentiments_by_day.get(day_key(row["date"]), []))
            for row in ordered_rows
        ),
    }