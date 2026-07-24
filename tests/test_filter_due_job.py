from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import Mock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Filter,
    FilterType,
    Notification,
    PushSubscription,
    Purifier,
    PurifierStatus,
    SystemSettings,
    User,
)


TODAY = date(2026, 7, 24)


def _filter_with_remaining_days(db: Session, user: User, remaining_days: int) -> Filter:
    purifier = Purifier(
        user_id=user.id,
        name="Máy bếp",
        model="RO-01",
        location="Bếp",
        install_date=TODAY - timedelta(days=151),
        status=PurifierStatus.ACTIVE,
    )
    filter_item = Filter(
        user_id=user.id,
        purifier=purifier,
        name="Lõi RO",
        type=FilterType.RO_MEMBRANE,
        stage=1,
        lifespan_days=180,
        installed_date=TODAY - timedelta(days=180 - remaining_days),
        last_replaced_date=TODAY - timedelta(days=180 - remaining_days),
    )
    db.add(filter_item)
    db.commit()
    return filter_item


def _subscription(db: Session, user: User) -> PushSubscription:
    subscription = PushSubscription(
        user_id=user.id,
        endpoint="https://push.example.test/subscription",
        p256dh="p256dh",
        auth="auth",
    )
    db.add(subscription)
    db.commit()
    return subscription


def test_job_skips_all_filters_when_auto_notify_disabled(db_session: Session, user: User):
    from app.jobs.filter_due_push import run_filter_due_push_job

    _filter_with_remaining_days(db_session, user, 29)
    db_session.add(SystemSettings(id=1, auto_notify_filter_due=False))
    db_session.commit()

    result = run_filter_due_push_job(db_session, today=TODAY)

    assert result == {"scanned": 0, "created": 0, "pushed": 0, "skipped_flag": 1, "skipped_dup": 0}
    assert db_session.scalars(select(Notification)).all() == []


def test_job_creates_notification_and_pushes_due_filter(
    db_session: Session, user: User, monkeypatch
):
    from app.jobs.filter_due_push import run_filter_due_push_job

    filter_item = _filter_with_remaining_days(db_session, user, 29)
    _subscription(db_session, user)
    sent = []
    monkeypatch.setattr(
        "app.jobs.filter_due_push.send_web_push",
        lambda subscription, title, body, data: sent.append((subscription, title, body, data)) or "ok",
    )

    result = run_filter_due_push_job(db_session, today=TODAY)
    notification = db_session.scalar(select(Notification).where(Notification.filter_id == filter_item.id))

    assert result == {"scanned": 1, "created": 1, "pushed": 1, "skipped_flag": 0, "skipped_dup": 0}
    assert notification is not None
    assert notification.remaining_days == 29
    assert notification.sent_date == TODAY
    assert notification.body == 'Lõi "Lõi RO" trên máy "Máy bếp" còn 29 ngày — nên thay sớm.'
    assert sent[0][3] == {"filterId": filter_item.id, "purifierId": filter_item.purifier_id, "url": f"/filters/{filter_item.id}"}


def test_job_ignores_filter_more_than_thirty_days_away(db_session: Session, user: User):
    from app.jobs.filter_due_push import run_filter_due_push_job

    _filter_with_remaining_days(db_session, user, 31)

    result = run_filter_due_push_job(db_session, today=TODAY)

    assert result == {"scanned": 1, "created": 0, "pushed": 0, "skipped_flag": 0, "skipped_dup": 0}
    assert db_session.scalars(select(Notification)).all() == []


def test_job_deduplicates_notification_for_same_filter_and_day(db_session: Session, user: User):
    from app.jobs.filter_due_push import run_filter_due_push_job

    _filter_with_remaining_days(db_session, user, 29)
    _subscription(db_session, user)
    send_web_push = Mock(return_value="ok")

    import app.jobs.filter_due_push as filter_due_push

    original_send_web_push = filter_due_push.send_web_push
    filter_due_push.send_web_push = send_web_push
    try:
        first = run_filter_due_push_job(db_session, today=TODAY)
        second = run_filter_due_push_job(db_session, today=TODAY)
    finally:
        filter_due_push.send_web_push = original_send_web_push

    assert first["created"] == 1
    assert second["created"] == 0
    assert second["skipped_dup"] == 1
    assert send_web_push.call_count == 1
    assert len(db_session.scalars(select(Notification)).all()) == 1


def test_job_uses_app_timezone_calendar_date_when_today_is_omitted(
    db_session: Session, user: User, monkeypatch
):
    import app.jobs.filter_due_push as filter_due_push

    expected_date = date(2026, 7, 25)
    _filter_with_remaining_days(db_session, user, 29)
    monkeypatch.setattr("app.config.settings.app_timezone", "Pacific/Kiritimati")

    class FixedDateTime:
        @classmethod
        def now(cls, timezone):
            timezone_name = getattr(timezone, "key", None) or timezone.zone
            assert timezone_name == "Pacific/Kiritimati"
            return cls()

        def date(self):
            return expected_date

    monkeypatch.setattr(filter_due_push, "datetime", FixedDateTime)

    result = filter_due_push.run_filter_due_push_job(db_session, send=False)

    notification = db_session.scalar(select(Notification))
    assert result["created"] == 1
    assert notification.sent_date == expected_date


def test_job_creates_history_without_subscription(db_session: Session, user: User):
    from app.jobs.filter_due_push import run_filter_due_push_job

    _filter_with_remaining_days(db_session, user, 29)

    result = run_filter_due_push_job(db_session, today=TODAY)

    assert result["created"] == 1
    assert result["pushed"] == 0
    assert len(db_session.scalars(select(Notification)).all()) == 1


def test_job_deletes_gone_subscription(db_session: Session, user: User, monkeypatch):
    from app.jobs.filter_due_push import run_filter_due_push_job

    _filter_with_remaining_days(db_session, user, 29)
    subscription = _subscription(db_session, user)
    monkeypatch.setattr("app.jobs.filter_due_push.send_web_push", lambda *_: "gone")

    result = run_filter_due_push_job(db_session, today=TODAY)

    assert result["created"] == 1
    assert result["pushed"] == 0
    assert db_session.get(PushSubscription, subscription.id) is None


def test_send_web_push_returns_error_when_transport_fails(user: User, monkeypatch):
    from app.services.push_sender import send_web_push

    subscription = PushSubscription(
        user_id=user.id,
        endpoint="https://push.example.test/subscription",
        p256dh="p256dh",
        auth="auth",
    )
    monkeypatch.setattr("app.services.push_sender.settings.vapid_private_key", "private-key")
    monkeypatch.setattr("app.services.push_sender.settings.vapid_public_key", "public-key")
    monkeypatch.setattr("app.services.push_sender.webpush", Mock(side_effect=ConnectionError))

    result = send_web_push(subscription, "Tiêu đề", "Nội dung", {})

    assert result == "error"
