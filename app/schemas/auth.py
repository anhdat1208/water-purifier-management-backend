from __future__ import annotations

from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponseSchema(BaseModel, Generic[T]):
    data: T
    message: str | None = None


class AuthTokensOut(BaseModel):
    access_token: str
    refresh_token: str


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6)


class RegisterIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1, max_length=200)


class ForgotPasswordIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class RefreshTokenIn(BaseModel):
    refresh_token: str


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    status: str | None = None
    created_at: datetime | None = None
    last_login_at: datetime | None = None
