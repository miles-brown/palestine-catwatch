"""
Rate limiting configuration for the API.

Uses slowapi to provide per-IP rate limiting on endpoints.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Create limiter instance
# Uses client IP address for rate limit tracking
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
# Format: "X per Y" where X is number of requests, Y is time period
# Periods: second, minute, hour, day

RATE_LIMITS = {
    # General API endpoints
    "default": "100/minute",

    # Authentication endpoints - strict limits to prevent brute force
    "auth_login": "5/minute",           # Login attempts - very strict
    "auth_login_hourly": "20/hour",     # Additional hourly limit
    "auth_register": "3/minute",        # Registration - prevent spam
    "auth_register_hourly": "10/hour",  # Hourly registration limit
    "auth_verify": "10/minute",         # Email verification
    "auth_password_reset": "3/minute",  # Password reset requests

    # Expensive AI processing endpoints - stricter limits
    "ingest": "5/minute",      # URL ingestion (triggers video download + AI)
    "upload": "10/minute",     # File uploads

    # Read-only endpoints - more permissive
    "officers_list": "60/minute",
    "officers_detail": "120/minute",
    "report": "30/minute",

    # Static data
    "protests": "60/minute",
}


def get_rate_limit(endpoint_type: str) -> str:
    """Get the rate limit string for an endpoint type."""
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["default"])


def setup_rate_limiting(app):
    """
    Configure rate limiting on a FastAPI app.

    Call this in main.py after creating the FastAPI app instance.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
