from datetime import datetime

from pydantic import BaseModel, Field

from app.core.object_id import PyObjectId


class CheckinRequest(BaseModel):
    # 1-10 scales match the blueprint's normalization design (Section 6) --
    # a fixed, small range that's easy to clip/normalize in the risk engine
    # (Phase 8) without extra unit conversion.
    self_rated_stress: int = Field(ge=1, le=10)
    workload: int = Field(ge=1, le=10)
    sleep_hours: float = Field(ge=0, le=24)
    activity_score: int = Field(ge=0, le=10)


class CheckinOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    student_id: PyObjectId
    date: datetime
    self_rated_stress: int
    workload: int
    sleep_hours: float
    activity_score: int
    checkin_completed: bool

    model_config = {"populate_by_name": True}


class StreakOut(BaseModel):
    streak: int
