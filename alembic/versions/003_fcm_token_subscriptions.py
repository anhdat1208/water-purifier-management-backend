"""Replace Web Push keys with FCM registration tokens

Revision ID: 003_fcm_token_subscriptions
Revises: 002_push_notifications
Create Date: 2026-09-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_fcm_token_subscriptions"
down_revision: Union[str, None] = "002_push_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Old Web Push endpoint/keys cannot be reused as FCM tokens.
    op.execute(sa.text("DELETE FROM push_subscriptions"))
    op.drop_constraint("push_subscriptions_endpoint_key", "push_subscriptions", type_="unique")
    op.drop_column("push_subscriptions", "endpoint")
    op.drop_column("push_subscriptions", "p256dh")
    op.drop_column("push_subscriptions", "auth")
    op.add_column("push_subscriptions", sa.Column("fcm_token", sa.Text(), nullable=False))
    op.create_unique_constraint("uq_push_subscriptions_fcm_token", "push_subscriptions", ["fcm_token"])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM push_subscriptions"))
    op.drop_constraint("uq_push_subscriptions_fcm_token", "push_subscriptions", type_="unique")
    op.drop_column("push_subscriptions", "fcm_token")
    op.add_column("push_subscriptions", sa.Column("endpoint", sa.Text(), nullable=False))
    op.add_column("push_subscriptions", sa.Column("p256dh", sa.Text(), nullable=False))
    op.add_column("push_subscriptions", sa.Column("auth", sa.Text(), nullable=False))
    op.create_unique_constraint("push_subscriptions_endpoint_key", "push_subscriptions", ["endpoint"])
