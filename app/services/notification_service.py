"""Notification service — FCM push notifications + in-app notification management."""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId, errors
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.database import NOTIFICATIONS_COLLECTION, USERS_COLLECTION
from app.schemas.notification import NotificationResponse

logger = logging.getLogger(__name__)

MAX_FCM_TOKENS_PER_USER = 5


# ── Helpers ────────────────────────────────────────────────────────────────


def _to_object_id(value: str, label: str = "ID") -> ObjectId:
    try:
        return ObjectId(value)
    except errors.InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label} format",
        )


# ── FCM Token Management ──────────────────────────────────────────────────


async def register_fcm_token(user_id: str, token: str, db: Any) -> dict:
    """Add FCM token to user's token list. Max 5 per user (oldest removed)."""
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="FCM token cannot be empty"
        )

    obj_id = _to_object_id(user_id, "User ID")
    user = await db[USERS_COLLECTION].find_one({"_id": obj_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    fcm_tokens = user.get("fcm_tokens", [])

    # Avoid duplicates
    if token in fcm_tokens:
        return {"message": "Token already registered"}

    fcm_tokens.append(token)

    # Trim to max
    if len(fcm_tokens) > MAX_FCM_TOKENS_PER_USER:
        fcm_tokens = fcm_tokens[-MAX_FCM_TOKENS_PER_USER:]

    await db[USERS_COLLECTION].update_one(
        {"_id": obj_id},
        {"$set": {"fcm_tokens": fcm_tokens, "updated_at": datetime.utcnow()}},
    )
    return {"message": "FCM token registered successfully"}


async def remove_fcm_token(user_id: str, token: str, db: Any) -> dict:
    """Remove an FCM token from user's token list."""
    obj_id = _to_object_id(user_id, "User ID")
    await db[USERS_COLLECTION].update_one(
        {"_id": obj_id},
        {
            "$pull": {"fcm_tokens": token},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )
    return {"message": "FCM token removed successfully"}


# ── FCM Push ───────────────────────────────────────────────────────────────


async def _send_fcm_message(token: str, title: str, body: str, data: Optional[dict]) -> bool:
    """Send a single FCM push via HTTP v1 API. Returns True on success."""
    project_id = settings.FIREBASE_PROJECT_ID
    service_account_key = settings.FIREBASE_SERVICE_ACCOUNT_KEY

    if not project_id or not service_account_key:
        logger.info("FCM not configured — skipping push notification (dev mode)")
        return False

    try:
        import google.auth.transport.requests
        from google.oauth2 import service_account

        # Parse service account key
        sa_info = json.loads(service_account_key)
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        credentials.refresh(google.auth.transport.requests.Request())

        import httpx

        url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }
        message = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
            }
        }
        if data:
            message["message"]["data"] = {k: str(v) for k, v in data.items()}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=message, headers=headers, timeout=10)

        if resp.status_code == 200:
            return True
        elif resp.status_code in (400, 404):
            # Invalid token — should be removed
            logger.warning(f"Invalid FCM token: {token[:20]}... — will be removed")
            return False
        else:
            logger.error(f"FCM send failed: {resp.status_code} {resp.text}")
            return False

    except ImportError:
        logger.info("google-auth / httpx not installed — FCM disabled")
        return False
    except Exception as e:
        logger.error(f"FCM send error: {e}")
        return False


# ── Send Notification ──────────────────────────────────────────────────────


async def send_push_notification(
    user_id: str,
    title: str,
    body: str,
    db: Any,
    data: Optional[dict] = None,
    notification_type: str = "system",
    reference_id: Optional[str] = None,
) -> bool:
    """Send push notification to user and store in-app notification. Fire-and-forget."""
    try:
        obj_id = _to_object_id(user_id, "User ID")
        user = await db[USERS_COLLECTION].find_one({"_id": obj_id})

        # Store in-app notification regardless of FCM result
        now = datetime.utcnow()
        notif_doc = {
            "user_id": user_id,
            "title": title,
            "body": body,
            "data": data,
            "is_read": False,
            "notification_type": notification_type,
            "reference_id": reference_id,
            "created_at": now,
            "updated_at": now,
        }
        await db[NOTIFICATIONS_COLLECTION].insert_one(notif_doc)

        if not user:
            return False

        fcm_tokens = user.get("fcm_tokens", [])
        if not fcm_tokens:
            return True  # stored in-app, no push needed

        # Send to all device tokens
        success = False
        invalid_tokens = []
        for token in fcm_tokens:
            result = await _send_fcm_message(token, title, body, data)
            if result:
                success = True
            else:
                invalid_tokens.append(token)

        # Remove invalid tokens
        if invalid_tokens and settings.FIREBASE_PROJECT_ID:
            for bad_token in invalid_tokens:
                await db[USERS_COLLECTION].update_one(
                    {"_id": obj_id}, {"$pull": {"fcm_tokens": bad_token}}
                )

        return success

    except Exception as e:
        logger.error(f"Failed to send notification to {user_id}: {e}")
        return False


async def send_bulk_notification(
    user_ids: list[str],
    title: str,
    body: str,
    db: Any,
    data: Optional[dict] = None,
    notification_type: str = "system",
) -> dict:
    """Send notification to multiple users. Fire-and-forget, logs failures."""
    sent = 0
    failed = 0
    for uid in user_ids:
        result = await send_push_notification(
            uid, title, body, db,
            data=data,
            notification_type=notification_type,
        )
        if result:
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed, "total": len(user_ids)}


# ── In-App Notification CRUD ──────────────────────────────────────────────


async def get_user_notifications(
    user_id: str, skip: int, limit: int, db: Any
) -> dict:
    """Get paginated notifications for a user, newest first."""
    query = {"user_id": user_id}
    total = await db[NOTIFICATIONS_COLLECTION].count_documents(query)
    cursor = (
        db[NOTIFICATIONS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    notifications = [NotificationResponse(**doc) async for doc in cursor]
    return {"data": notifications, "total": total, "skip": skip, "limit": limit}


async def mark_notifications_read(
    user_id: str, notification_ids: list[str], db: Any
) -> dict:
    """Mark specified notifications as read. If list is empty, mark all as read."""
    now = datetime.utcnow()
    if not notification_ids:
        # Mark ALL as read
        result = await db[NOTIFICATIONS_COLLECTION].update_many(
            {"user_id": user_id, "is_read": False},
            {"$set": {"is_read": True, "updated_at": now}},
        )
        return {"marked_read": result.modified_count}

    # Mark specific ones
    obj_ids = [_to_object_id(nid, "Notification ID") for nid in notification_ids]
    result = await db[NOTIFICATIONS_COLLECTION].update_many(
        {"_id": {"$in": obj_ids}, "user_id": user_id},
        {"$set": {"is_read": True, "updated_at": now}},
    )
    return {"marked_read": result.modified_count}


async def get_unread_count(user_id: str, db: Any) -> dict:
    """Return count of unread notifications for a user."""
    count = await db[NOTIFICATIONS_COLLECTION].count_documents(
        {"user_id": user_id, "is_read": False}
    )
    return {"unread_count": count}
