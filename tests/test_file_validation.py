"""Tests for file upload validation."""

import pytest

from app.utils.file_validation import (
    validate_image_file,
    validate_document_file,
    sanitize_filename,
)


def test_valid_image_file():
    """Test validation of a valid image file."""
    is_valid, error = validate_image_file(
        filename="profile.jpg",
        file_size=2 * 1024 * 1024,  # 2 MB
        content_type="image/jpeg",
    )

    assert is_valid is True
    assert error is None


def test_image_file_too_large():
    """Test validation of oversized image."""
    is_valid, error = validate_image_file(
        filename="profile.jpg",
        file_size=10 * 1024 * 1024,  # 10 MB (exceeds 5 MB limit)
        content_type="image/jpeg",
    )

    assert is_valid is False
    assert "too large" in error.lower()


def test_image_invalid_extension():
    """Test validation of image with invalid extension."""
    is_valid, error = validate_image_file(
        filename="profile.exe",
        file_size=1 * 1024 * 1024,
        content_type="image/jpeg",
    )

    assert is_valid is False
    assert "invalid" in error.lower()


def test_image_invalid_mime_type():
    """Test validation with invalid MIME type."""
    is_valid, error = validate_image_file(
        filename="profile.jpg",
        file_size=2 * 1024 * 1024,
        content_type="application/pdf",
    )

    assert is_valid is False
    assert "mime" in error.lower()


def test_valid_document_file():
    """Test validation of a valid document."""
    is_valid, error = validate_document_file(
        filename="license.pdf",
        file_size=5 * 1024 * 1024,  # 5 MB
        content_type="application/pdf",
    )

    assert is_valid is True
    assert error is None


def test_document_file_too_large():
    """Test validation of oversized document."""
    is_valid, error = validate_document_file(
        filename="license.pdf",
        file_size=15 * 1024 * 1024,  # 15 MB (exceeds 10 MB limit)
        content_type="application/pdf",
    )

    assert is_valid is False
    assert "too large" in error.lower()


def test_document_invalid_extension():
    """Test validation of document with invalid extension."""
    is_valid, error = validate_document_file(
        filename="license.txt",
        file_size=5 * 1024 * 1024,
        content_type="application/pdf",
    )

    assert is_valid is False
    assert "invalid" in error.lower()


def test_sanitize_filename():
    """Test filename sanitization."""
    # Test with directory traversal attempt
    result = sanitize_filename("../../../etc/passwd")
    assert "/" not in result
    assert "\\" not in result
    assert "." not in result[0:3]

    # Test with normal filename
    result = sanitize_filename("profile_photo.jpg")
    assert result == "profile_photo.jpg"

    # Test with null bytes
    result = sanitize_filename("photo\x00.jpg")
    assert "\x00" not in result


def test_sanitize_filename_length():
    """Test that sanitized filename is length-limited."""
    long_filename = "a" * 300 + ".jpg"
    result = sanitize_filename(long_filename)
    assert len(result) <= 255
