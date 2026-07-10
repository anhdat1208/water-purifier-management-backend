from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import (
    Activity,
    ActivityType,
    Filter,
    FilterType,
    Purifier,
    PurifierStatus,
    SystemSettings,
    User,
    UserRole,
    UserStatus,
)
from app.services.business import log_activity, sync_purifier_filter_life


def seed_database(db: Session) -> None:
    if db.scalar(select(User).limit(1)):
        return

    admin = User(
        email="admin@waterpurifier.local",
        password_hash=hash_password("Admin@123"),
        full_name="Quản trị viên",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        last_login_at=datetime.now(timezone.utc),
    )
    demo_user = User(
        email="user@waterpurifier.local",
        password_hash=hash_password("User@123"),
        full_name="Nguyễn Văn A",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        last_login_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db.add_all([admin, demo_user])
    db.flush()

    settings = SystemSettings(
        id=1,
        site_name="Water Purifier Management",
        maintenance_mode=False,
        filter_warning_threshold=40,
        filter_critical_threshold=20,
        notification_email="alerts@waterpurifier.local",
        auto_notify_filter_due=True,
    )
    db.add(settings)

    purifier_data = [
        ("Máy lọc phòng khách", "RO-500", "Phòng khách", date(2024, 3, 15), PurifierStatus.ACTIVE, 72),
        ("Máy lọc bếp", "UF-300", "Nhà bếp", date(2023, 11, 2), PurifierStatus.MAINTENANCE, 15),
        ("Máy lọc phòng ngủ", "RO-400", "Tầng 2", date(2024, 8, 20), PurifierStatus.ACTIVE, 45),
        ("Máy lọc văn phòng", "RO-600", "Tầng 1", date(2022, 5, 10), PurifierStatus.INACTIVE, 5),
        ("Máy lọc sảnh", "UF-250", "Tầng trệt", date(2025, 1, 8), PurifierStatus.MAINTENANCE, 8),
    ]

    purifiers: list[Purifier] = []
    for name, model, location, install_date, status, life in purifier_data:
        p = Purifier(
            user_id=admin.id,
            name=name,
            model=model,
            location=location,
            install_date=install_date,
            status=status,
            filter_life_percent=life,
        )
        db.add(p)
        purifiers.append(p)
    db.flush()

    filter_data = [
        (purifiers[0], "Lõi PP 5 micron", FilterType.SEDIMENT, 1, 68, 180, date(2024, 3, 15), date(2024, 3, 15)),
        (purifiers[0], "Lõi than hoạt tính", FilterType.CARBON, 2, 55, 180, date(2024, 3, 15), date(2024, 9, 1)),
        (purifiers[0], "Màng RO", FilterType.RO_MEMBRANE, 3, 72, 365, date(2024, 3, 15), date(2024, 3, 15)),
        (purifiers[1], "Lõi PP", FilterType.SEDIMENT, 1, 12, 180, date(2023, 11, 2), date(2025, 5, 1)),
        (purifiers[1], "Lõi UF", FilterType.CARBON, 2, 18, 180, date(2023, 11, 2), date(2025, 5, 1)),
        (purifiers[2], "Lõi PP", FilterType.SEDIMENT, 1, 45, 180, date(2024, 8, 20), date(2024, 8, 20)),
        (purifiers[4], "Lõi số 1", FilterType.SEDIMENT, 1, 8, 180, date(2025, 1, 8), date(2025, 1, 8)),
        (purifiers[4], "Lõi số 2", FilterType.POST_CARBON, 2, 10, 180, date(2025, 1, 8), date(2025, 1, 8)),
    ]

    for purifier, name, ftype, stage, life, lifespan, installed, replaced in filter_data:
        db.add(
            Filter(
                user_id=admin.id,
                purifier_id=purifier.id,
                name=name,
                type=ftype,
                stage=stage,
                life_percent=life,
                lifespan_days=lifespan,
                installed_date=installed,
                last_replaced_date=replaced,
            )
        )

    activities = [
        (admin.id, "Nhắc thay lõi lọc", "Máy lọc bếp còn 15% tuổi thọ lõi.", ActivityType.FILTER),
        (admin.id, "Bảo trì định kỳ", "Máy lọc phòng khách đã hoàn tất kiểm tra.", ActivityType.MAINTENANCE),
        (admin.id, "Cảnh báo chất lượng nước", "Máy lọc sảnh có chỉ số TDS tăng nhẹ.", ActivityType.ALERT),
    ]
    for user_id, title, description, atype in activities:
        db.add(Activity(user_id=user_id, title=title, description=description, type=atype))

    db.commit()

    for purifier in purifiers:
        sync_purifier_filter_life(db, purifier.id)

    _ = demo_user
