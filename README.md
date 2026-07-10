# Water Purifier Management — Backend

API REST cho hệ thống quản lý máy lọc nước, khớp contract từ frontend `repositories/*.ts`.

## Tech stack

- Python 3.11+
- FastAPI
- PostgreSQL + SQLAlchemy
- Redis (lưu refresh token)
- JWT (access + refresh)

## Yêu cầu

- Python 3.8+ (khuyến nghị **3.11+ 64-bit** — driver PostgreSQL cần bản 64-bit)
- PostgreSQL 16+ (Docker hoặc cài local)
- Redis (tùy chọn — có fallback in-memory)

## Docker — full stack

Docker orchestration nằm ở **root monorepo** `water-purifier-manager/`:

```
water-purifier-manager/
├── docker-compose.yml
└── src/
    ├── water-purifier-management-backend/    ← repo này
    └── water-purifier-management-frontend/
```

```bash
cd ../../   # từ src/water-purifier-management-backend → water-purifier-manager
docker compose up -d --build
```

Chi tiết: xem `water-purifier-manager/README.md`.

### Chỉ Postgres + Redis (dev API local)

```bash
cd ../../
docker compose up -d postgres redis
```

## Khởi chạy với PostgreSQL (local, không Docker app)

### Cách 1 — Docker (nhanh nhất)

```powershell
cd src\water-purifier-management-backend
.\scripts\setup-postgres.ps1
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Script sẽ: bật Postgres + Redis, chạy **Alembic migration** (tạo bảng), seed dữ liệu demo khi API khởi động.

### Cách 2 — Postgres cài sẵn trên máy

1. Tạo database (chạy với user `postgres`):

```bash
psql -U postgres -f database/init.sql
```

2. Cấu hình `.env` (đã mặc định PostgreSQL):

```env
DATABASE_URL=postgresql://waterpurifier:waterpurifier@localhost:5432/waterpurifier
```

3. Migration + chạy API:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Cấu trúc database

Migration `alembic/versions/001_initial_schema.py` tạo các bảng:

| Bảng | Mô tả |
|------|--------|
| `users` | Tài khoản, role admin/user |
| `purifiers` | Máy lọc nước (FK → users) |
| `filters` | Lõi lọc (FK → users, purifiers) |
| `activities` | Nhật ký hoạt động dashboard |
| `conversations` / `messages` | Trợ lý AI |
| `system_settings` | Cấu hình hệ thống (admin) |

API tự chạy `alembic upgrade head` khi khởi động (PostgreSQL). Dữ liệu demo được seed nếu `SEED_DEMO_DATA=true` và DB trống.

## SQLite (fallback dev)

Đổi trong `.env`: `DATABASE_URL=sqlite:///./water_purifier.db` — không cần migration, tự tạo bảng khi start.

- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health
- API base: http://localhost:8000/api/v1

## Tài khoản demo (seed)

| Email | Mật khẩu | Vai trò |
|-------|----------|---------|
| admin@waterpurifier.local | Admin@123 | admin |
| user@waterpurifier.local | User@123 | user |

## Kết nối Frontend

Trong `water-purifier-management-frontend/.env`:

```env
NUXT_PUBLIC_USE_MOCK_API=false
NUXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## API endpoints

| Module | Endpoints |
|--------|-----------|
| Auth | `POST /auth/login`, `/register`, `/forgot-password`, `/refresh`, `GET /auth/me` |
| Dashboard | `GET /dashboard/overview` |
| Purifiers | `GET/POST /purifiers`, `GET/PUT/DELETE /purifiers/{id}` |
| Filters | `GET/POST /filters`, `GET/PUT/DELETE /filters/{id}`, `POST /filters/{id}/replace` |
| AI Assistant | `GET/DELETE /ai-assistant/conversations/current`, `POST /ai-assistant/chat` |
| Admin | `GET /admin/stats`, CRUD `/admin/users`, `GET/PUT /admin/settings` |

Tất cả response bọc trong `{ "data": ..., "message?": "..." }`.

## Cấu trúc

```
app/
├── main.py
├── ...
alembic/              # Database migrations
database/init.sql     # Tạo database PostgreSQL
scripts/setup-postgres.ps1
```

## Biến môi trường

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| DATABASE_URL | postgresql://... | PostgreSQL connection string |
| REDIS_URL | redis://localhost:6379/0 | Redis cho refresh token |
| SECRET_KEY | (bắt buộc đổi prod) | JWT signing key |
| ACCESS_TOKEN_EXPIRE_MINUTES | 30 | Thời hạn access token |
| REFRESH_TOKEN_EXPIRE_DAYS | 7 | Thời hạn refresh token |
| CORS_ORIGINS | http://localhost:3000 | Origin FE, phân tách bằng dấu phẩy |
| SEED_DEMO_DATA | true | Tạo dữ liệu mẫu khi DB trống |
