from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.models.entities import PushSubscription, User, UserRole, UserStatus


def test_get_vapid_public_key_returns_configured_key(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    monkeypatch.setattr(settings, "vapid_public_key", "test-public-key")

    response = client.get("/api/v1/push/vapid-public-key", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"data": {"public_key": "test-public-key"}}


def test_subscribe_upserts_subscription_for_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
):
    endpoint = "https://push.example.test/subscriptions/123"
    first_payload = {
        "endpoint": endpoint,
        "keys": {"p256dh": "first-p256dh", "auth": "first-auth"},
        "user_agent": "first-agent",
    }
    second_payload = {
        "endpoint": endpoint,
        "keys": {"p256dh": "second-p256dh", "auth": "second-auth"},
        "user_agent": "second-agent",
    }

    first_response = client.post("/api/v1/push/subscribe", json=first_payload, headers=auth_headers)
    second_response = client.post("/api/v1/push/subscribe", json=second_payload, headers=auth_headers)

    subscriptions = db_session.scalars(select(PushSubscription).where(PushSubscription.endpoint == endpoint)).all()
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(subscriptions) == 1
    assert subscriptions[0].user_id == user.id
    assert subscriptions[0].p256dh == "second-p256dh"
    assert subscriptions[0].auth == "second-auth"
    assert subscriptions[0].user_agent == "second-agent"


def test_subscribe_recovers_when_concurrent_insert_owns_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
    monkeypatch,
):
    endpoint = "https://push.example.test/subscriptions/concurrent"
    original_commit = db_session.commit
    did_raise = False

    def commit_with_concurrent_insert() -> None:
        nonlocal did_raise
        if not did_raise:
            did_raise = True
            concurrent_session = Session(bind=db_session.get_bind())
            try:
                concurrent_session.add(
                    PushSubscription(
                        user_id=user.id,
                        endpoint=endpoint,
                        p256dh="concurrent-p256dh",
                        auth="concurrent-auth",
                    )
                )
                concurrent_session.commit()
            finally:
                concurrent_session.close()
            raise IntegrityError("INSERT", {}, Exception("unique constraint"))
        original_commit()

    monkeypatch.setattr(db_session, "commit", commit_with_concurrent_insert)

    response = client.post(
        "/api/v1/push/subscribe",
        json={
            "endpoint": endpoint,
            "keys": {"p256dh": "requested-p256dh", "auth": "requested-auth"},
            "user_agent": "requested-agent",
        },
        headers=auth_headers,
    )

    subscription = db_session.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    assert response.status_code == 200
    assert subscription is not None
    assert subscription.user_id == user.id
    assert subscription.p256dh == "requested-p256dh"
    assert subscription.auth == "requested-auth"
    assert subscription.user_agent == "requested-agent"


def test_subscribe_rejects_endpoint_owned_by_another_user(
    client: TestClient,
    db_session: Session,
    user: User,
):
    endpoint = "https://push.example.test/subscriptions/another-user"
    other_user = User(
        email="other-push@example.com",
        password_hash=hash_password("password123"),
        full_name="Other Push Test User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all(
        [
            other_user,
            PushSubscription(
                user_id=user.id,
                endpoint=endpoint,
                p256dh="existing-p256dh",
                auth="existing-auth",
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/v1/push/subscribe",
        json={
            "endpoint": endpoint,
            "keys": {"p256dh": "new-p256dh", "auth": "new-auth"},
        },
        headers={"Authorization": f"Bearer {create_access_token(str(other_user.id))}"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Push subscription đã thuộc về người dùng khác."


def test_unsubscribe_deletes_owned_subscription(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
):
    endpoint = "https://push.example.test/subscriptions/delete-me"
    db_session.add(
        PushSubscription(
            user_id=user.id,
            endpoint=endpoint,
            p256dh="p256dh",
            auth="auth",
        )
    )
    db_session.commit()

    response = client.request(
        "DELETE",
        "/api/v1/push/unsubscribe",
        json={"endpoint": endpoint},
        headers=auth_headers,
    )

    assert response.status_code == 204
    assert db_session.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint)) is None


def test_push_endpoints_require_authentication(client: TestClient):
    response = client.get("/api/v1/push/vapid-public-key")

    assert response.status_code == 401
