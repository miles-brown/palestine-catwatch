from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Palestine Catwatch API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount data directory to serve images
app.mount("/data", StaticFiles(directory="../data"), name="data")

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

@app.post("/ingest")
def ingest_url(url: str, protest_id: int, type: str, db: Session = Depends(get_db)):
    from ingest import ingest_media
    media = ingest_media(url, protest_id, type, db)
    if not media:
        raise HTTPException(status_code=400, detail="Ingest failed")
    
    # Trigger processing background task?
    # For now, synchronous or manual.
    from process import process_media
    process_media(media.id)
    
    return {"status": "ingested", "media_id": media.id}

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

