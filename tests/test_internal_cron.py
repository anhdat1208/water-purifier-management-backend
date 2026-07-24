from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture
def cron_client(client: TestClient) -> TestClient:
    settings.cron_secret = "test-cron-secret"
    return client


def test_run_filter_due_push_requires_auth(cron_client: TestClient):
    response = cron_client.get("/api/v1/internal/run-filter-due-push")
    assert response.status_code == 401


def test_run_filter_due_push_rejects_bad_secret(cron_client: TestClient):
    response = cron_client.get(
        "/api/v1/internal/run-filter-due-push",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401


def test_run_filter_due_push_ok(cron_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.routers.internal.run_filter_due_push_job",
        lambda db, today=None, send=True, force_resend=False: {
            "scanned": 1,
            "created": 0,
            "pushed": 0,
            "skipped_flag": 0,
            "skipped_dup": 0,
        },
    )
    response = cron_client.get(
        "/api/v1/internal/run-filter-due-push",
        headers={"Authorization": "Bearer test-cron-secret"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["scanned"] == 1
