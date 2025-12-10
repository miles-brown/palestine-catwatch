"""
Email service for Palestine Catwatch using Resend.

Handles:
- Email verification
- Password reset (future)
- Notifications (future)
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Only import resend if API key is configured
resend = None
if RESEND_API_KEY:
    try:
        import resend as resend_lib
        resend_lib.api_key = RESEND_API_KEY
        resend = resend_lib
        logger.info("Resend email service initialized")
    except ImportError:
        logger.warning("Resend package not installed. Email sending disabled.")
else:
    logger.warning("RESEND_API_KEY not set. Email sending disabled.")


def is_email_enabled() -> bool:
    """Check if email sending is configured and available."""
    return resend is not None and RESEND_API_KEY is not None


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """
    Send email verification link to new user.

    Args:
        to_email: User's email address
        username: User's username for personalization
        token: Verification token

    Returns:
        True if sent successfully, False otherwise
    """
    if not is_email_enabled():
        logger.warning(f"Email disabled - skipping verification email to {to_email}")
        return False

    verification_url = f"{FRONTEND_URL}/verify-email?token={token}"

    try:
        response = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [to_email],
            "subject": "Verify your Palestine Accountability account",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; text-align: center;">
                    <h1 style="color: #22c55e; margin: 0;">Palestine Accountability</h1>
                </div>

                <div style="padding: 30px; background: #f8fafc;">
                    <h2 style="color: #1e293b;">Welcome, {username}!</h2>

                    <p style="color: #475569; line-height: 1.6;">
                        Thank you for joining the Palestine Accountability platform.
                        Please verify your email address to activate your account.
                    </p>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_url}"
                           style="background: #22c55e; color: white; padding: 12px 30px;
                                  text-decoration: none; border-radius: 6px; font-weight: bold;
                                  display: inline-block;">
                            Verify Email Address
                        </a>
                    </div>

                    <p style="color: #64748b; font-size: 14px;">
                        Or copy and paste this link into your browser:<br>
                        <a href="{verification_url}" style="color: #22c55e; word-break: break-all;">
                            {verification_url}
                        </a>
                    </p>

                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">

                    <p style="color: #94a3b8; font-size: 12px;">
                        If you didn't create this account, you can safely ignore this email.
                        This link will expire in 24 hours.
                    </p>
                </div>

                <div style="background: #1e293b; padding: 20px; text-align: center;">
                    <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                        Palestine Accountability Campaign<br>
                        Documenting state oppression - Defending democratic rights
                    </p>
                </div>
            </div>
            """
        })

        logger.info(f"Verification email sent to {to_email}, id: {response.get('id', 'unknown')}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email to {to_email}: {e}")
        return False


def send_password_reset_email(to_email: str, username: str, token: str) -> bool:
    """
    Send password reset link to user.

    Args:
        to_email: User's email address
        username: User's username for personalization
        token: Password reset token

    Returns:
        True if sent successfully, False otherwise
    """
    if not is_email_enabled():
        logger.warning(f"Email disabled - skipping password reset email to {to_email}")
        return False

    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

    try:
        response = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [to_email],
            "subject": "Reset your Palestine Accountability password",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; text-align: center;">
                    <h1 style="color: #22c55e; margin: 0;">Palestine Accountability</h1>
                </div>

                <div style="padding: 30px; background: #f8fafc;">
                    <h2 style="color: #1e293b;">Password Reset Request</h2>

                    <p style="color: #475569; line-height: 1.6;">
                        Hi {username}, we received a request to reset your password.
                        Click the button below to create a new password.
                    </p>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}"
                           style="background: #22c55e; color: white; padding: 12px 30px;
                                  text-decoration: none; border-radius: 6px; font-weight: bold;
                                  display: inline-block;">
                            Reset Password
                        </a>
                    </div>

                    <p style="color: #64748b; font-size: 14px;">
                        Or copy and paste this link into your browser:<br>
                        <a href="{reset_url}" style="color: #22c55e; word-break: break-all;">
                            {reset_url}
                        </a>
                    </p>

                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">

                    <p style="color: #94a3b8; font-size: 12px;">
                        If you didn't request a password reset, you can safely ignore this email.
                        This link will expire in 1 hour.
                    </p>
                </div>

                <div style="background: #1e293b; padding: 20px; text-align: center;">
                    <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                        Palestine Accountability Campaign<br>
                        Documenting state oppression - Defending democratic rights
                    </p>
                </div>
            </div>
            """
        })

        logger.info(f"Password reset email sent to {to_email}, id: {response.get('id', 'unknown')}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {e}")
        return False
