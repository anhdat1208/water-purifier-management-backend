from __future__ import annotations

from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)


class PushSubscribeIn(BaseModel):
    endpoint: str = Field(min_length=1)
    keys: PushKeys
    user_agent: str | None = None


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=1)


class VapidPublicKeyOut(BaseModel):
    public_key: str
