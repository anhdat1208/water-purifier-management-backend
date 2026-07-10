from __future__ import annotations

from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import get_current_user
from app.models.entities import Purifier, PurifierStatus, User
from app.schemas.purifier import PurifierCreate, PurifierOut, PurifierUpdate
from app.services.business import purifier_to_out

router = APIRouter(prefix="/purifiers", tags=["Máy lọc nước"])


@router.get("")
def list_purifiers(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    purifiers = db.scalars(select(Purifier).where(Purifier.user_id == current_user.id).order_by(Purifier.id)).all()
    return success([purifier_to_out(p).model_dump(mode="json") for p in purifiers])


@router.get("/{purifier_id}")
def get_purifier(
    purifier_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    purifier = _get_user_purifier(db, current_user, purifier_id)
    return success(purifier_to_out(purifier).model_dump(mode="json"))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_purifier(
    payload: PurifierCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    purifier = Purifier(
        user_id=current_user.id,
        name=payload.name,
        model=payload.model,
        location=payload.location,
        install_date=payload.install_date,
        status=PurifierStatus(payload.status),
        filter_life_percent=payload.filter_life_percent,
    )
    db.add(purifier)
    db.commit()
    db.refresh(purifier)
    return success(purifier_to_out(purifier).model_dump(mode="json"))


@router.put("/{purifier_id}")
def update_purifier(
    purifier_id: int,
    payload: PurifierUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    purifier = _get_user_purifier(db, current_user, purifier_id)
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = PurifierStatus(updates["status"])
    for key, value in updates.items():
        setattr(purifier, key, value)
    db.commit()
    db.refresh(purifier)
    return success(purifier_to_out(purifier).model_dump(mode="json"))


@router.delete("/{purifier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purifier(
    purifier_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    purifier = _get_user_purifier(db, current_user, purifier_id)
    db.delete(purifier)
    db.commit()
    return None


def _get_user_purifier(db: Session, user: User, purifier_id: int) -> Purifier:
    purifier = db.scalar(select(Purifier).where(Purifier.id == purifier_id, Purifier.user_id == user.id))
    if purifier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy máy lọc.")
    return purifier
