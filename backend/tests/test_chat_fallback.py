import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from ai import llm_client


class GuidedReplyTests(unittest.TestCase):
    def test_greeting_gets_a_warm_reply_and_conversation_starter(self):
        for greeting in ("hi", "Hello!", "hey there", "good morning"):
            with self.subTest(greeting=greeting):
                reply = llm_client.generate_guided_reply(
                    [{"role": "user", "content": greeting}]
                )

                self.assertIn("Hi!", reply)
                self.assertIn("How are you feeling today?", reply)

    def test_stress_message_gets_a_relevant_reflective_prompt(self):
        reply = llm_client.generate_guided_reply(
            [{"role": "user", "content": "I am overwhelmed with exams."}]
        )

        self.assertIn("pressure", reply)
        self.assertIn("10-minute", reply)

    def test_crisis_language_gets_immediate_human_support_guidance(self):
        reply = llm_client.generate_guided_reply(
            [{"role": "user", "content": "I want to hurt myself."}]
        )

        self.assertIn("local emergency services", reply)
        self.assertIn("someone you trust", reply)

    def test_follow_up_uses_the_latest_student_message(self):
        reply = llm_client.generate_guided_reply(
            [
                {"role": "user", "content": "I could not sleep."},
                {"role": "assistant", "content": "What is going on?"},
                {"role": "user", "content": "I feel lonely."},
            ]
        )

        self.assertIn("What has felt hardest today", reply)


class HostedReplyTests(unittest.IsolatedAsyncioTestCase):
    def test_gemini_configuration_uses_openai_compatible_endpoint(self):
        with (
            patch.object(llm_client.settings, "chat_provider", "gemini"),
            patch.object(llm_client.settings, "gemini_api_key", "test-key"),
            patch.object(llm_client.settings, "gemini_chat_model", "gemini-test"),
            patch.object(llm_client, "AsyncOpenAI") as openai_client,
        ):
            client, model = llm_client._create_hosted_client()

        self.assertIs(client, openai_client.return_value)
        self.assertEqual(model, "gemini-test")
        openai_client.assert_called_once_with(
            api_key="test-key",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    async def test_quota_or_provider_error_returns_guided_response_and_mode(self):
        create = AsyncMock(side_effect=RuntimeError("provider unavailable"))
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        with patch.object(llm_client, "_client", client):
            reply, mode = await llm_client.generate_chat_reply(
                [{"role": "user", "content": "My roommate keeps leaving dishes everywhere."}]
            )

        self.assertEqual(mode, "guided")
        self.assertIn("what part of this has been affecting you", reply)

    async def test_successful_hosted_completion_is_marked_hosted(self):
        create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="That sounds difficult.")
                    )
                ]
            )
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        with patch.object(llm_client, "_client", client):
            reply, mode = await llm_client.generate_chat_reply(
                [{"role": "user", "content": "My roommate keeps leaving dishes everywhere."}]
            )

        self.assertEqual(reply, "That sounds difficult.")
        self.assertEqual(mode, "hosted")

    async def test_intent_reply_is_primary_and_skips_hosted_model(self):
        create = AsyncMock()
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        with patch.object(llm_client, "_client", client):
            reply, mode = await llm_client.generate_chat_reply(
                [{"role": "user", "content": "Hi"}]
            )

        self.assertEqual(mode, "intent")
        self.assertIn("How are you feeling today?", reply)
        create.assert_not_awaited()

    async def test_crisis_intent_routes_to_safety_reply_without_hosted_model(self):
        create = AsyncMock()
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        with patch.object(llm_client, "_client", client):
            reply, mode = await llm_client.generate_chat_reply(
                [{"role": "user", "content": "I want to hurt myself."}]
            )

        self.assertEqual(mode, "safety")
        self.assertIn("local emergency services", reply)
        create.assert_not_awaited()

    async def test_unrecognized_message_uses_gemini_after_intent_check(self):
        create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="Let's think through what to say.")
                    )
                ]
            )
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        with (
            patch.object(llm_client, "_client", client),
            patch.object(llm_client, "_chat_model", "gemini-test"),
        ):
            reply, mode = await llm_client.generate_chat_reply(
                [{"role": "user", "content": "My roommate keeps leaving dishes everywhere."}]
            )

        self.assertEqual(mode, "hosted")
        self.assertEqual(reply, "Let's think through what to say.")
        self.assertEqual(create.await_args.kwargs["model"], "gemini-test")


if __name__ == "__main__":
    unittest.main()
