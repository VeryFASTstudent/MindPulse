"""Explainable risk score calculations from check-in and chat signals."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


_CONFIG_PATH = Path(__file__).parent / "config" / "risk_weights.json"
with _CONFIG_PATH.open(encoding="utf-8") as config_file:
    RISK_CONFIG = json.load(config_file)

WEIGHTS: dict[str, float] = {
    name: float(value)
    for name, value in RISK_CONFIG.items()
    if name not in {"thresholds", "min_consecutive_days", "min_signal_coverage"}
}
LOW_MAX = float(RISK_CONFIG["thresholds"]["low_max"])
MEDIUM_MAX = float(RISK_CONFIG["thresholds"]["medium_max"])
MIN_SIGNAL_COVERAGE = float(RISK_CONFIG["min_signal_coverage"])


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def consecutive_days_at_level(
    scored_days: list[dict[str, Any]], target_day: date, risk_level: str
) -> int:
    consecutive = 0
    expected_day = target_day
    for item in reversed(scored_days):
        item_date = item["date"]
        item_day = item_date.date() if isinstance(item_date, datetime) else item_date
        if item_day != expected_day or item["risk_level"] != risk_level:
            break
        consecutive += 1
        expected_day -= timedelta(days=1)
    return consecutive


def calculate_deviations(today: dict[str, Any], baseline: dict[str, Any]) -> dict[str, float]:
    """Normalize higher-risk deviations to [0, 1], omitting unavailable inputs."""
    deviations: dict[str, float] = {}

    if today.get("avg_sentiment") is not None and baseline.get("typical_sentiment") is not None:
        deviations["sentiment_deviation"] = _clip(
            (baseline["typical_sentiment"] - today["avg_sentiment"]) / 2
        )

    for field, deviation_name in (
        ("stress", "stress_deviation"),
        ("workload", "workload_deviation"),
    ):
        current = today.get(field)
        typical = baseline.get(f"typical_{field}")
        if current is not None and typical is not None:
            deviations[deviation_name] = _clip((current - typical) / 9)

    sleep = today.get("sleep_hours")
    typical_sleep = baseline.get("typical_sleep")
    if sleep is not None and typical_sleep is not None:
        deviations["sleep_deviation"] = _clip((typical_sleep - sleep) / 8)

    engagement = today.get("chat_messages_count")
    typical_engagement = baseline.get("typical_engagement")
    if engagement is not None and typical_engagement is not None:
        deviations["engagement_deviation"] = _clip(
            (typical_engagement - engagement) / max(typical_engagement, 1)
        )

    return deviations


def score_risk(
    today: dict[str, Any],
    baseline: dict[str, Any],
    configuration: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Calculate a weighted score, renormalizing over signals actually present."""
    deviations = calculate_deviations(today, baseline)
    active_configuration = configuration or RISK_CONFIG
    weights = {
        name: float(active_configuration.get(name, WEIGHTS[name]))
        for name in WEIGHTS
    }
    thresholds = active_configuration.get("thresholds", {})
    low_max = float(active_configuration.get("low_max", thresholds.get("low_max", LOW_MAX)))
    medium_max = float(active_configuration.get("medium_max", thresholds.get("medium_max", MEDIUM_MAX)))
    available_weight = sum(weights[name] for name in deviations)
    if available_weight <= 0:
        return None
    min_signal_coverage = float(
        active_configuration.get("min_signal_coverage", MIN_SIGNAL_COVERAGE)
    )
    if available_weight < min_signal_coverage:
        return {
            "status": "insufficient_data",
            "risk_level": "INSUFFICIENT_DATA",
            "weighted_score": None,
            "raw_components": deviations,
            "signals_used": sorted(deviations),
        }

    score = sum(weights[name] * value for name, value in deviations.items()) / available_weight
    if score < low_max:
        level = "LOW"
    elif score < medium_max:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {
        "weighted_score": round(score, 4),
        "risk_level": level,
        "raw_components": deviations,
        "signals_used": sorted(deviations),
    }


def smooth_risk_score(
    recent_scores: list[float],
    current_score: float,
    configuration: dict[str, Any] | None = None,
    window: int = 3,
) -> dict[str, Any]:
    """Classify a short moving average to reduce single-day risk fluctuations."""
    if window < 1:
        raise ValueError("window must be at least 1")
    scores = [*recent_scores[-(window - 1):], current_score] if window > 1 else [current_score]
    score = sum(scores) / len(scores)
    active_configuration = configuration or RISK_CONFIG
    thresholds = active_configuration.get("thresholds", {})
    low_max = float(active_configuration.get("low_max", thresholds.get("low_max", LOW_MAX)))
    medium_max = float(
        active_configuration.get("medium_max", thresholds.get("medium_max", MEDIUM_MAX))
    )
    if score < low_max:
        level = "LOW"
    elif score < medium_max:
        level = "MEDIUM"
    else:
        level = "HIGH"
    return {
        "weighted_score": round(score, 4),
        "risk_level": level,
        "raw_weighted_score": round(current_score, 4),
        "smoothing_window": len(scores),
    }