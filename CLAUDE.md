# CLAUDE.md - Project Conventions for Palestine CatWatch

This document defines the coding standards, conventions, and guidelines for the Palestine CatWatch project. Follow these conventions when contributing code.

## Project Overview

Palestine CatWatch is a media analysis platform for documenting police conduct at protests. It uses computer vision (face detection, re-identification) and AI analysis (uniform recognition via Claude Vision API) to catalog officer appearances across media.

## Directory Structure

```
palestine-catwatch/
├── backend/                 # FastAPI backend
│   ├── ai/                  # AI/ML modules (analyzer, duplicate detection, uniform analysis)
│   ├── tests/               # pytest test files
│   ├── utils/               # Utility modules
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication & authorization
│   ├── database.py          # Database configuration
│   └── logging_config.py    # Structured logging setup
├── frontend/                # React frontend
├── data/                    # Media storage (gitignored)
└── alembic/                 # Database migrations
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
python -m pytest tests/ -v
python -m pytest tests/test_specific.py -v  # Single file
```

### Mocking Guidelines
```python
from unittest.mock import Mock, patch

# Mock database sessions
mock_db = Mock()
mock_db.query.return_value.filter.return_value.first.return_value = mock_object

# Mock external services
with patch('module.external_function') as mock_func:
    mock_func.return_value = expected_value
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

Required for production:
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_REFRESH_SECRET_KEY`
- `ALLOWED_ORIGINS`

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
