"""
CSRF protection for stateful operations.

For JWT-based APIs, CSRF is less critical since we don't use cookies for auth.
However, this provides additional protection for sensitive operations like registration.

Implementation uses double-submit cookie pattern adapted for SPAs:
1. Frontend calls /csrf/token to get a CSRF token
2. Token is returned in both response body AND set as a cookie
3. Frontend includes token in X-CSRF-Token header on protected requests
4. Backend validates header matches cookie

SECURITY NOTE - httpOnly=False on CSRF Cookie:
=============================================
The CSRF cookie intentionally has httpOnly=False. This is NOT a vulnerability but
a deliberate design choice for the double-submit cookie pattern in SPAs:

Why httpOnly=False is required:
- Double-submit pattern requires JavaScript to read the cookie value
- The value must be sent in both the cookie AND a custom header (X-CSRF-Token)
- An attacker's malicious site cannot read cross-origin cookies due to Same-Origin Policy
- Even if XSS allows reading the cookie, the attacker already has script execution
  and can bypass CSRF anyway

Why this is still secure:
1. SameSite=Strict prevents the cookie from being sent on cross-origin requests
2. Secure=true (in production) ensures HTTPS-only transmission
3. The real protection comes from the header+cookie double-submit, not httpOnly
4. XSS attacks are mitigated by CSP headers and input sanitization, not CSRF tokens

Alternative considered:
- Encrypted CSRF tokens with server-side validation (more complex, similar security)
- Synchronizer token pattern (requires server-side session state)

References:
- OWASP Double Submit Cookie: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie
- Why httpOnly doesn't help CSRF: https://security.stackexchange.com/questions/220797/
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
    Set the CSRF token as a cookie for double-submit validation.

    The cookie is:
    - SameSite=Strict: Prevents cross-site request inclusion
    - Secure=True (production): HTTPS-only transmission
    - HttpOnly=False: REQUIRED for double-submit pattern (see module docstring)

    Security: httpOnly=False is intentional and documented above.
    """
    is_production = os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=CSRF_TOKEN_EXPIRY_HOURS * 3600,
        # httpOnly=False is REQUIRED for double-submit pattern - JS must read cookie
        # to send in X-CSRF-Token header. See module docstring for security analysis.
        httponly=False,
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
