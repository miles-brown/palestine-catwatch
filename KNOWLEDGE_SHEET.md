# Palestine Catwatch - Knowledge Sheet

## Project Overview

Palestine Catwatch is a full-stack web application for documenting and cataloging evidence from protest footage using AI-powered analysis. It processes media (images/videos) to detect, identify, and track police officers at protests.

---

## Technology Stack

### Frontend
- **React 18.2.0** - UI framework
- **Vite 5.0** - Build tool & dev server
- **React Router DOM 6.20.1** - Client-side routing
- **Tailwind CSS 3.3.5** - Utility-first CSS framework
- **Leaflet 1.9.4 + React Leaflet 4.2.1** - Interactive maps
- **Lucide React 0.294** - Icon library
- **Socket.IO Client 4.8.1** - Real-time WebSocket communication

### Backend
- **FastAPI** - Python async web framework
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation
- **uvicorn** - ASGI server
- **PostgreSQL** - Primary database (Neon/Supabase in production)
- **Socket.IO (python-socketio)** - Real-time event broadcasting
- **yt-dlp** - Video downloading from YouTube etc.
- **BeautifulSoup4 + cloudscraper** - Web scraping

### AI/ML Stack
- **PyTorch + TorchVision** - Deep learning framework
- **facenet-pytorch (InceptionResnetV1)** - Face recognition/embedding
- **OpenCV DNN** - Face detection (SSD model)
- **ultralytics/YOLOv8** - Object detection
- **EasyOCR** - Text recognition (currently disabled)
- **SciPy** - Vector distance calculations

---

## Directory Structure

```
palestine-catwatch/
├── src/                          # React frontend
│   ├── components/               # Reusable components
│   │   ├── Header.jsx           # Navigation header
│   │   ├── HomePage.jsx         # Main page with officer grid/map
│   │   ├── OfficerCard.jsx      # Individual officer display card
│   │   ├── OfficerProfile.jsx   # Detailed officer modal
│   │   ├── MapView.jsx          # Leaflet map component
│   │   ├── LiveAnalysis.jsx     # Real-time analysis UI
│   │   ├── IngestQuestionnaire.jsx # URL submission form
│   │   └── ui/                  # UI primitives (button, card)
│   ├── pages/                   # Page components
│   │   ├── UploadPage.jsx       # Media submission (file/URL)
│   │   ├── ReportPage.jsx       # Analysis results display
│   │   ├── ManifestoPage.jsx    # Campaign manifesto
│   │   └── ...                  # Other static pages
│   ├── data/officers.js         # Static officer data (deprecated)
│   ├── App.jsx                  # Root component with routes
│   └── main.jsx                 # React entry point
│
├── backend/                     # Python FastAPI backend
│   ├── ai/                      # AI analysis modules
│   │   ├── analyzer.py          # Core AI functions (face/object detection)
│   │   ├── deploy.prototxt      # Face detection model config
│   │   └── res10_300x300_ssd_iter_140000.caffemodel  # Face detection weights
│   ├── main.py                  # FastAPI app definition & routes
│   ├── models.py                # SQLAlchemy ORM models
│   ├── schemas.py               # Pydantic validation schemas
│   ├── database.py              # Database connection config
│   ├── sio.py                   # Socket.IO server setup
│   ├── process.py               # Media processing pipeline
│   ├── ingest_video.py          # Video downloading & workflow
│   ├── ingest_images.py         # Image scraping from articles
│   ├── ingest.py                # File upload handling
│   ├── recon.py                 # URL reconnaissance/scoring
│   ├── reports.py               # PDF dossier generation
│   └── requirements.txt         # Python dependencies
│
├── data/                        # Runtime data storage
│   ├── frames/                  # Extracted video frames
│   ├── downloads/               # Downloaded media files
│   └── media/                   # Uploaded media files
│
├── .env                         # Environment variables
├── package.json                 # Node.js dependencies
├── vite.config.js               # Vite configuration
├── tailwind.config.js           # Tailwind CSS config
└── docker-compose.yml           # Local development setup
```

---

## Database Schema

### Protest
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| name | String | Event name |
| date | DateTime | Event date |
| location | String | Location name |
| latitude | String (nullable) | GPS latitude |
| longitude | String (nullable) | GPS longitude |
| description | Text (nullable) | Event description |

### Media
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| url | String | File path or web URL |
| type | String | 'image' or 'video' |
| protest_id | Integer (FK) | Links to Protest |
| timestamp | DateTime | When added |
| processed | Boolean | Analysis complete flag |

### Officer
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| badge_number | String (nullable) | Badge number from OCR |
| force | String (nullable) | Police force name |
| visual_id | String (nullable) | Face embedding JSON (512-d vector) |
| notes | Text (nullable) | Additional notes |
| latitude | Float (nullable) | Last known latitude |
| longitude | Float (nullable) | Last known longitude |

### OfficerAppearance
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| officer_id | Integer (FK) | Links to Officer |
| media_id | Integer (FK) | Links to Media |
| timestamp_in_video | String (nullable) | Time code (HH:MM:SS) |
| image_crop_path | String (nullable) | Path to face/body crop |
| role | String (nullable) | Officer's observed role |
| action | Text (nullable) | AI-described behavior |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/officers` | List all officers (with filters) |
| GET | `/officers/{id}` | Get single officer details |
| GET | `/officers/{id}/dossier` | Generate PDF dossier |
| GET | `/media/{id}/report` | Get analysis report for media |
| POST | `/ingest/url` | Start async URL ingestion |
| POST | `/upload` | Upload local file |
| GET | `/protests` | List all protests |
| WS | `/socket.io` | Real-time events |

---

## Core Functions

### AI Analyzer (`backend/ai/analyzer.py`)

| Function | Purpose |
|----------|---------|
| `detect_faces(image_path)` | OpenCV DNN face detection, returns bounding boxes |
| `generate_embedding(image_path, face_box)` | Creates 512-d face vector using InceptionResnetV1 |
| `detect_objects(image_path)` | YOLOv8 object detection |
| `extract_text(image_input)` | EasyOCR text extraction (disabled) |
| `get_body_roi(img, face_box)` | Extract body region from face location |
| `filter_badge_number(texts)` | Heuristic to identify badge numbers |
| `calculate_blur(image)` | Laplacian variance for blur detection |
| `process_image_ai(image_path, output_dir)` | Full analysis pipeline for single image |

### Process Pipeline (`backend/process.py`)

| Function | Purpose |
|----------|---------|
| `process_media(media_id, status_callback)` | Main entry - orchestrates full processing |
| `extract_frames(media_item, dir, interval)` | Extract frames from video at 1s intervals |
| `analyze_frames(media_id, dir, callback)` | Run AI analysis on all frames |
| `get_timestamp_str(seconds)` | Convert seconds to HH:MM:SS |

### Ingestion (`backend/ingest_video.py`, `ingest_images.py`)

| Function | Purpose |
|----------|---------|
| `download_video(url, ...)` | Download via yt-dlp with progress |
| `extract_metadata(info)` | Parse city/date from video metadata |
| `process_video_workflow(url, ...)` | Smart routing: video vs article |
| `scrape_images_from_url(url, ...)` | Scrape images from news articles |

### URL Reconnaissance (`backend/recon.py`)

| Function | Purpose |
|----------|---------|
| `analyze_url(url)` | Pre-analysis URL assessment |
| `ReconAgent.analyze()` | Keyword scoring, category detection |

---

## Data Flow

```
User Input (URL or File)
         │
         ▼
┌─────────────────────────────────────────┐
│           Frontend (React)              │
│  UploadPage → IngestQuestionnaire       │
│         ↓ POST /ingest/url              │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│        Backend (FastAPI)                │
│  1. URL Recon (analyze_url)             │
│  2. Route: Video site → yt-dlp          │
│           Article → Image scraper       │
│  3. Create Media record in DB           │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      AI Analysis Pipeline               │
│  1. Extract frames (if video)           │
│  2. For each frame:                     │
│     - detect_faces() → bounding boxes   │
│     - generate_embedding() → 512-d vec  │
│     - detect_objects() → scene context  │
│  3. Match/Create Officer records        │
│  4. Save OfficerAppearance              │
└─────────────────────────────────────────┘
         │
         ▼ (via Socket.IO)
┌─────────────────────────────────────────┐
│       LiveAnalysis Component            │
│  - Real-time frame visualization        │
│  - Progress logs                        │
│  - Candidate officer cards              │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         ReportPage                      │
│  - Display identified officers          │
│  - Statistics                           │
│  - Print-friendly layout                │
└─────────────────────────────────────────┘
```

---

## Socket.IO Events

| Event | Direction | Payload | Purpose |
|-------|-----------|---------|---------|
| `log` | Server→Client | string | Status message |
| `analyzing_frame` | Server→Client | `{url, timestamp, frame_id}` | Current frame being processed |
| `candidate_officer` | Server→Client | `{image_url, timestamp, confidence, badge, quality, meta}` | Detection result |
| `status_update` | Server→Client | string | Processing phase |
| `recon_result` | Server→Client | `{category, score, keywords, recommendation}` | URL analysis |
| `scraped_image` | Server→Client | `{url, filename}` | Scraped image notification |
| `media_created` | Server→Client | `{media_id}` | Media record created |
| `complete` | Server→Client | `{message, media_id}` | Processing finished |
| `join_task` | Client→Server | task_id | Join processing room |

---

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@localhost/protest_db` |
| `PORT` | Backend server port | `8000` |
| `VITE_API_BASE` | Frontend API endpoint | `http://localhost:8000` |

### Face Recognition Matching

- **Embedding Distance**: Euclidean distance between 512-d vectors
- **Match Threshold**: 0.8 (conservative - lower = stricter matching)
- **Model**: InceptionResnetV1 pretrained on VGGFace2

### Face Detection

- **Model**: OpenCV DNN with Caffe SSD
- **Confidence Threshold**: 0.5
- **Minimum Size**: 10x10 pixels

---

## Key State Variables

### Frontend (UploadPage.jsx)
- `activeTab` - 'upload' | 'link'
- `submitStatus` - null | 'loading' | 'success' | 'error'
- `liveTaskId` - Task ID for LiveAnalysis (when set, shows analysis UI)

### Frontend (LiveAnalysis.jsx)
- `status` - 'connecting' | 'active' | 'complete' | 'error'
- `logs` - Array of log messages
- `candidates` - Array of detected officers
- `currentFrame` - Currently analyzing frame data
- `reconData` - URL reconnaissance results
- `mediaId` - Final media ID for report generation

### Backend Processing
- Processing happens in background tasks via FastAPI's `BackgroundTasks`
- Socket.IO events bridge async backend to real-time frontend
- Database sessions are created per-operation with proper cleanup
