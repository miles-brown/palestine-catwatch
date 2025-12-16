"""
Rate limiting configuration for the API.

Uses slowapi to provide per-IP rate limiting on endpoints.

DoS Protection Strategy:
1. AI endpoints have strict per-minute AND per-hour limits
2. Concurrent request limiting via semaphores
3. Request size limits
4. Progressive rate limiting for repeated violations
"""

import os
import asyncio
from functools import wraps
from typing import Callable

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException

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

    # Expensive AI processing endpoints - strict limits
    "ingest": "5/minute",           # URL ingestion (triggers video download + AI)
    "ingest_hourly": "20/hour",     # Hourly cap for sustained abuse
    "upload": "10/minute",          # File uploads
    "upload_hourly": "50/hour",     # Hourly cap

    # AI analysis endpoints - very strict
    "ai_analysis": "3/minute",      # Claude Vision analysis
    "ai_analysis_hourly": "30/hour",
    "face_search": "5/minute",      # Face similarity search
    "face_search_hourly": "50/hour",
    "bulk_ingest": "2/minute",      # Bulk URL ingestion

    # Read-only endpoints - more permissive
    "officers_list": "60/minute",
    "officers_detail": "120/minute",
    "report": "30/minute",

    # Static data
    "protests": "60/minute",

    # Merge/unmerge operations - moderate limits to prevent abuse
    "merge_operations": "20/minute",
    "merge_operations_hourly": "100/hour",
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


# =============================================================================
# CONCURRENT REQUEST LIMITING (DoS Protection)
# =============================================================================

# Maximum concurrent AI processing tasks per IP
MAX_CONCURRENT_AI_TASKS = int(os.getenv("MAX_CONCURRENT_AI_TASKS", "3"))

# Global concurrent AI task tracking
_ai_task_semaphores: dict[str, asyncio.Semaphore] = {}
_ai_task_counts: dict[str, int] = {}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def acquire_ai_slot(request: Request) -> bool:
    """
    Try to acquire an AI processing slot for this client.
    Returns True if acquired, False if limit reached.
    """
    client_ip = get_client_ip(request)

    if client_ip not in _ai_task_semaphores:
        _ai_task_semaphores[client_ip] = asyncio.Semaphore(MAX_CONCURRENT_AI_TASKS)
        _ai_task_counts[client_ip] = 0

    # Try to acquire without blocking
    if _ai_task_semaphores[client_ip].locked():
        # Check current count
        if _ai_task_counts.get(client_ip, 0) >= MAX_CONCURRENT_AI_TASKS:
            return False

    await _ai_task_semaphores[client_ip].acquire()
    _ai_task_counts[client_ip] = _ai_task_counts.get(client_ip, 0) + 1
    return True


def release_ai_slot(request: Request):
    """Release an AI processing slot for this client."""
    client_ip = get_client_ip(request)

    if client_ip in _ai_task_semaphores:
        _ai_task_semaphores[client_ip].release()
        _ai_task_counts[client_ip] = max(0, _ai_task_counts.get(client_ip, 1) - 1)


def require_ai_slot(func: Callable):
    """
    Decorator that requires an AI processing slot.
    Raises 429 if client has too many concurrent AI tasks.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            # Try to find request in args
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

        if request:
            acquired = await acquire_ai_slot(request)
            if not acquired:
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many concurrent AI tasks. Maximum {MAX_CONCURRENT_AI_TASKS} allowed per client."
                )
            try:
                return await func(*args, **kwargs)
            finally:
                release_ai_slot(request)
        else:
            return await func(*args, **kwargs)

    return wrapper


# =============================================================================
# REQUEST SIZE LIMITS
# =============================================================================

# Maximum upload sizes in bytes
MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE_MB", "50")) * 1024 * 1024  # 50MB default
MAX_VIDEO_SIZE = int(os.getenv("MAX_VIDEO_SIZE_MB", "500")) * 1024 * 1024  # 500MB default
MAX_BULK_URLS = 10  # Maximum URLs in bulk ingest


def check_file_size(content_length: int, file_type: str) -> bool:
    """
    Check if file size is within limits.

    Args:
        content_length: Size in bytes
        file_type: 'image' or 'video'

    Returns:
        True if within limits

    Raises:
        HTTPException if over limit
    """
    max_size = MAX_VIDEO_SIZE if file_type == "video" else MAX_IMAGE_SIZE
    max_mb = max_size / (1024 * 1024)

    if content_length > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size for {file_type}: {max_mb:.0f}MB"
        )
    return True
