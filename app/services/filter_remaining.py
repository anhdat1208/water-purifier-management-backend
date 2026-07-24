# app/services/filter_remaining.py
from __future__ import annotations

from datetime import date


def compute_remaining_days(
    last_replaced_date: date,
    lifespan_days: int,
    today: date | None = None,
) -> int:
    as_of = today or date.today()
    return lifespan_days - (as_of - last_replaced_date).days


def build_filter_due_copy(filter_name: str, purifier_name: str, remaining_days: int) -> tuple[str, str]:
    title = "Nhắc thay lõi lọc"
    if remaining_days < 0:
        body = (
            f'Lõi "{filter_name}" trên máy "{purifier_name}" '
            f"đã quá hạn {abs(remaining_days)} ngày — cần thay ngay."
        )
    else:
        body = (
            f'Lõi "{filter_name}" trên máy "{purifier_name}" '
            f"còn {remaining_days} ngày — nên thay sớm."
        )
    return title, body
