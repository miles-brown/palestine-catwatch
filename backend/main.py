from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db, engine

models.Base.metadata.create_all(bind=engine)

from pydantic import BaseModel
class IngestURLRequest(BaseModel):
    url: str
    protest_id: int = None
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
from sio import sio_app
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
async def ingest_media_url(request: IngestURLRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Ingest a URL (YouTube, web).
    Triggers background download and analysis.
    """
    try:
        from ingest_video import process_video_workflow
    except ImportError as e:
        print(f"Import Error in ingest endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Server Configuration Error: {e}")
    except Exception as e:
        print(f"Unexpected Error in ingest endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Server Internal Error: {e}")

    import asyncio
    from datetime import datetime
    from sio import sio_server
    
    # Validation logic here (mock)
    if "2 + 3" in str(request.answers):
         pass
    
    # Create a unique Task ID and room
    # We will return this ID so the frontend can join the room
    task_id = f"task_{int(datetime.utcnow().timestamp())}"

    # We need to capture the current event loop to schedule async emits from the sync background thread
    loop = asyncio.get_running_loop()

    def background_wrapper(url, answers, protest_id, room_id, event_loop):
        def callback(event, data):
            # Schedule the emit coroutine on the main event loop
            # This is thread-safe
            asyncio.run_coroutine_threadsafe(
                sio_server.emit(event, data, room=room_id),
                event_loop
            )
        
        process_video_workflow(url, answers, protest_id, status_callback=callback)

    background_tasks.add_task(background_wrapper, request.url, request.answers, request.protest_id, task_id, loop)
    
    return {"status": "processing_started", "message": "Video queued for analysis.", "task_id": task_id}

@app.get("/protests")
def get_protests(db: Session = Depends(get_db)):
    return db.query(models.Protest).all()

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    protest_id: int = Form(...),
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

