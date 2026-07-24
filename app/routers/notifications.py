from __future__ import annotations

from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import get_current_user
from app.models.entities import Notification, User
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Thông báo"])


@router.get("")
def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    base_query = select(Notification).where(Notification.user_id == current_user.id)
    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0
    unread_count = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
    ) or 0
    notifications = db.scalars(
        base_query.order_by(Notification.sent_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return success(
        {
            "items": [NotificationOut.model_validate(item).model_dump(mode="json") for item in notifications],
            "total": total,
            "page": page,
            "page_size": page_size,
            "unread_count": unread_count,
        }
    )


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    notification = _get_user_notification(db, current_user, notification_id)
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return success(NotificationOut.model_validate(notification).model_dump(mode="json"))


@router.post("/read-all")
def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return success({"updated": result.rowcount})


def _get_user_notification(db: Session, user: User, notification_id: int) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông báo.")
    return notification
