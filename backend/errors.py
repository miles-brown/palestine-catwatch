"""
Standardized error handling for the API.

Provides consistent error response format across all endpoints.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Standardized error codes."""
    # Authentication errors (4xx)
    INVALID_CREDENTIALS = "invalid_credentials"
    EMAIL_NOT_VERIFIED = "email_not_verified"
    ACCOUNT_DISABLED = "account_disabled"
    ACCOUNT_LOCKED = "account_locked"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    TOKEN_REVOKED = "token_revoked"
    CSRF_VALIDATION_FAILED = "csrf_validation_failed"

    # Authorization errors
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    UNAUTHORIZED = "unauthorized"

    # Validation errors
    VALIDATION_ERROR = "validation_error"
    INVALID_INPUT = "invalid_input"
    MISSING_FIELD = "missing_field"
    INVALID_FORMAT = "invalid_format"

    # Resource errors
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Server errors
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_ERROR = "database_error"


class ErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error: dict


class APIError(HTTPException):
    """
    Custom API exception with standardized format.

    Usage:
        raise APIError(
            code=ErrorCode.NOT_FOUND,
            message="Officer not found",
            status_code=404
        )
    """
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        details: Optional[dict] = None,
        headers: Optional[dict] = None
    ):
        self.error_code = code
        self.error_message = message
        self.error_details = details

        detail = {
            "code": code.value,
            "message": message
        }
        if details:
            detail["details"] = details

        super().__init__(status_code=status_code, detail=detail, headers=headers)


def create_error_response(
    code: ErrorCode,
    message: str,
    status_code: int = 400,
    details: Optional[dict] = None
) -> JSONResponse:
    """
    Create a standardized error response.

    Returns:
        JSONResponse with standard error format
    """
    content = {
        "success": False,
        "error": {
            "code": code.value,
            "message": message
        }
    }
    if details:
        content["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=content)


def format_validation_errors(errors: list) -> dict:
    """
    Format Pydantic validation errors into standardized format.

    Args:
        errors: List of validation errors from Pydantic

    Returns:
        Dict with field-specific error messages
    """
    formatted = {}
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", ["unknown"]))
        formatted[field] = error.get("msg", "Invalid value")
    return formatted


async def validation_exception_handler(request: Request, exc):
    """
    Handle Pydantic validation errors with standardized format.

    Register with:
        from fastapi.exceptions import RequestValidationError
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
    """
    from fastapi.exceptions import RequestValidationError

    if isinstance(exc, RequestValidationError):
        errors = format_validation_errors(exc.errors())
        return create_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            status_code=422,
            details={"fields": errors}
        )

    return create_error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        status_code=500
    )


async def api_error_handler(request: Request, exc: APIError):
    """
    Handle APIError exceptions.

    Register with:
        app.add_exception_handler(APIError, api_error_handler)
    """
    content = {
        "success": False,
        "error": {
            "code": exc.error_code.value,
            "message": exc.error_message
        }
    }
    if exc.error_details:
        content["error"]["details"] = exc.error_details

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle standard HTTPException with standardized format.

    Register with:
        app.add_exception_handler(HTTPException, http_exception_handler)
    """
    # If detail is already a dict with code/message, use it
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail
            },
            headers=getattr(exc, "headers", None)
        )

    # Map status codes to error codes
    code_map = {
        400: ErrorCode.INVALID_INPUT,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.INSUFFICIENT_PERMISSIONS,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }

    error_code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": error_code.value,
                "message": message
            }
        },
        headers=getattr(exc, "headers", None)
    )


def setup_error_handlers(app):
    """
    Set up all error handlers on a FastAPI app.

    Call this in main.py after creating the app instance.

    Usage:
        from errors import setup_error_handlers
        setup_error_handlers(app)
    """
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
