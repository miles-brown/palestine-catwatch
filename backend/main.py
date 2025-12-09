from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas
from database import get_db, engine
from datetime import datetime
import asyncio

# Structured logging
from logging_config import setup_logging, get_logger, log_audit, log_error, timed

# Initialize structured logging
setup_logging()
logger = get_logger("main")

# Rate limiting
from ratelimit import limiter, setup_rate_limiting, get_rate_limit

# Path utilities for consistent path handling
from utils.paths import get_web_url, get_absolute_path, normalize_for_storage

try:
    logger.info("Attempting to connect to database and create tables...")
    models.Base.metadata.create_all(bind=engine)

    # --- LEGACY SCHEMA MIGRATIONS ---
    # NOTE: New migrations should use Alembic. Run: alembic upgrade head
    # These inline migrations are kept for backwards compatibility with existing deployments.
    from sqlalchemy import text
    with engine.connect() as conn:
        # Drop the index on visual_id because it is too large (vector) for b-tree
        conn.execute(text("DROP INDEX IF EXISTS ix_officers_visual_id"))

        # Add missing columns to officer_appearances (idempotent - checks if column exists)
        migrations = [
            "ALTER TABLE officer_appearances ADD COLUMN IF NOT EXISTS confidence FLOAT",
            "ALTER TABLE officer_appearances ADD COLUMN IF NOT EXISTS confidence_factors TEXT",
            "ALTER TABLE officer_appearances ADD COLUMN IF NOT EXISTS verified BOOLEAN DEFAULT FALSE",
            # User authentication support
            "ALTER TABLE media ADD COLUMN IF NOT EXISTS uploaded_by INTEGER REFERENCES users(id)",
            # Chain of command support
            "ALTER TABLE officers ADD COLUMN IF NOT EXISTS supervisor_id INTEGER REFERENCES officers(id)",
            "ALTER TABLE officers ADD COLUMN IF NOT EXISTS rank VARCHAR",
            # Extended user profile fields
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(100)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_given BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_date TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_sent_at TIMESTAMP",
        ]
        for migration in migrations:
            try:
                conn.execute(text(migration))
            except Exception as e:
                # Column might already exist or other non-critical error
                logger.debug(f"Migration note: {e}")

        conn.commit()
        logger.info("Schema migrations applied successfully.")
    # -------------------------

    logger.info("Database tables created successfully.")
except Exception as e:
    logger.error(f"Startup Warning: Database connection failed. App will start but DB features will fail.", extra_data={"error": str(e)})

from pydantic import BaseModel, field_validator, HttpUrl, Field
from urllib.parse import urlparse
import re

class IngestURLRequest(BaseModel):
    url: str
    protest_id: Optional[int] = None
    answers: dict = Field(default_factory=dict)  # Avoid mutable default argument

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        return validate_single_url(v)


class BulkIngestRequest(BaseModel):
    urls: List[str]
    protest_id: Optional[int] = None
    answers: dict = Field(default_factory=dict)  # Avoid mutable default argument


# =============================================================================
# HEALTH CHECK ENDPOINT
# =============================================================================

@app.get("/health", tags=["health"])
def health_check():
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        - status: "healthy" or "degraded"
        - database: "connected" or "disconnected"
        - version: Application version
        - timestamp: Current server time
    """
    import time

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {}
    }

    # Check database connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = "disconnected"
        health_status["status"] = "degraded"

    # Check if data directory exists
    import os
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    health_status["services"]["storage"] = "available" if os.path.exists(data_dir) else "unavailable"

    return health_status


@app.get("/health/ready", tags=["health"])
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe - checks if app is ready to receive traffic.
    Returns 503 if not ready.
    """
    try:
        # Verify database is accessible
        db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database not ready")


@app.get("/health/live", tags=["health"])
def liveness_check():
    """
    Liveness probe - checks if app is running.
    Simple check that returns immediately.
    """
    return {"alive": True}


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================
MAX_URL_LENGTH = 2048
MAX_PAGINATION_LIMIT = 500
DEFAULT_PAGINATION_LIMIT = 100


def to_crop_url(storage_path: str) -> str:
    """
    Convert a stored crop path to a web-accessible URL.
    Handles various storage formats:
    - Absolute paths: /Users/.../data/frames/1/face_0.jpg
    - Relative paths: data/frames/1/face_0.jpg
    - Legacy paths: ../data/frames/1/face_0.jpg
    """
    if not storage_path:
        return None
    return get_web_url(storage_path)


def validate_single_url(v):
    """Validate a single URL."""
    # Basic URL validation
    if not v or not isinstance(v, str):
        raise ValueError('URL is required')

    v = v.strip()

    # Check URL length (#19)
    if len(v) > MAX_URL_LENGTH:
        raise ValueError(f'URL too long (max {MAX_URL_LENGTH} characters)')

    # Must start with http:// or https://
    if not v.startswith(('http://', 'https://')):
        raise ValueError('URL must start with http:// or https://')

    # Parse and validate structure
    try:
        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError('Invalid URL: no domain found')

        # Check for suspicious patterns (path traversal, etc.)
        suspicious_patterns = ['../', '..\\', '<script', 'javascript:', 'data:']
        for pattern in suspicious_patterns:
            if pattern.lower() in v.lower():
                raise ValueError(f'URL contains suspicious pattern: {pattern}')

        # Basic domain validation (must have at least one dot)
        if '.' not in parsed.netloc:
            raise ValueError('Invalid domain in URL')

    except Exception as e:
        if 'Invalid' in str(e) or 'URL' in str(e):
            raise
        raise ValueError(f'Invalid URL format: {str(e)}')

    return v


app = FastAPI(
    title="Palestine Catwatch API",
    description="""
## Police Accountability Documentation System

This API powers the Palestine Catwatch application, providing tools for documenting
and analyzing police presence at protests.

### Features

* **Officer Detection** - Automatic face detection and tracking across media
* **Badge OCR** - Extract badge numbers and shoulder numbers from images
* **Uniform Analysis** - Claude Vision AI analysis of police uniforms, ranks, and equipment
* **Network Analysis** - Track which officers appear together and their chain of command
* **Geographic Clustering** - Map officer presence across protest locations
* **Equipment Correlation** - Detect equipment patterns that indicate escalation

### Authentication

Most endpoints require JWT authentication. Use `/auth/login` to obtain a token.
Include the token in the `Authorization` header as `Bearer <token>`.

### Rate Limiting

API calls are rate-limited to protect the service:
- General endpoints: 30 requests/minute
- AI analysis: 10 requests/minute
- Bulk operations: 5 requests/minute

### Support

For issues, visit: https://github.com/palestine-catwatch/issues
    """,
    version="2.0.0",
    contact={
        "name": "Palestine Accountability Campaign",
        "url": "https://github.com/palestine-catwatch",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and system status endpoints",
        },
        {
            "name": "auth",
            "description": "Authentication and user management",
        },
        {
            "name": "officers",
            "description": "Officer records and appearance tracking",
        },
        {
            "name": "media",
            "description": "Media upload and processing",
        },
        {
            "name": "protests",
            "description": "Protest event management",
        },
        {
            "name": "analysis",
            "description": "AI-powered uniform and equipment analysis",
        },
        {
            "name": "stats",
            "description": "Statistics and analytics endpoints",
        },
        {
            "name": "equipment",
            "description": "Equipment database and detection tracking",
        },
        {
            "name": "export",
            "description": "Data export in various formats",
        },
        {
            "name": "admin",
            "description": "Administrative operations (requires admin role)",
        },
    ]
)

# Setup rate limiting
setup_rate_limiting(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO
from sio import sio_app, sio_server, mark_room_complete
app.mount("/socket.io", sio_app)

# Mount data directory to serve images
# Mount data directory to serve images
import os
os.makedirs("data", exist_ok=True)
app.mount("/data", StaticFiles(directory="data"), name="data")

@app.get("/")
def read_root():
    return {"message": "Palestine Catwatch Backend Operational"}


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

from auth import (
    authenticate_user, create_user, create_access_token,
    get_current_user, get_current_user_optional, require_role,
    UserCreate, UserLogin, UserResponse, Token, Role,
    get_user_by_username, get_user_by_email, ACCESS_TOKEN_EXPIRE_MINUTES,
    verify_user_email, get_password_hash
)
from datetime import timedelta

# Admin credentials (password: BeKindRewind123)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "BeKindRewind123"


@app.post("/auth/register")
@limiter.limit("5/hour")  # Prevent registration spam
def register_user(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    Requires:
    - Username, email, password
    - Full name, date of birth, city, country
    - Consent to terms (must be True)
    - Must be 18 or older

    New users must verify their email before they can log in.
    Returns verification token (in production, this would be emailed).
    """
    # Check if username already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Force contributor role for self-registration
    user_data.role = Role.CONTRIBUTOR

    # Create user with email verification required
    user = create_user(db, user_data, require_verification=True)

    # In production, send verification email here
    # For now, return the verification token in response
    return {
        "message": "Registration successful. Please verify your email to activate your account.",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "verification_required": True,
        # Include token for development/testing - remove in production
        "verification_token": user.email_verification_token
    }


@app.get("/auth/verify-email/{token}")
def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verify a user's email address.

    After verification, the user can log in.
    """
    user = verify_user_email(db, token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    return {
        "message": "Email verified successfully. You can now log in.",
        "username": user.username
    }


@app.post("/auth/resend-verification")
@limiter.limit("3/hour")
def resend_verification(
    request: Request,
    email: str,
    db: Session = Depends(get_db)
):
    """Resend verification email."""
    import secrets

    user = get_user_by_email(db, email)

    if not user:
        # Don't reveal if email exists
        return {"message": "If this email is registered, a verification link has been sent."}

    if user.email_verified:
        return {"message": "Email is already verified. You can log in."}

    # Generate new token
    user.email_verification_token = secrets.token_urlsafe(32)
    user.email_verification_sent_at = datetime.utcnow()
    db.commit()

    # In production, send email here
    return {
        "message": "If this email is registered, a verification link has been sent.",
        # Include token for development - remove in production
        "verification_token": user.email_verification_token
    }


@app.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")  # Prevent brute force
def login(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate and get an access token.

    Returns a JWT token valid for 24 hours (configurable via JWT_EXPIRE_MINUTES).
    Users must have verified their email to log in.
    """
    user = authenticate_user(db, login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if email is verified (admin bypasses this)
    if not user.email_verified and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": user.role
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name
        }
    }


@app.on_event("startup")
async def create_admin_user():
    """Create the admin user on startup if it doesn't exist."""
    db = SessionLocal()
    try:
        admin = get_user_by_username(db, ADMIN_USERNAME)
        if not admin:
            print("Creating admin user...")
            admin = models.User(
                username=ADMIN_USERNAME,
                email="admin@palestineaccountability.org",
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                role="admin",
                is_active=True,
                email_verified=True,
                full_name="System Administrator",
                consent_given=True,
                consent_date=datetime.utcnow()
            )
            db.add(admin)
            db.commit()
            print(f"Admin user created: {ADMIN_USERNAME}")
        else:
            print(f"Admin user already exists: {ADMIN_USERNAME}")
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        db.close()


@app.get("/auth/me", response_model=UserResponse)
def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Get the current authenticated user's information."""
    return current_user


@app.get("/auth/users", response_model=List[UserResponse])
@limiter.limit(get_rate_limit("default"))
def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    current_user = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


@app.put("/auth/users/{user_id}/role")
@limiter.limit(get_rate_limit("default"))
def update_user_role(
    request: Request,
    user_id: int,
    new_role: Role,
    current_user = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db)
):
    """Update a user's role (admin only)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent removing your own admin status
    if user.id == current_user.id and new_role != Role.ADMIN:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove your own admin role"
        )

    user.role = new_role.value
    db.commit()
    return {"message": f"User {user.username} role updated to {new_role.value}"}


@app.delete("/auth/users/{user_id}")
@limiter.limit(get_rate_limit("default"))
def delete_user(
    request: Request,
    user_id: int,
    current_user = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db)
):
    """Delete a user account (admin only)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )

    db.delete(user)
    db.commit()
    return {"message": f"User {user.username} deleted"}


# =============================================================================
# OFFICER ENDPOINTS
# =============================================================================

@app.get("/officers", response_model=List[schemas.Officer])
@limiter.limit(get_rate_limit("officers_list"))
def get_officers(
    request: Request,
    skip: int = 0,
    limit: int = DEFAULT_PAGINATION_LIMIT,
    badge_number: str = None,
    force: str = None,
    date_from: str = None,  # Format: YYYY-MM-DD
    date_to: str = None,    # Format: YYYY-MM-DD
    min_confidence: float = None,  # Minimum confidence score (0-100)
    verified_only: bool = False,  # Only show verified detections
    db: Session = Depends(get_db)
):
    # Enforce pagination limits (#12)
    if limit > MAX_PAGINATION_LIMIT:
        limit = MAX_PAGINATION_LIMIT
    if limit < 1:
        limit = 1
    if skip < 0:
        skip = 0

    query = db.query(models.Officer)

    if badge_number:
        query = query.filter(models.Officer.badge_number.contains(badge_number))
    if force:
        query = query.filter(models.Officer.force == force)

    # Confidence and verification filters
    needs_appearance_join = date_from or date_to or min_confidence is not None or verified_only

    if needs_appearance_join:
        # Join with appearances to filter
        if not (date_from or date_to):
            query = query.join(models.OfficerAppearance)

    # Date range filter - filter by appearances
    if date_from or date_to:
        # Join with appearances to filter by date
        query = query.join(models.OfficerAppearance).join(models.Media)

        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(models.Media.timestamp >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")

        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                # Add one day to include the entire end date
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(models.Media.timestamp <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

    # Confidence filter
    if min_confidence is not None:
        if min_confidence < 0 or min_confidence > 100:
            raise HTTPException(status_code=400, detail="min_confidence must be between 0 and 100")
        query = query.filter(models.OfficerAppearance.confidence >= min_confidence)

    # Verified only filter
    if verified_only:
        query = query.filter(models.OfficerAppearance.verified == True)

    if needs_appearance_join:
        query = query.distinct()

    officers = query.offset(skip).limit(limit).all()
    return officers


@app.get("/officers/count")
@limiter.limit(get_rate_limit("officers_list"))
def get_officers_count(
    request: Request,
    badge_number: str = None,
    force: str = None,
    date_from: str = None,
    date_to: str = None,
    db: Session = Depends(get_db)
):
    """Get total count of officers (efficient for pagination)."""
    query = db.query(models.Officer)

    if badge_number:
        query = query.filter(models.Officer.badge_number.contains(badge_number))
    if force:
        query = query.filter(models.Officer.force == force)

    # Date range filter
    if date_from or date_to:
        query = query.join(models.OfficerAppearance).join(models.Media)

        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(models.Media.timestamp >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")

        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(models.Media.timestamp <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

        query = query.distinct()

    return {"count": query.count()}


@app.get("/officers/repeat")
@limiter.limit(get_rate_limit("officers_list"))
def get_repeat_officers(
    request: Request,
    min_appearances: int = 2,
    min_events: int = 2,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get officers who appear multiple times across different protests/events.
    These are 'repeat offenders' - officers seen at multiple demonstrations.
    """
    from sqlalchemy import func, distinct

    # Subquery to count appearances and distinct events per officer
    subq = (
        db.query(
            models.OfficerAppearance.officer_id,
            func.count(models.OfficerAppearance.id).label('appearance_count'),
            func.count(distinct(models.Media.protest_id)).label('event_count')
        )
        .join(models.Media)
        .group_by(models.OfficerAppearance.officer_id)
        .having(func.count(models.OfficerAppearance.id) >= min_appearances)
        .having(func.count(distinct(models.Media.protest_id)) >= min_events)
        .subquery()
    )

    # Get officers matching criteria
    results = (
        db.query(
            models.Officer,
            subq.c.appearance_count,
            subq.c.event_count
        )
        .join(subq, models.Officer.id == subq.c.officer_id)
        .order_by(subq.c.event_count.desc(), subq.c.appearance_count.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    repeat_officers = []
    for officer, app_count, evt_count in results:
        # Get first appearance image for display
        first_app = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.officer_id == officer.id,
            models.OfficerAppearance.image_crop_path.isnot(None)
        ).first()

        repeat_officers.append({
            "id": officer.id,
            "badge_number": officer.badge_number,
            "force": officer.force,
            "notes": officer.notes,
            "total_appearances": app_count,
            "distinct_events": evt_count,
            "crop_path": to_crop_url(first_app.image_crop_path) if first_app else None
        })

    return {
        "officers": repeat_officers,
        "total": len(repeat_officers)
    }


@app.get("/officers/{officer_id}/network")
@limiter.limit(get_rate_limit("officers_detail"))
def get_officer_network(
    request: Request,
    officer_id: int,
    db: Session = Depends(get_db)
):
    """
    Get officers who frequently appear with this officer.
    Useful for identifying units/squads that work together.
    """
    from sqlalchemy import func

    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    # Get all media IDs where this officer appears
    officer_media_ids = (
        db.query(models.OfficerAppearance.media_id)
        .filter(models.OfficerAppearance.officer_id == officer_id)
        .distinct()
        .all()
    )
    media_ids = [m[0] for m in officer_media_ids]

    if not media_ids:
        return {"officer_id": officer_id, "connections": [], "total_shared_media": 0}

    # Find other officers who appear in the same media
    co_appearances = (
        db.query(
            models.OfficerAppearance.officer_id,
            func.count(models.OfficerAppearance.id).label('shared_count')
        )
        .filter(
            models.OfficerAppearance.media_id.in_(media_ids),
            models.OfficerAppearance.officer_id != officer_id
        )
        .group_by(models.OfficerAppearance.officer_id)
        .order_by(func.count(models.OfficerAppearance.id).desc())
        .limit(20)
        .all()
    )

    connections = []
    for co_officer_id, shared_count in co_appearances:
        co_officer = db.query(models.Officer).filter(models.Officer.id == co_officer_id).first()
        if co_officer:
            first_app = db.query(models.OfficerAppearance).filter(
                models.OfficerAppearance.officer_id == co_officer_id,
                models.OfficerAppearance.image_crop_path.isnot(None)
            ).first()

            connections.append({
                "id": co_officer.id,
                "badge_number": co_officer.badge_number,
                "force": co_officer.force,
                "shared_appearances": shared_count,
                "crop_path": to_crop_url(first_app.image_crop_path) if first_app else None
            })

    return {
        "officer_id": officer_id,
        "connections": connections,
        "total_shared_media": len(media_ids)
    }


# =============================================================================
# CHAIN OF COMMAND ENDPOINTS
# =============================================================================

# UK Police rank hierarchy (lowest to highest)
UK_RANK_HIERARCHY = [
    "Constable",
    "Sergeant",
    "Inspector",
    "Chief Inspector",
    "Superintendent",
    "Chief Superintendent",
    "Assistant Commissioner",
    "Deputy Commissioner",
    "Commissioner"
]


def get_rank_level(rank: str) -> int:
    """Get numerical rank level for comparison. Returns -1 if rank not recognized."""
    if not rank:
        return -1
    rank_lower = rank.lower()
    for i, r in enumerate(UK_RANK_HIERARCHY):
        if r.lower() in rank_lower or rank_lower in r.lower():
            return i
    return -1


@app.get("/officers/{officer_id}/chain")
@limiter.limit(get_rate_limit("officers_detail"))
def get_officer_chain_of_command(
    request: Request,
    officer_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the chain of command for an officer.
    Returns supervisors (upward chain) and subordinates (downward chain).
    """
    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    # Get crop path for an officer (converted to web URL)
    def get_officer_crop(off_id):
        app = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.officer_id == off_id,
            models.OfficerAppearance.image_crop_path.isnot(None)
        ).first()
        return to_crop_url(app.image_crop_path) if app else None

    # Build upward chain (supervisors)
    supervisors = []
    current = officer
    seen_ids = {officer.id}  # Prevent circular references
    while current.supervisor_id and current.supervisor_id not in seen_ids:
        supervisor = db.query(models.Officer).filter(models.Officer.id == current.supervisor_id).first()
        if supervisor:
            seen_ids.add(supervisor.id)
            supervisors.append({
                "id": supervisor.id,
                "badge_number": supervisor.badge_number,
                "force": supervisor.force,
                "rank": supervisor.rank,
                "crop_path": get_officer_crop(supervisor.id)
            })
            current = supervisor
        else:
            break

    # Get direct subordinates
    subordinates = []
    direct_reports = db.query(models.Officer).filter(models.Officer.supervisor_id == officer_id).all()
    for sub in direct_reports:
        # Count their subordinates recursively
        sub_count = db.query(models.Officer).filter(models.Officer.supervisor_id == sub.id).count()
        subordinates.append({
            "id": sub.id,
            "badge_number": sub.badge_number,
            "force": sub.force,
            "rank": sub.rank,
            "crop_path": get_officer_crop(sub.id),
            "subordinate_count": sub_count
        })

    return {
        "officer": {
            "id": officer.id,
            "badge_number": officer.badge_number,
            "force": officer.force,
            "rank": officer.rank,
            "crop_path": get_officer_crop(officer.id)
        },
        "supervisors": supervisors,  # Ordered from immediate supervisor upward
        "subordinates": subordinates,
        "rank_level": get_rank_level(officer.rank)
    }


@app.put("/officers/{officer_id}/supervisor")
@limiter.limit(get_rate_limit("default"))
def set_officer_supervisor(
    request: Request,
    officer_id: int,
    supervisor_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Set or clear an officer's supervisor.
    Pass supervisor_id=null to clear the supervisor.
    """
    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    if supervisor_id is not None:
        # Validate supervisor exists
        supervisor = db.query(models.Officer).filter(models.Officer.id == supervisor_id).first()
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        # Prevent self-reference
        if supervisor_id == officer_id:
            raise HTTPException(status_code=400, detail="Officer cannot be their own supervisor")

        # Prevent circular chains
        current = supervisor
        seen = {officer_id}
        while current.supervisor_id:
            if current.supervisor_id in seen:
                raise HTTPException(status_code=400, detail="This would create a circular chain of command")
            seen.add(current.supervisor_id)
            current = db.query(models.Officer).filter(models.Officer.id == current.supervisor_id).first()
            if not current:
                break

        # Validate rank hierarchy (supervisor should outrank subordinate)
        officer_rank = get_rank_level(officer.rank)
        supervisor_rank = get_rank_level(supervisor.rank)
        if officer_rank >= 0 and supervisor_rank >= 0 and supervisor_rank <= officer_rank:
            raise HTTPException(
                status_code=400,
                detail=f"Supervisor ({supervisor.rank}) should outrank subordinate ({officer.rank})"
            )

    officer.supervisor_id = supervisor_id
    db.commit()

    return {
        "message": f"Supervisor {'set' if supervisor_id else 'cleared'} for officer {officer_id}",
        "officer_id": officer_id,
        "supervisor_id": supervisor_id
    }


@app.put("/officers/{officer_id}/rank")
@limiter.limit(get_rate_limit("default"))
def set_officer_rank(
    request: Request,
    officer_id: int,
    rank: str,
    db: Session = Depends(get_db)
):
    """Set an officer's rank."""
    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    officer.rank = rank
    db.commit()

    return {
        "message": f"Rank set to {rank} for officer {officer_id}",
        "officer_id": officer_id,
        "rank": rank,
        "rank_level": get_rank_level(rank)
    }


@app.get("/officers/hierarchy")
@limiter.limit(get_rate_limit("officers_list"))
def get_officers_hierarchy(
    request: Request,
    force: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get a hierarchical view of all officers organized by chain of command.
    Returns officers without supervisors as roots, with nested subordinates.
    """
    from sqlalchemy import func

    # Build query for root officers (no supervisor)
    query = db.query(models.Officer).filter(models.Officer.supervisor_id.is_(None))
    if force:
        query = query.filter(models.Officer.force == force)

    root_officers = query.all()

    def get_officer_crop(off_id):
        app = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.officer_id == off_id,
            models.OfficerAppearance.image_crop_path.isnot(None)
        ).first()
        return to_crop_url(app.image_crop_path) if app else None

    def build_tree(officer, depth=0, max_depth=5):
        """Recursively build officer tree with depth limit."""
        if depth > max_depth:
            return None

        subordinates = db.query(models.Officer).filter(
            models.Officer.supervisor_id == officer.id
        ).all()

        return {
            "id": officer.id,
            "badge_number": officer.badge_number,
            "force": officer.force,
            "rank": officer.rank,
            "rank_level": get_rank_level(officer.rank),
            "crop_path": get_officer_crop(officer.id),
            "subordinates": [build_tree(sub, depth + 1, max_depth) for sub in subordinates if sub]
        }

    hierarchy = []
    for root in root_officers:
        tree = build_tree(root)
        if tree:
            hierarchy.append(tree)

    # Sort by rank level (highest first)
    hierarchy.sort(key=lambda x: x.get("rank_level", -1), reverse=True)

    return {
        "hierarchy": hierarchy,
        "total_roots": len(hierarchy),
        "available_ranks": UK_RANK_HIERARCHY
    }


@app.post("/officers/{officer_id}/auto-link-supervisor")
@limiter.limit(get_rate_limit("default"))
def auto_link_supervisor(
    request: Request,
    officer_id: int,
    db: Session = Depends(get_db)
):
    """
    Automatically suggest and link a supervisor based on:
    1. Co-appearance in same media
    2. Higher rank
    3. Same force

    Returns suggestions but only links if confidence is high enough.
    """
    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    if officer.supervisor_id:
        return {
            "message": "Officer already has a supervisor",
            "current_supervisor_id": officer.supervisor_id,
            "suggestions": []
        }

    officer_rank = get_rank_level(officer.rank)

    # Find co-appearing officers with higher ranks
    from sqlalchemy import func

    # Get media IDs where this officer appears
    officer_media = db.query(models.OfficerAppearance.media_id).filter(
        models.OfficerAppearance.officer_id == officer_id
    ).distinct().all()
    media_ids = [m[0] for m in officer_media]

    if not media_ids:
        return {"message": "No appearances found", "suggestions": []}

    # Find other officers in same media
    co_officers = (
        db.query(
            models.OfficerAppearance.officer_id,
            func.count(models.OfficerAppearance.id).label('shared_count')
        )
        .filter(
            models.OfficerAppearance.media_id.in_(media_ids),
            models.OfficerAppearance.officer_id != officer_id
        )
        .group_by(models.OfficerAppearance.officer_id)
        .order_by(func.count(models.OfficerAppearance.id).desc())
        .all()
    )

    suggestions = []
    for co_id, shared_count in co_officers:
        co_officer = db.query(models.Officer).filter(models.Officer.id == co_id).first()
        if not co_officer:
            continue

        co_rank = get_rank_level(co_officer.rank)

        # Skip if same or lower rank
        if co_rank <= officer_rank:
            continue

        # Skip if different force (unless one is unknown)
        if officer.force and co_officer.force and officer.force != co_officer.force:
            continue

        # Calculate confidence score
        confidence = 0.0
        reasons = []

        # Rank difference (more levels = more confidence)
        rank_diff = co_rank - officer_rank
        if rank_diff == 1:
            confidence += 0.4
            reasons.append(f"Direct superior rank ({co_officer.rank})")
        elif rank_diff > 1:
            confidence += 0.2
            reasons.append(f"Higher rank ({co_officer.rank})")

        # Co-appearances (more = more confidence)
        if shared_count >= 5:
            confidence += 0.3
            reasons.append(f"Frequently together ({shared_count} appearances)")
        elif shared_count >= 2:
            confidence += 0.2
            reasons.append(f"Multiple appearances together ({shared_count})")
        else:
            confidence += 0.1
            reasons.append("Appeared together")

        # Same force
        if officer.force and co_officer.force == officer.force:
            confidence += 0.2
            reasons.append("Same force")

        # Get crop
        app = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.officer_id == co_id,
            models.OfficerAppearance.image_crop_path.isnot(None)
        ).first()

        suggestions.append({
            "id": co_officer.id,
            "badge_number": co_officer.badge_number,
            "force": co_officer.force,
            "rank": co_officer.rank,
            "rank_level": co_rank,
            "shared_appearances": shared_count,
            "confidence": round(confidence, 2),
            "reasons": reasons,
            "crop_path": to_crop_url(app.image_crop_path) if app else None
        })

    # Sort by confidence
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)

    # Auto-link if top suggestion has high confidence
    auto_linked = False
    if suggestions and suggestions[0]["confidence"] >= 0.7:
        best = suggestions[0]
        officer.supervisor_id = best["id"]
        db.commit()
        auto_linked = True

    return {
        "officer_id": officer_id,
        "suggestions": suggestions[:5],  # Top 5 suggestions
        "auto_linked": auto_linked,
        "linked_supervisor_id": officer.supervisor_id
    }


@app.get("/stats/overview")
@limiter.limit(get_rate_limit("officers_list"))
def get_stats_overview(request: Request, db: Session = Depends(get_db)):
    """
    Get overall statistics for the dashboard.
    """
    from sqlalchemy import func, distinct

    total_officers = db.query(models.Officer).count()
    total_appearances = db.query(models.OfficerAppearance).count()
    total_media = db.query(models.Media).count()
    total_protests = db.query(models.Protest).count()

    # Officers with multiple appearances
    repeat_count = (
        db.query(models.OfficerAppearance.officer_id)
        .group_by(models.OfficerAppearance.officer_id)
        .having(func.count(models.OfficerAppearance.id) >= 2)
        .count()
    )

    # Officers across multiple events
    multi_event_count = (
        db.query(models.OfficerAppearance.officer_id)
        .join(models.Media)
        .group_by(models.OfficerAppearance.officer_id)
        .having(func.count(distinct(models.Media.protest_id)) >= 2)
        .count()
    )

    # Most recent media processed
    recent_media = (
        db.query(models.Media)
        .filter(models.Media.processed == True)
        .order_by(models.Media.timestamp.desc())
        .limit(5)
        .all()
    )

    return {
        "total_officers": total_officers,
        "total_appearances": total_appearances,
        "total_media": total_media,
        "total_protests": total_protests,
        "repeat_officers": repeat_count,
        "multi_event_officers": multi_event_count,
        "recent_media": [
            {
                "id": m.id,
                "url": m.url,
                "type": m.type,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in recent_media
        ]
    }

@app.get("/officers/{officer_id}", response_model=schemas.Officer)
@limiter.limit(get_rate_limit("officers_detail"))
def get_officer(request: Request, officer_id: int, db: Session = Depends(get_db)):
    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if officer is None:
        raise HTTPException(status_code=404, detail="Officer not found")
    return officer

@app.get("/officers/{officer_id}/dossier")
def get_officer_dossier(officer_id: int, db: Session = Depends(get_db)):
    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
        
    # Get appearances
    appearances = db.query(models.OfficerAppearance).filter(models.OfficerAppearance.officer_id == officer_id).all()
    
    from reports import generate_officer_dossier
    pdf_buffer = generate_officer_dossier(officer, appearances)
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=officer_{officer_id}_dossier.pdf"}
    )

@app.get("/media/{media_id}/report")
@limiter.limit(get_rate_limit("report"))
def get_media_report(request: Request, media_id: int, db: Session = Depends(get_db)):
    """
    Returns aggregated data for the 'Webpage Report' of a specific media item.
    Includes timeline data with all appearance timestamps for video scrubbing.
    """
    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Get Protest
    protest = media.protest

    # Get Officer Appearances
    appearances = db.query(models.OfficerAppearance).filter(models.OfficerAppearance.media_id == media_id).all()

    # Aggregate Officers with all their appearances
    officer_ids = set(appearance.officer_id for appearance in appearances)
    officers = []
    timeline_markers = []  # All timestamps for video scrubbing

    for oid in officer_ids:
        officer = db.query(models.Officer).filter(models.Officer.id == oid).first()
        if officer:
            # Get ALL appearances for this officer in this video
            officer_appearances = [a for a in appearances if a.officer_id == oid]

            # Find the best crop (first one with an image)
            first_app = next((a for a in officer_appearances if a.image_crop_path), None)

            # Collect all timestamps for this officer
            officer_timestamps = []
            for app in officer_appearances:
                if app.timestamp_in_video:
                    timestamp_data = {
                        "timestamp": app.timestamp_in_video,
                        "crop_path": to_crop_url(app.image_crop_path),
                        "action": app.action,
                        "role": app.role
                    }
                    officer_timestamps.append(timestamp_data)
                    # Also add to global timeline
                    timeline_markers.append({
                        "officer_id": officer.id,
                        "badge": officer.badge_number,
                        "timestamp": app.timestamp_in_video,
                        "action": app.action,
                        "crop_path": to_crop_url(app.image_crop_path)
                    })

            officers.append({
                "id": officer.id,
                "badge": officer.badge_number,
                "force": officer.force,
                "role": first_app.role if first_app else None,
                "crop_path": to_crop_url(first_app.image_crop_path) if first_app else None,
                "total_appearances_in_video": len(officer_appearances),
                "timestamps": officer_timestamps  # All timestamps for this officer
            })

    # Sort timeline markers by timestamp
    def parse_timestamp(ts):
        """Convert HH:MM:SS or MM:SS to seconds for sorting."""
        if not ts:
            return 0
        parts = ts.split(':')
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            else:
                return float(parts[0])
        except (ValueError, IndexError):
            return 0

    timeline_markers.sort(key=lambda x: parse_timestamp(x.get('timestamp', '')))

    return {
        "media": {
            "id": media.id,
            "url": media.url,
            "type": media.type,
            "timestamp": media.timestamp
        },
        "protest": {
            "name": protest.name if protest else "Unknown Event",
            "location": protest.location if protest else "Unknown Location",
            "date": protest.date if protest else None
        },
        "stats": {
            "total_officers": len(officers),
            "total_appearances": len(appearances)
        },
        "officers": officers,
        "timeline": timeline_markers  # All markers for video timeline
    }

@app.post("/ingest/url")
@limiter.limit(get_rate_limit("ingest"))
@limiter.limit(get_rate_limit("ingest_hourly"))
async def ingest_media_url(request: Request, body: IngestURLRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Ingest a URL (YouTube, web).
    Triggers background download and analysis.
    Rate limited to prevent abuse of expensive AI processing.
    """
    # Validate protest_id if provided
    if body.protest_id is not None:
        protest = db.query(models.Protest).filter(models.Protest.id == body.protest_id).first()
        if not protest:
            raise HTTPException(status_code=404, detail=f"Protest with ID {body.protest_id} not found")

    # Create a unique Task ID and room
    task_id = f"task_{int(datetime.utcnow().timestamp())}"

    # We need to capture the current event loop to schedule async emits from the sync background thread
    loop = asyncio.get_running_loop()

    # Define wrapper here (or outside) to lazily import heavy modules
    def background_wrapper(url, answers, protest_id, room_id, event_loop):
        # 1. Define callback for socket events
        def status_callback(event, data):
            asyncio.run_coroutine_threadsafe(
                sio_server.emit(event, data, room=room_id),
                event_loop
            )

        try:
            status_callback("log", "Initializing AI engines (this may take a moment)...")
            
            # 2. Lazy Import - Move heavy imports HERE
            print("Importing ingest_video in background task...")
            from ingest_video import process_video_workflow
            import recon
            
            # --- AI RECONNAISSANCE ---
            status_callback("log", "🤖 AI Recon: analyzing URL context...")
            status_callback("status_update", "Intel Scan")
            
            recon_data = recon.analyze_url(url)
            
            # Emit Recon Data to Frontend
            status_callback("recon_result", recon_data)
            
            rec_str = f"Category: {recon_data['category']} | Score: {recon_data['score']}/100 | Action: {recon_data['recommendation']}"
            status_callback("log", f"AI Assessment: {rec_str}")
            
            if recon_data['keywords']:
                status_callback("log", f"Context Identifiers: {', '.join(recon_data['keywords'])}")
            
            # Optional: Stop if truly irrelevant? For now we just advise.
            # -------------------------
            
            # 3. Run Workflow
            process_video_workflow(url, answers, protest_id, status_callback=status_callback)
            
        except ImportError as e:
            error_msg = f"Server Configuration Error: Failed to load AI modules. {e}"
            print(error_msg)
            status_callback("log", error_msg)
            status_callback("Error", f"Import failed: {e}")
        except Exception as e:
            error_msg = f"Processing Error: {e}"
            print(error_msg)
            status_callback("log", error_msg)
            status_callback("Error", str(e))
        finally:
            # Schedule room cleanup regardless of success/failure
            asyncio.run_coroutine_threadsafe(
                mark_room_complete(room_id),
                event_loop
            )

    background_tasks.add_task(background_wrapper, body.url, body.answers, body.protest_id, task_id, loop)
    
    return {"status": "processing_started", "message": "Video queued for analysis.", "task_id": task_id}


@app.post("/ingest/bulk")
@limiter.limit(get_rate_limit("bulk_ingest"))
@limiter.limit(get_rate_limit("ingest_hourly"))
async def bulk_ingest_urls(request: Request, body: BulkIngestRequest, background_tasks: BackgroundTasks):
    """
    Ingest multiple URLs at once.
    Creates a separate task for each URL.
    """
    if not body.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    if len(body.urls) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 URLs per bulk request")

    # Validate all URLs first
    valid_urls = []
    errors = []
    for i, url in enumerate(body.urls):
        try:
            validated = validate_single_url(url)
            valid_urls.append(validated)
        except ValueError as e:
            errors.append({"index": i, "url": url, "error": str(e)})

    if not valid_urls:
        raise HTTPException(status_code=400, detail={"message": "No valid URLs", "errors": errors})

    # Create tasks for each valid URL
    task_ids = []
    loop = asyncio.get_running_loop()

    # Capture body values before the loop to avoid closure issues
    answers = body.answers
    protest_id = body.protest_id

    for url in valid_urls:
        task_id = f"task_{int(datetime.utcnow().timestamp())}_{hash(url) % 10000}"
        task_ids.append({"url": url, "task_id": task_id})

        # Define wrapper for this URL
        def create_wrapper(url_to_process, room_id, event_loop, ans, pid):
            def wrapper():
                def status_callback(event, data):
                    asyncio.run_coroutine_threadsafe(
                        sio_server.emit(event, data, room=room_id),
                        event_loop
                    )

                try:
                    from ingest_video import process_video_workflow
                    process_video_workflow(url_to_process, ans, pid, status_callback=status_callback)
                except Exception as e:
                    status_callback("Error", str(e))
                finally:
                    asyncio.run_coroutine_threadsafe(
                        mark_room_complete(room_id),
                        event_loop
                    )
            return wrapper

        background_tasks.add_task(create_wrapper(url, task_id, loop, answers, protest_id))

    return {
        "status": "processing_started",
        "message": f"Queued {len(valid_urls)} URLs for processing",
        "tasks": task_ids,
        "errors": errors if errors else None
    }


@app.get("/protests")
@limiter.limit(get_rate_limit("protests"))
def get_protests(request: Request, db: Session = Depends(get_db)):
    return db.query(models.Protest).all()


@app.get("/protests/{protest_id}/timeline", tags=["protests"])
@limiter.limit(get_rate_limit("default"))
def get_protest_timeline(
    request: Request,
    protest_id: int,
    db: Session = Depends(get_db)
):
    """
    Get chronological timeline of events for a specific protest.

    Returns all officer appearances, media, and detected events ordered by time,
    allowing reconstruction of how events unfolded.
    """
    from sqlalchemy import func

    # Get protest details
    protest = db.query(models.Protest).filter(models.Protest.id == protest_id).first()
    if not protest:
        raise HTTPException(status_code=404, detail="Protest not found")

    # Get all media for this protest with appearances
    media_items = db.query(models.Media).filter(
        models.Media.protest_id == protest_id
    ).order_by(models.Media.timestamp).all()

    events = []

    for media in media_items:
        # Get all appearances in this media
        appearances = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.media_id == media.id
        ).all()

        for app in appearances:
            officer = app.officer

            # Get uniform analysis if exists
            uniform_data = None
            if app.uniform_analysis:
                ua = app.uniform_analysis
                uniform_data = {
                    "force": ua.detected_force,
                    "unit_type": ua.unit_type,
                    "rank": ua.detected_rank,
                    "shoulder_number": ua.shoulder_number,
                    "uniform_type": ua.uniform_type
                }

            # Get equipment detections
            equipment_list = []
            for eq_det in app.equipment_detections:
                equipment_list.append({
                    "name": eq_det.equipment.name,
                    "category": eq_det.equipment.category,
                    "confidence": eq_det.confidence
                })

            # Parse timestamp from video
            event_time = media.timestamp
            video_timestamp = None
            if app.timestamp_in_video:
                video_timestamp = app.timestamp_in_video
                # Try to combine with media timestamp for more precise time
                try:
                    parts = app.timestamp_in_video.split(":")
                    if len(parts) == 3:
                        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                        from datetime import timedelta
                        # Add offset to media timestamp
                        if media.timestamp:
                            event_time = media.timestamp + timedelta(hours=h, minutes=m, seconds=s)
                except:
                    pass

            events.append({
                "id": app.id,
                "event_type": "officer_appearance",
                "timestamp": event_time.isoformat() if event_time else None,
                "video_timestamp": video_timestamp,
                "media_id": media.id,
                "media_type": media.type,
                "media_url": get_web_url(media.url) if media.url else None,
                "officer": {
                    "id": officer.id,
                    "badge_number": officer.badge_number,
                    "force": officer.force,
                    "rank": officer.rank
                },
                "action": app.action,
                "role": app.role,
                "confidence": app.confidence,
                "crop_url": get_web_url(app.image_crop_path) if app.image_crop_path else None,
                "uniform": uniform_data,
                "equipment": equipment_list
            })

    # Sort all events by timestamp
    events.sort(key=lambda e: e["timestamp"] or "")

    # Group events by time buckets (every 5 minutes) for visualization
    time_buckets = {}
    for event in events:
        if event["timestamp"]:
            # Round to nearest 5 minute bucket
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                bucket = dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
                bucket_key = bucket.isoformat()
                if bucket_key not in time_buckets:
                    time_buckets[bucket_key] = []
                time_buckets[bucket_key].append(event)
            except:
                pass

    return {
        "protest": {
            "id": protest.id,
            "name": protest.name,
            "date": protest.date.isoformat() if protest.date else None,
            "location": protest.location,
            "latitude": protest.latitude,
            "longitude": protest.longitude,
            "description": protest.description
        },
        "total_events": len(events),
        "total_officers": len(set(e["officer"]["id"] for e in events)),
        "total_media": len(media_items),
        "events": events,
        "time_buckets": time_buckets
    }


@app.get("/timeline", tags=["stats"])
@limiter.limit(get_rate_limit("default"))
def get_global_timeline(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get chronological timeline of all events across all protests.

    Useful for understanding patterns across multiple demonstrations.
    """
    from sqlalchemy import func, desc
    from datetime import datetime

    # Base query for appearances with media
    query = db.query(models.OfficerAppearance).join(
        models.Media, models.OfficerAppearance.media_id == models.Media.id
    ).join(
        models.Officer, models.OfficerAppearance.officer_id == models.Officer.id
    )

    # Date filters
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(models.Media.timestamp >= start_dt)
        except:
            pass

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(models.Media.timestamp <= end_dt)
        except:
            pass

    # Order by time and limit
    appearances = query.order_by(desc(models.Media.timestamp)).limit(limit).all()

    events = []
    for app in appearances:
        media = app.media
        officer = app.officer
        protest = media.protest if media.protest_id else None

        # Equipment summary
        equipment_count = len(app.equipment_detections)
        high_escalation_count = sum(
            1 for eq in app.equipment_detections
            if eq.equipment and eq.equipment.name in ["Shield", "Long Shield", "Baton", "Taser", "Ballistic Helmet"]
        )

        events.append({
            "id": app.id,
            "timestamp": media.timestamp.isoformat() if media.timestamp else None,
            "video_timestamp": app.timestamp_in_video,
            "protest": {
                "id": protest.id if protest else None,
                "name": protest.name if protest else "Unknown",
                "location": protest.location if protest else None
            } if protest else None,
            "media_id": media.id,
            "media_type": media.type,
            "officer": {
                "id": officer.id,
                "badge_number": officer.badge_number,
                "force": officer.force,
                "rank": officer.rank
            },
            "action": app.action,
            "role": app.role,
            "equipment_count": equipment_count,
            "high_escalation_equipment": high_escalation_count > 0,
            "crop_url": get_web_url(app.image_crop_path) if app.image_crop_path else None
        })

    # Summary stats
    unique_officers = len(set(e["officer"]["id"] for e in events))
    unique_protests = len(set(e["protest"]["id"] for e in events if e["protest"] and e["protest"]["id"]))

    return {
        "total_events": len(events),
        "unique_officers": unique_officers,
        "unique_protests": unique_protests,
        "date_range": {
            "earliest": events[-1]["timestamp"] if events else None,
            "latest": events[0]["timestamp"] if events else None
        },
        "events": events
    }


@app.post("/officers/merge")
@limiter.limit(get_rate_limit("default"))
def merge_officers(
    request: Request,
    primary_id: int,
    secondary_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Merge multiple officers into one primary officer.
    All appearances from secondary officers are transferred to the primary.
    Secondary officers are deleted after merge.
    """
    # Get primary officer
    primary = db.query(models.Officer).filter(models.Officer.id == primary_id).first()
    if not primary:
        raise HTTPException(status_code=404, detail="Primary officer not found")

    merged_count = 0
    for sec_id in secondary_ids:
        if sec_id == primary_id:
            continue  # Skip if same as primary

        secondary = db.query(models.Officer).filter(models.Officer.id == sec_id).first()
        if not secondary:
            continue

        # Transfer all appearances from secondary to primary
        appearances = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.officer_id == sec_id
        ).all()

        for app in appearances:
            app.officer_id = primary_id

        # Merge badge number if primary doesn't have one
        if not primary.badge_number and secondary.badge_number:
            primary.badge_number = secondary.badge_number

        # Merge force if primary doesn't have one
        if not primary.force and secondary.force:
            primary.force = secondary.force

        # Append notes
        if secondary.notes:
            if primary.notes:
                primary.notes += f"\n[Merged from Officer #{sec_id}]: {secondary.notes}"
            else:
                primary.notes = f"[Merged from Officer #{sec_id}]: {secondary.notes}"

        # Delete secondary officer
        db.delete(secondary)
        merged_count += 1

    db.commit()

    return {
        "status": "success",
        "message": f"Merged {merged_count} officers into Officer #{primary_id}",
        "primary_id": primary_id
    }

@app.patch("/officers/{officer_id}")
@limiter.limit(get_rate_limit("default"))
def update_officer(
    request: Request,
    officer_id: int,
    badge_number: Optional[str] = None,
    force: Optional[str] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update officer details (badge number, force, notes).
    """
    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    if badge_number is not None:
        officer.badge_number = badge_number
    if force is not None:
        officer.force = force
    if notes is not None:
        officer.notes = notes

    db.commit()
    db.refresh(officer)

    return {"status": "success", "officer": officer}


@app.delete("/officers/{officer_id}")
@limiter.limit(get_rate_limit("default"))
def delete_officer(
    request: Request,
    officer_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an officer and all their appearances.
    """
    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    # Delete all appearances first (foreign key constraint)
    db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.officer_id == officer_id
    ).delete()

    # Delete the officer
    db.delete(officer)
    db.commit()

    return {"status": "success", "message": f"Officer #{officer_id} deleted"}


# =============================================================================
# CONFIDENCE CALIBRATION ENDPOINTS
# =============================================================================

class AppearanceVerifyRequest(BaseModel):
    verified: bool
    confidence: Optional[float] = None


@app.patch("/appearances/{appearance_id}/verify")
@limiter.limit(get_rate_limit("default"))
def verify_appearance(
    request: Request,
    appearance_id: int,
    body: AppearanceVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Mark an officer appearance as verified/unverified and optionally update confidence.
    """
    appearance = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.id == appearance_id
    ).first()

    if not appearance:
        raise HTTPException(status_code=404, detail="Appearance not found")

    appearance.verified = body.verified

    if body.confidence is not None:
        if body.confidence < 0 or body.confidence > 100:
            raise HTTPException(status_code=400, detail="Confidence must be between 0 and 100")
        appearance.confidence = body.confidence

    db.commit()
    db.refresh(appearance)

    return {
        "status": "success",
        "appearance_id": appearance_id,
        "verified": appearance.verified,
        "confidence": appearance.confidence
    }


@app.get("/appearances/unverified")
@limiter.limit(get_rate_limit("default"))
def get_unverified_appearances(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    min_confidence: float = None,
    max_confidence: float = None,
    db: Session = Depends(get_db)
):
    """
    Get unverified appearances for review, optionally filtered by confidence range.
    """
    query = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.verified == False
    )

    if min_confidence is not None:
        query = query.filter(models.OfficerAppearance.confidence >= min_confidence)
    if max_confidence is not None:
        query = query.filter(models.OfficerAppearance.confidence <= max_confidence)

    # Order by confidence ascending (lowest confidence first for review)
    query = query.order_by(models.OfficerAppearance.confidence.asc().nullsfirst())

    total = query.count()
    appearances = query.offset(skip).limit(limit).all()

    result = []
    for app in appearances:
        officer = db.query(models.Officer).filter(models.Officer.id == app.officer_id).first()
        media = db.query(models.Media).filter(models.Media.id == app.media_id).first()

        result.append({
            "id": app.id,
            "officer_id": app.officer_id,
            "media_id": app.media_id,
            "badge_number": officer.badge_number if officer else None,
            "force": officer.force if officer else None,
            "timestamp_in_video": app.timestamp_in_video,
            "image_crop_path": to_crop_url(app.image_crop_path),
            "role": app.role,
            "action": app.action,
            "confidence": app.confidence,
            "confidence_factors": app.confidence_factors,
            "verified": app.verified,
            "media_type": media.type if media else None,
            "media_url": media.url if media else None
        })

    return {
        "total": total,
        "appearances": result
    }


@app.get("/confidence/stats")
@limiter.limit(get_rate_limit("default"))
def get_confidence_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get statistics about confidence levels across all appearances.
    """
    from sqlalchemy import func

    total = db.query(models.OfficerAppearance).count()
    verified = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.verified == True
    ).count()
    unverified = total - verified

    # Confidence distribution
    high_confidence = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.confidence >= 80
    ).count()
    medium_confidence = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.confidence >= 50,
        models.OfficerAppearance.confidence < 80
    ).count()
    low_confidence = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.confidence < 50,
        models.OfficerAppearance.confidence.isnot(None)
    ).count()
    no_confidence = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.confidence.is_(None)
    ).count()

    # Average confidence
    avg_confidence = db.query(func.avg(models.OfficerAppearance.confidence)).scalar()

    return {
        "total_appearances": total,
        "verified_count": verified,
        "unverified_count": unverified,
        "verification_rate": round((verified / total * 100) if total > 0 else 0, 1),
        "confidence_distribution": {
            "high": high_confidence,
            "medium": medium_confidence,
            "low": low_confidence,
            "unknown": no_confidence
        },
        "average_confidence": round(avg_confidence, 1) if avg_confidence else None
    }


@app.get("/export/officers/csv")
@limiter.limit(get_rate_limit("default"))
def export_officers_csv(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Export all officers as CSV.
    """
    import csv
    import io

    officers = db.query(models.Officer).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(['ID', 'Badge Number', 'Force', 'Notes', 'Total Appearances', 'Created At'])

    for officer in officers:
        appearances_count = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.officer_id == officer.id
        ).count()

        writer.writerow([
            officer.id,
            officer.badge_number or '',
            officer.force or '',
            officer.notes or '',
            appearances_count,
            officer.created_at.isoformat() if hasattr(officer, 'created_at') and officer.created_at else ''
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=officers_export.csv"}
    )


@app.get("/export/officers/json")
@limiter.limit(get_rate_limit("default"))
def export_officers_json(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Export all officers as JSON.
    """
    import json

    officers = db.query(models.Officer).all()
    export_data = []

    for officer in officers:
        appearances = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.officer_id == officer.id
        ).all()

        officer_data = {
            "id": officer.id,
            "badge_number": officer.badge_number,
            "force": officer.force,
            "notes": officer.notes,
            "appearances": [
                {
                    "id": app.id,
                    "media_id": app.media_id,
                    "timestamp_in_video": app.timestamp_in_video,
                    "role": app.role,
                    "action": app.action
                }
                for app in appearances
            ]
        }
        export_data.append(officer_data)

    json_str = json.dumps(export_data, indent=2)

    return StreamingResponse(
        iter([json_str]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=officers_export.json"}
    )


@app.get("/export/report/{media_id}/csv")
@limiter.limit(get_rate_limit("default"))
def export_report_csv(
    request: Request,
    media_id: int,
    db: Session = Depends(get_db)
):
    """
    Export a media report as CSV.
    """
    import csv
    import io

    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    appearances = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.media_id == media_id
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Officer ID', 'Badge Number', 'Force', 'Timestamp', 'Role', 'Action'])

    for app in appearances:
        officer = db.query(models.Officer).filter(models.Officer.id == app.officer_id).first()
        writer.writerow([
            app.officer_id,
            officer.badge_number if officer else '',
            officer.force if officer else '',
            app.timestamp_in_video or '',
            app.role or '',
            app.action or ''
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{media_id}_export.csv"}
    )


@app.post("/search/face")
@limiter.limit(get_rate_limit("face_search"))
@limiter.limit(get_rate_limit("face_search_hourly"))
async def search_by_face(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an image to search for matching officers by face.
    Returns officers sorted by similarity score.
    """
    import os
    import uuid
    import json
    from process import calculate_face_similarity

    # Validate file type
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file type. Allowed: jpg, jpeg, png, gif, webp, bmp"
        )

    # Save uploaded file temporarily
    temp_dir = "data/temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"search_{uuid.uuid4().hex}{ext}")

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Generate embedding for uploaded face
        from ai import analyzer
        embedding = analyzer.generate_embedding(temp_path)

        if embedding is None:
            raise HTTPException(
                status_code=400,
                detail="Could not detect a face in the uploaded image. Please try a clearer image."
            )

        # Search for matching officers
        officers_with_embeddings = db.query(models.Officer).filter(
            models.Officer.visual_id.isnot(None)
        ).all()

        matches = []
        for officer in officers_with_embeddings:
            try:
                officer_embedding = json.loads(officer.visual_id)
                is_match, confidence, dist_euc, sim_cos = calculate_face_similarity(
                    embedding, officer_embedding
                )

                if confidence > 0.3:  # Include potential matches
                    # Get first appearance for image
                    first_app = db.query(models.OfficerAppearance).filter(
                        models.OfficerAppearance.officer_id == officer.id,
                        models.OfficerAppearance.image_crop_path.isnot(None)
                    ).first()

                    matches.append({
                        "id": officer.id,
                        "badge_number": officer.badge_number,
                        "force": officer.force,
                        "confidence": round(confidence * 100, 1),
                        "is_strong_match": is_match,
                        "crop_path": to_crop_url(first_app.image_crop_path) if first_app else None
                    })
            except (json.JSONDecodeError, Exception) as e:
                continue

        # Sort by confidence
        matches.sort(key=lambda x: x['confidence'], reverse=True)

        return {
            "status": "success",
            "total_matches": len(matches),
            "matches": matches[:20]  # Return top 20 matches
        }

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


# Allowed file extensions by type
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v'}
MAX_UPLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500MB


@app.post("/upload")
@limiter.limit(get_rate_limit("upload"))
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    protest_id: Optional[int] = Form(None),
    type: str = Form(...),
    db: Session = Depends(get_db)
):
    from ingest import save_upload
    import os

    # Validate type
    if type not in ["image", "video"]:
         raise HTTPException(status_code=400, detail="Invalid media type. Must be 'image' or 'video'.")

    # Validate file extension matches declared type (#11)
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if type == "image":
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )
    elif type == "video":
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid video file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
            )

    # Validate content type header matches
    content_type = file.content_type or ""
    if type == "image" and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File content type doesn't match declared image type")
    if type == "video" and not content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File content type doesn't match declared video type")

    result = save_upload(file.file, file.filename, protest_id, type, db)

    # Handle tuple return (media, duplicate_info) or None
    if result is None or result[0] is None:
        raise HTTPException(status_code=500, detail="File upload failed")

    media, duplicate_info = result

    # Trigger processing (skip if exact duplicate - already processed)
    from process import process_media
    if not (duplicate_info and duplicate_info.get("duplicate_type") == "exact"):
        process_media(media.id)

    response = {
        "status": "uploaded",
        "media_id": media.id,
        "filename": file.filename
    }

    # Add duplicate info if detected
    if duplicate_info:
        response["duplicate_detected"] = True
        response["duplicate_type"] = duplicate_info.get("duplicate_type")
        response["original_media_id"] = duplicate_info.get("original_id")
        if duplicate_info.get("similarity_score") is not None:
            response["similarity_score"] = duplicate_info.get("similarity_score")

    return response


# =============================================================================
# UNIFORM RECOGNITION ENDPOINTS
# =============================================================================

@app.get("/equipment")
@limiter.limit(get_rate_limit("officers_list"))
def get_equipment(
    request: Request,
    category: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all equipment types, optionally filtered by category.
    Includes detection count for each equipment type.
    """
    from sqlalchemy import func

    query = db.query(
        models.Equipment,
        func.count(models.EquipmentDetection.id).label('detection_count')
    ).outerjoin(models.EquipmentDetection)

    if category:
        query = query.filter(models.Equipment.category == category)

    query = query.group_by(models.Equipment.id).order_by(models.Equipment.category, models.Equipment.name)
    results = query.all()

    equipment_list = []
    for equip, count in results:
        equipment_list.append({
            "id": equip.id,
            "name": equip.name,
            "category": equip.category,
            "description": equip.description,
            "detection_count": count
        })

    # Get categories for filtering
    categories = db.query(models.Equipment.category).distinct().all()

    return {
        "equipment": equipment_list,
        "categories": [c[0] for c in categories],
        "total": len(equipment_list)
    }


@app.get("/equipment/{equipment_id}/detections")
@limiter.limit(get_rate_limit("officers_list"))
def get_equipment_detections(
    request: Request,
    equipment_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get all detections of a specific equipment type.
    Returns appearance details where this equipment was detected.
    """
    equipment = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    detections = (
        db.query(models.EquipmentDetection)
        .filter(models.EquipmentDetection.equipment_id == equipment_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = db.query(models.EquipmentDetection).filter(
        models.EquipmentDetection.equipment_id == equipment_id
    ).count()

    result = []
    for det in detections:
        appearance = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.id == det.appearance_id
        ).first()
        officer = db.query(models.Officer).filter(
            models.Officer.id == appearance.officer_id
        ).first() if appearance else None

        result.append({
            "detection_id": det.id,
            "confidence": det.confidence,
            "bounding_box": det.bounding_box,
            "appearance_id": det.appearance_id,
            "officer_id": officer.id if officer else None,
            "badge_number": officer.badge_number if officer else None,
            "force": officer.force if officer else None,
            "crop_path": to_crop_url(appearance.image_crop_path) if appearance else None,
            "timestamp": appearance.timestamp_in_video if appearance else None
        })

    return {
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "category": equipment.category,
            "description": equipment.description
        },
        "total_detections": total,
        "detections": result
    }


@app.get("/officers/{officer_id}/uniform")
@limiter.limit(get_rate_limit("officers_detail"))
def get_officer_uniform_analysis(
    request: Request,
    officer_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all uniform analyses for an officer across all their appearances.
    """
    import json

    officer = db.query(models.Officer).filter(models.Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    # Get all appearances with uniform analysis
    appearances = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.officer_id == officer_id
    ).all()

    analyses = []
    for app in appearances:
        # Check if analysis exists
        analysis = db.query(models.UniformAnalysis).filter(
            models.UniformAnalysis.appearance_id == app.id
        ).first()

        if analysis:
            # Get equipment detections
            equipment = db.query(models.EquipmentDetection).filter(
                models.EquipmentDetection.appearance_id == app.id
            ).all()

            equipment_list = []
            for eq_det in equipment:
                eq = db.query(models.Equipment).filter(models.Equipment.id == eq_det.equipment_id).first()
                if eq:
                    equipment_list.append({
                        "name": eq.name,
                        "category": eq.category,
                        "confidence": eq_det.confidence
                    })

            analyses.append({
                "appearance_id": app.id,
                "timestamp_in_video": app.timestamp_in_video,
                "crop_path": to_crop_url(app.image_crop_path),
                "analysis": {
                    "detected_force": analysis.detected_force,
                    "force_confidence": analysis.force_confidence,
                    "force_indicators": json.loads(analysis.force_indicators) if analysis.force_indicators else [],
                    "unit_type": analysis.unit_type,
                    "unit_confidence": analysis.unit_confidence,
                    "detected_rank": analysis.detected_rank,
                    "rank_confidence": analysis.rank_confidence,
                    "shoulder_number": analysis.shoulder_number,
                    "shoulder_number_confidence": analysis.shoulder_number_confidence,
                    "uniform_type": analysis.uniform_type,
                    "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None
                },
                "equipment": equipment_list
            })

    # Calculate consensus (most common values across analyses)
    forces = [a["analysis"]["detected_force"] for a in analyses if a["analysis"]["detected_force"]]
    units = [a["analysis"]["unit_type"] for a in analyses if a["analysis"]["unit_type"]]
    ranks = [a["analysis"]["detected_rank"] for a in analyses if a["analysis"]["detected_rank"]]

    from collections import Counter
    consensus = {
        "force": Counter(forces).most_common(1)[0][0] if forces else None,
        "unit": Counter(units).most_common(1)[0][0] if units else None,
        "rank": Counter(ranks).most_common(1)[0][0] if ranks else None
    }

    return {
        "officer_id": officer_id,
        "badge_number": officer.badge_number,
        "force": officer.force,
        "total_appearances": len(appearances),
        "analyzed_appearances": len(analyses),
        "consensus": consensus,
        "analyses": analyses
    }


@app.post("/appearances/{appearance_id}/analyze")
@limiter.limit(get_rate_limit("ai_analysis"))
@limiter.limit(get_rate_limit("ai_analysis_hourly"))
async def analyze_appearance_uniform(
    request: Request,
    appearance_id: int,
    background_tasks: BackgroundTasks,
    force_reanalyze: bool = False,
    db: Session = Depends(get_db)
):
    """
    Trigger Claude Vision analysis for an officer appearance.
    Runs as a background task to avoid blocking.
    """
    import os
    import json

    appearance = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.id == appearance_id
    ).first()

    if not appearance:
        raise HTTPException(status_code=404, detail="Appearance not found")

    if not appearance.image_crop_path:
        raise HTTPException(status_code=400, detail="No image available for this appearance")

    # Check if already analyzed
    existing = db.query(models.UniformAnalysis).filter(
        models.UniformAnalysis.appearance_id == appearance_id
    ).first()

    if existing and not force_reanalyze:
        return {
            "status": "already_analyzed",
            "analysis_id": existing.id,
            "analyzed_at": existing.analyzed_at.isoformat() if existing.analyzed_at else None,
            "message": "Use force_reanalyze=true to re-analyze"
        }

    # Get full image path using path utilities for consistent handling
    image_path = get_absolute_path(appearance.image_crop_path)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=400, detail=f"Image file not found: {appearance.image_crop_path}")

    # Background task for analysis
    def run_analysis(app_id: int, img_path: str, force: bool):
        from database import SessionLocal
        from ai.uniform_analyzer import UniformAnalyzer

        db_session = SessionLocal()
        try:
            # Check for API key
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                print("Warning: ANTHROPIC_API_KEY not set, skipping uniform analysis")
                return

            analyzer = UniformAnalyzer(api_key=api_key)
            result = analyzer.analyze_uniform_sync(img_path, force_reanalyze=force)

            if not result.get("success"):
                print(f"Uniform analysis failed: {result.get('error')}")
                return

            # Parse to DB format
            db_data = analyzer.parse_to_db_format(result, app_id)
            if not db_data:
                return

            # Check if analysis exists
            existing_analysis = db_session.query(models.UniformAnalysis).filter(
                models.UniformAnalysis.appearance_id == app_id
            ).first()

            if existing_analysis:
                # Update existing
                for key, value in db_data.items():
                    if key != "appearance_id":
                        setattr(existing_analysis, key, value)
            else:
                # Create new
                analysis = models.UniformAnalysis(**db_data)
                db_session.add(analysis)

            # Save equipment detections
            equipment_items = analyzer.extract_equipment(result)
            for eq_item in equipment_items:
                # Find or skip equipment
                equip = db_session.query(models.Equipment).filter(
                    models.Equipment.name == eq_item["name"]
                ).first()

                if equip:
                    # Check if detection exists
                    existing_det = db_session.query(models.EquipmentDetection).filter(
                        models.EquipmentDetection.appearance_id == app_id,
                        models.EquipmentDetection.equipment_id == equip.id
                    ).first()

                    if not existing_det:
                        detection = models.EquipmentDetection(
                            appearance_id=app_id,
                            equipment_id=equip.id,
                            confidence=eq_item.get("confidence")
                        )
                        db_session.add(detection)

            # Update officer force if high confidence
            analysis_data = result.get("analysis", {})
            force_info = analysis_data.get("force", {})
            if force_info.get("confidence", 0) >= 0.8 and force_info.get("name"):
                appearance = db_session.query(models.OfficerAppearance).filter(
                    models.OfficerAppearance.id == app_id
                ).first()
                if appearance:
                    officer = db_session.query(models.Officer).filter(
                        models.Officer.id == appearance.officer_id
                    ).first()
                    if officer and not officer.force:
                        officer.force = force_info["name"]

            db_session.commit()
            print(f"Uniform analysis saved for appearance {app_id}")

        except Exception as e:
            print(f"Error in uniform analysis background task: {e}")
            db_session.rollback()
        finally:
            db_session.close()

    background_tasks.add_task(run_analysis, appearance_id, image_path, force_reanalyze)

    return {
        "status": "analysis_started",
        "appearance_id": appearance_id,
        "message": "Analysis running in background. Check /officers/{id}/uniform for results."
    }


# Track batch analysis progress in memory
_batch_analysis_progress = {}


@app.post("/appearances/batch-analyze")
@limiter.limit(get_rate_limit("ai_analysis"))
async def batch_analyze_uniforms(
    request: Request,
    background_tasks: BackgroundTasks,
    appearance_ids: List[int],
    force_reanalyze: bool = False,
    db: Session = Depends(get_db)
):
    """
    Batch analyze multiple officer appearances.
    Returns a batch_id to track progress via /appearances/batch-status/{batch_id}.
    """
    import uuid
    import os

    if len(appearance_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 appearances per batch")

    if len(appearance_ids) == 0:
        raise HTTPException(status_code=400, detail="No appearance IDs provided")

    # Validate appearances exist and have images
    valid_appearances = []
    for app_id in appearance_ids:
        appearance = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.id == app_id
        ).first()
        if appearance and appearance.image_crop_path:
            # Check if already analyzed (unless force_reanalyze)
            if not force_reanalyze:
                existing = db.query(models.UniformAnalysis).filter(
                    models.UniformAnalysis.appearance_id == app_id
                ).first()
                if existing:
                    continue  # Skip already analyzed
            valid_appearances.append(app_id)

    if not valid_appearances:
        return {
            "status": "no_work",
            "message": "All appearances already analyzed or no valid appearances found"
        }

    # Create batch tracking
    batch_id = str(uuid.uuid4())[:8]
    _batch_analysis_progress[batch_id] = {
        "total": len(valid_appearances),
        "completed": 0,
        "failed": 0,
        "in_progress": True,
        "results": []
    }

    def run_batch_analysis(batch_id: str, app_ids: list, force: bool):
        from database import SessionLocal
        from ai.uniform_analyzer import UniformAnalyzer
        import time

        db_session = SessionLocal()
        try:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                _batch_analysis_progress[batch_id]["in_progress"] = False
                _batch_analysis_progress[batch_id]["error"] = "ANTHROPIC_API_KEY not set"
                return

            analyzer = UniformAnalyzer(api_key=api_key)

            for app_id in app_ids:
                try:
                    # Get appearance
                    appearance = db_session.query(models.OfficerAppearance).filter(
                        models.OfficerAppearance.id == app_id
                    ).first()

                    if not appearance or not appearance.image_crop_path:
                        _batch_analysis_progress[batch_id]["failed"] += 1
                        continue

                    # Build image path
                    from utils.paths import normalize_storage_path, get_full_storage_path
                    storage_path = normalize_storage_path(appearance.image_crop_path)
                    image_path = get_full_storage_path(storage_path)

                    # Run analysis
                    result = analyzer.analyze_uniform_sync(image_path, force_reanalyze=force)

                    if not result.get("success"):
                        _batch_analysis_progress[batch_id]["failed"] += 1
                        _batch_analysis_progress[batch_id]["results"].append({
                            "appearance_id": app_id,
                            "success": False,
                            "error": result.get("error", "Unknown error")
                        })
                        continue

                    # Save to DB
                    db_data = analyzer.parse_to_db_format(result, app_id)
                    if db_data:
                        existing_analysis = db_session.query(models.UniformAnalysis).filter(
                            models.UniformAnalysis.appearance_id == app_id
                        ).first()

                        if existing_analysis:
                            for key, value in db_data.items():
                                if key != "appearance_id":
                                    setattr(existing_analysis, key, value)
                        else:
                            analysis = models.UniformAnalysis(**db_data)
                            db_session.add(analysis)

                        db_session.commit()

                    _batch_analysis_progress[batch_id]["completed"] += 1
                    _batch_analysis_progress[batch_id]["results"].append({
                        "appearance_id": app_id,
                        "success": True,
                        "force": result.get("analysis", {}).get("force", {}).get("name")
                    })

                    # Rate limiting - wait between analyses
                    time.sleep(1)

                except Exception as e:
                    _batch_analysis_progress[batch_id]["failed"] += 1
                    _batch_analysis_progress[batch_id]["results"].append({
                        "appearance_id": app_id,
                        "success": False,
                        "error": str(e)
                    })
                    db_session.rollback()

        except Exception as e:
            _batch_analysis_progress[batch_id]["error"] = str(e)
        finally:
            _batch_analysis_progress[batch_id]["in_progress"] = False
            db_session.close()

    background_tasks.add_task(run_batch_analysis, batch_id, valid_appearances, force_reanalyze)

    return {
        "status": "batch_started",
        "batch_id": batch_id,
        "total_to_analyze": len(valid_appearances),
        "skipped": len(appearance_ids) - len(valid_appearances),
        "message": f"Batch analysis started. Check progress at /appearances/batch-status/{batch_id}"
    }


@app.get("/appearances/batch-status/{batch_id}")
@limiter.limit(get_rate_limit("officers_list"))
def get_batch_status(request: Request, batch_id: str):
    """
    Get progress of a batch uniform analysis.
    """
    if batch_id not in _batch_analysis_progress:
        raise HTTPException(status_code=404, detail="Batch not found")

    progress = _batch_analysis_progress[batch_id]
    return {
        "batch_id": batch_id,
        "total": progress["total"],
        "completed": progress["completed"],
        "failed": progress["failed"],
        "in_progress": progress["in_progress"],
        "percent_complete": round((progress["completed"] + progress["failed"]) / progress["total"] * 100, 1) if progress["total"] > 0 else 0,
        "results": progress["results"][-10:] if not progress["in_progress"] else [],  # Only show results when done
        "error": progress.get("error")
    }


@app.get("/appearances/pending-analysis")
@limiter.limit(get_rate_limit("officers_list"))
def get_pending_analysis(
    request: Request,
    limit: int = 50,
    officer_id: int = None,
    protest_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Get officer appearances that haven't been analyzed yet.
    Useful for batch analysis selection.
    """
    from sqlalchemy import func

    # Find appearances with images but no uniform analysis
    query = (
        db.query(
            models.OfficerAppearance.id,
            models.OfficerAppearance.officer_id,
            models.OfficerAppearance.media_id,
            models.OfficerAppearance.image_crop_path,
            models.Officer.badge_number,
            models.Officer.force
        )
        .join(models.Officer)
        .outerjoin(models.UniformAnalysis)
        .filter(
            models.OfficerAppearance.image_crop_path.isnot(None),
            models.UniformAnalysis.id.is_(None)
        )
    )

    if officer_id:
        query = query.filter(models.OfficerAppearance.officer_id == officer_id)

    if protest_id:
        query = query.join(models.Media).filter(models.Media.protest_id == protest_id)

    pending = query.limit(limit).all()

    return {
        "pending_count": len(pending),
        "appearances": [
            {
                "id": p.id,
                "officer_id": p.officer_id,
                "media_id": p.media_id,
                "badge_number": p.badge_number,
                "current_force": p.force,
                "has_image": bool(p.image_crop_path)
            }
            for p in pending
        ]
    }


@app.get("/stats/forces")
@limiter.limit(get_rate_limit("officers_list"))
def get_force_statistics(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get statistics on detected police forces from uniform analysis.
    """
    from sqlalchemy import func

    # Force counts from UniformAnalysis
    force_stats = (
        db.query(
            models.UniformAnalysis.detected_force,
            func.count(models.UniformAnalysis.id).label('count'),
            func.avg(models.UniformAnalysis.force_confidence).label('avg_confidence')
        )
        .filter(models.UniformAnalysis.detected_force.isnot(None))
        .group_by(models.UniformAnalysis.detected_force)
        .order_by(func.count(models.UniformAnalysis.id).desc())
        .all()
    )

    # Unit type counts
    unit_stats = (
        db.query(
            models.UniformAnalysis.unit_type,
            func.count(models.UniformAnalysis.id).label('count'),
            func.avg(models.UniformAnalysis.unit_confidence).label('avg_confidence')
        )
        .filter(models.UniformAnalysis.unit_type.isnot(None))
        .group_by(models.UniformAnalysis.unit_type)
        .order_by(func.count(models.UniformAnalysis.id).desc())
        .all()
    )

    # Rank distribution
    rank_stats = (
        db.query(
            models.UniformAnalysis.detected_rank,
            func.count(models.UniformAnalysis.id).label('count')
        )
        .filter(models.UniformAnalysis.detected_rank.isnot(None))
        .group_by(models.UniformAnalysis.detected_rank)
        .order_by(func.count(models.UniformAnalysis.id).desc())
        .all()
    )

    # Total analyses
    total_analyses = db.query(models.UniformAnalysis).count()
    total_with_force = db.query(models.UniformAnalysis).filter(
        models.UniformAnalysis.detected_force.isnot(None)
    ).count()

    return {
        "total_analyses": total_analyses,
        "analyses_with_force": total_with_force,
        "forces": [
            {
                "force": f[0],
                "count": f[1],
                "avg_confidence": round(f[2], 2) if f[2] else None
            }
            for f in force_stats
        ],
        "units": [
            {
                "unit": u[0],
                "count": u[1],
                "avg_confidence": round(u[2], 2) if u[2] else None
            }
            for u in unit_stats
        ],
        "ranks": [
            {"rank": r[0], "count": r[1]}
            for r in rank_stats
        ]
    }


@app.get("/stats/equipment-correlation")
@limiter.limit(get_rate_limit("officers_list"))
def get_equipment_correlation(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Analyze equipment combinations to detect escalation patterns.
    Identifies which equipment items commonly appear together.
    """
    from sqlalchemy import func, text
    from collections import defaultdict
    import itertools

    # Define escalation indicators
    ESCALATION_EQUIPMENT = {
        'high': ['Shield', 'Long Shield', 'Round Shield', 'Baton', 'Taser', 'Ballistic Helmet'],
        'medium': ['Helmet', 'Body Armor', 'Public Order Vest', 'Handcuffs'],
        'monitoring': ['Body Camera', 'Radio', 'Earpiece']
    }

    # Get all equipment detections with appearance context
    detections = (
        db.query(
            models.EquipmentDetection.appearance_id,
            models.Equipment.name,
            models.Equipment.category,
            models.OfficerAppearance.media_id,
            models.Media.protest_id
        )
        .join(models.Equipment)
        .join(models.OfficerAppearance, models.EquipmentDetection.appearance_id == models.OfficerAppearance.id)
        .join(models.Media)
        .all()
    )

    if not detections:
        return {
            "total_detections": 0,
            "equipment_counts": [],
            "co_occurrences": [],
            "escalation_events": [],
            "category_distribution": {}
        }

    # Group equipment by appearance
    appearance_equipment = defaultdict(set)
    for det in detections:
        appearance_equipment[det.appearance_id].add(det.name)

    # Calculate co-occurrences (which items appear together)
    co_occurrence_counts = defaultdict(int)
    for app_id, equipment_set in appearance_equipment.items():
        if len(equipment_set) >= 2:
            for combo in itertools.combinations(sorted(equipment_set), 2):
                co_occurrence_counts[combo] += 1

    # Sort co-occurrences by frequency
    co_occurrences = [
        {"item1": combo[0], "item2": combo[1], "count": count}
        for combo, count in sorted(co_occurrence_counts.items(), key=lambda x: -x[1])[:20]
    ]

    # Count total equipment by type
    equipment_counts = (
        db.query(
            models.Equipment.name,
            models.Equipment.category,
            func.count(models.EquipmentDetection.id).label('count')
        )
        .join(models.EquipmentDetection)
        .group_by(models.Equipment.name, models.Equipment.category)
        .order_by(func.count(models.EquipmentDetection.id).desc())
        .all()
    )

    # Calculate escalation scores per protest
    protest_equipment = defaultdict(lambda: {'equipment': set(), 'media_ids': set()})
    for det in detections:
        if det.protest_id:
            protest_equipment[det.protest_id]['equipment'].add(det.name)
            protest_equipment[det.protest_id]['media_ids'].add(det.media_id)

    escalation_events = []
    for protest_id, data in protest_equipment.items():
        equipment = data['equipment']
        high_count = sum(1 for e in equipment if e in ESCALATION_EQUIPMENT['high'])
        medium_count = sum(1 for e in equipment if e in ESCALATION_EQUIPMENT['medium'])

        escalation_score = (high_count * 3) + (medium_count * 1)

        if escalation_score > 0:
            # Get protest info
            protest = db.query(models.Protest).filter(models.Protest.id == protest_id).first()
            escalation_events.append({
                "protest_id": protest_id,
                "protest_name": protest.name if protest else f"Protest #{protest_id}",
                "date": protest.date.isoformat() if protest and protest.date else None,
                "escalation_score": escalation_score,
                "high_risk_equipment": [e for e in equipment if e in ESCALATION_EQUIPMENT['high']],
                "medium_risk_equipment": [e for e in equipment if e in ESCALATION_EQUIPMENT['medium']],
                "total_equipment_types": len(equipment),
                "media_count": len(data['media_ids'])
            })

    # Sort by escalation score
    escalation_events.sort(key=lambda x: -x['escalation_score'])

    # Category distribution
    category_counts = defaultdict(int)
    for det in detections:
        category_counts[det.category] += 1

    return {
        "total_detections": len(detections),
        "equipment_counts": [
            {"name": e[0], "category": e[1], "count": e[2]}
            for e in equipment_counts
        ],
        "co_occurrences": co_occurrences,
        "escalation_events": escalation_events[:15],
        "category_distribution": dict(category_counts),
        "escalation_indicators": ESCALATION_EQUIPMENT
    }


@app.get("/stats/geographic")
@limiter.limit(get_rate_limit("officers_list"))
def get_geographic_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get geographic clustering data for protests and officers.
    Returns protest locations with officer counts and patterns.
    """
    from sqlalchemy import func, distinct

    # Get all protests with coordinates
    protests = db.query(models.Protest).filter(
        models.Protest.latitude.isnot(None),
        models.Protest.longitude.isnot(None)
    ).all()

    protest_data = []
    for protest in protests:
        # Count officers at this protest
        officer_count = (
            db.query(distinct(models.OfficerAppearance.officer_id))
            .join(models.Media)
            .filter(models.Media.protest_id == protest.id)
            .count()
        )

        # Count media items
        media_count = db.query(models.Media).filter(
            models.Media.protest_id == protest.id
        ).count()

        # Get force breakdown
        force_breakdown = (
            db.query(
                models.Officer.force,
                func.count(distinct(models.Officer.id)).label('count')
            )
            .join(models.OfficerAppearance)
            .join(models.Media)
            .filter(models.Media.protest_id == protest.id)
            .filter(models.Officer.force.isnot(None))
            .group_by(models.Officer.force)
            .all()
        )

        protest_data.append({
            "id": protest.id,
            "name": protest.name,
            "date": protest.date.isoformat() if protest.date else None,
            "location": protest.location,
            "latitude": float(protest.latitude) if protest.latitude else None,
            "longitude": float(protest.longitude) if protest.longitude else None,
            "officer_count": officer_count,
            "media_count": media_count,
            "forces": [{"force": f[0], "count": f[1]} for f in force_breakdown]
        })

    # Get officers who appear at multiple locations
    multi_location_officers = (
        db.query(
            models.Officer.id,
            models.Officer.badge_number,
            models.Officer.force,
            func.count(distinct(models.Media.protest_id)).label('protest_count')
        )
        .join(models.OfficerAppearance)
        .join(models.Media)
        .group_by(models.Officer.id, models.Officer.badge_number, models.Officer.force)
        .having(func.count(distinct(models.Media.protest_id)) >= 2)
        .order_by(func.count(distinct(models.Media.protest_id)).desc())
        .limit(20)
        .all()
    )

    # For each multi-location officer, get their protest locations
    officer_movements = []
    for officer in multi_location_officers:
        protests_visited = (
            db.query(
                models.Protest.id,
                models.Protest.name,
                models.Protest.date,
                models.Protest.latitude,
                models.Protest.longitude
            )
            .join(models.Media)
            .join(models.OfficerAppearance)
            .filter(models.OfficerAppearance.officer_id == officer.id)
            .filter(models.Protest.latitude.isnot(None))
            .distinct()
            .order_by(models.Protest.date)
            .all()
        )

        if len(protests_visited) >= 2:
            officer_movements.append({
                "officer_id": officer.id,
                "badge_number": officer.badge_number,
                "force": officer.force,
                "protest_count": officer.protest_count,
                "locations": [
                    {
                        "protest_id": p.id,
                        "name": p.name,
                        "date": p.date.isoformat() if p.date else None,
                        "latitude": float(p.latitude) if p.latitude else None,
                        "longitude": float(p.longitude) if p.longitude else None
                    }
                    for p in protests_visited
                ]
            })

    return {
        "protests": protest_data,
        "officer_movements": officer_movements,
        "total_protests_with_coords": len(protest_data),
        "total_multi_location_officers": len(officer_movements)
    }


# =============================================================================
# DUPLICATE DETECTION ENDPOINTS
# =============================================================================

@app.get("/duplicates")
@limiter.limit(get_rate_limit("officers_list"))
def get_duplicates(
    request: Request,
    include_resolved: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all duplicate media entries.
    """
    from sqlalchemy import func

    query = db.query(models.Media).filter(
        models.Media.is_duplicate == True  # noqa: E712
    )

    if not include_resolved:
        # Only show unresolved duplicates (not manually reviewed)
        pass  # For now, show all duplicates

    duplicates = query.order_by(models.Media.timestamp.desc()).all()

    result = []
    for dup in duplicates:
        original = db.query(models.Media).filter(
            models.Media.id == dup.duplicate_of_id
        ).first()

        result.append({
            "id": dup.id,
            "url": dup.url,
            "type": dup.type,
            "file_size": dup.file_size,
            "content_hash": dup.content_hash,
            "perceptual_hash": dup.perceptual_hash,
            "uploaded_at": dup.timestamp.isoformat() if dup.timestamp else None,
            "original_id": dup.duplicate_of_id,
            "original_url": original.url if original else None
        })

    return {
        "duplicates": result,
        "total": len(result)
    }


@app.get("/duplicates/scan")
@limiter.limit(get_rate_limit("ai_analysis"))
def scan_for_duplicates(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Scan database for duplicate groups based on content hash.
    Returns groups of media that are exact duplicates.
    """
    from ai.duplicate_detector import DuplicateDetector

    detector = DuplicateDetector(db)
    groups = detector.find_all_duplicates()

    return {
        "duplicate_groups": groups,
        "total_groups": len(groups)
    }


@app.post("/duplicates/backfill")
@limiter.limit(get_rate_limit("ai_analysis"))
def backfill_hashes(
    request: Request,
    batch_size: int = 100,
    db: Session = Depends(get_db)
):
    """
    Backfill content/perceptual hashes for existing media without hashes.
    Useful after upgrading to add duplicate detection.
    """
    from ai.duplicate_detector import DuplicateDetector

    detector = DuplicateDetector(db)
    stats = detector.backfill_hashes(batch_size)

    # Count remaining media without hashes
    remaining = db.query(models.Media).filter(
        models.Media.content_hash.is_(None)
    ).count()

    return {
        "status": "completed",
        "processed": stats["processed"],
        "success": stats["success"],
        "failed": stats["failed"],
        "remaining": remaining
    }


@app.delete("/duplicates/{media_id}")
@limiter.limit(get_rate_limit("officers_detail"))
def delete_duplicate(
    request: Request,
    media_id: int,
    keep_file: bool = False,
    db: Session = Depends(get_db)
):
    """
    Delete a duplicate media entry.
    By default also deletes the file from disk.
    """
    import os

    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if not media.is_duplicate:
        raise HTTPException(
            status_code=400,
            detail="This media is not marked as a duplicate. Use /media/{id} endpoint to delete."
        )

    file_deleted = False
    if not keep_file and media.url and os.path.exists(media.url):
        try:
            os.remove(media.url)
            file_deleted = True
        except Exception as e:
            print(f"Warning: Could not delete file {media.url}: {e}")

    db.delete(media)
    db.commit()

    return {
        "status": "deleted",
        "media_id": media_id,
        "file_deleted": file_deleted
    }


# =============================================================================
# FILE CLEANUP ENDPOINTS
# =============================================================================

@app.get("/admin/cleanup/preview")
@limiter.limit(get_rate_limit("ai_analysis"))
def preview_cleanup(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Preview what files would be cleaned up.
    Returns stats without deleting anything.
    """
    from cleanup import run_cleanup

    stats = run_cleanup(dry_run=True, verbose=False)
    return stats.summary()


@app.post("/admin/cleanup/execute")
@limiter.limit(get_rate_limit("ai_analysis"))
def execute_cleanup(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Execute file cleanup.
    Deletes orphaned files, temp files, and old cache.
    """
    from cleanup import run_cleanup

    stats = run_cleanup(dry_run=False, verbose=False)
    summary = stats.summary()

    return {
        "status": "completed",
        **summary
    }

