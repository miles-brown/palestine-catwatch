from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas
from database import get_db, engine
from datetime import datetime, timezone
import asyncio
import os

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
            # Token revocation support
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 0",
            # Account lockout fields
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMP",
            # Duplicate detection fields for media
            "ALTER TABLE media ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)",
            "ALTER TABLE media ADD COLUMN IF NOT EXISTS perceptual_hash VARCHAR(64)",
            "ALTER TABLE media ADD COLUMN IF NOT EXISTS file_size INTEGER",
            "ALTER TABLE media ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE",
            "ALTER TABLE media ADD COLUMN IF NOT EXISTS duplicate_of_id INTEGER REFERENCES media(id)",
            # Enhanced protest fields
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS city VARCHAR",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS country VARCHAR DEFAULT 'United Kingdom'",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS organizer VARCHAR",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS estimated_attendance INTEGER",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS police_force VARCHAR",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS event_type VARCHAR",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'documented'",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
            "ALTER TABLE protests ADD COLUMN IF NOT EXISTS cover_image_url VARCHAR",
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
# CONFIGURATION CONSTANTS
# =============================================================================
MAX_URL_LENGTH = 2048
MIN_URL_LENGTH = 10  # Minimum realistic URL length (e.g., "http://a.co")
MAX_PAGINATION_LIMIT = 500
DEFAULT_PAGINATION_LIMIT = 100

# Allowed URL schemes (security: prevent file://, ftp://, etc.)
ALLOWED_URL_SCHEMES = {'http', 'https'}


def validate_single_url(v):
    """Validate a single URL."""
    # Basic URL validation
    if not v or not isinstance(v, str):
        raise ValueError('URL is required')

    v = v.strip()

    # Check minimum URL length
    if len(v) < MIN_URL_LENGTH:
        raise ValueError(f'URL too short (min {MIN_URL_LENGTH} characters)')

    # Check URL length (#19)
    if len(v) > MAX_URL_LENGTH:
        raise ValueError(f'URL too long (max {MAX_URL_LENGTH} characters)')

    # Parse and validate structure
    try:
        parsed = urlparse(v)

        # Validate scheme (security: only allow http/https)
        if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
            raise ValueError(f'URL scheme must be http or https, got: {parsed.scheme}')

        if not parsed.netloc:
            raise ValueError('Invalid URL: no domain found')

        # Check for suspicious patterns (path traversal, etc.)
        suspicious_patterns = ['../', '..\\', '<script', 'javascript:', 'data:']
        for pattern in suspicious_patterns:
            if pattern.lower() in v.lower():
                raise ValueError(f'URL contains suspicious pattern: {pattern}')

        # Basic domain validation (must have at least one dot for TLD)
        if '.' not in parsed.netloc:
            raise ValueError('Invalid domain in URL')

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f'Invalid URL format: {str(e)}')

    return v


app = FastAPI(title="Palestine Catwatch API")

# HTTPS enforcement in production
_environment = os.getenv("ENVIRONMENT", "development").lower()
if _environment in ("production", "prod"):
    app.add_middleware(HTTPSRedirectMiddleware)

# Setup rate limiting
setup_rate_limiting(app)

# Setup standardized error handling
from errors import setup_error_handlers, APIError, ErrorCode
setup_error_handlers(app)

# Configure CORS
# Note: When allow_credentials=True, allow_origins cannot be ["*"]
# The browser requires explicit origins for credentialed requests
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
_allowed_origins = [o.strip() for o in _allowed_origins if o.strip()]
# Default origins for development and production
if not _allowed_origins:
    _allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://palestine-catwatch.vercel.app",
        "https://www.palestine-catwatch.vercel.app",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
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


@app.get("/config/storage")
def get_storage_config():
    """
    Get storage configuration for the frontend.
    Returns the R2 public URL if configured, otherwise null.
    """
    from utils.r2_storage import R2_ENABLED, R2_PUBLIC_URL
    return {
        "r2_enabled": R2_ENABLED,
        "r2_public_url": R2_PUBLIC_URL if R2_ENABLED else None,
    }

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
    db: Session = Depends(get_db)
):
    """Get total count of officers (efficient for pagination)."""
    query = db.query(models.Officer)

    if badge_number:
        query = query.filter(models.Officer.badge_number.contains(badge_number))
    if force:
        query = query.filter(models.Officer.force == force)

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
            "crop_path": first_app.image_crop_path if first_app else None
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
                "crop_path": first_app.image_crop_path if first_app else None
            })

    return {
        "officer_id": officer_id,
        "connections": connections,
        "total_shared_media": len(media_ids)
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
                        "crop_path": app.image_crop_path,
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
                        "crop_path": app.image_crop_path
                    })

            officers.append({
                "id": officer.id,
                "badge": officer.badge_number,
                "force": officer.force,
                "role": first_app.role if first_app else None,
                "crop_path": first_app.image_crop_path if first_app else None,
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
    task_id = f"task_{int(datetime.now(timezone.utc).timestamp())}"

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
@limiter.limit("2/minute")  # Stricter limit for bulk operations
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
        task_id = f"task_{int(datetime.now(timezone.utc).timestamp())}_{hash(url) % 10000}"
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
def get_protests(
    request: Request,
    city: Optional[str] = None,
    country: Optional[str] = None,
    event_type: Optional[str] = None,
    sort_by: str = "date",  # date, city, name, attendance
    sort_order: str = "desc",  # asc, desc
    limit: int = DEFAULT_PAGINATION_LIMIT,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get all protests with optional filtering and sorting.
    Returns protests with computed statistics (media count, officer count).
    """
    from sqlalchemy import func, desc, asc

    query = db.query(models.Protest)

    # Apply filters
    if city:
        query = query.filter(models.Protest.city.ilike(f"%{city}%"))
    if country:
        query = query.filter(models.Protest.country.ilike(f"%{country}%"))
    if event_type:
        query = query.filter(models.Protest.event_type == event_type)

    # Get total count before pagination
    total_count = query.count()

    # Apply sorting
    sort_column = {
        "date": models.Protest.date,
        "city": models.Protest.city,
        "name": models.Protest.name,
        "attendance": models.Protest.estimated_attendance,
        "created_at": models.Protest.created_at,
    }.get(sort_by, models.Protest.date)

    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    protests = query.offset(offset).limit(min(limit, MAX_PAGINATION_LIMIT)).all()

    # Compute statistics for each protest
    results = []
    for protest in protests:
        media_count = db.query(models.Media).filter(models.Media.protest_id == protest.id).count()

        # Count officers from appearances in this protest's media
        officer_count = db.query(func.count(func.distinct(models.OfficerAppearance.officer_id))).join(
            models.Media, models.OfficerAppearance.media_id == models.Media.id
        ).filter(models.Media.protest_id == protest.id).scalar() or 0

        # Count verified appearances
        verified_count = db.query(models.OfficerAppearance).join(
            models.Media, models.OfficerAppearance.media_id == models.Media.id
        ).filter(
            models.Media.protest_id == protest.id,
            models.OfficerAppearance.verified == True
        ).count()

        results.append({
            "id": protest.id,
            "name": protest.name,
            "date": protest.date.isoformat() if protest.date else None,
            "location": protest.location,
            "city": protest.city,
            "country": protest.country,
            "latitude": protest.latitude,
            "longitude": protest.longitude,
            "description": protest.description,
            "organizer": protest.organizer,
            "estimated_attendance": protest.estimated_attendance,
            "police_force": protest.police_force,
            "event_type": protest.event_type,
            "status": protest.status,
            "cover_image_url": protest.cover_image_url,
            "created_at": protest.created_at.isoformat() if protest.created_at else None,
            "updated_at": protest.updated_at.isoformat() if protest.updated_at else None,
            "media_count": media_count,
            "officer_count": officer_count,
            "verified_count": verified_count,
        })

    # Get unique cities and event types for filters
    cities = db.query(models.Protest.city).filter(models.Protest.city.isnot(None)).distinct().all()
    event_types = db.query(models.Protest.event_type).filter(models.Protest.event_type.isnot(None)).distinct().all()

    return {
        "protests": results,
        "total": total_count,
        "cities": [c[0] for c in cities if c[0]],
        "event_types": [e[0] for e in event_types if e[0]],
    }


@app.get("/protests/{protest_id}")
@limiter.limit(get_rate_limit("default"))
def get_protest(request: Request, protest_id: int, db: Session = Depends(get_db)):
    """Get a single protest by ID with full details."""
    from sqlalchemy import func

    protest = db.query(models.Protest).filter(models.Protest.id == protest_id).first()
    if not protest:
        raise HTTPException(status_code=404, detail="Protest not found")

    # Get media for this protest
    media_items = db.query(models.Media).filter(models.Media.protest_id == protest_id).all()

    # Get officers documented at this protest
    officers = db.query(models.Officer).join(
        models.OfficerAppearance, models.Officer.id == models.OfficerAppearance.officer_id
    ).join(
        models.Media, models.OfficerAppearance.media_id == models.Media.id
    ).filter(models.Media.protest_id == protest_id).distinct().all()

    return {
        "id": protest.id,
        "name": protest.name,
        "date": protest.date.isoformat() if protest.date else None,
        "location": protest.location,
        "city": protest.city,
        "country": protest.country,
        "latitude": protest.latitude,
        "longitude": protest.longitude,
        "description": protest.description,
        "organizer": protest.organizer,
        "estimated_attendance": protest.estimated_attendance,
        "police_force": protest.police_force,
        "event_type": protest.event_type,
        "status": protest.status,
        "cover_image_url": protest.cover_image_url,
        "created_at": protest.created_at.isoformat() if protest.created_at else None,
        "updated_at": protest.updated_at.isoformat() if protest.updated_at else None,
        "media": [
            {
                "id": m.id,
                "url": get_web_url(m.url),
                "type": m.type,
                "processed": m.processed,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in media_items
        ],
        "officers": [
            {
                "id": o.id,
                "badge_number": o.badge_number,
                "force": o.force,
                "rank": o.rank,
            }
            for o in officers
        ],
        "media_count": len(media_items),
        "officer_count": len(officers),
    }


@app.post("/protests")
@limiter.limit(get_rate_limit("default"))
def create_protest(
    request: Request,
    protest_data: schemas.ProtestCreate,
    db: Session = Depends(get_db)
):
    """Create a new protest."""
    protest = models.Protest(
        name=protest_data.name,
        date=protest_data.date,
        location=protest_data.location,
        city=protest_data.city,
        country=protest_data.country or "United Kingdom",
        latitude=protest_data.latitude,
        longitude=protest_data.longitude,
        description=protest_data.description,
        organizer=protest_data.organizer,
        estimated_attendance=protest_data.estimated_attendance,
        police_force=protest_data.police_force,
        event_type=protest_data.event_type,
        cover_image_url=protest_data.cover_image_url,
    )
    db.add(protest)
    db.commit()
    db.refresh(protest)

    log_audit("protest_created", {"protest_id": protest.id, "name": protest.name})

    return {
        "id": protest.id,
        "name": protest.name,
        "message": "Protest created successfully"
    }


@app.patch("/protests/{protest_id}")
@limiter.limit(get_rate_limit("default"))
def update_protest(
    request: Request,
    protest_id: int,
    protest_data: schemas.ProtestUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing protest."""
    protest = db.query(models.Protest).filter(models.Protest.id == protest_id).first()
    if not protest:
        raise HTTPException(status_code=404, detail="Protest not found")

    # Update only provided fields
    update_data = protest_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(protest, field, value)

    db.commit()
    db.refresh(protest)

    log_audit("protest_updated", {"protest_id": protest.id})

    return {"message": "Protest updated successfully", "id": protest.id}


@app.delete("/protests/{protest_id}")
@limiter.limit(get_rate_limit("default"))
def delete_protest(request: Request, protest_id: int, db: Session = Depends(get_db)):
    """Delete a protest and all associated media."""
    protest = db.query(models.Protest).filter(models.Protest.id == protest_id).first()
    if not protest:
        raise HTTPException(status_code=404, detail="Protest not found")

    # Delete associated media first (cascading would handle this but being explicit)
    db.query(models.Media).filter(models.Media.protest_id == protest_id).delete()
    db.delete(protest)
    db.commit()

    log_audit("protest_deleted", {"protest_id": protest_id})

    return {"message": "Protest deleted successfully"}

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
            "image_crop_path": app.image_crop_path,
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
@limiter.limit(get_rate_limit("upload"))
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
                        "crop_path": first_app.image_crop_path if first_app else None
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

    media = save_upload(file.file, file.filename, protest_id, type, db)
    
    if not media:
        raise HTTPException(status_code=500, detail="File upload failed")
        
    # Trigger processing
    from process import process_media
    process_media(media.id)
    
    return {"status": "uploaded", "media_id": media.id, "filename": file.filename}


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
            "crop_path": appearance.image_crop_path if appearance else None,
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
                "crop_path": app.image_crop_path,
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
@limiter.limit("5/minute")  # Strict limit due to API costs
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

    # Get full image path
    image_path = os.path.join("data", appearance.image_crop_path.lstrip("/data/"))
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


# =============================================================================
# CSRF PROTECTION
# =============================================================================

from csrf import generate_csrf_token, set_csrf_cookie, require_csrf, CSRF_ENABLED


@app.get("/csrf/token")
@limiter.limit("30/minute")
def get_csrf_token(request: Request, response: Response):
    """
    Get a CSRF token for protected form submissions.

    The token is returned in both:
    1. Response body (for SPA to read)
    2. Cookie (for double-submit validation)

    Frontend should include this token in X-CSRF-Token header
    when making protected requests (registration, etc.).
    """
    token = generate_csrf_token()
    set_csrf_cookie(response, token)

    return {
        "csrf_token": token,
        "expires_in": 24 * 3600,  # 24 hours in seconds
        "header_name": "X-CSRF-Token"
    }


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

from auth import (
    UserCreate, UserLogin, UserResponse, Token,
    create_user, authenticate_user, create_access_token, create_refresh_token,
    decode_refresh_token, get_user_by_username, get_user_by_email, verify_user_email,
    AuthenticationError, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
    log_security_event, revoke_user_tokens, get_current_user, require_admin
)
from email_service import send_verification_email, is_email_enabled
from datetime import timedelta


# Environment variable to control email verification requirement
# Set to "false" in development to skip email verification
REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").lower() == "true"


@app.post("/auth/register")
@limiter.limit(get_rate_limit("auth_register"))
@limiter.limit(get_rate_limit("auth_register_hourly"))
async def register_user(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    _csrf = Depends(require_csrf)  # CSRF protection for registration
):
    """
    Register a new user account.

    Rate limited to prevent registration spam and abuse.

    Email verification behavior controlled by REQUIRE_EMAIL_VERIFICATION env var:
    - true (default): User must verify email before logging in
    - false: User is immediately active (for development)

    In development mode, returns verification_token for testing.
    """
    # Verify Turnstile token
    from turnstile import verify_turnstile_token, TURNSTILE_ENABLED
    if TURNSTILE_ENABLED:
        client_ip = request.client.host if request.client else None
        turnstile_result = await verify_turnstile_token(user_data.turnstile_token, client_ip)
        if not turnstile_result.get("success"):
            raise APIError(
                code=ErrorCode.INVALID_INPUT,
                message=turnstile_result.get("error", "Security verification failed"),
                status_code=400
            )

    # Check if username already exists
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise APIError(
            code=ErrorCode.ALREADY_EXISTS,
            message="Username already registered",
            status_code=400
        )

    # Check if email already exists
    existing_email = get_user_by_email(db, user_data.email)
    if existing_email:
        raise APIError(
            code=ErrorCode.ALREADY_EXISTS,
            message="Email already registered",
            status_code=400
        )

    # Create user - verification requirement based on environment
    user = create_user(db, user_data, require_verification=REQUIRE_EMAIL_VERIFICATION)

    # Build response
    response = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "full_name": user.full_name,
        "city": user.city,
        "country": user.country,
        "email_verified": user.email_verified,
        "verification_required": REQUIRE_EMAIL_VERIFICATION,
        "message": "Registration successful!"
    }

    # Only return verification token in development mode (security: prevents token exposure in logs)
    is_development = os.getenv("ENVIRONMENT", "development").lower() in ("development", "dev")
    if REQUIRE_EMAIL_VERIFICATION:
        response["message"] = "Registration successful! Please check your email to verify your account."

        # Send verification email
        if user.email_verification_token:
            email_sent = send_verification_email(
                to_email=user.email,
                username=user.username,
                token=user.email_verification_token
            )
            response["email_sent"] = email_sent

            if not email_sent and is_development:
                # In dev mode without email, expose token for testing
                response["verification_token"] = user.email_verification_token
                response["message"] = "Registration successful! Email sending not configured - use the token below to verify."
    else:
        response["message"] = "Registration successful! You can now log in."

    return response


@app.post("/auth/login", response_model=Token)
@limiter.limit(get_rate_limit("auth_login"))
@limiter.limit(get_rate_limit("auth_login_hourly"))
async def login(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT access and refresh tokens.

    Rate limited to prevent brute force attacks:
    - 5 attempts per minute
    - 20 attempts per hour

    Returns specific error codes for different failure reasons.
    Account is locked after 5 failed attempts for 15 minutes.
    """
    # Get client IP for security logging
    client_ip = request.client.host if request.client else None

    # Verify Turnstile token
    from turnstile import verify_turnstile_token, TURNSTILE_ENABLED
    if TURNSTILE_ENABLED:
        turnstile_result = await verify_turnstile_token(login_data.turnstile_token, client_ip)
        if not turnstile_result.get("success"):
            raise APIError(
                code=ErrorCode.INVALID_INPUT,
                message=turnstile_result.get("error", "Security verification failed"),
                status_code=400
            )

    try:
        user = authenticate_user(
            db,
            login_data.username,
            login_data.password,
            require_verified_email=REQUIRE_EMAIL_VERIFICATION,
            ip_address=client_ip
        )
    except AuthenticationError as e:
        # Map error codes to standardized API errors
        error_map = {
            "invalid_credentials": (ErrorCode.INVALID_CREDENTIALS, 401),
            "email_not_verified": (ErrorCode.EMAIL_NOT_VERIFIED, 403),
            "account_disabled": (ErrorCode.ACCOUNT_DISABLED, 403),
            "account_locked": (ErrorCode.ACCOUNT_LOCKED, 429),
        }

        error_info = error_map.get(e.code, (ErrorCode.UNAUTHORIZED, 401))
        raise APIError(
            code=error_info[0],
            message=e.message,
            status_code=error_info[1],
            headers={"WWW-Authenticate": "Bearer"} if error_info[1] == 401 else None
        )

    # Update last login timestamp (use timezone-aware datetime)
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Token payload (include token_version for revocation support)
    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "token_version": user.token_version or 0
    }

    # Create access token (short-lived: 30 minutes)
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Create refresh token (long-lived: 7 days)
    refresh_token = create_refresh_token(data=token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name
        }
    )


@app.get("/auth/verify-email/{token}")
@limiter.limit(get_rate_limit("auth_verify"))
def verify_email(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verify user email address using the verification token.
    """
    user = verify_user_email(db, token)

    if not user:
        raise APIError(
            code=ErrorCode.TOKEN_INVALID,
            message="Invalid or expired verification token",
            status_code=400
        )

    return {
        "success": True,
        "message": "Email verified successfully. You can now log in.",
        "username": user.username
    }


@app.post("/auth/verify-by-email")
@limiter.limit(get_rate_limit("auth_verify"))
def verify_by_email_address(
    request: Request,
    email: str = Form(...),
    admin_key: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Emergency endpoint to verify a user by email address.
    Requires admin key for security.
    """
    import models
    expected_key = os.getenv("ADMIN_VERIFY_KEY", "")
    if not expected_key or admin_key != expected_key:
        raise APIError(
            code=ErrorCode.FORBIDDEN,
            message="Invalid admin key",
            status_code=403
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise APIError(
            code=ErrorCode.NOT_FOUND,
            message="User not found",
            status_code=404
        )

    user.email_verified = True
    user.is_active = True
    user.email_verification_token = None
    db.commit()

    return {
        "success": True,
        "message": f"User {user.username} verified successfully",
        "username": user.username
    }


@app.get("/auth/me", response_model=UserResponse)
@limiter.limit(get_rate_limit("default"))
def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's information.
    Requires valid JWT token in Authorization header.
    """
    from auth import get_current_user
    from fastapi import Security

    # This endpoint requires manual token validation since we can't use Depends easily here
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise APIError(
            code=ErrorCode.UNAUTHORIZED,
            message="Not authenticated",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth_header.split(" ")[1]
    from auth import decode_token, get_user_by_username as get_user

    token_data = decode_token(token)
    if not token_data:
        raise APIError(
            code=ErrorCode.TOKEN_INVALID,
            message="Invalid token",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = get_user(db, token_data.username)
    if not user:
        raise APIError(
            code=ErrorCode.NOT_FOUND,
            message="User not found",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        full_name=user.full_name,
        city=user.city,
        country=user.country,
        email_verified=user.email_verified
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@app.post("/auth/refresh")
@limiter.limit("30/minute")  # Generous limit for token refresh
def refresh_access_token(
    request: Request,
    body: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Exchange a valid refresh token for a new access token.

    This allows clients to maintain sessions without re-authenticating.
    Access tokens expire in 30 minutes, refresh tokens in 7 days.
    """
    client_ip = request.client.host if request.client else None

    token_data = decode_refresh_token(body.refresh_token)
    if not token_data:
        raise APIError(
            code=ErrorCode.TOKEN_INVALID,
            message="Invalid or expired refresh token",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verify user still exists and is active
    user = get_user_by_username(db, token_data.username)
    if not user:
        raise APIError(
            code=ErrorCode.NOT_FOUND,
            message="User not found",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise APIError(
            code=ErrorCode.ACCOUNT_DISABLED,
            message="Account is disabled",
            status_code=403
        )

    # Validate token version for revocation support
    user_token_version = user.token_version or 0
    token_version = token_data.token_version or 0
    if token_version < user_token_version:
        # Refresh token was issued before tokens were revoked
        raise APIError(
            code=ErrorCode.TOKEN_REVOKED,
            message="Token has been revoked. Please log in again.",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Log the token refresh
    log_security_event(
        "TOKEN_REFRESH",
        username=user.username,
        user_id=user.id,
        ip_address=client_ip
    )

    # Create new access token (include current token_version)
    new_token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "token_version": user_token_version
    }

    access_token = create_access_token(
        data=new_token_data,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@app.post("/auth/revoke/{user_id}")
@limiter.limit("10/minute")
async def revoke_user_tokens_endpoint(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Revoke all tokens for a specific user (admin only).

    This invalidates all existing access and refresh tokens for the user,
    forcing them to re-authenticate. Useful for:
    - Security incidents
    - Account compromises
    - Admin forcing logout
    """
    from auth import get_user_by_id

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise APIError(
            code=ErrorCode.NOT_FOUND,
            message="User not found",
            status_code=404
        )

    # Prevent revoking own tokens through this endpoint
    if target_user.id == current_user.id:
        raise APIError(
            code=ErrorCode.INVALID_INPUT,
            message="Cannot revoke your own tokens. Use /auth/logout instead.",
            status_code=400
        )

    old_version = target_user.token_version
    revoke_user_tokens(db, target_user)

    # Audit log for security events
    import logging
    audit_logger = logging.getLogger("audit.security")
    audit_logger.warning(
        f"TOKEN_REVOCATION: admin_user_id={current_user.id} "
        f"admin_username={current_user.username} "
        f"target_user_id={user_id} "
        f"target_username={target_user.username} "
        f"old_token_version={old_version} "
        f"new_token_version={target_user.token_version} "
        f"client_ip={request.client.host if request.client else 'unknown'}"
    )

    return {
        "success": True,
        "message": f"All tokens revoked for user {target_user.username}",
        "user_id": user_id,
        "new_token_version": target_user.token_version,
        "revoked_by": current_user.username
    }


@app.post("/auth/logout")
@limiter.limit("10/minute")
async def logout_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Logout the current user by revoking all their tokens.

    This invalidates all access and refresh tokens, requiring re-authentication.
    """
    revoke_user_tokens(db, current_user)

    return {
        "success": True,
        "message": "Logged out successfully. All tokens have been revoked."
    }
