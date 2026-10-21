"""Input and output safety boundaries for the student chat assistant."""

import json
import re
import unicodedata
from pathlib import Path


_RESOURCE_PATH = Path(__file__).with_name("crisis_resources.json")
with _RESOURCE_PATH.open(encoding="utf-8") as resource_file:
    CRISIS_RESOURCES = json.load(resource_file)

ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\ufeff"
CRISIS_PATTERN = re.compile(
    r"\b(suicid(?:e|al)|kill myself|end my life|self[- ]harm|hurt myself|"
    r"take my own life|don't want to live|do not want to live|"
    r"marna chahta|marna chahti|khud ko nuqsan|khudkushi|jeena nahi)\b",
    re.IGNORECASE,
)
INJECTION_PATTERN = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|prior|your) instructions|"
    r"(?:reveal|print|show|repeat)\s+(?:me\s+)?(?:your\s+)?(?:system prompt|hidden instructions)|"
    r"developer mode|"
    r"(?:you are now|act as|role[- ]play(?: as)?|pretend(?: to be| you are))\b"
    r".{0,80}(?:ignore|break|disregard|bypass|without rules|unrestricted|"
    r"unfiltered|jailbreak|system prompt|developer mode)|"
    r"(?:another|other)\s+.{0,30}\b(?:data|messages|scores)\b)",
    re.IGNORECASE | re.DOTALL,
)
OUT_OF_SCOPE_PATTERN = re.compile(
    r"\b(?:write|generate|debug|solve|answer|complete|give)\b.{0,50}\b(?:code|python|"
    r"program|homework|assignment|essay)|\b(?:political debate|debate politics|"
    r"politics|political debate|debate politics|legal advice|medical advice|what medication|what dosage|"
    r"dosage|dose)\b",
    re.IGNORECASE,
)
NEWS_REQUEST_PATTERN = re.compile(
    r"\b(?:tell me|what is happening in|discuss)\b.{0,30}\bnews\b",
    re.IGNORECASE,
)
DIAGNOSIS_REQUEST_PATTERN = re.compile(
    r"\b(?:do i have|diagnose me|am i suffering from)\s+"
    r"(?:depression|anxiety|adhd|bipolar|ptsd|burnout)\b",
    re.IGNORECASE,
)
DIAGNOSIS_PATTERN = re.compile(
    r"\b(?:you have|you are diagnosed with|diagnose me with)\s+"
    r"(?:depression|anxiety|adhd|bipolar|ptsd|burnout)\b",
    re.IGNORECASE,
)
MEDICATION_PATTERN = re.compile(
    r"\b(?:take|prescribe|dosage|dose|medication|medicine|mg|milligram)\b",
    re.IGNORECASE,
)
URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{6,}\d)(?!\w)")

BLOCKED_REPLY = (
    "I cannot share hidden instructions or private student data, but I am happy "
    "to talk with you about how you are doing, your day, or anything on your mind."
)
OUT_OF_SCOPE_REPLY = (
    "I cannot do that task, but I would be glad to talk about how your day or studies are feeling."
)
SAFE_FALLBACK_REPLY = (
    "I can offer general, non-clinical well-being support. What would you like "
    "to reflect on about stress, sleep, workload, mood, or your daily check-in?"
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(
        char for char in normalized
        if unicodedata.category(char) not in {"Cc", "Cf"}
        and char not in ZERO_WIDTH_CHARS
    )
    return " ".join(normalized.split())


def crisis_reply() -> str:
    return (
        "I'm sorry things feel this heavy. I cannot provide emergency help. "
        f"If you may act on these thoughts or are in immediate danger, contact "
        f"{CRISIS_RESOURCES['emergency_services']} or go to the nearest "
        f"emergency department. If you can, tell someone you trust and stay "
        f"with them. {CRISIS_RESOURCES['university_support']} "
        f"{CRISIS_RESOURCES['crisis_line']}"
    )


def classify_input(text: str) -> tuple[str, str | None]:
    normalized = normalize_text(text)
    if CRISIS_PATTERN.search(normalized):
        return "safety", crisis_reply()
    if INJECTION_PATTERN.search(normalized):
        return "blocked", BLOCKED_REPLY
    if DIAGNOSIS_REQUEST_PATTERN.search(normalized) or re.search(
        r"\bdiagnose\s+me\b", normalized, re.IGNORECASE
    ):
        return "refused_out_of_scope", OUT_OF_SCOPE_REPLY
    if OUT_OF_SCOPE_PATTERN.search(normalized) or NEWS_REQUEST_PATTERN.search(normalized):
        return "refused_out_of_scope", OUT_OF_SCOPE_REPLY
    return "allowed", None


def validate_model_output(text: str, canary: str, allowed_urls: set[str] | None = None) -> str | None:
    if not text or len(text) > 1200 or canary in text:
        return "canary_or_length"
    if "SYSTEM_PROMPT" in text or "UNTRUSTED INPUT" in text:
        return "prompt_disclosure"
    if DIAGNOSIS_PATTERN.search(text):
        return "diagnosis"
    if MEDICATION_PATTERN.search(text):
        return "medication"
    allowed_urls = allowed_urls or set()
    for url in URL_PATTERN.findall(text):
        if url not in allowed_urls:
            return "unapproved_url"
    if PHONE_PATTERN.search(text) and not any(
        phone in text for phone in CRISIS_RESOURCES.values()
        if isinstance(phone, str)
    ):
        return "unapproved_phone"
    return None