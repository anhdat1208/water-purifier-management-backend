# tests/test_filter_remaining.py
from datetime import date

from app.services.filter_remaining import build_filter_due_copy, compute_remaining_days


def test_remaining_days_basic():
    assert compute_remaining_days(date(2026, 1, 1), 180, today=date(2026, 1, 31)) == 150


def test_remaining_days_at_threshold():
    assert compute_remaining_days(date(2026, 1, 1), 180, today=date(2026, 5, 31)) == 30


def test_remaining_days_overdue():
    assert compute_remaining_days(date(2026, 1, 1), 10, today=date(2026, 1, 20)) == -9


def test_copy_remaining():
    title, body = build_filter_due_copy("Lõi RO", "Máy bếp", 12)
    assert title == "Nhắc thay lõi lọc"
    assert body == 'Lõi "Lõi RO" trên máy "Máy bếp" còn 12 ngày — nên thay sớm.'


def test_copy_overdue():
    title, body = build_filter_due_copy("Lõi RO", "Máy bếp", -3)
    assert title == "Nhắc thay lõi lọc"
    assert body == 'Lõi "Lõi RO" trên máy "Máy bếp" đã quá hạn 3 ngày — cần thay ngay.'
