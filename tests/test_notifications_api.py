from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.entities import Notification, User, UserRole, UserStatus


def _notification(
    *,
    user_id,
    filter_id: int,
    title: str,
    sent_at: datetime,
    is_read: bool = False,
) -> Notification:
    return Notification(
        user_id=user_id,
        filter_id=filter_id,
        purifier_id=None,
        type="filter_due",
        title=title,
        body=f"{title} body",
        remaining_days=7,
        is_read=is_read,
        sent_at=sent_at,
        sent_date=sent_at.date(),
    )


def test_list_notifications_returns_only_current_users_newest_first(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
):
    now = datetime.now(timezone.utc)
    other_user = User(
        email="other-notifications@example.com",
        password_hash=hash_password("password123"),
        full_name="Other Notifications User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(other_user)
    db_session.flush()
    db_session.add_all(
        [
            _notification(
                user_id=user.id,
                filter_id=101,
                title="Older notification",
                sent_at=now - timedelta(days=1),
                is_read=True,
            ),
            _notification(
                user_id=user.id,
                filter_id=102,
                title="Newest notification",
                sent_at=now,
            ),
            _notification(
                user_id=other_user.id,
                filter_id=103,
                title="Other user's notification",
                sent_at=now + timedelta(days=1),
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/notifications?page=1&page_size=20", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert [item["title"] for item in payload["items"]] == ["Newest notification", "Older notification"]
    assert payload["total"] == 2
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    assert payload["unread_count"] == 1
    assert set(payload["items"][0]) == {
        "id",
        "filter_id",
        "purifier_id",
        "type",
        "title",
        "body",
        "remaining_days",
        "is_read",
        "sent_at",
    }


def test_mark_read_and_read_all_only_update_current_users_notifications(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
):
    now = datetime.now(timezone.utc)
    other_user = User(
        email="other-mark-read@example.com",
        password_hash=hash_password("password123"),
        full_name="Other Mark Read User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(other_user)
    db_session.flush()
    first = _notification(user_id=user.id, filter_id=201, title="First", sent_at=now)
    second = _notification(user_id=user.id, filter_id=202, title="Second", sent_at=now - timedelta(seconds=1))
    other = _notification(user_id=other_user.id, filter_id=203, title="Other", sent_at=now)
    db_session.add_all([first, second, other])
    db_session.commit()

    mark_response = client.patch(f"/api/v1/notifications/{first.id}/read", headers=auth_headers)
    read_all_response = client.post("/api/v1/notifications/read-all", headers=auth_headers)
    forbidden_response = client.patch(f"/api/v1/notifications/{other.id}/read", headers=auth_headers)

    db_session.expire_all()
    notifications = {
        notification.id: notification
        for notification in db_session.scalars(select(Notification)).all()
    }
    assert mark_response.status_code == 200
    assert mark_response.json()["data"]["id"] == first.id
    assert mark_response.json()["data"]["is_read"] is True
    assert read_all_response.status_code == 200
    assert read_all_response.json() == {"data": {"updated": 1}}
    assert notifications[first.id].is_read is True
    assert notifications[second.id].is_read is True
    assert notifications[other.id].is_read is False
    assert forbidden_response.status_code == 404
