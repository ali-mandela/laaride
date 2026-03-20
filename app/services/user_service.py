import os
import time
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, UploadFile, status
from bson import ObjectId, errors

from app.core.database import USERS_COLLECTION, BOOKINGS_COLLECTION
from app.enums.common import UserRole
from app.schemas.booking import BookingResponse
from app.schemas.user import UserResponse, UserUpdate


ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
UPLOAD_DIR = os.path.join("uploads", "profiles")


async def get_user_by_id(user_id: str, db: Any) -> UserResponse:
    """Fetch a user by their ID."""
    try:
        obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid User ID format")
        
    user_data = await db[USERS_COLLECTION].find_one({"_id": obj_id})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse(**user_data)


async def update_user(user_id: str, data: UserUpdate, db: Any) -> UserResponse:
    """Partially update a user's profile."""
    # Build $set dict from only the provided (non-None) fields
    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    update_fields["updated_at"] = datetime.utcnow()

    try:
        obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid User ID format")

    result = await db[USERS_COLLECTION].update_one(
        {"_id": obj_id},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return await get_user_by_id(user_id, db)


async def upload_profile_photo(
    user_id: str, file: UploadFile, db: Any
) -> UserResponse:
    """Validate, save, and attach a profile photo to the user."""
    # Validate extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        )

    # Read file and validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
        )

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save file
    timestamp = int(time.time())
    filename = f"{user_id}_{timestamp}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    # Store relative path in DB (served via /uploads static mount)
    relative_path = f"/uploads/profiles/{filename}"

    try:
        obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid User ID format")

    result = await db[USERS_COLLECTION].update_one(
        {"_id": obj_id},
        {"$set": {"profile_photo": relative_path, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        # Clean up the file if user doesn't exist
        os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return await get_user_by_id(user_id, db)


async def get_user_booking_history(
    user_id: str, skip: int, limit: int, db: Any
) -> dict:
    """Fetch paginated booking history for a user."""
    try:
        obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid User ID format")

    query = {"passenger_id": str(obj_id)}  # Usually stored as string in bookings, but checking consistency

    total = await db[BOOKINGS_COLLECTION].count_documents(query)


    cursor = (
        db[BOOKINGS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    bookings = [BookingResponse(**doc) async for doc in cursor]

    return {
        "data": bookings,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


async def deactivate_user(user_id: str, db: Any) -> dict:
    """Soft-delete a user by setting is_active to False."""
    try:
        obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid User ID format")

    result = await db[USERS_COLLECTION].update_one(
        {"_id": obj_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return {"message": "Account deactivated successfully"}


async def list_users(
    skip: int,
    limit: int,
    db: Any,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
) -> dict:
    """Admin: list all users with optional filters, paginated."""
    query: dict = {}
    if role is not None:
        query["role"] = role.value
    if is_active is not None:
        query["is_active"] = is_active

    total = await db[USERS_COLLECTION].count_documents(query)

    cursor = (
        db[USERS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    users = [UserResponse(**doc) async for doc in cursor]

    return {
        "data": users,
        "total": total,
        "skip": skip,
        "limit": limit,
    }
