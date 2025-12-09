# Palestine Catwatch - Concepts & Ideas for Improvement

**Last Updated:** 2024-12-09

---

## COMPLETED ITEMS

### Bug Fixes Applied
- [x] Mutable default argument in main.py - Fixed with `Field(default_factory=dict)`
- [x] parseInt validation in UploadPage.jsx - Added NaN check
- [x] API URL exposure in error messages - Only show in dev mode
- [x] Protest ID validation - Backend checks protest exists before ingest
- [x] Pydantic v2 migration - All schemas use `ConfigDict(from_attributes=True)`
- [x] HTTPS protocol for localhost - Check for localhost/127.0.0.1 first
- [x] Error message formatting - Extracted to helper function

### Features Implemented
- [x] **Uniform Recognition** - Claude Vision API integration for force/rank/unit detection
- [x] **Face Search** - Upload face to find matching officers (FaceSearchPage)
- [x] **Bulk URL Import** - Import up to 10 URLs at once
- [x] **Export Functionality** - CSV/JSON export from AdminPage
- [x] **Officer Merge** - Merge duplicate officers in AdminPage
- [x] **Manual Badge Editing** - Edit badge numbers in AdminPage
- [x] **Equipment Database** - EquipmentPage with categories and detection counts
- [x] **Dashboard Analytics** - Stats, repeat offenders, network analysis
- [x] **PDF Dossier Generation** - /officers/{id}/dossier endpoint
- [x] **URL Validation** - Pattern checks on ingest endpoint
- [x] **WebSocket Live Analysis** - Socket.IO with room management

---

## Critical Bugs Remaining

### 1. `backend/ai/analyzer.py:60-61` - Duplicate Exception Handler
**Severity: Low** (code smell, unreachable code)
```python
except Exception as e:
    print(f"Warning: Failed to load Re-ID model: {e}")
except Exception as e:  # DUPLICATE - unreachable
    print(f"Warning: Failed to load Re-ID model: {e}")
```
**Fix:** Remove the duplicate exception handler.

---

### 2. `backend/process.py:238` - Object Comparison Bug
**Severity: High** (AI analysis broken)
```python
relevant_objects = [obj for obj in objects if obj in ['baseball bat', 'knife', ...]]
```
`objects` is a list of dicts `{'label': str, 'box': list, 'confidence': float}`, so comparing `obj` (a dict) to strings always fails.

**Fix:**
```python
relevant_objects = [obj['label'] for obj in objects if obj['label'] in ['baseball bat', 'knife', ...]]
```

---

### 3. `src/pages/UploadPage.jsx:77` - Undefined Variable
**Severity: Medium** (crashes on successful upload)
```jsx
setSelectedProtestId('');  // 'selectedProtestId' is never declared
```
**Fix:** Either declare the state variable or remove this line (it's unnecessary since `file` is already set to null).

---

### 4. `src/pages/UploadPage.jsx:121, 137` - Wrong Function Calls
**Severity: High** (error handling broken)
```jsx
// Line 121 in catch block:
setStatus('error');  // Should be setSubmitStatus('error')

// Line 137 in onComplete:
setStatus('idle');   // Should be setSubmitStatus('idle')
```
`setStatus` doesn't exist - should be `setSubmitStatus`.

---

### ~~5. `backend/main.py:121` - Variable Shadowing~~
**Status: Low priority** - Works correctly, just confusing naming.

---

### 6. `backend/ingest_images.py` - Severe Code Duplication & Syntax Errors
**Severity: Critical** (file likely non-functional)

The file has:
- Duplicated code blocks (lines ~46-119 repeat at ~120-281)
- Broken indentation (try blocks never properly close)
- The `finally: db.close()` appears multiple times at wrong indentation levels
- The function essentially has two copies of the same logic

**Fix:** Complete rewrite of this file to remove duplicates and fix indentation.

---

### 7. `backend/reports.py:32` - Non-existent Attribute Access
**Severity: Medium** (PDF generation will fail)
```python
c.drawString(50, y, f"Role: {officer.role or 'Unknown'}")
```
The `Officer` model has no `role` attribute - `role` is on `OfficerAppearance`.

**Fix:** Remove this line or get role from first appearance:
```python
first_role = appearances[0].role if appearances else 'Unknown'
c.drawString(50, y, f"Role: {first_role}")
```

---

### ~~8. `backend/schemas.py:26` - Typo~~
**Status: FIXED** - Comment typo corrected during Pydantic v2 migration.

---

## Architectural Issues

### Resolved
- [x] ~~No Input Validation on URLs~~ - Added URL validation with pattern checks

### Remaining Issues
| Issue | Severity | Status |
|-------|----------|--------|
| No Error Boundaries in React | Medium | TODO |
| Hardcoded Values Throughout | Low | TODO |
| No Rate Limiting | High | PARTIAL (framework exists) |
| File Cleanup Not Implemented | Medium | TODO |
| OCR Disabled | High | TODO |
| No Authentication | High | TODO |
| Socket.IO Room Cleanup | Low | PARTIAL (5-min delay cleanup exists) |

---

## Feature Ideas

### Immediate Value - COMPLETED
| Feature | Status |
|---------|--------|
| Officer Re-identification Dashboard | DONE - DashboardPage with network analysis |
| Bulk Import Tool | DONE - UploadPage bulk tab |
| Manual Correction Interface | DONE - AdminPage merge/edit |
| Export Functionality | DONE - CSV/JSON export |
| Search Improvements | PARTIAL - Badge search done, date range TODO |

### Immediate Value - TODO
| Feature | Priority |
|---------|----------|
| Date range filtering | HIGH |
| Full-text search on notes/actions | MEDIUM |
| Filter by police force | MEDIUM |

### Medium-term Enhancements - COMPLETED
| Feature | Status |
|---------|--------|
| Face Search | DONE - FaceSearchPage |
| Confidence Calibration | PARTIAL - Stats shown, feedback loop TODO |

### Medium-term Enhancements - TODO
| Feature | Priority |
|---------|----------|
| Timeline View | HIGH |
| Video timestamp scrubber | HIGH |
| Mobile Responsive Design | MEDIUM |
| Offline/PWA Capability | LOW |

### Advanced Features - COMPLETED
| Feature | Status |
|---------|--------|
| Uniform Recognition | DONE - Claude Vision API |
| Equipment Detection | DONE - EquipmentPage |

### Advanced Features - TODO
| Feature | Priority | Notes |
|---------|----------|-------|
| Behavior Classification | HIGH | Auto-detect kettling, arresting, shield line |
| Video Highlights | MEDIUM | Auto-generate highlight reel |
| Collaborative Annotations | LOW | Multi-user workflow |
| API for External Tools | LOW | Public API documentation |

---

## NEW IDEAS (Added 2024-12-09)

### Evidence Collection for Accountability

| Idea | Description | Impact |
|------|-------------|--------|
| **Cross-Event Tracking** | Dashboard showing same officers at multiple protests | HIGH - Pattern analysis |
| **Chain of Command Linking** | Connect sergeants to constables they supervise | HIGH - Accountability |
| **Protest Timeline View** | Chronological reconstruction of events | HIGH - Legal evidence |
| **Geographic Clustering** | Map view showing officer deployment patterns | MEDIUM |
| **Equipment Escalation Analysis** | Track which equipment combos indicate escalation | MEDIUM |
| **Behavior Action Tags** | Auto-tag "kettling", "baton drawn", etc. | HIGH |

### Security & Compliance

| Idea | Description | Impact |
|------|-------------|--------|
| **Authentication System** | JWT-based login | HIGH - Data protection |
| **Role-Based Access** | Admin vs contributor vs viewer | HIGH |
| **Audit Trail** | Log all modifications | MEDIUM - Compliance |
| **DoS Protection** | Rate limit expensive endpoints | HIGH - Availability |

### Data Quality

| Idea | Description | Impact |
|------|-------------|--------|
| **Confidence Calibration UI** | User feedback to tune AI thresholds | MEDIUM |
| **Duplicate Detection** | Warn on re-upload of same media | LOW |
| **Data Retention Policy** | Auto-cleanup temp files | LOW |

---

## Performance Improvements

### Frontend - TODO

| Improvement | Priority |
|-------------|----------|
| Lazy Loading | MEDIUM |
| State Management (Zustand/Jotai) | LOW |
| Image Optimization (thumbnails) | MEDIUM |
| Code Splitting | LOW |

### Backend - TODO

| Improvement | Priority |
|-------------|----------|
| Async Processing Queue (Celery) | MEDIUM |
| Database Indexes | LOW |
| GPU Acceleration | LOW |
| CDN for Static Assets | LOW |

---

## Security Recommendations

### Completed
- [x] Input Sanitization - URL validation added
- [x] SQL injection protection - SQLAlchemy ORM

### TODO
| Recommendation | Priority |
|----------------|----------|
| Authentication System | HIGH |
| Role-based access control | HIGH |
| Content Validation (file type) | MEDIUM |
| HTTPS Enforcement (restrict CORS) | MEDIUM |
| Rate Limiting | HIGH |
| Audit Logging | MEDIUM |

---

## UX Improvements - TODO

| Improvement | Priority |
|-------------|----------|
| Better Loading States (skeleton) | LOW |
| Error Messages (toast notifications) | MEDIUM |
| Onboarding Flow | LOW |
| Accessibility (keyboard nav) | LOW |
| Dark Mode Toggle | LOW |

---

## Code Quality - TODO

| Task | Priority |
|------|----------|
| TypeScript Migration | LOW |
| Unit Tests (pytest) | MEDIUM |
| Integration Tests | MEDIUM |
| E2E Tests (Playwright) | LOW |
| API Documentation (OpenAPI) | MEDIUM |
| CI/CD Pipeline | LOW |

---

## Summary

### Done: 15+ items
- Uniform recognition, face search, bulk import, export, merge, edit, equipment tracking, dashboard, PDF dossiers, URL validation, WebSocket, multiple bug fixes

### In Progress: 3 items
- Rate limiting (framework exists)
- Error handling in LiveAnalysis
- Socket.IO cleanup

### High Priority TODO: 10+ items
- 5 critical bugs
- Authentication
- Date range filtering
- Behavior classification
- Cross-event tracking
- Chain of command linking

---

*Last reviewed: 2024-12-09*
