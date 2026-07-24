### Task 4: Notifications list / mark-read APIs

**Files:**
- Create: `src/water-purifier-management-backend/app/schemas/notification.py`
- Create: `src/water-purifier-management-backend/app/routers/notifications.py`
- Modify: `src/water-purifier-management-backend/app/main.py`
- Create: `src/water-purifier-management-backend/tests/test_notifications_api.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/notifications?page=1&page_size=20` → `{ data: { items: NotificationOut[], total, page, page_size, unread_count } }`
  - `PATCH /api/v1/notifications/{id}/read` → notification updated
  - `POST /api/v1/notifications/read-all` → `{ data: { updated: int } }`
- `NotificationOut`: `id, filter_id, purifier_id, type, title, body, remaining_days, is_read, sent_at`

- [ ] **Step 1: Failing API tests**

- Seed 2 notifications for user A, 1 for user B.
- List chỉ thấy của A, newest first.
- Mark one read; read-all; ownership 404 for B's id.

- [ ] **Step 2: Implement schemas + router**

Order: `Notification.sent_at.desc()`. Chỉ `user_id == current_user.id`.

- [ ] **Step 3: pytest PASS + commit**

```bash
git commit -m "feat: add in-app notifications list and read APIs"
```

---

