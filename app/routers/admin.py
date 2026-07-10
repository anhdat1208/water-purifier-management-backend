from __future__ import annotations

from typing_extensions import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.response import success
from app.core.security import hash_password
from app.database import get_db
from app.dependencies import get_admin_user
from app.models.entities import User, UserRole, UserStatus
from app.schemas.admin import AdminUserCreate, AdminUserUpdate, SystemSettingsUpdate
from app.services.business import (
    admin_user_to_out,
    get_admin_stats,
    get_system_settings,
    settings_to_out,
)

router = APIRouter(prefix="/admin", tags=["Quản trị"])


@router.get("/stats")
def admin_stats(
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success(get_admin_stats(db).model_dump())


@router.get("/users")
def list_users(
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return success([admin_user_to_out(u).model_dump(mode="json") for u in users])


@router.get("/users/{user_id}")
def get_user(
    user_id: UUID,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    user = _get_user_or_404(db, user_id)
    return success(admin_user_to_out(user).model_dump(mode="json"))


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email đã được sử dụng.")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=UserRole(payload.role),
        status=UserStatus(payload.status),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return success(admin_user_to_out(user).model_dump(mode="json"))


@router.put("/users/{user_id}")
def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    current_admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    user = _get_user_or_404(db, user_id)
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates and updates["email"]:
        existing = db.scalar(select(User).where(User.email == updates["email"], User.id != user_id))
        if existing:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email đã được sử dụng.")
    if "role" in updates and updates["role"] is not None:
        updates["role"] = UserRole(updates["role"])
    if "status" in updates and updates["status"] is not None:
        updates["status"] = UserStatus(updates["status"])
    if "password" in updates and updates["password"]:
        updates["password_hash"] = hash_password(updates.pop("password"))
    elif "password" in updates:
        updates.pop("password")

    for key, value in updates.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return success(admin_user_to_out(user).model_dump(mode="json"))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    current_admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if current_admin.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Không thể xóa tài khoản của chính bạn.")
    user = _get_user_or_404(db, user_id)
    db.delete(user)
    db.commit()
    return None


@router.get("/settings")
def get_settings(
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success(settings_to_out(get_system_settings(db)).model_dump())


@router.put("/settings")
def update_settings(
    payload: SystemSettingsUpdate,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if payload.filter_critical_threshold >= payload.filter_warning_threshold:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ngưỡng cảnh báo phải lớn hơn ngưỡng nguy hiểm.",
        )
    row = get_system_settings(db)
    row.site_name = payload.site_name
    row.maintenance_mode = payload.maintenance_mode
    row.filter_warning_threshold = payload.filter_warning_threshold
    row.filter_critical_threshold = payload.filter_critical_threshold
    row.notification_email = payload.notification_email
    row.auto_notify_filter_due = payload.auto_notify_filter_due
    db.commit()
    db.refresh(row)
    return success(settings_to_out(row).model_dump())


def _get_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    return user
