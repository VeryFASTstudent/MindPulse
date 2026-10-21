from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.object_id import PyObjectId


class ChatMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value


class CheckinConfirmRequest(BaseModel):
    session_id: PyObjectId
    action: Literal["confirm", "edit", "cancel"] = "confirm"


class MessageOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    session_id: PyObjectId
    sender: str
    text: str
    created_at: datetime
    response_mode: str | None = None
    synthetic: bool = False

    model_config = {"populate_by_name": True}


class ChatReplyResponse(BaseModel):
    session_id: PyObjectId
    student_message: MessageOut
    assistant_message: MessageOut
    response_mode: str
    checkin_state: str | None = None
    checkin_draft: dict | None = None


class SessionOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    student_id: PyObjectId
    started_at: datetime
    last_message_at: datetime
    status: str

    model_config = {"populate_by_name": True}
