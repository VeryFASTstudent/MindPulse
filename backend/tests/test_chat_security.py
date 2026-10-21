import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.chat.guardrails import classify_input, normalize_text, validate_model_output
from app.risk_engine.scoring import score_risk


class ChatSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = Path(__file__).parent / "fixtures" / "chat_redteam.json"
        cls.cases = json.loads(fixture.read_text(encoding="utf-8"))

    def test_redteam_fixture(self):
        failures = []
        benign_false_positives = 0
        category_counts = {}
        for case in self.cases:
            actual, _ = classify_input(case["text"])
            category_counts.setdefault(case["category"], [0, 0])
            category_counts[case["category"]][1] += 1
            if actual == case["expected"]:
                category_counts[case["category"]][0] += 1
            else:
                failures.append((case["text"], case["expected"], actual))
            if case["expected"] == "allowed" and actual != "allowed":
                benign_false_positives += 1
        pass_rates = {
            category: f"{passed}/{total} ({passed / total:.0%})"
            for category, (passed, total) in category_counts.items()
        }
        print("security pass rates:", pass_rates)
        print("benign false positives:", benign_false_positives)
        self.assertFalse(failures, failures)

    def test_normalization_removes_zero_width_and_controls(self):
        self.assertEqual(normalize_text("  stress\u200b\n\t today "), "stress today")

    def test_output_filter_rejects_sensitive_content(self):
        self.assertEqual(validate_model_output("token", "token"), "canary_or_length")
        self.assertEqual(validate_model_output("You have depression", "secret"), "diagnosis")
        self.assertEqual(validate_model_output("Visit https://example.com", "secret"), "unapproved_url")
        self.assertEqual(validate_model_output("x" * 1201, "secret"), "canary_or_length")

    def test_score_coverage_returns_insufficient_data(self):
        result = score_risk(
            {"stress": 2},
            {"typical_stress": 2},
            {"stress_deviation": 0.25, "min_signal_coverage": 0.5},
        )
        self.assertEqual(result["risk_level"], "INSUFFICIENT_DATA")

    def test_full_coverage_still_scores(self):
        result = score_risk(
            {"stress": 8, "workload": 8, "sleep_hours": 4, "chat_messages_count": 0},
            {"typical_stress": 2, "typical_workload": 2, "typical_sleep": 8, "typical_engagement": 4},
        )
        self.assertIn(result["risk_level"], {"LOW", "MEDIUM", "HIGH"})

    def test_chat_client_context_has_only_prompt_and_session_messages(self):
        from ai import llm_client
        fake = AsyncMock()
        fake.chat.completions.create.return_value = type(
            "Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": '{"in_scope": true, "reply": "Okay."}'})()})()]}
        )()
        with patch.object(llm_client, "_client", fake):
            import asyncio
            asyncio.run(llm_client.generate_chat_reply([{"role": "user", "content": "Tell me about clouds"}]))
        messages = fake.chat.completions.create.await_args.kwargs["messages"]
        history = [message for message in messages if message["role"] != "system"]
        self.assertNotIn("risk", json.dumps(history).lower())
        self.assertNotIn("baseline", json.dumps(history).lower())
        self.assertNotIn("consent", json.dumps(history).lower())

    def test_chat_text_is_not_logged_by_llm_client(self):
        from ai import llm_client
        with patch.object(llm_client.logger, "warning") as warning:
            with patch.object(llm_client, "_client", None):
                import asyncio
                asyncio.run(llm_client.generate_chat_reply([{"role": "user", "content": "PRIVATE CHAT TEXT"}]))
        self.assertNotIn("PRIVATE CHAT TEXT", str(warning.call_args))


if __name__ == "__main__":
    unittest.main()
