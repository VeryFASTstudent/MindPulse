import unittest
from datetime import datetime, timedelta

from app.baseline.service import build_baseline
from app.risk_engine.scoring import (
    WEIGHTS,
    calculate_deviations,
    consecutive_days_at_level,
    score_risk,
    smooth_risk_score,
)


class RiskScoringTests(unittest.TestCase):
    def test_baseline_weights_recent_checkins_and_available_sentiment(self):
        start = datetime(2026, 1, 1)
        rows = [
            {
                "date": start + timedelta(days=index),
                "self_rated_stress": index + 1,
                "workload": 4,
                "sleep_hours": 7.5,
                "chat_messages_count": index,
            }
            for index in range(2)
        ]

        baseline = build_baseline(rows, {start.date(): [-0.5, 0.5]})

        self.assertEqual(baseline["sample_size"], 2)
        self.assertEqual(baseline["typical_stress"], 1.5405)
        self.assertEqual(baseline["typical_engagement"], 0.5405)
        self.assertEqual(baseline["typical_sentiment"], 0.0)
        self.assertEqual(baseline["sentiment_sample_size"], 2)

    def test_no_checkins_produces_no_baseline(self):
        self.assertIsNone(build_baseline([], {}))

    def test_high_risk_requires_consecutive_days(self):
        today = datetime(2026, 1, 3).date()
        scored_days = [
            {"date": datetime(2026, 1, day), "risk_level": "HIGH"}
            for day in (1, 2, 3)
        ]

        self.assertEqual(consecutive_days_at_level(scored_days, today, "HIGH"), 3)

    def test_a_gap_breaks_the_persistence_streak(self):
        today = datetime(2026, 1, 4).date()
        scored_days = [
            {"date": datetime(2026, 1, 1), "risk_level": "HIGH"},
            {"date": datetime(2026, 1, 3), "risk_level": "HIGH"},
            {"date": datetime(2026, 1, 4), "risk_level": "HIGH"},
        ]

        self.assertEqual(consecutive_days_at_level(scored_days, today, "HIGH"), 2)

    def test_configured_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)

    def test_negative_sentiment_and_worse_checkin_increase_score(self):
        baseline = {
            "typical_sentiment": 1.0,
            "typical_stress": 1.0,
            "typical_workload": 1.0,
            "typical_sleep": 8.0,
            "typical_engagement": 0.0,
        }
        today = {
            "avg_sentiment": -1.0,
            "stress": 10,
            "workload": 10,
            "sleep_hours": 0.0,
            "chat_messages_count": 0,
        }

        result = score_risk(today, baseline)

        self.assertEqual(result["risk_level"], "HIGH")
        self.assertGreater(result["weighted_score"], 0.65)
        self.assertEqual(result["raw_components"]["sentiment_deviation"], 1.0)

    def test_missing_sentiment_is_omitted_and_remaining_weights_are_normalized(self):
        baseline = {"typical_stress": 2.0, "typical_workload": 3.0, "typical_sleep": 8.0}
        today = {"stress": 2.0, "workload": 3.0, "sleep_hours": 8.0}

        result = score_risk(today, baseline)

        self.assertNotIn("sentiment_deviation", result["raw_components"])
        self.assertEqual(result["weighted_score"], 0.0)
        self.assertEqual(result["risk_level"], "LOW")

    def test_missing_all_comparable_signals_returns_no_score(self):
        self.assertIsNone(score_risk({}, {}))

    def test_moving_average_smooths_one_high_day_before_classification(self):
        result = smooth_risk_score([0.2, 0.3], 0.9)

        self.assertEqual(result["weighted_score"], 0.4667)
        self.assertEqual(result["raw_weighted_score"], 0.9)
        self.assertEqual(result["risk_level"], "MEDIUM")

    def test_deviations_are_clipped_to_zero_and_one(self):
        deviations = calculate_deviations(
            {"avg_sentiment": 1.0, "stress": 0, "sleep_hours": 24},
            {"typical_sentiment": -1.0, "typical_stress": 10, "typical_sleep": 0},
        )

        self.assertEqual(deviations["sentiment_deviation"], 0.0)
        self.assertEqual(deviations["stress_deviation"], 0.0)
        self.assertEqual(deviations["sleep_deviation"], 0.0)


if __name__ == "__main__":
    unittest.main()