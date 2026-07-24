from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import Filter, Notification, PushSubscription
from app.services.business import get_system_settings
from app.services.filter_remaining import build_filter_due_copy, compute_remaining_days
from app.services.push_sender import send_web_push


def run_filter_due_push_job(
    db: Session,
    today: date | None = None,
    send: bool = True,
) -> dict[str, int]:
    as_of = today or date.today()
    system_settings = get_system_settings(db)
    if not system_settings.auto_notify_filter_due:
        return {"scanned": 0, "created": 0, "pushed": 0, "skipped_flag": 1, "skipped_dup": 0}

    filters = db.scalars(select(Filter).options(joinedload(Filter.purifier))).all()
    created = 0
    pushed = 0
    skipped_dup = 0

    for filter_item in filters:
        remaining_days = compute_remaining_days(
            filter_item.last_replaced_date,
            filter_item.lifespan_days,
            as_of,
        )
        if remaining_days > 30:
            continue

        notification_exists = db.scalar(
            select(Notification.id).where(
                Notification.filter_id == filter_item.id,
                Notification.sent_date == as_of,
            )
        )
        if notification_exists is not None:
            skipped_dup += 1
            continue

        title, body = build_filter_due_copy(
            filter_item.name,
            filter_item.purifier.name if filter_item.purifier else "",
            remaining_days,
        )
        db.add(
            Notification(
                user_id=filter_item.user_id,
                filter_id=filter_item.id,
                purifier_id=filter_item.purifier_id,
                type="filter_due",
                title=title,
                body=body,
                remaining_days=remaining_days,
                is_read=False,
                sent_date=as_of,
            )
        )
        created += 1

        if not send:
            continue

        subscriptions = db.scalars(
            select(PushSubscription).where(PushSubscription.user_id == filter_item.user_id)
        ).all()
        for subscription in subscriptions:
            result = send_web_push(
                subscription,
                title,
                body,
                {
                    "filterId": filter_item.id,
                    "purifierId": filter_item.purifier_id,
                    "url": f"/filters/{filter_item.id}",
                },
            )
            if result == "ok":
                pushed += 1
            elif result == "gone":
                db.delete(subscription)

    db.commit()
    return {
        "scanned": len(filters),
        "created": created,
        "pushed": pushed,
        "skipped_flag": 0,
        "skipped_dup": skipped_dup,
    }
