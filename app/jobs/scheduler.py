from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python 3.8 compatibility
    from pytz import timezone as ZoneInfo

from app.config import settings
from app.database import SessionLocal
from app.jobs.filter_due_push import run_filter_due_push_job

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
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


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _job_wrapper() -> None:
    db = SessionLocal()
    try:
        run_filter_due_push_job(db)
    finally:
        db.close()
