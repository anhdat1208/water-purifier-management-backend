from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import PushSubscription, User


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
