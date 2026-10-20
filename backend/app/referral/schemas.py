from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, HttpUrl, model_validator

from app.core.object_id import PyObjectId


class ReferralStatus(str, Enum):
    requested = "requested"
    accepted = "accepted"
    declined = "declined"
    completed = "completed"


class ReferralRequestCreate(BaseModel):
    counselor_id: PyObjectId
    student_confirmed: bool


class CounselorOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    full_name: str
    specialization: str = ""
    contact_email: str = ""
    availability: str = ""

    model_config = {"populate_by_name": True}


class ExternalSupportResourceBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    specialization: str = Field(min_length=2, max_length=160)
    contact_email: EmailStr | None = None
    website_url: HttpUrl | None = None
    cost_description: str = Field(min_length=2, max_length=120)

    @model_validator(mode="after")
    def require_contact_method(self):
        if self.contact_email is None and self.website_url is None:
            raise ValueError("Provide a verified contact email or website URL")
        return self


class ExternalSupportResourceCreate(ExternalSupportResourceBase):
    pass


class ExternalSupportResourceOut(ExternalSupportResourceBase):
    id: PyObjectId = Field(alias="_id")
    is_active: bool = True

    model_config = {"populate_by_name": True}


class ExternalResourceStatusUpdate(BaseModel):
    is_active: bool


class ReferralOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    student_id: PyObjectId | None = None
    student_name: str | None = None
    counselor_id: PyObjectId
    status: ReferralStatus
    requested_at: datetime
    updated_at: datetime
    student_consent_confirmed: bool

    model_config = {"populate_by_name": True}


class ReferralStatusUpdate(BaseModel):
    status: ReferralStatus
