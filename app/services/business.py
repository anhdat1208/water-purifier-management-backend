from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.redis_client import is_refresh_token_valid, revoke_refresh_token, store_refresh_token
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.entities import (
    Activity,
    ActivityType,
    Conversation,
    Filter,
    Message,
    MessageRole,
    Purifier,
    PurifierStatus,
    SystemSettings,
    User,
    UserRole,
    UserStatus,
)
from app.schemas.admin import AdminStatsOut, AdminUserOut, SystemSettingsOut
from app.schemas.assistant import AssistantMessageOut, ChatOut, ConversationOut
from app.schemas.auth import AuthTokensOut, UserProfileOut
from app.schemas.dashboard import (
    DashboardOverviewOut,
    DashboardStatsOut,
    DeviceAttentionItem,
    FilterLifeTrendPoint,
    RecentActivityItem,
    StatusDistribution,
)
from app.schemas.filter import FilterOut
from app.schemas.purifier import PurifierOut


def user_to_profile(user: User) -> UserProfileOut:
    return UserProfileOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        status=user.status.value,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def purifier_to_out(purifier: Purifier) -> PurifierOut:
    return PurifierOut(
        id=purifier.id,
        name=purifier.name,
        model=purifier.model,
        location=purifier.location,
        install_date=purifier.install_date,
        status=purifier.status.value,
        filter_life_percent=purifier.filter_life_percent,
    )


def compute_filter_life_percent(
    last_replaced_date: date,
    lifespan_days: int,
    today: date | None = None,
) -> int:
    """% tuổi thọ còn lại theo số ngày đã dùng từ lần thay gần nhất."""
    if lifespan_days <= 0:
        return 0
    as_of = today or date.today()
    days_used = (as_of - last_replaced_date).days
    if days_used <= 0:
        return 100
    remaining_ratio = 1 - (days_used / lifespan_days)
    return max(0, min(100, round(remaining_ratio * 100)))


def filter_to_out(filter_item: Filter) -> FilterOut:
    life_percent = compute_filter_life_percent(
        filter_item.last_replaced_date,
        filter_item.lifespan_days,
    )
    return FilterOut(
        id=filter_item.id,
        name=filter_item.name,
        type=filter_item.type.value,
        purifier_id=filter_item.purifier_id,
        purifier_name=filter_item.purifier.name if filter_item.purifier else "",
        stage=filter_item.stage,
        life_percent=life_percent,
        lifespan_days=filter_item.lifespan_days,
        installed_date=filter_item.installed_date,
        last_replaced_date=filter_item.last_replaced_date,
        notes=filter_item.notes,
    )


def login_user(db: Session, email: str, password: str) -> AuthTokensOut:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(str(user.id))
    refresh_token, jti = create_refresh_token(str(user.id))
    ttl = settings.refresh_token_expire_days * 24 * 60 * 60
    store_refresh_token(jti, str(user.id), ttl)
    return AuthTokensOut(access_token=access_token, refresh_token=refresh_token)


def register_user(db: Session, email: str, password: str, full_name: str) -> UserProfileOut:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email đã được sử dụng.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_profile(user)


def refresh_tokens(db: Session, refresh_token: str) -> AuthTokensOut:
    from jose import JWTError

    from app.core.security import decode_token

    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ.")
        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not jti or not user_id or not is_refresh_token_valid(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ.")

    revoke_refresh_token(jti)
    user = db.get(User, UUID(user_id))
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không hợp lệ.")

    access_token = create_access_token(str(user.id))
    new_refresh_token, new_jti = create_refresh_token(str(user.id))
    ttl = settings.refresh_token_expire_days * 24 * 60 * 60
    store_refresh_token(new_jti, str(user.id), ttl)
    return AuthTokensOut(access_token=access_token, refresh_token=new_refresh_token)


def sync_purifier_filter_life(db: Session, purifier_id: int) -> None:
    purifier = db.get(Purifier, purifier_id)
    if purifier is None:
        return
    filters = db.scalars(select(Filter).where(Filter.purifier_id == purifier_id)).all()
    if not filters:
        return
    for filter_item in filters:
        filter_item.life_percent = compute_filter_life_percent(
            filter_item.last_replaced_date,
            filter_item.lifespan_days,
        )
    purifier.filter_life_percent = min(filter_item.life_percent for filter_item in filters)
    db.commit()


def get_system_settings(db: Session) -> SystemSettings:
    settings_row = db.get(SystemSettings, 1)
    if settings_row is None:
        settings_row = SystemSettings(id=1)
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


def settings_to_out(row: SystemSettings) -> SystemSettingsOut:
    return SystemSettingsOut(
        site_name=row.site_name,
        maintenance_mode=row.maintenance_mode,
        filter_warning_threshold=row.filter_warning_threshold,
        filter_critical_threshold=row.filter_critical_threshold,
        notification_email=row.notification_email,
        auto_notify_filter_due=row.auto_notify_filter_due,
    )


def get_dashboard_overview(db: Session, user: User) -> DashboardOverviewOut:
    sys_settings = get_system_settings(db)
    for purifier_id in db.scalars(select(Purifier.id).where(Purifier.user_id == user.id)).all():
        sync_purifier_filter_life(db, purifier_id)

    purifiers = list(db.scalars(select(Purifier).where(Purifier.user_id == user.id)).all())
    filters = list(
        db.scalars(
            select(Filter).options(joinedload(Filter.purifier)).where(Filter.user_id == user.id)
        ).all()
    )

    total = len(purifiers)
    active = sum(1 for p in purifiers if p.status == PurifierStatus.ACTIVE)
    maintenance = sum(1 for p in purifiers if p.status == PurifierStatus.MAINTENANCE)
    inactive = sum(1 for p in purifiers if p.status == PurifierStatus.INACTIVE)
    filters_due = sum(
        1 for f in filters if f.life_percent <= sys_settings.filter_warning_threshold
    )

    trend = _build_filter_life_trend(filters)
    attention = _build_attention_list(purifiers, sys_settings)
    activities = _get_recent_activities(db, user.id)

    return DashboardOverviewOut(
        stats=DashboardStatsOut(
            total_devices=total,
            active_devices=active,
            maintenance_devices=maintenance,
            filters_due_soon=filters_due,
        ),
        filter_life_trend=trend,
        status_distribution=StatusDistribution(active=active, maintenance=maintenance, inactive=inactive),
        devices_needing_attention=attention,
        recent_activities=activities,
    )


def _build_filter_life_trend(filters: list[Filter]) -> list[FilterLifeTrendPoint]:
    labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    if not filters:
        return [FilterLifeTrendPoint(label=label, value=0) for label in labels]

    avg = sum(f.life_percent for f in filters) / len(filters)
    step = max(2, int(avg / len(labels)))
    values = [min(100, max(0, int(avg - step * i))) for i in range(len(labels))]
    return [FilterLifeTrendPoint(label=label, value=value) for label, value in zip(labels, values)]


def _build_attention_list(purifiers: list[Purifier], sys_settings: SystemSettings) -> list[DeviceAttentionItem]:
    items: list[DeviceAttentionItem] = []
    for p in purifiers:
        reason = None
        if p.filter_life_percent <= sys_settings.filter_critical_threshold:
            reason = f"Mức lõi lọc dưới {sys_settings.filter_critical_threshold}%"
        elif p.filter_life_percent <= sys_settings.filter_warning_threshold:
            reason = "Sắp đến hạn thay lõi"
        elif p.status == PurifierStatus.MAINTENANCE:
            reason = "Cần bảo trì gấp"

        if reason:
            items.append(
                DeviceAttentionItem(
                    id=p.id,
                    name=p.name,
                    location=p.location,
                    filter_life_percent=p.filter_life_percent,
                    status=p.status.value,
                    reason=reason,
                )
            )
    return items[:10]


def _get_recent_activities(db: Session, user_id: UUID) -> list[RecentActivityItem]:
    rows = db.scalars(
        select(Activity).where(Activity.user_id == user_id).order_by(Activity.created_at.desc()).limit(10)
    ).all()
    return [
        RecentActivityItem(
            id=str(row.id),
            title=row.title,
            description=row.description,
            created_at=row.created_at.isoformat(),
            type=row.type.value,
        )
        for row in rows
    ]


def log_activity(db: Session, user_id: UUID, title: str, description: str, activity_type: ActivityType) -> None:
    db.add(Activity(user_id=user_id, title=title, description=description, type=activity_type))
    db.commit()


def get_admin_stats(db: Session) -> AdminStatsOut:
    sys_settings = get_system_settings(db)
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    active_users = db.scalar(select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)) or 0
    admin_users = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)) or 0
    total_devices = db.scalar(select(func.count()).select_from(Purifier)) or 0
    total_filters = db.scalar(select(func.count()).select_from(Filter)) or 0
    filters_due = (
        db.scalar(
            select(func.count()).select_from(Filter).where(Filter.life_percent <= sys_settings.filter_warning_threshold)
        )
        or 0
    )

    critical_count = (
        db.scalar(
            select(func.count())
            .select_from(Filter)
            .where(Filter.life_percent <= sys_settings.filter_critical_threshold)
        )
        or 0
    )
    if critical_count > 0:
        system_status = "critical"
    elif filters_due > 0:
        system_status = "warning"
    else:
        system_status = "healthy"

    return AdminStatsOut(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        total_devices=total_devices,
        total_filters=total_filters,
        filters_due_soon=filters_due,
        system_status=system_status,
    )


def admin_user_to_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        status=user.status.value,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def message_to_out(message: Message) -> AssistantMessageOut:
    return AssistantMessageOut(
        id=str(message.id),
        role=message.role.value,
        content=message.content,
        created_at=message.created_at.isoformat(),
    )


def conversation_to_out(conversation: Conversation) -> ConversationOut:
    return ConversationOut(
        id=str(conversation.id),
        messages=[message_to_out(m) for m in conversation.messages],
        updated_at=conversation.updated_at.isoformat(),
    )


WELCOME_MESSAGE = (
    "Xin chào! Tôi là trợ lý AI của hệ thống quản lý máy lọc nước. Tôi có thể giúp bạn:\n\n"
    "• Kiểm tra lõi lọc cần thay\n"
    "• Tóm tắt trạng thái thiết bị\n"
    "• Hướng dẫn bảo trì và thay lõi\n\n"
    "Bạn muốn hỏi gì?"
)


def get_or_create_conversation(db: Session, user: User, conversation_id: UUID | None = None) -> Conversation:
    if conversation_id:
        conversation = db.scalar(
            select(Conversation)
            .options(joinedload(Conversation.messages))
            .where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        )
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc hội thoại.")
        return conversation

    conversation = db.scalar(
        select(Conversation)
        .options(joinedload(Conversation.messages))
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    if conversation:
        return conversation

    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    db.flush()
    welcome = Message(conversation_id=conversation.id, role=MessageRole.ASSISTANT, content=WELCOME_MESSAGE)
    db.add(welcome)
    db.commit()
    db.refresh(conversation)
    return db.scalar(
        select(Conversation).options(joinedload(Conversation.messages)).where(Conversation.id == conversation.id)
    )


def clear_conversation(db: Session, user: User, conversation_id: UUID | None = None) -> Conversation:
    conversation = get_or_create_conversation(db, user, conversation_id)
    for message in list(conversation.messages):
        db.delete(message)
    welcome = Message(conversation_id=conversation.id, role=MessageRole.ASSISTANT, content=WELCOME_MESSAGE)
    db.add(welcome)
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    return db.scalar(
        select(Conversation).options(joinedload(Conversation.messages)).where(Conversation.id == conversation.id)
    )


def chat(db: Session, user: User, message_text: str, conversation_id: UUID | None = None) -> ChatOut:
    conversation = get_or_create_conversation(db, user, conversation_id)
    user_message = Message(conversation_id=conversation.id, role=MessageRole.USER, content=message_text)
    db.add(user_message)
    db.flush()

    reply = _build_assistant_reply(db, user, message_text)
    assistant_message = Message(conversation_id=conversation.id, role=MessageRole.ASSISTANT, content=reply)
    db.add(assistant_message)
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    return ChatOut(
        user_message=message_to_out(user_message),
        assistant_message=message_to_out(assistant_message),
        conversation_id=str(conversation.id),
    )


def _build_assistant_reply(db: Session, user: User, user_text: str) -> str:
    text = user_text.lower()
    sys_settings = get_system_settings(db)
    purifiers = list(db.scalars(select(Purifier).where(Purifier.user_id == user.id)).all())
    filters = list(
        db.scalars(select(Filter).options(joinedload(Filter.purifier)).where(Filter.user_id == user.id)).all()
    )

    critical = [f for f in filters if f.life_percent <= sys_settings.filter_critical_threshold]
    warning = [f for f in filters if sys_settings.filter_critical_threshold < f.life_percent <= sys_settings.filter_warning_threshold]
    maintenance = [p for p in purifiers if p.status == PurifierStatus.MAINTENANCE]

    if any(k in text for k in ("cần thay", "thay gấp", "sắp thay")):
        if not critical:
            return "Hiện không có lõi lọc nào ở mức cần thay gấp. Bạn có thể theo dõi chi tiết tại mục Lõi lọc."
        lines = [f"• {f.name} ({f.purifier.name}) — còn {f.life_percent}%" for f in critical]
        return f"Có {len(critical)} lõi lọc cần thay gấp:\n\n" + "\n".join(lines) + "\n\nNên lên lịch thay trong tuần này."

    if any(k in text for k in ("trạng thái", "máy lọc", "thiết bị")):
        if not purifiers:
            return "Bạn chưa có máy lọc nào. Hãy thêm máy lọc tại mục Máy lọc nước."
        status_map = {"active": "Hoạt động", "maintenance": "Bảo trì", "inactive": "Ngưng"}
        lines = [
            f"• {p.name} ({p.location}) — {status_map.get(p.status.value, p.status.value)}, lõi còn {p.filter_life_percent}%"
            for p in purifiers
        ]
        active = sum(1 for p in purifiers if p.status == PurifierStatus.ACTIVE)
        return (
            f"Hệ thống có {len(purifiers)} máy lọc:\n\n"
            + "\n".join(lines)
            + f"\n\nTổng quan: {active} đang hoạt động, {len(maintenance)} cần bảo trì."
        )

    if "bảo trì" in text:
        return (
            "Hướng dẫn bảo trì máy lọc RO định kỳ:\n\n"
            "1. Kiểm tra áp suất nước đầu vào mỗi tháng\n"
            "2. Vệ sinh vỏ máy và khu vực lắp đặt\n"
            "3. Thay lõi PP và than hoạt tính mỗi 6 tháng\n"
            "4. Thay màng RO mỗi 12–24 tháng\n"
            "5. Xả nước bồn chứa nếu không dùng quá 3 ngày\n\n"
            f"Hiện có {len(maintenance)} máy đang ở trạng thái bảo trì."
        )

    if any(k in text for k in ("lịch", "bao lâu", "định kỳ")):
        if not filters:
            return "Chưa có lõi lọc nào để lên lịch. Hãy thêm lõi lọc cho máy của bạn."
        lines = [f"• {f.name}: thay mỗi {f.lifespan_days} ngày, còn {f.life_percent}%" for f in filters[:5]]
        return "Lịch thay lõi lọc tham khảo:\n\n" + "\n".join(lines)

    if any(k in text for k in ("cảnh báo", "warning", "nguy hiểm")):
        if not warning and not critical:
            return "Không có cảnh báo nào. Tất cả lõi lọc đang ở mức an toàn."
        parts = []
        if critical:
            parts.append(f"{len(critical)} lõi ở mức nguy hiểm (<{sys_settings.filter_critical_threshold}%)")
        if warning:
            parts.append(f"{len(warning)} lõi cần chú ý (<{sys_settings.filter_warning_threshold}%)")
        return "Cảnh báo hiện tại: " + ", ".join(parts) + "."

    return (
        "Tôi có thể giúp bạn kiểm tra lõi lọc, trạng thái máy lọc, hoặc hướng dẫn bảo trì. "
        "Hãy thử hỏi: \"Lõi lọc nào cần thay gấp?\" hoặc \"Tóm tắt trạng thái thiết bị\"."
    )
