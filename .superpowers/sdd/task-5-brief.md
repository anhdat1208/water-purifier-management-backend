### Task 5: Daily job + pywebpush sender + APScheduler

**Files:**
- Create: `src/water-purifier-management-backend/app/services/push_sender.py`
- Create: `src/water-purifier-management-backend/app/jobs/filter_due_push.py`
- Create: `src/water-purifier-management-backend/app/jobs/scheduler.py`
- Create: `src/water-purifier-management-backend/app/jobs/__init__.py`
- Modify: `src/water-purifier-management-backend/app/main.py` (lifespan start/stop scheduler)
- Create: `src/water-purifier-management-backend/tests/test_filter_due_job.py`

**Interfaces:**
- Consumes: `compute_remaining_days`, `build_filter_due_copy`, `get_system_settings`, `Filter`, `Purifier`, `PushSubscription`, `Notification`, `settings`
- Produces:
  - `send_web_push(subscription: PushSubscription, title: str, body: str, data: dict) -> Literal["ok", "gone", "error"]`
  - `run_filter_due_push_job(db: Session, today: date | None = None, send: bool = True) -> dict` with counts `{ scanned, created, pushed, skipped_flag, skipped_dup }`
  - Scheduler: cron daily at `settings.push_job_hour` in `settings.app_timezone`

- [ ] **Step 1: Write failing job tests** (mock `send_web_push`)

Cases:
1. `auto_notify_filter_due=False` → created=0.
2. Filter remaining 29 + subscription → created=1, pushed=1; notification row tồn tại.
3. Filter remaining 31 → created=0.
4. Chạy job 2 lần cùng `today` → created lần 2 = 0 (unique).
5. Không subscription → created=1, pushed=0.
6. `send_web_push` trả `"gone"` → subscription bị xóa.

- [ ] **Step 2: Implement `push_sender.py`**

```python
from pywebpush import webpush, WebPushException
from app.config import settings

def send_web_push(subscription, title, body, data: dict) -> str:
    if not settings.vapid_private_key or not settings.vapid_public_key:
        return "error"
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps({"title": title, "body": body, "data": data}, ensure_ascii=False),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return "ok"
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            return "gone"
        return "error"
```

- [ ] **Step 3: Implement `run_filter_due_push_job`**

Pseudo:

```python
def run_filter_due_push_job(db, today=None, send=True):
    today = today or date.today()
    settings_row = get_system_settings(db)
    if not settings_row.auto_notify_filter_due:
        return {"scanned": 0, "created": 0, "pushed": 0, "skipped_flag": 1, "skipped_dup": 0}

    filters = db.scalars(select(Filter).options(joinedload(Filter.purifier))).all()
    created = pushed = skipped_dup = 0
    for f in filters:
        remaining = compute_remaining_days(f.last_replaced_date, f.lifespan_days, today)
        if remaining > 30:
            continue
        exists = db.scalar(
            select(Notification.id).where(
                Notification.filter_id == f.id,
                Notification.sent_date == today,
            )
        )
        if exists:
            skipped_dup += 1
            continue
        title, body = build_filter_due_copy(
            f.name, f.purifier.name if f.purifier else "", remaining
        )
        notif = Notification(
            user_id=f.user_id,
            filter_id=f.id,
            purifier_id=f.purifier_id,
            type="filter_due",
            title=title,
            body=body,
            remaining_days=remaining,
            is_read=False,
            sent_date=today,
        )
        db.add(notif)
        created += 1
        if send:
            subs = db.scalars(
                select(PushSubscription).where(PushSubscription.user_id == f.user_id)
            ).all()
            for sub in subs:
                result = send_web_push(
                    sub, title, body,
                    {"filterId": f.id, "purifierId": f.purifier_id, "url": f"/filters/{f.id}"},
                )
                if result == "ok":
                    pushed += 1
                elif result == "gone":
                    db.delete(sub)
    db.commit()
    return {"scanned": len(filters), "created": created, "pushed": pushed, "skipped_flag": 0, "skipped_dup": skipped_dup}
```

- [ ] **Step 4: Scheduler**

```python
# app/jobs/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

_scheduler: BackgroundScheduler | None = None

def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=ZoneInfo(settings.app_timezone))
    _scheduler.add_job(
        _job_wrapper,
        trigger="cron",
        hour=settings.push_job_hour,
        minute=0,
        id="filter_due_push",
        replace_existing=True,
    )
    _scheduler.start()

def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None

def _job_wrapper():
    db = SessionLocal()
    try:
        run_filter_due_push_job(db)
    finally:
        db.close()
```

Trong `lifespan`: `start_scheduler()` sau migrate/seed; `yield`; `stop_scheduler()` trong finally/after yield.

- [ ] **Step 5: pytest PASS + commit**

```bash
git commit -m "feat: add daily filter-due web push job"
```

---

