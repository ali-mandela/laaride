"""
Storage service — abstract file storage with Backblaze B2 backend.

Provides a StorageService protocol for uploading/deleting files.
Falls back to local filesystem when B2 credentials are not configured.
Swap to Cloudinary by implementing the same protocol in a new file.
"""

import os
from io import BytesIO
from typing import Optional, Protocol, runtime_checkable
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, ValidationError
from app.core.logging import get_logger

logger = get_logger("laaride.storage")

# ── Constants ──────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


# ── Protocol ───────────────────────────────────────────────────────────────


@runtime_checkable
class StorageService(Protocol):
    """Abstract interface for file storage backends."""

    async def upload_file(
        self, file: UploadFile, folder: str, filename: str
    ) -> str: ...

    async def delete_file(self, file_url: str) -> bool: ...

    def get_public_url(self, key: str) -> str: ...


# ── Helpers ────────────────────────────────────────────────────────────────


def _validate_file(filename: str, content: bytes) -> str:
    """Validate file extension and size. Returns the extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            message=f"Invalid file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            code="INVALID_FILE_TYPE",
        )
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            message=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
            code="FILE_TOO_LARGE",
        )
    return ext


def _generate_key(folder: str, filename: str) -> str:
    """Generate a unique storage key: {folder}/{uuid4}_{original_filename}."""
    safe_name = filename.replace(" ", "_")
    return f"{folder}/{uuid4().hex[:12]}_{safe_name}"


# ── B2 Implementation ─────────────────────────────────────────────────────


class B2StorageService:
    """Backblaze B2 storage via S3-compatible API (boto3)."""

    def __init__(self) -> None:
        import boto3

        self._bucket_name = settings.BACKBLAZE_BUCKET_NAME or ""
        self._region = settings.BACKBLAZE_REGION
        endpoint_url = f"https://s3.{self._region}.backblazeb2.com"

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.BACKBLAZE_KEY_ID,
            aws_secret_access_key=settings.BACKBLAZE_APPLICATION_KEY,
            region_name=self._region,
        )
        logger.info(
            "B2 storage initialised",
            bucket=self._bucket_name,
            region=self._region,
        )

    def get_public_url(self, key: str) -> str:
        """Construct the public URL for a stored object."""
        return (
            f"https://{self._bucket_name}.s3.{self._region}.backblazeb2.com/{key}"
        )

    async def upload_file(
        self, file: UploadFile, folder: str, filename: str
    ) -> str:
        """Upload a file to B2. Returns the public URL."""
        if not file.filename:
            raise ValidationError(
                message="Filename is required", code="MISSING_FILENAME"
            )

        content = await file.read()
        _validate_file(file.filename, content)

        key = _generate_key(folder, file.filename)

        try:
            content_type = file.content_type or "application/octet-stream"
            self._client.upload_fileobj(
                BytesIO(content),
                self._bucket_name,
                key,
                ExtraArgs={"ContentType": content_type},
            )
        except Exception as exc:
            logger.error("B2 upload failed", key=key, error=str(exc))
            raise ExternalServiceError(
                message="File upload failed. Please try again later.",
                code="STORAGE_UPLOAD_ERROR",
            )

        url = self.get_public_url(key)
        logger.info("File uploaded to B2", key=key, folder=folder)
        return url

    async def delete_file(self, file_url: str) -> bool:
        """Delete a file from B2 by its public URL. Never raises."""
        try:
            # Extract key from URL — everything after the bucket hostname
            prefix = f"https://{self._bucket_name}.s3.{self._region}.backblazeb2.com/"
            if not file_url.startswith(prefix):
                logger.warning("URL doesn't match B2 bucket", url=file_url)
                return False

            key = file_url[len(prefix) :]
            self._client.delete_object(Bucket=self._bucket_name, Key=key)
            logger.info("File deleted from B2", key=key)
            return True
        except Exception as exc:
            logger.error("B2 delete failed", url=file_url, error=str(exc))
            return False


# ── Local Fallback ─────────────────────────────────────────────────────────


class LocalStorageService:
    """Fallback: saves files to the local filesystem under /uploads/."""

    def __init__(self) -> None:
        logger.warning("B2 not configured, using local storage")

    def get_public_url(self, key: str) -> str:
        return f"/uploads/{key}"

    async def upload_file(
        self, file: UploadFile, folder: str, filename: str
    ) -> str:
        """Save file locally. Returns a relative path."""
        if not file.filename:
            raise ValidationError(
                message="Filename is required", code="MISSING_FILENAME"
            )

        content = await file.read()
        _validate_file(file.filename, content)

        key = _generate_key(folder, file.filename)
        filepath = os.path.join("uploads", key)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(content)

        url = f"/uploads/{key}"
        logger.info("File saved locally", path=url, folder=folder)
        return url

    async def delete_file(self, file_url: str) -> bool:
        """Delete a local file. Never raises."""
        try:
            # Strip leading /uploads/ to get relative path
            relative = file_url.lstrip("/")
            if os.path.exists(relative):
                os.remove(relative)
                logger.info("Local file deleted", path=relative)
                return True
            logger.warning("Local file not found for deletion", path=relative)
            return False
        except Exception as exc:
            logger.error("Local delete failed", path=file_url, error=str(exc))
            return False


# ── Factory / Singleton ────────────────────────────────────────────────────

_instance: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Return a cached StorageService instance (B2 or local fallback)."""
    global _instance
    if _instance is not None:
        return _instance

    b2_configured = all([
        settings.BACKBLAZE_KEY_ID,
        settings.BACKBLAZE_APPLICATION_KEY,
        settings.BACKBLAZE_BUCKET_NAME,
    ])

    if b2_configured:
        _instance = B2StorageService()
    else:
        _instance = LocalStorageService()

    return _instance
