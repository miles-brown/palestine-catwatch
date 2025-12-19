# Palestine Catwatch - TODO List

**Last Updated:** 2024-12-19

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
| 31 | Lazy loading for officer grid | DONE | LazyOfficerGrid.jsx with intersection observer |
| 32 | Skeleton loaders | DONE | OfficerGridSkeleton component |
| 39 | CDN/cloud storage for images | DONE | Cloudflare R2 integration with public URLs |
| - | YouTube 403 bypass | DONE | PR #41 - Multi-config yt-dlp retry mechanism |
| - | Dashboard officer display fix | DONE | PR #42 - face_crop_path/body_crop_path fallback |
| - | Live analysis log visibility | DONE | PR #42 - Fixed faint grey text in upload logs |
| 11 | Image path handling | DONE | Standardized with utils/paths.py and get_file_url() |

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
| - | Video download 403 errors | DONE | PR #41 - yt-dlp retry with iOS/Android/TV clients |
| - | Officers not on dashboard | DONE | PR #42 - Added face/body crop path support |
| - | Upload log text visibility | DONE | PR #42 - Changed slate-600 to slate-400 |

### Infrastructure Completed
| Task | Status | Notes |
|------|--------|-------|
| Vercel frontend deployment | DONE | https://palestine-catwatch.vercel.app/ |
| Railway backend deployment | DONE | https://palestine-catwatch-production.up.railway.app |
| Neon PostgreSQL setup | DONE | Cloud database with SSL |
| Cloudflare R2 storage | DONE | Image storage with public URLs |
| Path utility standardization | DONE | utils/paths.py with get_file_url(), normalize_for_storage() |
| URL generation tests | DONE | tests/test_paths.py - 19 test cases |

---

## CRITICAL Priority (App Broken/Non-functional)

| # | Task | Size | Status | Description |
|---|------|------|--------|-------------|
| 1 | ~~Fix `ingest_images.py` syntax errors~~ | M | DONE | Fixed in earlier PRs |
| 2 | ~~Fix `UploadPage.jsx` setStatus typos~~ | S | DONE | Fixed setSubmitStatus calls |
| 54 | **Railway DB connection issue** | M | **BLOCKED** | Railway returns 500 on all DB endpoints. Need to verify DATABASE_URL in Railway env vars. |

---

## HIGH Priority (Core Functionality Issues)

| # | Task | Size | Status | Description |
|---|------|------|--------|-------------|
| 6 | Enable EasyOCR for badge detection | M | TODO | OCR is imported but disabled (`reader = None`). Badge number detection non-functional. |
| 7 | ~~Fix analyzer.py duplicate exception~~ | S | DONE | Removed unreachable code. |
| 8 | ~~Add proper error handling in LiveAnalysis~~ | M | DONE | Granular error states, retry mechanism, stale detection |
| 9 | Fix face embedding matching | M | TODO | Current threshold (0.8) may be too loose. Test and calibrate with real data. |
| 12 | Add database migration system | M | PARTIAL | Alembic exists but not always used for schema changes. |
| 13 | ~~Fix Socket.IO room memory leak~~ | S | DONE | Rooms cleaned up with delay, mark_room_complete() implemented |
| 55 | **Configure R2 in Railway** | M | **TODO** | R2_ENABLED, R2_PUBLIC_URL not set in Railway. Images may not load in production. |

---

## MEDIUM Priority (Significant Improvements)

| # | Task | Size | Status | Description |
|---|------|------|--------|-------------|
| 14 | Add authentication system | L | DONE | JWT-based auth with refresh tokens implemented |
| 15 | Implement rate limiting | M | DONE | ratelimit.py applied to endpoints |
| 16 | Add file cleanup job | M | TODO | Downloaded files accumulate forever. Implement scheduled cleanup or retention policy. |
| 17 | Add React Error Boundaries | S | TODO | Component errors crash entire app. Wrap routes in error boundaries. |
| 18 | Improve mobile responsiveness | M | TODO | Current UI breaks on small screens. Need responsive design pass. |
| 19 | ~~Add pagination to /officers endpoint~~ | S | DONE | AdminPage has pagination (20 per page). |
| 23 | Add search by date range | M | TODO | Can only search by text. Add date range filter. |
| 25 | Add video timestamp scrubber | M | TODO | ReportPage shows timestamps but can't seek. Add video player integration. |
| 40 | Add audit logging | M | TODO | Log all data modifications for compliance. |

---

## LOW Priority (Nice to Have)

| # | Task | Size | Status | Description |
|---|------|------|--------|-------------|
| 26 | Add TypeScript to frontend | XL | TODO | No type safety. Gradual migration to TypeScript. |
| 27 | Create unit tests for AI functions | L | PARTIAL | tests/test_paths.py exists. Need more coverage for analyzer.py |
| 28 | Add integration tests for API | L | TODO | No API tests. Add pytest + httpx tests for endpoints. |
| 29 | Create E2E tests with Playwright | L | TODO | No E2E tests. Add critical path tests. |
| 30 | Add dark mode toggle | M | TODO | LiveAnalysis is dark, rest is light. Add consistent theme toggle. |
| 33 | Create API documentation | M | DONE | Auto-generated at /docs (Swagger) and /redoc |
| 35 | Implement behavior classification | XL | TODO | Train model to classify officer actions automatically. |
| 37 | Create collaborative annotation system | XL | TODO | Allow multiple users to annotate and validate. |
| 38 | Add offline/PWA support | L | TODO | Support offline queuing and sync. |

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
| 50 | ~~DoS protection~~ | M | DONE | Rate limiting implemented on expensive AI endpoints |

### Data Quality

| # | Task | Size | Priority | Description |
|---|------|------|----------|-------------|
| 51 | Confidence calibration UI | M | MEDIUM | Let users rate AI accuracy to improve thresholds |
| 52 | Duplicate detection | M | DONE | Hash-based duplicate detection in ingest pipeline |
| 53 | Data retention policy | S | LOW | Auto-cleanup of old temporary files |

---

## NEW TASKS (Added 2024-12-19)

### Infrastructure & DevOps

| # | Task | Size | Priority | Description |
|---|------|------|----------|-------------|
| 54 | Fix Railway DATABASE_URL | S | **CRITICAL** | All DB endpoints return 500. Verify env var is set correctly in Railway dashboard. |
| 55 | Configure R2 in Railway | M | HIGH | Set R2_ENABLED, R2_PUBLIC_URL, credentials in Railway for image serving |
| 56 | Add health check endpoint | S | MEDIUM | `/health` endpoint that verifies DB connection for Railway monitoring |
| 57 | Environment variable documentation | S | LOW | Document all required Railway/Vercel env vars in README |

### Code Quality

| # | Task | Size | Priority | Description |
|---|------|------|----------|-------------|
| 58 | Add tests for ingest_video.py | M | MEDIUM | Test retry mechanism, error handling, progress callbacks |
| 59 | Add tests for crop path fallback | S | LOW | Verify face > body > image priority in all components |

---

## Quick Reference by Status

### Ready to Start (No Dependencies)
- #6, #17, #56, #57, #58

### Needs User Action
- **#54** - Railway DATABASE_URL configuration (CRITICAL)
- **#55** - Railway R2 configuration

### Blocked by Other Work
- #48 Role-based access depends on auth being stable
- #25 Video seeking needs video player component first

---

## Suggested Next Sprint

### Sprint 1: Production Stability (URGENT)
1. **#54 - Fix Railway DATABASE_URL** - All API calls failing with 500
2. **#55 - Configure R2 in Railway** - Images won't load without this
3. **#56 - Add health check endpoint** - For monitoring

### Sprint 2: Core Features
4. **#6 - Enable EasyOCR** - Badge detection non-functional
5. **#43 - Cross-event tracking** - Critical for pattern analysis
6. **#47 - Video timestamp seeking** - Essential for reviewing incidents

### Sprint 3: Quality & Polish
7. **#17 - React Error Boundaries** - Prevent full-app crashes
8. **#23 - Date range filtering** - Essential for protest-specific searches
9. **#58 - Add video ingest tests** - Ensure retry mechanism works

---

## Progress Summary

| Category | Done | In Progress | TODO |
|----------|------|-------------|------|
| Critical Bugs | 4 | 0 | 1 |
| High Priority | 6 | 0 | 3 |
| Medium Priority | 6 | 0 | 5 |
| Low Priority | 3 | 1 | 6 |
| Features | 18 | 0 | 12 |
| Infrastructure | 6 | 0 | 2 |
| **Total** | **43** | **1** | **29** |

---

## Recent PRs

| PR | Title | Status |
|----|-------|--------|
| #42 | fix: Display detected officers on dashboard with proper crop paths | Open |
| #41 | feat: Add retry mechanism for video downloads with multiple yt-dlp configs | Merged |

---

*Last reviewed: 2024-12-19*
