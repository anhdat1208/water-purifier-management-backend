from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PurifierStatus(str, enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"


class FilterType(str, enum.Enum):
    SEDIMENT = "sediment"
    CARBON = "carbon"
    RO_MEMBRANE = "ro_membrane"
    MINERAL = "mineral"
    POST_CARBON = "post_carbon"


class ActivityType(str, enum.Enum):
    FILTER = "filter"
    MAINTENANCE = "maintenance"
    ALERT = "alert"
    SYSTEM = "system"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


def _pg_enum(enum_cls: type[enum.Enum], name: str, **kwargs):
    return mapped_column(
        Enum(enum_cls, name=name, values_callable=lambda members: [member.value for member in members]),
        **kwargs,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = _pg_enum(UserRole, "userrole", default=UserRole.USER, nullable=False)
    status: Mapped[UserStatus] = _pg_enum(UserStatus, "userstatus", default=UserStatus.ACTIVE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    purifiers: Mapped[List["Purifier"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    filters: Mapped[List["Filter"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    activities: Mapped[List["Activity"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Purifier(Base):
    __tablename__ = "purifiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    install_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PurifierStatus] = _pg_enum(PurifierStatus, "purifierstatus", default=PurifierStatus.ACTIVE)
    filter_life_percent: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="purifiers")
    filters: Mapped[List["Filter"]] = relationship(back_populates="purifier", cascade="all, delete-orphan")


class Filter(Base):
    __tablename__ = "filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purifier_id: Mapped[int] = mapped_column(Integer, ForeignKey("purifiers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[FilterType] = _pg_enum(FilterType, "filtertype", nullable=False)
    stage: Mapped[int] = mapped_column(Integer, nullable=False)
    life_percent: Mapped[int] = mapped_column(Integer, default=100)
    lifespan_days: Mapped[int] = mapped_column(Integer, default=180)
    installed_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_replaced_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="filters")
    purifier: Mapped["Purifier"] = relationship(back_populates="filters")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[ActivityType] = _pg_enum(ActivityType, "activitytype", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="activities")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = _pg_enum(MessageRole, "messagerole", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    site_name: Mapped[str] = mapped_column(String(200), default="Water Purifier Management")
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    filter_warning_threshold: Mapped[int] = mapped_column(Integer, default=40)
    filter_critical_threshold: Mapped[int] = mapped_column(Integer, default=20)
    notification_email: Mapped[str] = mapped_column(String(255), default="alerts@waterpurifier.local")
    auto_notify_filter_due: Mapped[bool] = mapped_column(Boolean, default=True)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("filter_id", "sent_date", name="uq_notifications_filter_sent_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("filters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purifier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("purifiers.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(50), default="filter_due", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    remaining_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    owner: Mapped["User"] = relationship()
