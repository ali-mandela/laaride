"""File upload validation utilities."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# File upload constraints
MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}


def validate_image_file(
    filename: str,
    file_size: int,
    content_type: Optional[str] = None,
    max_size: int = MAX_PROFILE_PHOTO_SIZE,
) -> tuple[bool, Optional[str]]:
    """Validate an image file for upload.

    Args:
        filename: Original filename
        file_size: File size in bytes
        content_type: MIME type (e.g., 'image/jpeg')
        max_size: Maximum allowed file size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    if file_size > max_size:
        error = f"File too large: {file_size / 1024 / 1024:.1f} MB > {max_size / 1024 / 1024:.0f} MB"
        logger.warning("file_upload_too_large", filename=filename, size=file_size)
        return False, error

    # Check file extension
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    file_ext = "." + (filename.rsplit(".", 1)[1].lower() if "." in filename else "")
    if file_ext not in allowed_extensions:
        error = f"Invalid file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        logger.warning("file_upload_invalid_extension", filename=filename, ext=file_ext)
        return False, error

    # Check MIME type if provided
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        error = f"Invalid MIME type: {content_type}"
        logger.warning("file_upload_invalid_mime", filename=filename, mime=content_type)
        return False, error

    return True, None


def validate_document_file(
    filename: str,
    file_size: int,
    content_type: Optional[str] = None,
    max_size: int = MAX_DOCUMENT_SIZE,
) -> tuple[bool, Optional[str]]:
    """Validate a document file (PDF, image) for upload.

    Args:
        filename: Original filename
        file_size: File size in bytes
        content_type: MIME type
        max_size: Maximum allowed file size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    if file_size > max_size:
        error = f"File too large: {file_size / 1024 / 1024:.1f} MB > {max_size / 1024 / 1024:.0f} MB"
        logger.warning("document_upload_too_large", filename=filename, size=file_size)
        return False, error

    # Check file extension
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
    file_ext = "." + (filename.rsplit(".", 1)[1].lower() if "." in filename else "")
    if file_ext not in allowed_extensions:
        error = f"Invalid file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        logger.warning("document_upload_invalid_extension", filename=filename, ext=file_ext)
        return False, error

    # Check MIME type if provided
    if content_type and content_type not in ALLOWED_DOCUMENT_TYPES:
        error = f"Invalid MIME type: {content_type}"
        logger.warning("document_upload_invalid_mime", filename=filename, mime=content_type)
        return False, error

    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and other attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove directory separators
    filename = filename.replace("\\", "").replace("/", "")
    # Remove null bytes
    filename = filename.replace("\x00", "")
    # Limit length
    filename = filename[:255]
    return filename
