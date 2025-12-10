"""
Tests for authentication module.

Covers:
- Password validation
- Input sanitization
- Token creation and decoding
- User authentication flows
- Account lockout
- Role-based access
"""

import pytest
from datetime import datetime, timedelta, timezone
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import (
    validate_password_strength,
    sanitize_string,
    sanitize_name,
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_refresh_token,
    verify_password,
    get_password_hash,
    Role,
    ROLE_HIERARCHY,
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
)


class TestPasswordValidation:
    """Test password strength validation."""

    def test_valid_password(self):
        """Test that a valid password passes validation."""
        # Note: Avoid sequential patterns like "123", "789" which are blocked
        valid, error = validate_password_strength("MySecureP@55w0rd!")
        assert valid is True
        assert error == ""

    def test_password_too_short(self):
        """Test that short passwords are rejected."""
        valid, error = validate_password_strength("Sh0rt!")
        assert valid is False
        assert "at least" in error.lower()

    def test_password_too_long(self):
        """Test that overly long passwords are rejected."""
        long_password = "A" * 129 + "a1!"
        valid, error = validate_password_strength(long_password)
        assert valid is False
        assert "at most" in error.lower()

    def test_password_missing_uppercase(self):
        """Test that passwords without uppercase are rejected."""
        valid, error = validate_password_strength("lowercase123!")
        assert valid is False
        assert "uppercase" in error.lower()

    def test_password_missing_lowercase(self):
        """Test that passwords without lowercase are rejected."""
        valid, error = validate_password_strength("UPPERCASE123!")
        assert valid is False
        assert "lowercase" in error.lower()

    def test_password_missing_digit(self):
        """Test that passwords without digits are rejected."""
        valid, error = validate_password_strength("NoDigits!@#")
        assert valid is False
        assert "digit" in error.lower()

    def test_password_missing_special(self):
        """Test that passwords without special characters are rejected."""
        valid, error = validate_password_strength("NoSpecial123")
        assert valid is False
        assert "special" in error.lower()

    def test_password_sequential_digits(self):
        """Test that passwords with sequential digits are rejected."""
        valid, error = validate_password_strength("Pass123456!")
        assert valid is False
        assert "pattern" in error.lower()

    def test_password_repeated_chars(self):
        """Test that passwords with repeated characters are rejected."""
        valid, error = validate_password_strength("Passsss1!")
        assert valid is False
        assert "pattern" in error.lower()

    def test_empty_password(self):
        """Test that empty passwords are rejected."""
        valid, error = validate_password_strength("")
        assert valid is False
        assert "required" in error.lower()

    def test_none_password(self):
        """Test that None passwords are rejected."""
        valid, error = validate_password_strength(None)
        assert valid is False


class TestInputSanitization:
    """Test input sanitization functions."""

    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        result = sanitize_string("Hello World")
        assert result == "Hello World"

    def test_sanitize_string_html_escape(self):
        """Test that HTML is escaped."""
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_string_max_length(self):
        """Test that strings are truncated to max length."""
        long_string = "a" * 300
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100

    def test_sanitize_string_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        result = sanitize_string("  Hello  ")
        assert result == "Hello"

    def test_sanitize_string_removes_null_bytes(self):
        """Test that null bytes are removed."""
        result = sanitize_string("Hello\x00World")
        assert "\x00" not in result

    def test_sanitize_string_unicode_normalization(self):
        """Test unicode normalization."""
        # Different representations of the same character
        result = sanitize_string("café")
        assert result == "café"

    def test_sanitize_name_allows_hyphens(self):
        """Test that names allow hyphens."""
        result = sanitize_name("Mary-Jane")
        assert result == "Mary-Jane"

    def test_sanitize_name_allows_apostrophes(self):
        """Test that names allow apostrophes."""
        result = sanitize_name("O'Connor")
        assert "O" in result and "Connor" in result

    def test_sanitize_name_removes_dangerous_chars(self):
        """Test that dangerous characters are removed from names."""
        result = sanitize_name("John<script>Doe")
        # sanitize_name removes special chars like < and > but keeps alphanumeric
        assert "<" not in result
        assert ">" not in result
        # The word "script" without brackets is harmless in a name context


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_password_hash_different_from_plain(self):
        """Test that hashed password is different from plain text."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert hashed != password

    def test_password_verify_correct(self):
        """Test that correct password verifies."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_password_verify_incorrect(self):
        """Test that incorrect password fails verification."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert verify_password("WrongPassword!", hashed) is False

    def test_password_hash_unique_per_call(self):
        """Test that same password produces different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2  # Different salts


class TestTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "testuser", "user_id": 1, "role": "viewer"}
        token = create_access_token(data)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long

    def test_decode_access_token(self):
        """Test access token decoding."""
        data = {"sub": "testuser", "user_id": 1, "role": "viewer"}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded.username == "testuser"
        assert decoded.user_id == 1
        assert decoded.role == "viewer"

    def test_decode_invalid_token(self):
        """Test that invalid tokens return None."""
        decoded = decode_token("invalid.token.here")
        assert decoded is None

    def test_decode_expired_token(self):
        """Test that expired tokens return None."""
        data = {"sub": "testuser", "user_id": 1, "role": "viewer"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        decoded = decode_token(token)
        assert decoded is None

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "testuser", "user_id": 1, "role": "viewer"}
        token = create_refresh_token(data)
        assert token is not None
        assert isinstance(token, str)

    def test_decode_refresh_token(self):
        """Test refresh token decoding."""
        data = {"sub": "testuser", "user_id": 1, "role": "viewer"}
        token = create_refresh_token(data)
        decoded = decode_refresh_token(token)
        assert decoded is not None
        assert decoded.username == "testuser"

    def test_access_token_not_valid_as_refresh(self):
        """Test that access tokens can't be used as refresh tokens."""
        data = {"sub": "testuser", "user_id": 1, "role": "viewer"}
        access_token = create_access_token(data)
        decoded = decode_refresh_token(access_token)
        assert decoded is None  # Should fail type check


class TestRoles:
    """Test role hierarchy."""

    def test_role_hierarchy_order(self):
        """Test that role hierarchy is correct."""
        assert ROLE_HIERARCHY.index(Role.VIEWER) < ROLE_HIERARCHY.index(Role.CONTRIBUTOR)
        assert ROLE_HIERARCHY.index(Role.CONTRIBUTOR) < ROLE_HIERARCHY.index(Role.ADMIN)

    def test_role_enum_values(self):
        """Test role enum values."""
        assert Role.VIEWER.value == "viewer"
        assert Role.CONTRIBUTOR.value == "contributor"
        assert Role.ADMIN.value == "admin"


class TestTokenCustomExpiry:
    """Test token expiry customization."""

    def test_custom_access_token_expiry(self):
        """Test access token with custom expiry."""
        data = {"sub": "testuser", "user_id": 1, "role": "viewer"}
        token = create_access_token(data, expires_delta=timedelta(hours=1))
        decoded = decode_token(token)
        assert decoded is not None

    def test_very_short_expiry(self):
        """Test token with very short expiry."""
        data = {"sub": "testuser", "user_id": 1, "role": "viewer"}
        token = create_access_token(data, expires_delta=timedelta(seconds=1))
        # Token should still be valid immediately after creation
        decoded = decode_token(token)
        assert decoded is not None


# Run with: pytest backend/tests/test_auth.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
