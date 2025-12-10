"""
Cloudflare Turnstile verification module.

Verifies Turnstile tokens with Cloudflare's siteverify API.
"""

import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

# Whether Turnstile verification is enabled
TURNSTILE_ENABLED = bool(TURNSTILE_SECRET_KEY)


async def verify_turnstile_token(token: str, remote_ip: Optional[str] = None) -> dict:
    """
    Verify a Turnstile token with Cloudflare.

    Args:
        token: The Turnstile response token from the client
        remote_ip: Optional client IP address for additional validation

    Returns:
        dict with 'success' (bool) and optionally 'error' (str)
    """
    if not TURNSTILE_ENABLED:
        logger.warning("Turnstile verification skipped - TURNSTILE_SECRET_KEY not configured")
        return {"success": True, "skipped": True}

    if not token:
        return {"success": False, "error": "Missing Turnstile token"}

    payload = {
        "secret": TURNSTILE_SECRET_KEY,
        "response": token,
    }

    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data=payload,
                timeout=10.0
            )
            result = response.json()

            if result.get("success"):
                logger.debug("Turnstile verification successful")
                return {"success": True}
            else:
                error_codes = result.get("error-codes", [])
                logger.warning(f"Turnstile verification failed: {error_codes}")
                return {
                    "success": False,
                    "error": "Security verification failed",
                    "error_codes": error_codes
                }

    except httpx.TimeoutException:
        logger.error("Turnstile verification timed out")
        return {"success": False, "error": "Security verification timed out"}
    except Exception as e:
        logger.error(f"Turnstile verification error: {e}")
        return {"success": False, "error": "Security verification error"}


def verify_turnstile_token_sync(token: str, remote_ip: Optional[str] = None) -> dict:
    """
    Synchronous version of verify_turnstile_token.

    Args:
        token: The Turnstile response token from the client
        remote_ip: Optional client IP address for additional validation

    Returns:
        dict with 'success' (bool) and optionally 'error' (str)
    """
    if not TURNSTILE_ENABLED:
        logger.warning("Turnstile verification skipped - TURNSTILE_SECRET_KEY not configured")
        return {"success": True, "skipped": True}

    if not token:
        return {"success": False, "error": "Missing Turnstile token"}

    payload = {
        "secret": TURNSTILE_SECRET_KEY,
        "response": token,
    }

    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        with httpx.Client() as client:
            response = client.post(
                TURNSTILE_VERIFY_URL,
                data=payload,
                timeout=10.0
            )
            result = response.json()

            if result.get("success"):
                logger.debug("Turnstile verification successful")
                return {"success": True}
            else:
                error_codes = result.get("error-codes", [])
                logger.warning(f"Turnstile verification failed: {error_codes}")
                return {
                    "success": False,
                    "error": "Security verification failed",
                    "error_codes": error_codes
                }

    except httpx.TimeoutException:
        logger.error("Turnstile verification timed out")
        return {"success": False, "error": "Security verification timed out"}
    except Exception as e:
        logger.error(f"Turnstile verification error: {e}")
        return {"success": False, "error": "Security verification error"}
