"""
Authentication module for Palestine Catwatch.

Provides JWT-based authentication with role-based access control.

Roles:
- viewer: Can view officers, reports, and public data
- contributor: Can upload media and trigger analysis
- admin: Full access including user management and data deletion

Usage:
    from auth import get_current_user, require_role, Role

    @app.get("/protected")
    def protected_endpoint(user: User = Depends(get_current_user)):
        return {"message": f"Hello {user.username}"}

    @app.delete("/admin-only")
    def admin_only(user: User = Depends(require_role(Role.ADMIN))):
        return {"message": "Admin action performed"}
"""

import os
import re
import secrets
import warnings
from datetime import datetime, timedelta, date, timezone
from typing import Optional, Tuple
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from database import get_db

# =============================================================================
# CONFIGURATION
# =============================================================================

# Secret key for JWT signing - MUST be set in environment for production
_DEFAULT_SECRET = "dev-secret-key-change-in-production-INSECURE"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEFAULT_SECRET)

# Warn loudly if using default secret in production
if SECRET_KEY == _DEFAULT_SECRET:
    _env = os.getenv("ENVIRONMENT", "development").lower()
    if _env in ("production", "prod", "staging"):
        raise RuntimeError(
            "CRITICAL: JWT_SECRET_KEY environment variable must be set in production! "
            "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    else:
        warnings.warn(
            "WARNING: Using default JWT secret key. Set JWT_SECRET_KEY in production!",
            UserWarning
        )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # Default 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer(auto_error=False)


# =============================================================================
# ENUMS AND MODELS
# =============================================================================

class Role(str, Enum):
    """User roles with increasing privilege levels."""
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"


# Role hierarchy - higher index = more privileges
ROLE_HIERARCHY = [Role.VIEWER, Role.CONTRIBUTOR, Role.ADMIN]


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserCreate(BaseModel):
    """User registration request with full profile and consent."""
    username: str
    email: str
    password: str
    full_name: str
    date_of_birth: date
    city: str
    country: str
    consent_given: bool = False
    role: Role = Role.CONTRIBUTOR  # Default to contributor for registered users

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Backend password validation - prevents bypass of frontend checks."""
        # Import here to avoid circular dependency during class definition
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v

    @field_validator('consent_given')
    @classmethod
    def validate_consent(cls, v):
        if not v:
            raise ValueError('You must consent to the terms to create an account')
        return v

    @field_validator('date_of_birth')
    @classmethod
    def validate_age(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('You must be at least 18 years old to create an account')
        return v

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('Username must be at most 50 characters')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v


class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User data returned in API responses."""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    full_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    email_verified: bool = False

    class Config:
        from_attributes = True


# =============================================================================
# PASSWORD UTILITIES
# =============================================================================

# Password validation constants
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength with multiple security checks.

    Requirements:
    - Minimum 8 characters, maximum 128
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: The plain text password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"

    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"

    # Check for common weak patterns
    common_patterns = [
        r'(.)\1{2,}',  # Same character 3+ times in a row
        r'(012|123|234|345|456|567|678|789|890)',  # Sequential digits
        r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
    ]

    password_lower = password.lower()
    for pattern in common_patterns:
        if re.search(pattern, password_lower):
            return False, "Password contains predictable patterns (sequential characters or repeated characters)"

    return True, ""


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


# =============================================================================
# JWT UTILITIES
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary with claims to encode (should include 'sub' for user id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()

    # Use timezone-aware datetime (not deprecated datetime.utcnow())
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT string to decode

    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")

        if username is None:
            return None

        return TokenData(username=username, user_id=user_id, role=role)
    except JWTError:
        return None


# =============================================================================
# USER DATABASE OPERATIONS
# =============================================================================

def get_user_by_username(db: Session, username: str):
    """Fetch a user by username."""
    import models
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    """Fetch a user by email."""
    import models
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    """Fetch a user by ID."""
    import models
    return db.query(models.User).filter(models.User.id == user_id).first()


def generate_verification_token() -> str:
    """Generate a secure random token for email verification."""
    return secrets.token_urlsafe(32)


def create_user(db: Session, user: UserCreate, require_verification: bool = True):
    """
    Create a new user in the database.

    Args:
        db: Database session
        user: User creation data
        require_verification: If True, user must verify email before account is active

    Returns:
        The created User object
    """
    import models

    hashed_password = get_password_hash(user.password)
    verification_token = generate_verification_token() if require_verification else None

    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role.value,
        is_active=not require_verification,  # Only active if no verification required
        full_name=user.full_name,
        date_of_birth=datetime.combine(user.date_of_birth, datetime.min.time()),
        city=user.city,
        country=user.country,
        consent_given=user.consent_given,
        consent_date=datetime.now(timezone.utc) if user.consent_given else None,
        email_verified=not require_verification,
        email_verification_token=verification_token,
        email_verification_sent_at=datetime.now(timezone.utc) if require_verification else None
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def verify_user_email(db: Session, token: str):
    """
    Verify a user's email address using their verification token.

    Returns:
        The verified User object, or None if token invalid
    """
    import models

    user = db.query(models.User).filter(
        models.User.email_verification_token == token
    ).first()

    if not user:
        return None

    user.email_verified = True
    user.is_active = True
    user.email_verification_token = None
    db.commit()
    db.refresh(user)
    return user


# Dummy hash for constant-time comparison when user not found
# This prevents timing attacks that could enumerate valid usernames
_DUMMY_HASH = pwd_context.hash("dummy_password_for_timing_attack_prevention")


class AuthenticationError(Exception):
    """Custom exception for authentication failures with specific error codes."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def authenticate_user(db: Session, username: str, password: str, require_verified_email: bool = True):
    """
    Authenticate a user by username and password.

    Security features:
    - Always performs password hash verification to prevent timing attacks
    - Checks email verification status if required
    - Checks account active status

    Args:
        db: Database session
        username: The username to authenticate
        password: The plain text password
        require_verified_email: If True, requires email to be verified (default: True)

    Returns:
        User object if authentication successful

    Raises:
        AuthenticationError: With specific code for different failure reasons:
            - "invalid_credentials": Username or password incorrect
            - "email_not_verified": Email address not verified
            - "account_disabled": Account is disabled
    """
    user = get_user_by_username(db, username)

    # SECURITY: Always verify password hash to prevent timing attacks
    # If user doesn't exist, verify against dummy hash to ensure
    # consistent response time regardless of username validity
    if user is None:
        # Perform dummy verification to prevent timing-based username enumeration
        pwd_context.verify(password, _DUMMY_HASH)
        raise AuthenticationError("invalid_credentials", "Invalid username or password")

    if not verify_password(password, user.hashed_password):
        raise AuthenticationError("invalid_credentials", "Invalid username or password")

    # Check if account is active
    if not user.is_active:
        raise AuthenticationError("account_disabled", "Account is disabled")

    # Check email verification if required
    if require_verified_email and not user.email_verified:
        raise AuthenticationError(
            "email_not_verified",
            "Please verify your email address before logging in. Check your inbox for the verification link."
        )

    return user


def authenticate_user_simple(db: Session, username: str, password: str):
    """
    Simple authentication without raising exceptions (for backwards compatibility).

    Returns User if successful, None otherwise.
    """
    try:
        return authenticate_user(db, username, password, require_verified_email=False)
    except AuthenticationError:
        return None


# =============================================================================
# FASTAPI DEPENDENCIES
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    FastAPI dependency to get the current authenticated user.

    Usage:
        @app.get("/protected")
        def protected(user = Depends(get_current_user)):
            return {"user": user.username}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    token_data = decode_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception

    user = get_user_by_username(db, token_data.username)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    FastAPI dependency that returns the current user if authenticated, None otherwise.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if credentials is None:
        return None

    token_data = decode_token(credentials.credentials)
    if token_data is None:
        return None

    user = get_user_by_username(db, token_data.username)
    if user is None or not user.is_active:
        return None

    return user


def require_role(required_role: Role):
    """
    Factory function that creates a dependency requiring a specific role.

    Uses role hierarchy - higher roles can access lower role endpoints.

    Usage:
        @app.delete("/admin-only")
        def admin_only(user = Depends(require_role(Role.ADMIN))):
            return {"success": True}
    """
    async def role_checker(user = Depends(get_current_user)):
        user_role_index = ROLE_HIERARCHY.index(Role(user.role))
        required_role_index = ROLE_HIERARCHY.index(required_role)

        if user_role_index < required_role_index:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )
        return user

    return role_checker


# =============================================================================
# CONVENIENCE DEPENDENCIES
# =============================================================================

# Pre-built role dependencies for common use cases
require_viewer = require_role(Role.VIEWER)
require_contributor = require_role(Role.CONTRIBUTOR)
require_admin = require_role(Role.ADMIN)
