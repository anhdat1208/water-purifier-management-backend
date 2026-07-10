from __future__ import annotations

from datetime import date
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.response import success
from app.database import get_db
from app.dependencies import get_current_user
from app.models.entities import ActivityType, Filter, FilterType, Purifier, User
from app.schemas.filter import FilterCreate, FilterOut, FilterUpdate
from app.services.business import filter_to_out, log_activity, sync_purifier_filter_life

router = APIRouter(prefix="/filters", tags=["Lõi lọc"])


@router.get("")
def list_filters(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    filters = db.scalars(
        select(Filter)
        .options(joinedload(Filter.purifier))
        .where(Filter.user_id == current_user.id)
        .order_by(Filter.id)
    ).all()
    return success([filter_to_out(f).model_dump(mode="json") for f in filters])


@router.get("/{filter_id}")
def get_filter(
    filter_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    filter_item = _get_user_filter(db, current_user, filter_id)
    return success(filter_to_out(filter_item).model_dump(mode="json"))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_filter(
    payload: FilterCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _ensure_purifier_owner(db, current_user, payload.purifier_id)
    filter_item = Filter(
        user_id=current_user.id,
        purifier_id=payload.purifier_id,
        name=payload.name,
        type=FilterType(payload.type),
        stage=payload.stage,
        life_percent=payload.life_percent,
        lifespan_days=payload.lifespan_days,
        installed_date=payload.installed_date,
        last_replaced_date=payload.last_replaced_date,
        notes=payload.notes,
    )
    db.add(filter_item)
    db.commit()
    db.refresh(filter_item)
    filter_item = db.scalar(
        select(Filter).options(joinedload(Filter.purifier)).where(Filter.id == filter_item.id)
    )
    sync_purifier_filter_life(db, payload.purifier_id)
    return success(filter_to_out(filter_item).model_dump(mode="json"))


@router.put("/{filter_id}")
def update_filter(
    filter_id: int,
    payload: FilterUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    filter_item = _get_user_filter(db, current_user, filter_id)
    updates = payload.model_dump(exclude_unset=True)
    if "type" in updates and updates["type"] is not None:
        updates["type"] = FilterType(updates["type"])
    if "purifier_id" in updates and updates["purifier_id"] is not None:
        _ensure_purifier_owner(db, current_user, updates["purifier_id"])
    for key, value in updates.items():
        setattr(filter_item, key, value)
    db.commit()
    db.refresh(filter_item)
    filter_item = db.scalar(
        select(Filter).options(joinedload(Filter.purifier)).where(Filter.id == filter_item.id)
    )
    sync_purifier_filter_life(db, filter_item.purifier_id)
    return success(filter_to_out(filter_item).model_dump(mode="json"))


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_filter(
    filter_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    filter_item = _get_user_filter(db, current_user, filter_id)
    purifier_id = filter_item.purifier_id
    db.delete(filter_item)
    db.commit()
    sync_purifier_filter_life(db, purifier_id)
    return None


@router.post("/{filter_id}/replace")
def replace_filter(
    filter_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    filter_item = _get_user_filter(db, current_user, filter_id)
    today = date.today()
    filter_item.life_percent = 100
    filter_item.last_replaced_date = today
    db.commit()
    db.refresh(filter_item)
    filter_item = db.scalar(
        select(Filter).options(joinedload(Filter.purifier)).where(Filter.id == filter_item.id)
    )
    sync_purifier_filter_life(db, filter_item.purifier_id)
    log_activity(
        db,
        current_user.id,
        "Đã thay lõi lọc",
        f"{filter_item.name} trên {filter_item.purifier.name} đã được thay mới.",
        ActivityType.FILTER,
    )
    return success(filter_to_out(filter_item).model_dump(mode="json"))


def _get_user_filter(db: Session, user: User, filter_id: int) -> Filter:
    filter_item = db.scalar(
        select(Filter)
        .options(joinedload(Filter.purifier))
        .where(Filter.id == filter_id, Filter.user_id == user.id)
    )
    if filter_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lõi lọc.")
    return filter_item


def _ensure_purifier_owner(db: Session, user: User, purifier_id: int) -> Purifier:
    purifier = db.scalar(select(Purifier).where(Purifier.id == purifier_id, Purifier.user_id == user.id))
    if purifier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy máy lọc.")
    return purifier
