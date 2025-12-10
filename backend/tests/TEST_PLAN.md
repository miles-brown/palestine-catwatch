# Backend Infrastructure Test Plan

This document provides comprehensive test scenarios for PR #24 (feature/backend-infrastructure).

## Quick Verification (5 minutes)

- [ ] `python -m pytest tests/ -v` - All tests pass
- [ ] `GET /health` returns 200
- [ ] `GET /docs` shows OpenAPI documentation
- [ ] Application starts without errors

---

## 1. Database & Migrations

### Fresh Database Setup
```bash
# Create fresh database
dropdb protest_db_test && createdb protest_db_test

# Set DATABASE_URL to test database
export DATABASE_URL=postgresql://localhost/protest_db_test

# Run migrations
alembic upgrade head

# Verify tables created
psql protest_db_test -c "\dt"
```

**Expected**: All tables created (users, media, officers, officer_appearances, protests, equipment, etc.)

### Upgrade from Previous Schema
```bash
# Start with older schema version
alembic downgrade -2

# Upgrade to head
alembic upgrade head

# Verify no data loss
psql protest_db_test -c "SELECT COUNT(*) FROM media"
```

**Expected**: Migration completes without errors, existing data preserved

---

## 2. Duplicate Detection

### Exact Duplicate Test
```bash
# Upload same file twice
curl -X POST http://localhost:8000/upload \
  -F "file=@test_image.jpg" \
  -F "protest_id=1"

# Upload again
curl -X POST http://localhost:8000/upload \
  -F "file=@test_image.jpg" \
  -F "protest_id=1"
```

**Expected**: Second upload marked as `is_duplicate=true`, references first upload

### Perceptual Similarity Test
```bash
# Upload original image
curl -X POST http://localhost:8000/upload -F "file=@original.jpg"

# Upload resized version (same content, different resolution)
convert original.jpg -resize 50% resized.jpg
curl -X POST http://localhost:8000/upload -F "file=@resized.jpg"
```

**Expected**: Resized image detected as similar (duplicate_type="similar")

### Threshold Testing
```python
# In Python test:
from ai.duplicate_detector import is_perceptually_similar

# Test with different thresholds
assert is_perceptually_similar(hash1, hash2, threshold=5) == False
assert is_perceptually_similar(hash1, hash2, threshold=15) == True
```

### Memory Test (High Load)
```bash
# Insert 10,000 media records
for i in {1..10000}; do
  psql $DATABASE_URL -c "INSERT INTO media (url, type, protest_id, perceptual_hash) VALUES ('path$i.jpg', 'image', 1, md5(random()::text))"
done

# Time duplicate detection
time curl -X POST http://localhost:8000/upload -F "file=@test.jpg"
```

**Expected**: Completes in <5 seconds, memory usage stable

---

## 3. File Cleanup

### Dry Run vs Execute
```bash
# Create orphaned test file
touch data/media/orphan_$(date +%s).jpg
sleep 1

# Dry run - should list file but not delete
python cleanup.py --dry-run

# Verify file still exists
ls data/media/orphan_*.jpg

# Execute - should delete
python cleanup.py --execute

# Verify file deleted
ls data/media/orphan_*.jpg  # Should fail
```

### Path Traversal Protection
```python
from cleanup import is_safe_path

# These should return False
assert is_safe_path("/etc/passwd") == False
assert is_safe_path("../../../etc/passwd") == False
assert is_safe_path("/tmp/../../etc/passwd") == False

# These should return True (if directories exist)
assert is_safe_path("data/media/test.jpg") == True
```

### Directory Validation
```python
from cleanup import validate_directories

report = validate_directories()
print(f"Valid: {len(report['valid'])}")
print(f"Missing: {len(report['missing'])}")
print(f"Errors: {len(report['errors'])}")
```

---

## 4. Rate Limiting

### Basic Rate Limit Test
```bash
# Hit endpoint rapidly
for i in {1..20}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/endpoint &
done
wait
```

**Expected**: First N requests return 200, subsequent return 429

### Concurrent Load Test
```bash
# Install vegeta (load testing tool)
# brew install vegeta

echo "POST http://localhost:8000/ingest" | \
  vegeta attack -rate=50/s -duration=10s | \
  vegeta report
```

**Expected**: Rate limiting kicks in, no server crashes

### AI Task Concurrency
```bash
# Start multiple AI processing tasks
for i in {1..10}; do
  curl -X POST http://localhost:8000/ingest \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com/image'$i'.jpg"}' &
done
wait
```

**Expected**: Only MAX_CONCURRENT_AI_TASKS (default 3) run simultaneously

---

## 5. OCR Badge Detection

### Performance Baseline
```bash
# Process image and check logs for timing
LOG_LEVEL=DEBUG python -c "
from ai.analyzer import extract_badge_number
import cv2
img = cv2.imread('test_officer.jpg')
result = extract_badge_number(img, (100, 100, 200, 200))
print(f'Result: {result}')
"
```

**Expected**: Log shows `badge_ocr_extraction` performance metrics

### Accuracy Comparison
```python
# Test known badge numbers
test_cases = [
    ("officer_U1234.jpg", "U1234"),
    ("officer_AB567.jpg", "AB567"),
    ("officer_PC9012.jpg", "PC9012"),
]

for image_path, expected in test_cases:
    result = extract_badge_number(cv2.imread(image_path), face_box)
    print(f"{image_path}: Expected={expected}, Got={result}")
```

---

## 6. Logging & Rotation

### Log Output Verification
```bash
# Set log file
export LOG_FILE=/tmp/test.log
export LOG_FORMAT=json

# Start application, make requests
uvicorn main:app &
curl http://localhost:8000/health

# Verify structured JSON logs
cat /tmp/test.log | jq .
```

**Expected**: Valid JSON lines with timestamp, level, logger, message

### Log Rotation Test
```bash
export LOG_FILE=/tmp/rotation_test.log
export LOG_MAX_SIZE=1K  # Small for testing
export LOG_BACKUP_COUNT=3

# Generate logs until rotation
for i in {1..1000}; do
  curl http://localhost:8000/health
done

# Check rotated files
ls -la /tmp/rotation_test.log*
```

**Expected**: Multiple rotated files (rotation_test.log, .log.1, .log.2, .log.3)

---

## 7. WebSocket Room Management

### Room Creation & Cleanup
```python
import socketio

sio = socketio.Client()
sio.connect('http://localhost:8000')

# Join task room
sio.emit('join_room', {'task_id': 'test_task_123'})

# Verify room created
# Check server logs or /debug/rooms endpoint if available

# Wait for cleanup (after task completes)
import time
time.sleep(SIO_ROOM_CLEANUP_DELAY + 10)

# Verify room cleaned up
```

### Stale Room Cleanup
```bash
# Create room, don't complete task
# Wait for SIO_ROOM_MAX_AGE_HOURS

# Verify room is cleaned up by periodic sweep
```

---

## 8. Authentication & Security

### CSRF Protection
```bash
# Without CSRF token (should fail)
curl -X POST http://localhost:8000/api/protected \
  -H "Content-Type: application/json" \
  -d '{"data": "test"}'

# Expected: 403 Forbidden

# With CSRF token (should succeed)
TOKEN=$(curl -c - http://localhost:8000/ | grep csrf)
curl -X POST http://localhost:8000/api/protected \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $TOKEN" \
  -d '{"data": "test"}'
```

### Account Lockout
```bash
# Attempt login with wrong password multiple times
for i in {1..6}; do
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "test", "password": "wrong"}'
done

# Verify account locked
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "correct"}'

# Expected: Account locked message, even with correct password
```

### JWT Token Refresh
```bash
# Login to get tokens
RESPONSE=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "password"}')

REFRESH_TOKEN=$(echo $RESPONSE | jq -r .refresh_token)

# Use refresh token
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}"

# Expected: New access token returned
```

---

## 9. Timeline API

### Chronological Order
```bash
# Create events at different times
curl -X POST http://localhost:8000/events -d '{"timestamp": "2024-01-01T10:00:00Z", ...}'
curl -X POST http://localhost:8000/events -d '{"timestamp": "2024-01-01T09:00:00Z", ...}'
curl -X POST http://localhost:8000/events -d '{"timestamp": "2024-01-01T11:00:00Z", ...}'

# Get timeline
curl http://localhost:8000/timeline?protest_id=1

# Expected: Events in chronological order (09:00, 10:00, 11:00)
```

---

## 10. Health Endpoints

### Basic Health
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", "timestamp": "..."}
```

### Database Health
```bash
curl http://localhost:8000/health/db
# Expected: {"status": "healthy", "database": "connected"}
```

### Readiness Check
```bash
curl http://localhost:8000/health/ready
# Expected: {"status": "ready", "database": "ok", "storage": "ok"}
```

---

## Automated Test Commands

```bash
# Run all unit tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run specific test categories
python -m pytest tests/test_auth.py -v           # Auth tests
python -m pytest tests/test_cleanup.py -v        # Cleanup tests
python -m pytest tests/test_duplicate_detector.py -v  # Duplicate detection

# Run integration tests (requires running server)
python -m pytest tests/integration/ -v
```

---

## Performance Benchmarks

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Health check | < 50ms | Should be instant |
| Duplicate hash check | < 100ms | Database query |
| Perceptual similarity (10k images) | < 5s | Batched processing |
| File upload (10MB image) | < 2s | Depends on disk I/O |
| Badge OCR extraction | < 2s | Multiple ROI attempts |
| WebSocket room creation | < 10ms | In-memory |

---

## Known Limitations

1. **Perceptual hashing** requires `imagehash` library (optional dependency)
2. **Badge OCR** accuracy varies with image quality and lighting
3. **Rate limiting** is per-IP, not per-user
4. **Log rotation** only works when LOG_FILE is set
