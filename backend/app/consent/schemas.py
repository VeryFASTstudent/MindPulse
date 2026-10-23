from datetime import datetime

from pydantic import BaseModel, Field, field_validator
import re

from app.core.object_id import PyObjectId


class ConsentUpdate(BaseModel):
    share_summary_with_parent: bool
    share_with_university_support: bool
    allow_referral_data_share: bool
    parent_phone: str | None = None
    parent_name: str | None = None
    reviewed_at: datetime | None = None

    @field_validator("parent_phone")
    @classmethod
    def normalize_parent_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        digits = re.sub(r"\D", "", value)
        if digits.startswith("03") and len(digits) == 11:
            return "+92" + digits[1:]
        if digits.startswith("923") and len(digits) == 12:
            return "+" + digits
        raise ValueError("Use a Pakistani mobile number: 03XXXXXXXXX or +923XXXXXXXXX")


class ConsentOut(ConsentUpdate):
    student_id: PyObjectId
    updated_at: datetime
