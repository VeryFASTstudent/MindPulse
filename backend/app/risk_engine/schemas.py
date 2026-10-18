from typing import Literal

from pydantic import BaseModel, Field


class RiskStatusOut(BaseModel):
    status: Literal["awaiting_checkin", "insufficient_data", "monitoring", "sustained"]
    risk_level: Literal["INSUFFICIENT_DATA", "MONITORING", "LOW", "MEDIUM", "HIGH"]
    observed_level: Literal["LOW", "MEDIUM", "HIGH"] | None = None
    weighted_score: float | None = None
    consecutive_days_at_level: int = 0
    sample_size: int = 0
    required_sample_size: int = 5
    raw_components: dict[str, float] = Field(default_factory=dict)
    message: str