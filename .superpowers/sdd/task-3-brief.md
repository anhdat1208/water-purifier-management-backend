### Task 3: Config VAPID + Push subscribe APIs

**Files:**
- Modify: `src/water-purifier-management-backend/app/config.py`
- Create: `src/water-purifier-management-backend/app/schemas/push.py`
- Create: `src/water-purifier-management-backend/app/routers/push.py`
- Modify: `src/water-purifier-management-backend/app/main.py` (include router only; scheduler later)
- Create: `src/water-purifier-management-backend/tests/conftest.py`
- Create: `src/water-purifier-management-backend/tests/test_push_api.py`
- Modify: `.env.example` (root)
- Modify: `docker-compose.yml` (api environment)

**Interfaces:**
- Consumes: `get_current_user`, `PushSubscription` model, `settings`
- Produces endpoints:
  - `GET /api/v1/push/vapid-public-key` → `{ data: { public_key: string } }`
  - `POST /api/v1/push/subscribe` body `{ endpoint, keys: { p256dh, auth }, user_agent? }` → upsert by endpoint
  - `DELETE /api/v1/push/unsubscribe` body `{ endpoint }` → delete if owned
- Settings fields: `vapid_public_key`, `vapid_private_key`, `vapid_subject`, `push_job_hour` (int default 8), `app_timezone` (default `Asia/Ho_Chi_Minh`)

- [ ] **Step 1: Extend Settings**

```python
# in Settings class
vapid_public_key: str = ""
vapid_private_key: str = ""
vapid_subject: str = "mailto:admin@waterpurifier.local"
push_job_hour: int = 8
app_timezone: str = "Asia/Ho_Chi_Minh"
```

Add to root `.env.example`:

```env
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=mailto:admin@waterpurifier.local
PUSH_JOB_HOUR=8
APP_TIMEZONE=Asia/Ho_Chi_Minh
```

Pass same keys into `docker-compose.yml` `api.environment`.

- [ ] **Step 2: Schemas**

```python
# app/schemas/push.py
from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeIn(BaseModel):
    endpoint: str
    keys: PushKeys
    user_agent: str | None = None


class PushUnsubscribeIn(BaseModel):
    endpoint: str


class VapidPublicKeyOut(BaseModel):
    public_key: str
```

- [ ] **Step 3: Write API tests (sqlite TestClient)**

`conftest.py` tạo app với `DATABASE_URL=sqlite:///:memory:` (hoặc file temp), `create_all`, user + JWT helper. Pattern tối thiểu:

```python
# tests/conftest.py — tạo fixture `client`, `auth_headers`, seed 1 user
# Dùng Base.metadata.create_all trên engine sqlite; override get_db.
```

Test cases trong `test_push_api.py`:
1. GET vapid-public-key trả public key từ settings (set env trong fixture).
2. POST subscribe tạo row; POST lại cùng endpoint cập nhật keys / giữ 1 row.
3. DELETE unsubscribe xóa row của user.
4. Unauthenticated → 401.

- [ ] **Step 4: Implement router**

```python
# app/routers/push.py
router = APIRouter(prefix="/push", tags=["Push"])

@router.get("/vapid-public-key")
def get_vapid_public_key(current_user: Annotated[User, Depends(get_current_user)]):
    if not settings.vapid_public_key:
        raise HTTPException(503, detail="VAPID public key chưa cấu hình.")
    return success({"public_key": settings.vapid_public_key})

@router.post("/subscribe")
def subscribe(...):
    # select by endpoint; if exists and other user → 409
    # else update or insert PushSubscription for current_user
    ...

@router.delete("/unsubscribe")
def unsubscribe(payload: PushUnsubscribeIn, ...):
    # delete where endpoint + user_id
    ...
```

Include trong `main.py`: `from app.routers import ... push` và thêm vào tuple routers.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_push_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit (backend)**

```bash
git commit -m "feat: add web push subscribe APIs and VAPID config"
```

(Also note: root `.env.example` / `docker-compose.yml` không nằm trong BE git — để thay đổi đó trong working tree; nếu user có git root sau này thì commit chung.)

---

