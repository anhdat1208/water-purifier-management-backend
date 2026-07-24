# Task 2 Report: Entities + Alembic migration

**Status:** DONE_WITH_CONCERNS  
**Branch:** `feat/web-push-filter-reminder`  
**Date:** 2026-07-24

## Summary

Added `PushSubscription` and `Notification` ORM models to `app/models/entities.py`, exported them from `app/models/__init__.py`, and created Alembic revision `002_push_notifications` chained after `001_initial`.

## Changes

| File | Action |
|------|--------|
| `app/models/entities.py` | Added `PushSubscription`, `Notification`; imported `UniqueConstraint` |
| `app/models/__init__.py` | Exported `PushSubscription`, `Notification` |
| `alembic/versions/002_push_notifications.py` | New migration (push_subscriptions + notifications tables) |

## Models

### PushSubscription
- Table: `push_subscriptions`
- Fields: `id`, `user_id` (FK users CASCADE), `endpoint` (unique), `p256dh`, `auth`, `user_agent`, `created_at`, `updated_at`
- Relationship: `owner` → `User`

### Notification
- Table: `notifications`
- Unique constraint: `(filter_id, sent_date)` as `uq_notifications_filter_sent_date`
- Fields: `id`, `user_id` (FK CASCADE), `filter_id` (FK CASCADE), `purifier_id` (FK SET NULL), `type` (String default `"filter_due"`), `title`, `body`, `remaining_days`, `is_read`, `sent_at`, `sent_date`
- Relationship: `owner` → `User`

## Migration

- **Revision ID:** `002_push_notifications`
- **Down revision:** `001_initial`
- **Upgrade:** creates both tables with indexes and constraints per brief
- **Downgrade:** drops `notifications`, then `push_subscriptions`

## Verification

| Check | Result |
|-------|--------|
| `from app.models import PushSubscription, Notification` | PASS (sqlite `DATABASE_URL`) |
| `Base.metadata.create_all` includes new tables | PASS |
| `py_compile` on `002_push_notifications.py` | PASS |
| `alembic heads` / `alembic history` | PASS — chain `001_initial → 002_push_notifications (head)` |
| `alembic upgrade head` (Postgres) | NOT RUN — `psycopg2` unavailable in local venv (Python 3.8 win32 build failure) |

## Commit

```
4646512 feat: add push_subscriptions and notifications tables
```

Files committed:
- `app/models/entities.py`
- `app/models/__init__.py`
- `alembic/versions/002_push_notifications.py`

## Self-review

- [x] Code matches task brief exactly (field types, defaults, FK ondelete, unique constraints)
- [x] No API/job code added (out of scope)
- [x] `Notification.type` is String, not a new enum
- [x] Models registered via `entities` import in `alembic/env.py` (existing pattern)
- [ ] Full Postgres migration upgrade not verified locally — recommend CI or dev with Postgres

## Concerns

1. **Postgres upgrade not executed locally** — environment lacks working `psycopg2-binary` on Python 3.8.32-bit Windows. Migration SQL matches brief and revision chain is valid; run `alembic upgrade head` where Postgres is available.
2. **No unit tests for models** — brief did not require; schema covered by migration + ORM definitions.

## Out of scope (later tasks)

- Push subscription API endpoints
- Notification send/read API
- Scheduled push jobs
