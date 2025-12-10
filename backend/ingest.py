import os
import requests
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

# Ensure media directory exists
MEDIA_DIR = "data/media"
os.makedirs(MEDIA_DIR, exist_ok=True)

def ingest_media(url: str, protest_id: int, media_type: str, db: Session):
    """
    Downloads media from a URL and saves it to the database.
    """
    print(f"Ingesting {url} for protest {protest_id}...")
    
    # Generate unique filename
    ext = ".jpg" if media_type == "image" else ".mp4"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(MEDIA_DIR, filename)
    
    # Download
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"Saved to {filepath}")
        
        # Save to DB
        db_media = models.Media(
            url=filepath, # Storing local path for now
            type=media_type,
            protest_id=protest_id,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(db_media)
        db.commit()
        db.refresh(db_media)
        print(f"Media record created with ID: {db_media.id}")
        return db_media
        
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def save_upload(file_obj, filename: str, protest_id: int, media_type: str, db: Session, check_duplicates: bool = True):
    """
    Saves an uploaded file to disk and creates DB record.
    Optionally checks for duplicates before saving.

    Returns:
        Tuple of (Media object, duplicate_info dict or None)
        If duplicate found, returns (original_media, duplicate_info)
    """
    from ai.duplicate_detector import DuplicateDetector, compute_content_hash, compute_perceptual_hash, get_file_size

    print(f"Saving upload {filename} for protest {protest_id}...")

    if protest_id is None:
        # Find or create "General Uploads" protest
        general_protest = db.query(models.Protest).filter(models.Protest.name == "General Uploads").first()
        if not general_protest:
            general_protest = models.Protest(
                name="General Uploads",
                date=datetime.now(timezone.utc),
                location="N/A",
                description="Bucket for uploads without a specific protest."
            )
            db.add(general_protest)
            db.commit()
            db.refresh(general_protest)
        protest_id = general_protest.id
        print(f"Assigned to General Uploads (ID: {protest_id})")

    # Generate unique filename (keep extension from original if possible, else default)
    _, ext = os.path.splitext(filename)
    if not ext:
        ext = ".jpg" if media_type == "image" else ".mp4"

    unique_filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(MEDIA_DIR, unique_filename)

    try:
        with open(filepath, "wb") as buffer:
            # Handle both bytes and file-like objects (FastAPI UploadFile.file)
            if hasattr(file_obj, "read"):
                # Read in chunks
                while content := file_obj.read(1024 * 1024):  # 1MB chunks
                    buffer.write(content)
            else:
                buffer.write(file_obj)

        print(f"Saved to {filepath}")

        # Compute hashes for duplicate detection
        content_hash = compute_content_hash(filepath)
        perceptual_hash = compute_perceptual_hash(filepath) if media_type == "image" else None
        file_size = get_file_size(filepath)

        # Check for duplicates
        duplicate_info = None
        if check_duplicates and content_hash:
            detector = DuplicateDetector(db)
            dup_result = detector.check_for_duplicate(filepath, media_type)

            if dup_result["is_duplicate"]:
                duplicate_info = dup_result
                print(f"Duplicate detected! Type: {dup_result['duplicate_type']}, Original ID: {dup_result['original_id']}")

                # Get original media for reference
                original_media = db.query(models.Media).filter(
                    models.Media.id == dup_result["original_id"]
                ).first()

                # Still save but mark as duplicate
                db_media = models.Media(
                    url=filepath,
                    type=media_type,
                    protest_id=protest_id,
                    timestamp=datetime.now(timezone.utc),
                    content_hash=content_hash,
                    perceptual_hash=perceptual_hash,
                    file_size=file_size,
                    is_duplicate=True,
                    duplicate_of_id=dup_result["original_id"]
                )
                db.add(db_media)
                db.commit()
                db.refresh(db_media)
                return db_media, duplicate_info

        # Save to DB (not a duplicate)
        db_media = models.Media(
            url=filepath,
            type=media_type,
            protest_id=protest_id,
            timestamp=datetime.now(timezone.utc),
            content_hash=content_hash,
            perceptual_hash=perceptual_hash,
            file_size=file_size,
            is_duplicate=False
        )
        db.add(db_media)
        db.commit()
        db.refresh(db_media)
        return db_media, None

    except Exception as e:
        print(f"Error saving upload: {e}")
        # Clean up file if it was created
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass
        return None, None

if __name__ == "__main__":
    # Test run
    db = SessionLocal()
    # Create a dummy protest if none exists
    protest = db.query(models.Protest).first()
    if not protest:
        protest = models.Protest(
            name="Test Protest",
            date=datetime.now(timezone.utc),
            location="London",
            description="Initial test protest"
        )
        db.add(protest)
        db.commit()
        db.refresh(protest)
    
    # Test with a placeholder image
    test_url = "https://via.placeholder.com/600x400.jpg"
    ingest_media(test_url, protest.id, "image", db)
