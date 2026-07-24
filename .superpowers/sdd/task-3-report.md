# Task 3 Report: VAPID config and Push subscription APIs

## Delivered

- Added VAPID and scheduling settings to `app.config.Settings`:
  `vapid_public_key`, `vapid_private_key`, `vapid_subject`, `push_job_hour`,
  and `app_timezone`.
- Added request/response schemas for VAPID key retrieval, push subscription,
  and unsubscription.
- Added authenticated endpoints under `/api/v1/push`:
  - `GET /vapid-public-key` returns the configured key, or `503` when absent.
  - `POST /subscribe` creates a subscription or updates the same user's existing
    endpoint; an endpoint held by another user returns `409`.
  - `DELETE /unsubscribe` removes only the current user's matching subscription.
- Registered the push router in `app.main`.
- Updated root `.env.example` and `docker-compose.yml` with all five new
  configuration variables. These root files are intentionally outside the
  backend commit.

## Tests

Added sqlite-backed `TestClient` fixtures in `tests/conftest.py`, including a
seeded active user, JWT authorization headers, and a `get_db` override.

`tests/test_push_api.py` covers:

1. configured VAPID public-key retrieval;
2. subscription create and same-endpoint upsert;
3. owned-subscription deletion;
4. unauthenticated access rejection.

Verification run:

```text
.\.venv\Scripts\python.exe -m pytest -v
9 passed in 2.90s
```

## Environment note

The host initially only exposed Python 3.8 without pytest; the first test run
could not start. A local ignored `.venv` was created for verification. Installing
the complete requirements initially failed because 32-bit Windows has no
`psycopg2-binary` wheel; the sqlite API tests do not require that PostgreSQL
driver, so the test-only dependency subset was installed instead. The router
and test suite were then executed successfully.

## Commit

Backend commit succeeded:

`8af3a80 feat: add web push subscribe APIs and VAPID config`

Root `.env.example` / `docker-compose.yml` remain uncommitted at monorepo
(no root git). Initial wrapper `git commit` failed on Git 2.27 due to an
injected `--trailer` option; commit was completed via `Git\bin\git.exe`.

## Review fixes

- Made `POST /api/v1/push/subscribe` race-safe: an `IntegrityError` during
  insert now rolls back, re-selects by endpoint, updates the newly found
  same-user subscription, or returns `409` if another user owns it.
- Added coverage for the concurrent-insert recovery path and for attempting to
  subscribe to an endpoint owned by another user.

Verification after the fix:

```text
.\.venv\Scripts\python.exe -m pytest tests/test_push_api.py -v
6 passed in 4.23s

.\.venv\Scripts\python.exe -m pytest -v
11 passed in 4.52s
```
