"""Notification endpoints — FCM token management + notification CRUD."""

from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.core.database import get_database, USERS_COLLECTION
from app.core.security import get_current_active_user, get_current_admin
from app.models.user import UserDocument
from app.schemas.notification import (
    BroadcastRequest,
    FCMTokenRequest,
    MarkReadRequest,
)
from app.services import notification_service

router = APIRouter(tags=["Notifications"])


# ── User endpoints ─────────────────────────────────────────────────────────


@router.post("/fcm-token", summary="Register FCM token")
async def register_fcm_token(
    data: FCMTokenRequest,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Register a device FCM token for push notifications."""
    return await notification_service.register_fcm_token(
        str(current_user.id), data.token, db
    )


@router.delete("/fcm-token", summary="Remove FCM token")
async def remove_fcm_token(
    data: FCMTokenRequest,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Remove a device FCM token (e.g. on logout)."""
    return await notification_service.remove_fcm_token(
        str(current_user.id), data.token, db
    )


@router.get("/", summary="Get my notifications")
async def get_notifications(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Get paginated notifications for the current user."""
    return await notification_service.get_user_notifications(
        str(current_user.id), skip, limit, db
    )


@router.put("/read", summary="Mark notifications as read")
async def mark_read(
    data: MarkReadRequest,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Mark specific notifications as read. Empty list = mark all as read."""
    return await notification_service.mark_notifications_read(
        str(current_user.id), data.notification_ids, db
    )


@router.get("/unread-count", summary="Get unread count")
async def unread_count(
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Get the count of unread notifications."""
    return await notification_service.get_unread_count(str(current_user.id), db)


# ── Admin endpoints ───────────────────────────────────────────────────────


@router.post("/broadcast", summary="Broadcast notification (admin)")
async def broadcast_notification(
    data: BroadcastRequest,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: send a notification to all users (optionally filtered by role)."""
    query: dict = {"is_active": True}
    if data.role_filter:
        query["role"] = data.role_filter

    cursor = db[USERS_COLLECTION].find(query, {"_id": 1})
    user_ids = [str(doc["_id"]) async for doc in cursor]

    if not user_ids:
        return {"message": "No matching users found", "sent": 0}

    result = await notification_service.send_bulk_notification(
        user_ids, data.title, data.body, db, data=data.data, notification_type="system"
    )
    return result
