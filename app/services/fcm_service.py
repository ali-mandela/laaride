"""Firebase Cloud Messaging (FCM) service via Firebase Admin SDK.

Requires: firebase-admin (added to pyproject.toml dependencies).
Set FIREBASE_PROJECT_ID and FIREBASE_SERVICE_ACCOUNT_KEY in .env to enable.
When not configured, all calls degrade gracefully (return False / empty counts).
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_firebase_app = None  # module-level singleton


def initialize_firebase(service_account_key: str | dict, project_id: str) -> None:
    """Initialise Firebase Admin SDK once at application startup."""
    global _firebase_app
    if _firebase_app is not None:
        return  # already initialised

    import firebase_admin
    from firebase_admin import credentials

    if isinstance(service_account_key, str):
        try:
            cred_dict = json.loads(service_account_key)
        except json.JSONDecodeError:
            # Treat as file path
            cred_dict = service_account_key  # type: ignore[assignment]
    else:
        cred_dict = service_account_key

    cred = credentials.Certificate(cred_dict)
    _firebase_app = firebase_admin.initialize_app(cred, {"projectId": project_id})
    logger.info("firebase_admin_initialised", project_id=project_id)


def _is_ready() -> bool:
    return _firebase_app is not None


async def send_push_notification(
    token: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    image_url: str | None = None,
) -> bool:
    """Send a push notification to a single FCM token.

    Returns True on success, False on failure (invalid token, SDK not initialised, etc.).
    """
    if not _is_ready():
        logger.debug("fcm_not_initialised_skipping")
        return False

    from firebase_admin import messaging

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body, image=image_url),
        data={str(k): str(v) for k, v in (data or {}).items()},
        token=token,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(sound="default"),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default", badge=1)
            )
        ),
    )
    try:
        response = messaging.send(message)
        logger.info("fcm_sent", message_id=response, token_prefix=token[:12])
        return True
    except messaging.UnregisteredError:
        logger.warning("fcm_token_unregistered", token_prefix=token[:12])
        return False
    except messaging.SenderIdMismatchError:
        logger.warning("fcm_sender_mismatch", token_prefix=token[:12])
        return False
    except Exception as exc:
        logger.error("fcm_send_error", error=str(exc))
        return False


async def send_multicast_notification(
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Send push to multiple tokens. Returns success_count + failure_count."""
    if not _is_ready() or not tokens:
        return {"success_count": 0, "failure_count": len(tokens)}

    from firebase_admin import messaging

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in (data or {}).items()},
        tokens=tokens,
        android=messaging.AndroidConfig(priority="high"),
    )
    try:
        response = messaging.send_each_for_multicast(message)
        logger.info(
            "fcm_multicast_sent",
            success=response.success_count,
            failure=response.failure_count,
        )
        return {
            "success_count": response.success_count,
            "failure_count": response.failure_count,
        }
    except Exception as exc:
        logger.error("fcm_multicast_error", error=str(exc))
        return {"success_count": 0, "failure_count": len(tokens)}


async def unregister_invalid_tokens(tokens: list[str]) -> list[str]:
    """Return only tokens that are still registered (dry-run send to validate)."""
    if not _is_ready() or not tokens:
        return tokens

    from firebase_admin import messaging

    valid: list[str] = []
    for token in tokens:
        msg = messaging.Message(
            data={"_validate": "1"},
            token=token,
        )
        try:
            messaging.send(msg, dry_run=True)
            valid.append(token)
        except messaging.UnregisteredError:
            logger.info("fcm_pruned_invalid_token", token_prefix=token[:12])
        except Exception:
            valid.append(token)  # keep on unknown errors
    return valid
