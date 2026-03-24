"""Firebase Cloud Messaging (FCM) service for push notifications.

This module implements the actual FCM push notification delivery
using the Firebase Admin SDK.

TODO: Replace all placeholder implementations with real Firebase Admin SDK calls.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# TODO: Install firebase-admin: uv add firebase-admin
# import firebase_admin
# from firebase_admin import credentials, messaging

_firebase_app = None


def initialize_firebase(service_account_key: str | dict, project_id: str) -> None:
    """Initialize Firebase Admin SDK.

    Args:
        service_account_key: Path to JSON key file or JSON string of service account credentials.
        project_id: Firebase project ID.
    """
    # TODO: Implement
    # global _firebase_app
    # if isinstance(service_account_key, str):
    #     try:
    #         cred_dict = json.loads(service_account_key)
    #     except json.JSONDecodeError:
    #         cred_dict = service_account_key  # treat as file path
    # else:
    #     cred_dict = service_account_key
    # cred = credentials.Certificate(cred_dict)
    # _firebase_app = firebase_admin.initialize_app(cred, {"projectId": project_id})
    logger.info("Firebase initialized (stub)", extra={"project_id": project_id})


async def send_push_notification(
    token: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    image_url: str | None = None,
) -> bool:
    """Send a push notification to a single FCM token.

    Args:
        token: FCM device registration token.
        title: Notification title.
        body: Notification body text.
        data: Optional key-value data payload.
        image_url: Optional image URL for rich notifications.

    Returns:
        True if successfully sent, False otherwise.
    """
    # TODO: Implement with firebase_admin.messaging
    # message = messaging.Message(
    #     notification=messaging.Notification(title=title, body=body, image=image_url),
    #     data={str(k): str(v) for k, v in (data or {}).items()},
    #     token=token,
    #     android=messaging.AndroidConfig(
    #         priority="high",
    #         notification=messaging.AndroidNotification(sound="default"),
    #     ),
    #     apns=messaging.APNSConfig(
    #         payload=messaging.APNSPayload(
    #             aps=messaging.Aps(sound="default", badge=1)
    #         )
    #     ),
    # )
    # try:
    #     response = messaging.send(message)
    #     logger.info("FCM message sent", extra={"message_id": response})
    #     return True
    # except messaging.UnregisteredError:
    #     logger.warning("FCM token unregistered", extra={"token": token[:20]})
    #     return False
    # except Exception as e:
    #     logger.error("FCM send error", extra={"error": str(e)})
    #     return False
    logger.info("FCM push sent (stub)", extra={"title": title, "token_prefix": token[:10]})
    return True


async def send_multicast_notification(
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Send push notification to multiple FCM tokens.

    Args:
        tokens: List of FCM device registration tokens.
        title: Notification title.
        body: Notification body.
        data: Optional data payload.

    Returns:
        Dict with 'success_count' and 'failure_count'.
    """
    # TODO: Implement with messaging.MulticastMessage
    # message = messaging.MulticastMessage(
    #     notification=messaging.Notification(title=title, body=body),
    #     data={str(k): str(v) for k, v in (data or {}).items()},
    #     tokens=tokens,
    # )
    # response = messaging.send_each_for_multicast(message)
    # return {"success_count": response.success_count, "failure_count": response.failure_count}
    logger.info("FCM multicast sent (stub)", extra={"token_count": len(tokens)})
    return {"success_count": len(tokens), "failure_count": 0}


async def unregister_invalid_tokens(tokens: list[str]) -> list[str]:
    """Check which tokens are invalid/unregistered and return valid ones.

    Args:
        tokens: List of FCM tokens to validate.

    Returns:
        List of still-valid tokens.
    """
    # TODO: Use dry_run send to validate tokens
    return tokens
