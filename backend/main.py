from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas
from database import get_db, engine
from datetime import datetime
import asyncio

try:
    print("Attempting to connect to database and create tables...")
    models.Base.metadata.create_all(bind=engine)
    
    # --- HOTFIX FOR SCHEMA ---
    # Drop the index on visual_id because it is too large (vector) for b-tree
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_officers_visual_id"))
        conn.commit()
        print("Schema Patch: Dropped ix_officers_visual_id index.")
    # -------------------------
        
    print("Database tables created successfully.")
except Exception as e:
    print(f"Startup Warning: Database connection failed. App will start but DB features will fail. Error: {e}")

from pydantic import BaseModel
class IngestURLRequest(BaseModel):
    url: str
    protest_id: Optional[int] = None
    answers: dict = {}


app = FastAPI(title="Palestine Catwatch API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO
from sio import sio_app, sio_server
app.mount("/socket.io", sio_app)

# Mount data directory to serve images
# Mount data directory to serve images
import os
os.makedirs("data", exist_ok=True)
app.mount("/data", StaticFiles(directory="data"), name="data")

@app.get("/")
def read_root():
    return {"message": "Palestine Catwatch Backend Operational"}

@app.get("/officers", response_model=List[schemas.Officer])
def get_officers(
    skip: int = 0, 
    limit: int = 100, 
    badge_number: str = None,
    force: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Officer)
    
    if badge_number:
        query = query.filter(models.Officer.badge_number.contains(badge_number))
    if force:
        query = query.filter(models.Officer.force == force)
        
    officers = query.offset(skip).limit(limit).all()
    return officers

@app.get("/officers/{officer_id}", response_model=schemas.Officer)
def get_officer(officer_id: int, db: Session = Depends(get_db)):
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

@app.post("/ingest/url")
async def ingest_media_url(request: IngestURLRequest, background_tasks: BackgroundTasks):
    """
    Ingest a URL (YouTube, web).
    Triggers background download and analysis.
    """
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

    background_tasks.add_task(background_wrapper, request.url, request.answers, request.protest_id, task_id, loop)
    
    return {"status": "processing_started", "message": "Video queued for analysis.", "task_id": task_id}

@app.get("/protests")
def get_protests(db: Session = Depends(get_db)):
    return db.query(models.Protest).all()

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    protest_id: Optional[int] = Form(None),
    type: str = Form(...),
    db: Session = Depends(get_db)
):
    from ingest import save_upload
    
    # Validate type
    if type not in ["image", "video"]:
         raise HTTPException(status_code=400, detail="Invalid media type. Must be 'image' or 'video'.")

    media = save_upload(file.file, file.filename, protest_id, type, db)
    
    if not media:
        raise HTTPException(status_code=500, detail="File upload failed")
        
    # Trigger processing
    from process import process_media
    process_media(media.id)
    
    return {"status": "uploaded", "media_id": media.id, "filename": file.filename}

