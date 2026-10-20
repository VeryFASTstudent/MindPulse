from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.core.object_id import PyObjectId


class EscalationStatus(str, Enum):
    new = "new"
    acknowledged = "acknowledged"
    closed = "closed"


class EscalationOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    student_id: PyObjectId
    student_name: str | None = None
    risk_level: str
    consecutive_days: int
    summary: str
    status: EscalationStatus
    trigger_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class EscalationStatusUpdate(BaseModel):
    status: EscalationStatus
