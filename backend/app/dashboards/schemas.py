from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.object_id import PyObjectId
from app.escalations.schemas import EscalationOut


class ParentStudentSummary(BaseModel):
    student_id: PyObjectId
    full_name: str
    last_checkin_at: datetime | None = None
    average_stress: float | None = None
    average_sleep_hours: float | None = None
    latest_wellbeing_status: str | None = None
    escalations: list[EscalationOut] = Field(default_factory=list)


class AdminOverview(BaseModel):
    available: bool
    suppressed: bool
    period_days: int
    cohort_size: int | None = None
    risk_distribution: dict[str, int]
    message: str


class StudentAlertDeliveryOut(BaseModel):
    channel: Literal["email", "whatsapp"]
    recipient: str
    message_text: str
    status: str
    created_at: datetime


class AdminUserOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    full_name: str
    email: str
    role: Literal["student", "parent", "counselor", "admin"]
    is_active: bool
    created_at: datetime

    model_config = {"populate_by_name": True}


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class AuditEventOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    actor_type: str
    actor_id: PyObjectId | None = None
    action: str
    status: str | None = None
    created_at: datetime

    model_config = {"populate_by_name": True}


class RiskConfiguration(BaseModel):
    sentiment_deviation: float = Field(gt=0, le=1)
    stress_deviation: float = Field(gt=0, le=1)
    workload_deviation: float = Field(gt=0, le=1)
    sleep_deviation: float = Field(gt=0, le=1)
    engagement_deviation: float = Field(gt=0, le=1)
    low_max: float = Field(gt=0, lt=1)
    medium_max: float = Field(gt=0, lt=1)
    min_consecutive_days: int = Field(ge=2, le=14)
    min_signal_coverage: float = Field(default=0.5, gt=0, le=1)

    @model_validator(mode="after")
    def validate_thresholds_and_weights(self):
        if self.low_max >= self.medium_max:
            raise ValueError("low_max must be lower than medium_max")
        weights = (
            self.sentiment_deviation,
            self.stress_deviation,
            self.workload_deviation,
            self.sleep_deviation,
            self.engagement_deviation,
        )
        if abs(sum(weights) - 1.0) > 0.001:
            raise ValueError("Risk weights must add up to 1.0")
        return self
