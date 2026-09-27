from datetime import datetime

from pydantic import BaseModel, Field

from app.core.object_id import PyObjectId


class ChatMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    session_id: PyObjectId
    sender: str
    text: str
    created_at: datetime

    model_config = {"populate_by_name": True}


class ChatReplyResponse(BaseModel):
    session_id: PyObjectId
    student_message: MessageOut
    assistant_message: MessageOut


class SessionOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    student_id: PyObjectId
    started_at: datetime
    last_message_at: datetime
    status: str

    model_config = {"populate_by_name": True}
