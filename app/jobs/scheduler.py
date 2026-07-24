from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.jobs.filter_due_push import run_filter_due_push_job
from app.jobs.timezone import get_timezone

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone=get_timezone(settings.app_timezone))
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
