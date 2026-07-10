from __future__ import annotations

from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import get_current_user
from app.models.entities import User
from app.schemas.auth import (
    AuthTokensOut,
    ForgotPasswordIn,
    LoginIn,
    RefreshTokenIn,
    RegisterIn,
    UserProfileOut,
)
from app.services.business import login_user, refresh_tokens, register_user, user_to_profile

router = APIRouter(prefix="/auth", tags=["Xác thực"])


@router.post("/login")
def login(payload: LoginIn, db: Annotated[Session, Depends(get_db)]):
    tokens: AuthTokensOut = login_user(db, payload.email, payload.password)
    return success(tokens.model_dump())


@router.post("/register")
def register(payload: RegisterIn, db: Annotated[Session, Depends(get_db)]):
    profile: UserProfileOut = register_user(db, payload.email, payload.password, payload.full_name)
    return success(profile.model_dump(mode="json"), message="Đăng ký thành công.")


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordIn, db: Annotated[Session, Depends(get_db)]):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user:
        pass  # MVP: không gửi email thật
    return success({"message": "Nếu email tồn tại, liên kết đặt lại mật khẩu đã được gửi."})


@router.get("/me")
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return success(user_to_profile(current_user).model_dump(mode="json"))


@router.post("/refresh")
def refresh(payload: RefreshTokenIn, db: Annotated[Session, Depends(get_db)]):
    tokens: AuthTokensOut = refresh_tokens(db, payload.refresh_token)
    return success(tokens.model_dump())
