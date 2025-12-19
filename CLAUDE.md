# CLAUDE.md - Project Conventions for Palestine CatWatch

This document defines the coding standards, conventions, and guidelines for the Palestine CatWatch project. Follow these conventions when contributing code.

## Project Overview

Palestine CatWatch is a media analysis platform for documenting police conduct at protests. It uses computer vision (face detection, re-identification) and AI analysis (uniform recognition via Claude Vision API) to catalog officer appearances across media.

## Deployment Infrastructure

### Production Services
| Service | Provider | URL |
|---------|----------|-----|
| Frontend | Vercel | https://palestine-catwatch.vercel.app/ |
| Backend API | Railway | https://palestine-catwatch-production.up.railway.app |
| Database | Neon PostgreSQL | (connection via DATABASE_URL) |
| Image Storage | Cloudflare R2 | (public URL via R2_PUBLIC_URL) |

### Environment Variables for R2 Storage
```bash
R2_ENABLED=true                    # Enable R2 storage (false = local storage)
R2_PUBLIC_URL=https://pub-xxx.r2.dev  # Public bucket URL for serving images
R2_ENDPOINT_URL=                   # R2 API endpoint
R2_ACCESS_KEY_ID=                  # R2 access credentials
R2_SECRET_ACCESS_KEY=              # R2 secret key
R2_BUCKET_NAME=                    # Bucket name
```

### Cross-Service Connections
- **Vercel -> Railway**: Frontend calls API via `VITE_API_BASE` environment variable
- **Railway -> Neon**: Backend connects via `DATABASE_URL` with SSL required
- **Railway -> R2**: Backend uploads images; serves via public R2 URL
- **Railway CORS**: Must include Vercel domain in `ALLOWED_ORIGINS`

## Directory Structure

```
palestine-catwatch/
├── backend/                 # FastAPI backend
│   ├── ai/                  # AI/ML modules (analyzer, duplicate detection, uniform analysis)
│   ├── tests/               # pytest test files
│   ├── utils/               # Utility modules (paths.py, r2_storage.py)
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication & authorization
│   ├── database.py          # Database configuration
│   ├── process.py           # Media processing pipeline
│   ├── ingest_video.py      # Video download with yt-dlp
│   ├── ingest_images.py     # Web scraping for images
│   └── logging_config.py    # Structured logging setup
├── src/                     # React frontend (Vite)
│   ├── components/          # Reusable UI components
│   │   ├── LiveAnalysis.jsx # Real-time processing feed
│   │   ├── OfficerCard.jsx  # Officer display card
│   │   ├── LazyOfficerGrid.jsx # Infinite scroll grid
│   │   └── MergeSuggestionCard.jsx # Officer merge UI
│   ├── pages/               # Page components
│   │   ├── UploadPage.jsx   # URL/file submission
│   │   ├── DashboardPage.jsx # Analytics dashboard
│   │   └── OfficerProfilePage.jsx # Individual officer view
│   └── context/             # React Context providers
├── data/                    # Media storage (gitignored)
│   ├── downloads/           # Downloaded videos/images
│   └── frames/              # Extracted frames and crops
└── alembic/                 # Database migrations
```

## Data Models & Conventions

### Officer Appearance Crop Paths

OfficerAppearance stores three crop types. **Always use priority fallback**:

```python
# Backend: Priority fallback for crop path
crop_path = (
    appearance.face_crop_path or      # 1. Close-up face crop
    appearance.body_crop_path or      # 2. Full body shot (head to toe)
    appearance.image_crop_path        # 3. Legacy field (backwards compat)
)
```

```javascript
// Frontend: Same fallback pattern
const cropPath = appearance?.face_crop_path
    || appearance?.body_crop_path
    || appearance?.image_crop_path;
```

| Field | Purpose | Example |
|-------|---------|---------|
| `face_crop_path` | Close-up face for officer cards | `data/frames/123/face_0.jpg` |
| `body_crop_path` | Full body for evidence/uniform | `data/frames/123/body_0.jpg` |
| `image_crop_path` | Legacy fallback | `data/frames/123/crop_0.jpg` |

### Media Processing Directory Structure

Each media item gets a unique directory based on its database ID:
```
data/frames/{media_id}/
├── frame_0000.jpg          # Source frame (or copied image)
├── face_0.jpg              # Detected face crop
├── body_0.jpg              # Detected body crop
└── ...
```

### URL Handling Pattern

Handle both R2 absolute URLs and relative API paths:

```javascript
// Frontend helper - use in all components displaying images
const getImageUrl = (url) => {
    if (!url) return '';
    // R2 URLs are absolute - use directly
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
    }
    // Relative paths need API base prepended
    return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`;
};
```

```python
# Backend: Use get_file_url() from utils/paths.py
from utils.paths import get_file_url

# Returns R2 public URL if enabled, otherwise local /data/ path
url = get_file_url(appearance.face_crop_path)
```

## Code Style

### Python (Backend)

1. **Formatting**: Follow PEP 8. Use 4 spaces for indentation.

2. **Imports**: Group in order: stdlib, third-party, local. Use absolute imports.
   ```python
   import os
   from datetime import datetime, timezone

   from fastapi import HTTPException
   from sqlalchemy.orm import Session

   import models
   from logging_config import get_logger
   ```

3. **Type Hints**: Required for all function signatures.
   ```python
   def process_media(media_id: int, db: Session) -> Optional[Dict[str, Any]]:
   ```

4. **Docstrings**: Required for all public functions and classes.
   ```python
   def compute_hash(file_path: str) -> Optional[str]:
       """
       Compute SHA256 hash of file content.

       Args:
           file_path: Path to the file

       Returns:
           Hex string of hash, or None if file cannot be read
       """
   ```

5. **Datetime Handling**: Always use timezone-aware datetimes.
   ```python
   # Correct
   from datetime import datetime, timezone
   timestamp = datetime.now(timezone.utc)

   # Wrong - deprecated in Python 3.12+
   timestamp = datetime.utcnow()
   ```

6. **Exception Handling**: Be specific with exception types.
   ```python
   # Correct
   except (OSError, FileNotFoundError) as e:
       logger.error(f"File error: {e}")

   # Avoid - too broad
   except Exception as e:
       pass
   ```

### JavaScript/React (Frontend)

1. **Formatting**: Use Prettier defaults. 2 spaces for indentation.

2. **Components**: Use functional components with hooks.

3. **State Management**: Use React Context for global state.

4. **Image URLs**: Always use the `getImageUrl()` helper for crop paths.

## Video Download System

### yt-dlp Retry Mechanism

Video downloads use a multi-configuration retry system to bypass YouTube restrictions:

```python
# ingest_video.py - Retry configurations tried in order:
retry_configs = [
    {'name': 'iOS/Android clients', 'player_client': ['ios', 'android', 'web']},
    {'name': 'TV embed client', 'player_client': ['tv_embedded', 'mediaconnect']},
    {'name': 'Web client 720p', 'player_client': ['web'], 'format': 'best[height<=720]'},
    {'name': 'mweb client', 'player_client': ['mweb', 'android']},
]
```

### Supported Video Platforms
- YouTube (youtube.com, youtu.be)
- Twitter/X (twitter.com, x.com)
- Instagram, Facebook, TikTok
- Rumble, Bitchute, Odysee
- Twitch, Vimeo, Dailymotion

### URL Routing Logic
```python
# Non-video URLs (news articles) route to image scraper
video_domains = ["youtube.com", "twitter.com", "tiktok.com", ...]
if not any(domain in url for domain in video_domains):
    # Route to scrape_images_from_url()
else:
    # Route to download_video()
```

## Logging

Use structured logging throughout the codebase:

```python
from logging_config import get_logger, log_performance, log_error

logger = get_logger("module_name")

# Standard logging
logger.info("Processing media", extra_data={"media_id": 123})

# Performance metrics
log_performance(logger, "operation_name", duration_ms, success=True, details={...})

# Error logging with context
log_error(logger, exception, context={"media_id": 123})
```

## WebSocket Status Callbacks

Long-running tasks use status callbacks for real-time UI updates:

```python
def process_video_workflow(url, answers, protest_id, status_callback=None):
    if status_callback:
        status_callback("log", "Starting download...")      # Log message
        status_callback("status_update", "Downloading")     # Stage update
        status_callback("scraped_image", {"url": url})      # Image found
        status_callback("candidate_officer", {...})         # Officer detected
        status_callback("media_created", {"media_id": 123}) # DB record created
        status_callback("complete", {"message": "Done"})    # Finished
```

Frontend listens via Socket.IO:
```javascript
socket.on('log', (msg) => addLog('Info', msg));
socket.on('candidate_officer', (data) => setCandidates(prev => [...prev, data]));
socket.on('complete', (data) => setStatus('complete'));
```

## Security Requirements

1. **Input Validation**: Validate all user input. Use Pydantic validators.

2. **Path Traversal**: Always validate file paths are within expected directories.
   ```python
   from cleanup import is_safe_path
   if not is_safe_path(user_provided_path):
       raise HTTPException(400, "Invalid path")
   ```

3. **SQL Injection**: Use parameterized queries (SQLAlchemy handles this).

4. **Secrets**: Never commit secrets. Use environment variables.

5. **CSRF**: Protected by `CSRFProtectionMiddleware` on state-changing endpoints.

6. **Authentication**: JWT-based with refresh tokens. See `auth.py`.

## Testing Requirements

### Test File Naming
- Test files: `tests/test_<module>.py`
- Test functions: `test_<behavior>()` or `test_<class>_<method>()`

### Required Test Coverage

1. **Unit Tests**: All utility functions and core logic
2. **Integration Tests**: API endpoints with database
3. **Security Tests**: Input validation, authentication, authorization

### Running Tests
```bash
cd backend
python3 -m pytest tests/ -v
python3 -m pytest tests/test_specific.py -v  # Single file
```

### Mocking Guidelines
```python
from unittest.mock import Mock, patch

# Mock database sessions
mock_db = Mock()
mock_db.query.return_value.filter.return_value.first.return_value = mock_object

# Mock R2 storage
@patch('utils.r2_storage.R2_ENABLED', True)
@patch('utils.r2_storage.R2_PUBLIC_URL', 'https://test.r2.dev')
def test_r2_urls(self):
    ...
```

## Performance Expectations

1. **API Response Times**:
   - Simple queries: < 100ms
   - Complex queries: < 500ms
   - File uploads: < 5s per file

2. **Memory Usage**:
   - Batch process large datasets (1000 items max per batch)
   - Release resources (VideoCapture, file handles) promptly

3. **Database**:
   - Avoid N+1 queries - use batched queries
   - Add indexes for frequently queried columns

## Environment Variables

All configuration via environment variables. See `.env.example` for complete list.

### Required for Production
```bash
DATABASE_URL=                  # Neon PostgreSQL connection string
JWT_SECRET_KEY=                # JWT signing key
JWT_REFRESH_SECRET_KEY=        # Refresh token key
ALLOWED_ORIGINS=               # CORS origins (include Vercel URL)
ANTHROPIC_API_KEY=             # For Claude Vision uniform analysis
```

### Optional but Recommended
```bash
R2_ENABLED=true                # Enable Cloudflare R2 storage
R2_PUBLIC_URL=                 # Public R2 bucket URL
VITE_API_BASE=                 # Backend URL for frontend
GEO_BYPASS_COUNTRY=GB          # yt-dlp geo-bypass country
```

## Database Migrations

Use Alembic for all schema changes:

```bash
# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## API Documentation

All endpoints auto-documented at `/docs` (Swagger UI) and `/redoc`.

When adding endpoints:
1. Use descriptive operation IDs
2. Add response models with examples
3. Document all parameters
4. Include error responses

### Key Endpoints
| Endpoint | Purpose |
|----------|---------|
| `POST /ingest/url` | Submit URL for scraping/download |
| `GET /officers` | List all officers with appearances |
| `GET /officers/repeat` | Officers with multiple appearances (dashboard) |
| `GET /officers/{id}/network` | Officer co-appearance network |
| `GET /media/{id}/officers` | Officers detected in specific media |

## Git Conventions

### Branch Naming
- `feature/<description>` - New features
- `fix/<description>` - Bug fixes
- `docs/<description>` - Documentation

### Commit Messages
```
type: Short description

Longer description if needed.

- Bullet points for multiple changes
- Reference issues: #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

### Pull Requests
- Descriptive title
- Summary of changes
- Test plan with checkboxes
- Link related issues

## Rate Limiting

Endpoints are rate-limited to prevent abuse:

```python
from ratelimit import limiter, get_rate_limit

@app.get("/endpoint")
@limiter.limit(get_rate_limit("default"))
async def endpoint(request: Request):
    ...
```

Configure via:
- `MAX_CONCURRENT_AI_TASKS` - AI processing concurrency
- `UNIFORM_ANALYSIS_RATE_LIMIT` - Claude API calls/minute

## WebSocket (Socket.IO)

Real-time updates via Socket.IO for long-running tasks:

```python
from sio import create_room, emit_progress, mark_room_complete

# Create room for task
await create_room(task_id)

# Send progress updates
await emit_progress(task_id, {"status": "processing", "progress": 50})

# Mark complete (schedules cleanup)
mark_room_complete(task_id)
```

## Common Patterns

### Background Tasks
```python
@app.post("/process")
async def process(background_tasks: BackgroundTasks):
    task_id = generate_task_id()
    background_tasks.add_task(process_worker, task_id)
    return {"task_id": task_id}
```

### Pydantic Validators
```python
class RequestModel(BaseModel):
    url: str

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        parsed = urlparse(v)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError('URL must use http or https')
        return v
```

### Resource Cleanup
```python
cap = None
try:
    cap = cv2.VideoCapture(path)
    if cap.isOpened():
        # Process video
        pass
finally:
    if cap is not None:
        cap.release()
```

### Officer Crop URL in API Responses
```python
# Always return all three crop paths with fallback for backwards compatibility
repeat_officers.append({
    "id": officer.id,
    "crop_path": face_crop or body_crop or legacy_crop,  # Best available
    "face_crop_path": get_file_url(app.face_crop_path),  # Face close-up
    "body_crop_path": get_file_url(app.body_crop_path),  # Full body
})
```

## Troubleshooting

### Railway Returns 500 on All DB Endpoints
- Check `DATABASE_URL` is set in Railway environment variables
- Verify Neon allows connections from Railway IPs
- Check Railway logs: `railway logs`

### Officers Not Appearing on Dashboard
- Verify crop paths are being saved (check `face_crop_path`, `body_crop_path`)
- Check `/officers/repeat` endpoint returns data
- Ensure frontend uses crop path fallback pattern

### YouTube Downloads Failing (403 Forbidden)
- The retry mechanism tries 4 different client configurations
- Check if `cookies.txt` exists for authenticated downloads
- Try setting `GEO_BYPASS_COUNTRY` environment variable

### Images Not Loading
- Check if R2 is enabled and `R2_PUBLIC_URL` is set
- Verify image paths in database start with `data/`
- Check browser console for CORS errors
