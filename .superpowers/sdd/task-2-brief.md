### Task 2: Entities + Alembic migration

**Files:**
- Modify: `src/water-purifier-management-backend/app/models/entities.py`
- Modify: `src/water-purifier-management-backend/app/models/__init__.py`
- Create: `src/water-purifier-management-backend/alembic/versions/002_push_notifications.py`

**Interfaces:**
- Consumes: existing `Base`, `User`, `Filter`, `Purifier`
- Produces:
  - `PushSubscription(id, user_id, endpoint, p256dh, auth, user_agent, created_at, updated_at)` — unique `endpoint`
  - `Notification(id, user_id, filter_id, purifier_id, type, title, body, remaining_days, is_read, sent_at, sent_date)` — unique `(filter_id, sent_date)`
  - `Notification.type` default `"filter_due"` (String, không enum mới)

- [ ] **Step 1: Add ORM models**

Append to `entities.py` (import `UniqueConstraint` từ `sqlalchemy` nếu chưa có):

```python
class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("filter_id", "sent_date", name="uq_notifications_filter_sent_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("filters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purifier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("purifiers.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(50), default="filter_due", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    remaining_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    owner: Mapped["User"] = relationship()
```

Export trong `app/models/__init__.py`.

- [ ] **Step 2: Write Alembic `002_push_notifications.py`**

```python
"""Push subscriptions and notifications

Revision ID: 002_push_notifications
Revises: 001_initial
Create Date: 2026-07-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_push_notifications"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filter_id", sa.Integer(), nullable=False),
        sa.Column("purifier_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("remaining_days", sa.Integer(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["filter_id"], ["filters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purifier_id"], ["purifiers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("filter_id", "sent_date", name="uq_notifications_filter_sent_date"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_filter_id", "notifications", ["filter_id"])
    op.create_index("ix_notifications_sent_date", "notifications", ["sent_date"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("push_subscriptions")
```

- [ ] **Step 3: Verify migration upgrades (sqlite path OK via app lifespan; for Postgres):**

```bash
cd src/water-purifier-management-backend
alembic upgrade head
```

Expected: `Running upgrade 001_initial -> 002_push_notifications`.

- [ ] **Step 4: Commit (backend repo)**

```bash
git add app/models/entities.py app/models/__init__.py alembic/versions/002_push_notifications.py
git commit -m "feat: add push_subscriptions and notifications tables"
```

---

