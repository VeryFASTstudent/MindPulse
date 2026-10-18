from datetime import datetime

from pydantic import BaseModel


class DailySentimentOut(BaseModel):
    """One row per day: average sentiment across that day's chat messages."""

    date: datetime
    avg_sentiment: float  # -1 (very negative) .. +1 (very positive)
    message_count: int
