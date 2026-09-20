from __future__ import annotations

import logging
from typing import Literal, Optional

import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

from app.config import settings
from app.models.entities import PushSubscription


logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None


def _get_firebase_app() -> Optional[firebase_admin.App]:
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    if not settings.fcm_configured:
        return None
    try:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app
    except ValueError:
        pass

    cred = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "private_key": settings.firebase_private_key_normalized,
            "client_email": settings.firebase_client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def send_fcm_push(
    subscription: PushSubscription,
    title: str,
    body: str,
    data: dict,
) -> Literal["ok", "gone", "error"]:
    if _get_firebase_app() is None:
        return "error"

    string_data = {str(key): "" if value is None else str(value) for key, value in data.items()}
    string_data["title"] = title
    string_data["body"] = body

    message = messaging.Message(
        token=subscription.fcm_token,
        data=string_data,
        webpush=messaging.WebpushConfig(
            fcm_options=messaging.WebpushFCMOptions(
                link=string_data.get("url") or "/notifications",
            ),
        ),
    )

    try:
        messaging.send(message)
    except messaging.UnregisteredError:
        return "gone"
    except FirebaseError as exc:
        code = str(getattr(exc, "code", "") or "").upper()
        message_text = str(exc).upper()
        if code in {"NOT_FOUND", "UNREGISTERED"} or "UNREGISTERED" in message_text or "NOT_FOUND" in message_text:
            return "gone"
        logger.exception("FCM send failed for subscription %s", subscription.id)
        return "error"
    except Exception:
        logger.exception("FCM transport failed for subscription %s", subscription.id)
        return "error"

    return "ok"
