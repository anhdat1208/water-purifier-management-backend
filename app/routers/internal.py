from __future__ import annotations

import os
import secrets
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.response import success
from app.database import get_db
from app.jobs.filter_due_push import run_filter_due_push_job

router = APIRouter(prefix="/internal", tags=["Internal"])


def _require_cron_secret(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected = settings.cron_secret.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET chưa cấu hình.",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu Authorization Bearer.",
        )
    token = authorization[len("Bearer ") :].strip()
    if not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CRON_SECRET không hợp lệ.",
        )


@router.get("/run-filter-due-push")
def run_filter_due_push(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(_require_cron_secret)],
    force: Annotated[bool, Query()] = False,
):
    """Vercel Cron (GET) gọi endpoint này mỗi ngày để quét lõi ≤ 30 ngày.

    `force=true`: gửi lại Web Push dù hôm nay đã có bản ghi lịch sử (dùng để test).
    """
    result = run_filter_due_push_job(db, force_resend=force)
    return success(result)


def is_vercel_runtime() -> bool:
    return os.getenv("VERCEL") == "1"
