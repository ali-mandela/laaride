"""Custom exception classes for consistent error handling across the platform."""

from typing import Optional


class LaaRideException(Exception):
    """Base exception for all LaaRide errors."""

    def __init__(
        self,
        message: str = "An error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(LaaRideException):
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND", details: Optional[dict] = None):
        super().__init__(message=message, code=code, status_code=404, details=details)


class ValidationError(LaaRideException):
    def __init__(self, message: str = "Validation error", code: str = "VALIDATION_ERROR", details: Optional[dict] = None):
        super().__init__(message=message, code=code, status_code=400, details=details)


class AuthenticationError(LaaRideException):
    def __init__(self, message: str = "Authentication failed", code: str = "AUTH_ERROR", details: Optional[dict] = None):
        super().__init__(message=message, code=code, status_code=401, details=details)


class AuthorizationError(LaaRideException):
    def __init__(self, message: str = "Forbidden", code: str = "FORBIDDEN", details: Optional[dict] = None):
        super().__init__(message=message, code=code, status_code=403, details=details)


class ConflictError(LaaRideException):
    def __init__(self, message: str = "Conflict", code: str = "CONFLICT", details: Optional[dict] = None):
        super().__init__(message=message, code=code, status_code=409, details=details)


class ExternalServiceError(LaaRideException):
    def __init__(self, message: str = "External service error", code: str = "EXTERNAL_SERVICE_ERROR", details: Optional[dict] = None):
        super().__init__(message=message, code=code, status_code=502, details=details)
