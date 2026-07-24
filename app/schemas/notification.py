from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filter_id: int
    purifier_id: int | None
    type: str
    title: str
    body: str
    remaining_days: int
    is_read: bool
    sent_at: datetime
