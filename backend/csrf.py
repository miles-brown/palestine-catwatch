"""
CSRF protection for stateful operations.

For JWT-based APIs, CSRF is less critical since we don't use cookies for auth.
However, this provides additional protection for sensitive operations like registration.

Implementation uses double-submit cookie pattern adapted for SPAs:
1. Frontend calls /csrf/token to get a CSRF token
2. Token is returned in both response body AND set as a cookie
3. Frontend includes token in X-CSRF-Token header on protected requests
4. Backend validates header matches cookie
"""

import secrets
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Request, HTTPException, Response


# CSRF token settings
CSRF_TOKEN_LENGTH = 32  # 256 bits
CSRF_TOKEN_EXPIRY_HOURS = 24
CSRF_COOKIE_NAME = "catwatch_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Whether to enforce CSRF (can disable in development)
CSRF_ENABLED = os.getenv("CSRF_ENABLED", "true").lower() == "true"


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def set_csrf_cookie(response: Response, token: str) -> None:
    """
    Set the CSRF token as an HTTP-only cookie.

    The cookie is:
    - SameSite=Strict to prevent cross-site requests
    - Secure in production (HTTPS only)
    - HttpOnly=False so JavaScript can read it
    """
    is_production = os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=CSRF_TOKEN_EXPIRY_HOURS * 3600,
        httponly=False,  # Allow JS to read for double-submit
        samesite="strict",
        secure=is_production,
        path="/"
    )


def get_csrf_from_request(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract CSRF token from both header and cookie.

    Returns:
        Tuple of (header_token, cookie_token)
    """
    header_token = request.headers.get(CSRF_HEADER_NAME)
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    return header_token, cookie_token


def validate_csrf(request: Request) -> bool:
    """
    Validate CSRF token using double-submit pattern.

    Checks that:
    1. Both header and cookie tokens exist
    2. They match each other

    Returns:
        True if valid, False otherwise
    """
    if not CSRF_ENABLED:
        return True

    header_token, cookie_token = get_csrf_from_request(request)

    # Both must exist
    if not header_token or not cookie_token:
        return False

    # Must match (constant-time comparison)
    return secrets.compare_digest(header_token, cookie_token)


def require_csrf(request: Request) -> None:
    """
    FastAPI dependency to require valid CSRF token.

    Raises HTTPException if CSRF validation fails.

    Usage:
        @app.post("/protected")
        def protected_endpoint(request: Request, _ = Depends(require_csrf)):
            ...
    """
    if not CSRF_ENABLED:
        return

    if not validate_csrf(request):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "csrf_validation_failed",
                "message": "Invalid or missing CSRF token. Please refresh the page and try again."
            }
        )
