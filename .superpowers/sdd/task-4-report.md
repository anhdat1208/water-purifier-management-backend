# Task 4 Report: Notifications list / mark-read APIs

## Implemented

- Added `NotificationOut` response schema.
- Added authenticated notification APIs:
  - `GET /api/v1/notifications` with pagination, newest-first order, totals, and unread count.
  - `PATCH /api/v1/notifications/{notification_id}/read`.
  - `POST /api/v1/notifications/read-all`.
- Scoped all reads and writes to the authenticated user's notifications; other users' notification IDs return 404.
- Registered the notifications router in the application.

## TDD evidence

- Added API tests before implementation.
- Initial notification test run failed with 404 because the router was not registered.
- After implementation, `tests/test_notifications_api.py` passed: 2 passed.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest -q
13 passed in 7.07s
```

## Commit

`feat: add in-app notifications list and read APIs`
