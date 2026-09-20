from __future__ import annotations

from pydantic import BaseModel, Field


class PushSubscribeIn(BaseModel):
    token: str = Field(min_length=1)
    user_agent: str | None = None


class PushUnsubscribeIn(BaseModel):
    token: str = Field(min_length=1)
