from __future__ import annotations

import json
import logging
from typing import Literal

from pywebpush import WebPushException, webpush

from app.config import settings
from app.models.entities import PushSubscription


logger = logging.getLogger(__name__)


def send_web_push(
    subscription: PushSubscription,
    title: str,
    body: str,
    data: dict,
) -> Literal["ok", "gone", "error"]:
    if not settings.vapid_private_key or not settings.vapid_public_key:
        return "error"

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps({"title": title, "body": body, "data": data}, ensure_ascii=False),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return "gone" if status in (404, 410) else "error"
    except Exception:
        logger.exception("Web push transport failed for subscription %s", subscription.id)
        return "error"

    return "ok"
