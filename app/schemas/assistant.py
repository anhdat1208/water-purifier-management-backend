from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AssistantMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: str


class ConversationOut(BaseModel):
    id: str
    messages: list[AssistantMessageOut]
    updated_at: str


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class ChatOut(BaseModel):
    user_message: AssistantMessageOut
    assistant_message: AssistantMessageOut
    conversation_id: str
