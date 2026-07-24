# Task 5 Report — Daily Filter-Due Web Push

## Delivered

- Added `send_web_push`, which sends VAPID payloads and classifies 404/410 subscriptions as gone.
- Added a daily filter-due job that honors the feature flag, records one notification per filter/day, sends to all subscriptions, and deletes gone subscriptions.
- Added APScheduler lifecycle management to FastAPI, scheduled daily at `push_job_hour` in `app_timezone`.
- Added six job tests covering the feature flag, threshold, same-day deduplication, history without a subscription, successful delivery, and deleted gone subscriptions.

## Verification

`python -m pytest -v` completed successfully: 19 passed.

## Environment note

The local runner uses Python 3.8, so scheduler timezone loading falls back to APScheduler's installed `pytz` when the Python 3.9+ `zoneinfo` module is unavailable. Production Python 3.9+ uses `zoneinfo`.

## Review fixes — 2026-07-24

- The due job now derives an omitted `today` from `settings.app_timezone`, using the same `zoneinfo`/`pytz` fallback helper as the scheduler.
- Each notification is committed before any web push is attempted. A competing unique-constraint insert is rolled back, recorded as a duplicate skip, and does not send a push.
- The deduplication test now sends on both runs and asserts a single total push. A timezone regression test verifies the notification uses the configured timezone's calendar date.

## Verification after review fixes

- `python -m pytest tests/test_filter_due_job.py -v`: 7 passed.
- `python -m pytest -v`: 20 passed.
