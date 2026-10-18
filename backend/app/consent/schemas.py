from datetime import datetime

from pydantic import BaseModel

from app.core.object_id import PyObjectId


class ConsentUpdate(BaseModel):
    share_summary_with_parent: bool
    share_with_university_support: bool
    allow_referral_data_share: bool


class ConsentOut(ConsentUpdate):
    student_id: PyObjectId
    updated_at: datetime
