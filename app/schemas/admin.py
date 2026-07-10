from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    status: str
    created_at: datetime
    last_login_at: datetime | None = None


class AdminUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=200)
    role: str = "user"
    status: str = "active"
    password: str = Field(min_length=6)


class AdminUserUpdate(BaseModel):
    email: str | None = Field(None, min_length=3, max_length=255)
    full_name: str | None = Field(None, min_length=1, max_length=200)
    role: str | None = None
    status: str | None = None
    password: str | None = Field(None, min_length=6)


class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    total_devices: int
    total_filters: int
    filters_due_soon: int
    system_status: str


class SystemSettingsOut(BaseModel):
    site_name: str
    maintenance_mode: bool
    filter_warning_threshold: int
    filter_critical_threshold: int
    notification_email: str
    auto_notify_filter_due: bool


class SystemSettingsUpdate(BaseModel):
    site_name: str = Field(min_length=1, max_length=200)
    maintenance_mode: bool
    filter_warning_threshold: int = Field(ge=1, le=100)
    filter_critical_threshold: int = Field(ge=1, le=100)
    notification_email: str = Field(min_length=3, max_length=255)
    auto_notify_filter_due: bool
