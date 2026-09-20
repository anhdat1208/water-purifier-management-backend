from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.entities import PushSubscription, User, UserRole, UserStatus


def test_subscribe_upserts_subscription_for_token(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
):
    token = "fcm-token-123"
    first_payload = {
        "token": token,
        "user_agent": "first-agent",
    }
    second_payload = {
        "token": token,
        "user_agent": "second-agent",
    }

    first_response = client.post("/api/v1/push/subscribe", json=first_payload, headers=auth_headers)
    second_response = client.post("/api/v1/push/subscribe", json=second_payload, headers=auth_headers)

    subscriptions = db_session.scalars(select(PushSubscription).where(PushSubscription.fcm_token == token)).all()
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == {"data": {"token": token}}
    assert len(subscriptions) == 1
    assert subscriptions[0].user_id == user.id
    assert subscriptions[0].user_agent == "second-agent"


def test_subscribe_recovers_when_concurrent_insert_owns_token(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
    monkeypatch,
):
    token = "fcm-token-concurrent"
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
                        fcm_token=token,
                        user_agent="concurrent-agent",
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
            "token": token,
            "user_agent": "requested-agent",
        },
        headers=auth_headers,
    )

    subscription = db_session.scalar(select(PushSubscription).where(PushSubscription.fcm_token == token))
    assert response.status_code == 200
    assert subscription is not None
    assert subscription.user_id == user.id
    assert subscription.user_agent == "requested-agent"


def test_subscribe_rejects_token_owned_by_another_user(
    client: TestClient,
    db_session: Session,
    user: User,
):
    token = "fcm-token-another-user"
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
                fcm_token=token,
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/v1/push/subscribe",
        json={"token": token},
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
    token = "fcm-token-delete-me"
    db_session.add(
        PushSubscription(
            user_id=user.id,
            fcm_token=token,
        )
    )
    db_session.commit()

    response = client.request(
        "DELETE",
        "/api/v1/push/unsubscribe",
        json={"token": token},
        headers=auth_headers,
    )

    assert response.status_code == 204
    assert db_session.scalar(select(PushSubscription).where(PushSubscription.fcm_token == token)) is None


def test_push_endpoints_require_authentication(client: TestClient):
    response = client.post("/api/v1/push/subscribe", json={"token": "x"})

    assert response.status_code == 401
