"""
Conversational AI wrapper (Section 5 of the blueprint: "Conversational AI").

This module has exactly one job: turn a conversation history into a
supportive, non-clinical reply. It has NO knowledge of risk scores,
baselines, or behavioral signals, and nothing it returns is ever written
to risk_scores directly -- that separation is intentional and is what
keeps the eventual risk decision explainable (see app/risk_engine,
built in Phase 8).

If the OpenAI API is unavailable or misconfigured, generate_chat_reply
falls back to a fixed supportive message instead of raising -- per
Section 19 (Error Handling), an AI outage should never block the chat
feature outright.
"""

from openai import AsyncOpenAI

from app.core.config import settings

SYSTEM_PROMPT = """You are the in-app supportive companion inside MindPulse, \
an app that helps university students stay aware of their well-being during \
stressful academic periods.

Your role:
- Listen and respond with warmth to what the student shares about stress, \
workload, motivation, sleep, or their general mood.
- Ask gentle, open follow-up questions when it helps the student reflect.
- Suggest practical, general well-being strategies (e.g. breaking down \
workload, short breaks, talking to someone they trust) when relevant.
- If a student describes something serious -- persistent hopelessness, \
thoughts of self-harm, or a crisis -- respond with care, take it seriously, \
and clearly encourage them to reach out to a counselor, a trusted person, or \
a crisis line right away.

Strict boundaries -- never break these:
- You are NOT a licensed therapist or psychiatrist. Never diagnose any \
condition (e.g. "it sounds like you have depression/anxiety").
- Never claim to replace professional help. When appropriate, gently \
encourage the student to consider talking to the university counselor \
available in the app.
- Keep responses conversational and concise (a few sentences), not \
clinical or lecture-like.
"""

FALLBACK_REPLY = (
    "I'm having trouble responding right now, but I still want to hear "
    "what's going on. Could you try sending that again in a moment? If "
    "you need to talk to someone right away, the Support tab can connect "
    "you with a university counselor."
)

_client: AsyncOpenAI | None = None
if settings.openai_api_key:
    _client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_chat_reply(conversation_history: list[dict]) -> str:
    """
    conversation_history: list of {"role": "user"|"assistant", "content": str},
    oldest first. Building this list is the caller's job (app/chat/service.py)
    since it needs to read prior messages from MongoDB first.
    """
    if _client is None:
        # No API key configured -- fail safely rather than crash the endpoint.
        return FALLBACK_REPLY

    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *conversation_history],
            max_tokens=300,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return content.strip() if content else FALLBACK_REPLY
    except Exception:
        # Broad catch is intentional here: any failure mode (rate limit,
        # network error, malformed response) should degrade to the fallback
        # message rather than surface a 500 to the student.
        return FALLBACK_REPLY
