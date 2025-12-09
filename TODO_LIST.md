# Palestine Catwatch - TODO List

**Last Updated:** 2024-12-09

---

## COMPLETED TASKS

### Features Implemented
| # | Task | Status | Notes |
|---|------|--------|-------|
| 34 | Face search feature | DONE | FaceSearchPage.jsx with drag-and-drop upload |
| 36 | Uniform recognition | DONE | Claude Vision API integration with force/rank/unit detection |
| 24 | Bulk URL import | DONE | UploadPage bulk tab, up to 10 URLs |
| 22 | Export to CSV/JSON | DONE | AdminPage export buttons |
| 20 | Officer merge functionality | DONE | AdminPage merge UI |
| 21 | Manual badge number editing | DONE | AdminPage edit modal |
| 10 | URL validation on ingest | DONE | IngestURLRequest validator with pattern checks |
| - | Equipment database | DONE | EquipmentPage with categories and detection counts |
| - | Dashboard analytics | DONE | DashboardPage with stats, repeat offenders, network analysis |
| - | PDF dossier generation | DONE | /officers/{id}/dossier endpoint |
| - | WebSocket live analysis | DONE | Socket.IO with room management |
| - | Officer network analysis | DONE | /officers/{id}/network endpoint |

### Bug Fixes Completed
| # | Task | Status | Notes |
|---|------|--------|-------|
| - | Mutable default argument | DONE | Fixed with Field(default_factory=dict) |
| - | parseInt NaN validation | DONE | Added explicit NaN check |
| - | API URL exposure in errors | DONE | Only show in dev mode |
| - | Protest ID validation | DONE | Backend checks protest exists |
| - | Pydantic v2 ConfigDict | DONE | All schemas updated |
| - | HTTPS protocol for localhost | DONE | Check for localhost/127.0.0.1 first |
| - | Error message formatting | DONE | Extracted to helper function |

---

## CRITICAL Priority (App Broken/Non-functional)

| # | Task | Size | Status | Description |
|---|------|------|--------|-------------|
| 1 | Fix `ingest_images.py` syntax errors | M | TODO | File has duplicate code blocks, broken indentation, and unclosed try blocks. Scraping is completely broken. |
| 2 | Fix `UploadPage.jsx` setStatus typos | S | TODO | Lines 121 & 137 call `setStatus()` but should call `setSubmitStatus()`. Error handling broken. |
| 3 | Fix `process.py` object comparison bug | S | TODO | Line 238 compares dicts to strings. Object context detection completely broken. |
| 4 | Fix `UploadPage.jsx` undefined variable | S | TODO | Line 77 calls `setSelectedProtestId('')` but variable never declared. Upload success crashes. |
| 5 | Fix `reports.py` non-existent attribute | S | TODO | Line 32 accesses `officer.role` but Officer model has no role field. PDF generation fails. |

---

## HIGH Priority (Core Functionality Issues)

| # | Task | Size | Status | Description |
|---|------|------|--------|-------------|
| 6 | Enable EasyOCR for badge detection | M | TODO | OCR is imported but disabled (`reader = None`). Badge number detection non-functional. |
| 7 | Fix analyzer.py duplicate exception | S | TODO | Lines 60-61 have duplicate `except` blocks. Remove unreachable code. |
| 8 | Add proper error handling in LiveAnalysis | M | PARTIAL | Has basic WebSocket error handling but needs more granular states. |
| 9 | Fix face embedding matching | M | TODO | Current threshold (0.8) may be too loose. Test and calibrate with real data. |
| 11 | Fix image path handling inconsistency | M | TODO | Paths use mix of relative (`../data/`), absolute, and various formats. Standardize. |
| 12 | Add database migration system | M | TODO | Schema changes require manual intervention. Add Alembic for migrations. |
| 13 | Fix Socket.IO room memory leak | S | PARTIAL | Rooms cleaned up with 5-min delay but could optimize further. |

---

## MEDIUM Priority (Significant Improvements)

| # | Task | Size | Status | Description |
|---|------|------|--------|-------------|
| 14 | Add authentication system | L | TODO | No auth currently. Anyone can access/modify data. Add JWT-based auth. |
| 15 | Implement rate limiting | M | PARTIAL | Framework exists (ratelimit.py) but not applied to all endpoints. |
| 16 | Add file cleanup job | M | TODO | Downloaded files accumulate forever. Implement scheduled cleanup or retention policy. |
| 17 | Add React Error Boundaries | S | TODO | Component errors crash entire app. Wrap routes in error boundaries. |
| 18 | Improve mobile responsiveness | M | TODO | Current UI breaks on small screens. Need responsive design pass. |
| 19 | Add pagination to /officers endpoint | S | DONE | AdminPage has pagination (20 per page). |
| 23 | Add search by date range | M | TODO | Can only search by text. Add date range filter. |
| 25 | Add video timestamp scrubber | M | TODO | ReportPage shows timestamps but can't seek. Add video player integration. |
| 40 | Add audit logging | M | TODO | Log all data modifications for compliance. |

---

## LOW Priority (Nice to Have)

| # | Task | Size | Status | Description |
|---|------|------|--------|-------------|
| 26 | Add TypeScript to frontend | XL | TODO | No type safety. Gradual migration to TypeScript. |
| 27 | Create unit tests for AI functions | L | TODO | No tests. Add pytest tests for analyzer.py functions. |
| 28 | Add integration tests for API | L | TODO | No API tests. Add pytest + httpx tests for endpoints. |
| 29 | Create E2E tests with Playwright | L | TODO | No E2E tests. Add critical path tests. |
| 30 | Add dark mode toggle | M | TODO | LiveAnalysis is dark, rest is light. Add consistent theme toggle. |
| 31 | Implement lazy loading for officer grid | M | TODO | All officers load at once. Add intersection observer lazy loading. |
| 32 | Add skeleton loaders | S | TODO | Show skeleton UI while loading instead of spinners. |
| 33 | Create API documentation | M | TODO | No docs. Add Swagger/OpenAPI documentation. |
| 35 | Implement behavior classification | XL | TODO | Train model to classify officer actions automatically. |
| 37 | Create collaborative annotation system | XL | TODO | Allow multiple users to annotate and validate. |
| 38 | Add offline/PWA support | L | TODO | Support offline queuing and sync. |
| 39 | Implement CDN for images | M | TODO | Serve face crops from CDN for performance. |

---

## NEW TASKS (Added 2024-12-09)

### Evidence Collection Enhancements

| # | Task | Size | Priority | Description |
|---|------|------|----------|-------------|
| 41 | Protest timeline view | L | MEDIUM | Chronological event reconstruction across all media for a protest |
| 42 | Geographic clustering | M | MEDIUM | Map officers by protest location, show patterns |
| 43 | Cross-event tracking dashboard | L | HIGH | Same officers appearing at multiple protests - pattern analysis |
| 44 | Equipment correlation analysis | M | MEDIUM | Which equipment combinations indicate escalation (shields + batons) |
| 45 | Chain of command linking | L | HIGH | Link sergeants/inspectors to constables they command |
| 46 | Behavior action tagging | XL | MEDIUM | Auto-detect "kettling", "arresting", "shield line", "baton drawn" via Claude |
| 47 | Video moment seeking | M | HIGH | Click timestamp in report to jump to that moment in video |

### Security & Access Control

| # | Task | Size | Priority | Description |
|---|------|------|----------|-------------|
| 48 | Role-based access control | L | HIGH | Admin vs contributor vs viewer distinction |
| 49 | Audit trail | M | MEDIUM | Track who uploaded/modified what and when |
| 50 | DoS protection | M | HIGH | Rate limiting on expensive AI endpoints |

### Data Quality

| # | Task | Size | Priority | Description |
|---|------|------|----------|-------------|
| 51 | Confidence calibration UI | M | MEDIUM | Let users rate AI accuracy to improve thresholds |
| 52 | Duplicate detection | M | MEDIUM | Warn when uploading same video/image twice |
| 53 | Data retention policy | S | LOW | Auto-cleanup of old temporary files |

---

## Quick Reference by Status

### Ready to Start (No Dependencies)
- #1, #2, #3, #4, #5, #6, #7, #17, #32

### Needs Investigation First
- #9 (face matching calibration needs test data)
- #11 (path handling needs audit of all usages)

### Blocked by Other Work
- #14 must complete before #48, #49
- #25 needs video player component first

---

## Suggested Next Sprint

### Sprint: Stability & Critical Fixes
1. **Fix `ingest_images.py`** - Image scraping completely broken
2. **Fix `UploadPage.jsx` bugs** - setStatus typos and undefined variable
3. **Fix `process.py` object comparison** - AI context detection broken
4. **Fix `reports.py` attribute error** - PDF generation fails
5. **Enable EasyOCR** - Badge detection non-functional
6. **Add React Error Boundaries** - Prevent full-app crashes

### Sprint: Evidence Features
7. **Cross-event tracking (#43)** - Critical for pattern analysis
8. **Video timestamp seeking (#47)** - Essential for reviewing incidents
9. **Date range filtering (#23)** - Essential for protest-specific searches
10. **Chain of command linking (#45)** - Understand unit structure

### Sprint: Security
11. **Authentication (#14)** - Protect data access
12. **Role-based access (#48)** - Admin vs user
13. **Rate limiting (#50)** - Protect expensive endpoints

---

## Progress Summary

| Category | Done | In Progress | TODO |
|----------|------|-------------|------|
| Critical Bugs | 0 | 0 | 5 |
| High Priority | 1 | 2 | 4 |
| Medium Priority | 2 | 1 | 6 |
| Features | 12 | 0 | 15+ |
| **Total** | **15** | **3** | **30+** |

---

*Last reviewed: 2024-12-09*
