from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, engine
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.routers import admin, ai_assistant, auth, dashboard, filters, internal, notifications, push, purifiers
from app.routers.internal import is_vercel_runtime
from app.services.seed import seed_database


def _run_migrations() -> None:
    if settings.database_url.startswith("sqlite"):
        from app.database import Base

        Base.metadata.create_all(bind=engine)
        return

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _run_migrations()
    if settings.seed_demo_data:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    # Vercel serverless không giữ process 24/7 — dùng Vercel Cron thay APScheduler.
    use_inprocess_scheduler = not is_vercel_runtime()
    if use_inprocess_scheduler:
        start_scheduler()
    try:
        yield
    finally:
        if use_inprocess_scheduler:
            stop_scheduler()


app = FastAPI(
    title="Water Purifier Management API",
    description="API quản lý máy lọc nước — FastAPI + PostgreSQL + Redis + JWT",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
for router in (
    auth,
    dashboard,
    purifiers,
    filters,
    notifications,
    push,
    internal,
    ai_assistant,
    admin,
):
    app.include_router(router.router, prefix=API_PREFIX)


@app.get("/")
def root():
    return {
        "message": "Water Purifier Management API",
        "docs": "/docs",
        "api": "/api/v1",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
