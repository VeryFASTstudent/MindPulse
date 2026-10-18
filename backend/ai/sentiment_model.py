"""
Local sentiment/emotion analysis (blueprint Section 5B).

Why a separate local model instead of asking the chatbot LLM to rate
sentiment: the model that writes supportive replies should not also be the
judge of the student's emotional state. A small dedicated classifier is
cheap, runs on CPU, is swappable, and can be evaluated on its own.

Model: j-hartmann/emotion-english-distilroberta-base
Outputs probabilities for 7 emotions: anger, disgust, fear, joy, neutral,
sadness, surprise.

The risk engine (Phase 8) needs ONE continuous number per message, so we
collapse the 7 probabilities into a sentiment_score in [-1, 1] using a
fixed valence table:

    sentiment_score = sum(probability_i * valence_i)

Using all probabilities (not just the top label) means an uncertain
prediction naturally lands near neutral instead of committing to one label.
The valence values are a configurable assumption -- document and justify
them in the FYP report, and adjust them during evaluation.

`transformers` is imported lazily so the backend still starts (and every
other feature still works) on a machine where the model isn't installed.
"""

import asyncio
import logging
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)

# How positive/negative each emotion is treated as. Assumption, not a
# clinical measurement -- tune during evaluation.
EMOTION_VALENCE = {
    "joy": 1.0,
    "surprise": 0.1,
    "neutral": 0.0,
    "disgust": -0.5,
    "fear": -0.6,
    "sadness": -0.7,
    "anger": -0.8,
}

# Messages longer than this are truncated before inference (the model's
# context limit is 512 tokens; characters are a cheap safe upper bound).
MAX_CHARS = 1500


def score_from_predictions(predictions: list[dict]) -> dict:
    """
    Pure function (no model needed, easy to unit test).

    predictions: [{"label": "sadness", "score": 0.71}, ...] -- one entry per
    emotion label. Returns the sentiment_score plus the dominant emotion.
    """
    if not predictions:
        raise ValueError("No predictions returned by the sentiment model")

    sentiment = sum(
        float(p["score"]) * EMOTION_VALENCE.get(p["label"].lower(), 0.0)
        for p in predictions
    )
    top = max(predictions, key=lambda p: float(p["score"]))
    return {
        "sentiment_score": round(max(-1.0, min(1.0, sentiment)), 4),
        "dominant_emotion": top["label"].lower(),
        "confidence": round(float(top["score"]), 4),
    }


@lru_cache(maxsize=1)
def _get_pipeline():
    # Loaded once per process. First call downloads the model (~330 MB)
    # from the HuggingFace Hub and caches it on disk; later runs load from
    # the cache in a few seconds.
    from transformers import pipeline  # lazy import, see module docstring

    return pipeline(
        "text-classification",
        model=settings.sentiment_model_name,
        top_k=None,  # return probabilities for ALL emotions
    )


def _run_inference_sync(text: str) -> dict:
    result = _get_pipeline()(text[:MAX_CHARS], truncation=True, max_length=512)
    # Depending on the transformers version, a single string yields either
    # [[{...}, ...]] or [{...}, ...]; normalize to a flat list.
    predictions = result[0] if result and isinstance(result[0], list) else result
    return score_from_predictions(predictions)


async def analyze_sentiment(text: str) -> dict:
    """
    Runs inference in a worker thread so the (synchronous, CPU-bound)
    model call never blocks the FastAPI event loop.
    """
    return await asyncio.to_thread(_run_inference_sync, text)


async def warm_up() -> None:
    """
    Loads the model at startup (in the background) so the first student
    message doesn't pay the load/download cost. Failure here is logged,
    never raised -- the app must still start without the model.
    """
    if not settings.sentiment_enabled:
        return
    try:
        await asyncio.to_thread(_get_pipeline)
        logger.info("Sentiment model loaded: %s", settings.sentiment_model_name)
    except Exception:
        logger.exception("Sentiment model could not be loaded; sentiment will be skipped")
