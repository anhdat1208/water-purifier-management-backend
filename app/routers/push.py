from __future__ import annotations

from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import get_current_user
from app.models.entities import PushSubscription, User
from app.schemas.push import PushSubscribeIn, PushUnsubscribeIn

router = APIRouter(prefix="/push", tags=["Push"])


@router.post("/subscribe")
def subscribe(
    payload: PushSubscribeIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    token = payload.token.strip()
    subscription = db.scalar(select(PushSubscription).where(PushSubscription.fcm_token == token))
    if subscription is not None and subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Push subscription đã thuộc về người dùng khác.",
        )

    if subscription is None:
        subscription = PushSubscription(
            user_id=current_user.id,
            fcm_token=token,
            user_agent=payload.user_agent,
        )
        db.add(subscription)
    else:
        subscription.user_agent = payload.user_agent

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        subscription = db.scalar(select(PushSubscription).where(PushSubscription.fcm_token == token))
        if subscription is None:
            raise
        if subscription.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Push subscription đã thuộc về người dùng khác.",
            )
        subscription.user_agent = payload.user_agent
        db.commit()
    return success({"token": subscription.fcm_token})


@router.delete("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(
    payload: PushUnsubscribeIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    subscription = db.scalar(
        select(PushSubscription).where(
            PushSubscription.fcm_token == payload.token.strip(),
            PushSubscription.user_id == current_user.id,
        )
    )
    if subscription is not None:
        db.delete(subscription)
        db.commit()
    return None
