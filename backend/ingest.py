import os
import requests
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal, engine
import models
from logging_config import get_logger, log_error
from utils.paths import save_file, normalize_for_storage

logger = get_logger("ingest")

# Ensure media directory exists
MEDIA_DIR = "data/media"
os.makedirs(MEDIA_DIR, exist_ok=True)

def ingest_media(url: str, protest_id: int, media_type: str, db: Session) -> Optional[models.Media]:
    """
    Downloads media from a URL and saves it to the database.

    Args:
        url: URL to download media from
        protest_id: ID of the protest to associate with
        media_type: Type of media ('image' or 'video')
        db: Database session

    Returns:
        Media object if successful, None on failure
    """
    logger.info(f"Ingesting media from URL", extra_data={"url": url, "protest_id": protest_id})

    # Generate unique filename
    ext = ".jpg" if media_type == "image" else ".mp4"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(MEDIA_DIR, filename)

    # Download
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Downloaded media to {filepath}")

        # Upload to R2 if enabled
        storage_key = save_file(filepath, normalize_for_storage(filepath))

        # Save to DB with normalized storage path
        db_media = models.Media(
            url=storage_key,  # Store normalized path (works for both local and R2)
            type=media_type,
            protest_id=protest_id,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(db_media)
        db.commit()
        db.refresh(db_media)
        logger.info(f"Media record created", extra_data={"media_id": db_media.id})
        return db_media

    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading media", extra_data={"url": url})
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error downloading media", extra_data={"url": url, "status": e.response.status_code if e.response else None})
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error downloading media", extra_data={"url": url, "error": str(e)})
        return None
    except (IOError, OSError) as e:
        logger.error(f"File error saving media", extra_data={"filepath": filepath, "error": str(e)})
        return None
    except SQLAlchemyError as e:
        log_error(logger, e, context={"url": url, "filepath": filepath})
        db.rollback()
        return None

def save_upload(
    file_obj,
    filename: str,
    protest_id: Optional[int],
    media_type: str,
    db: Session,
    check_duplicates: bool = True
) -> Tuple[Optional[models.Media], Optional[Dict[str, Any]]]:
    """
    Saves an uploaded file to disk and creates DB record.
    Optionally checks for duplicates before saving.

    Args:
        file_obj: File object or bytes to save
        filename: Original filename
        protest_id: ID of protest to associate with (None for general uploads)
        media_type: Type of media ('image' or 'video')
        db: Database session
        check_duplicates: Whether to check for duplicates

    Returns:
        Tuple of (Media object, duplicate_info dict or None)
        If duplicate found, returns (media, duplicate_info)
        On error, returns (None, None)
    """
    from ai.duplicate_detector import DuplicateDetector, compute_content_hash, compute_perceptual_hash, get_file_size

    logger.info(f"Saving upload", extra_data={"filename": filename, "protest_id": protest_id})

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
        logger.info(f"Assigned to General Uploads", extra_data={"protest_id": protest_id})

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

        logger.info(f"Saved upload to disk", extra_data={"filepath": filepath})

        # Upload to R2 if enabled (do this after saving locally for hash computation)
        storage_key = normalize_for_storage(filepath)

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
                logger.info(
                    f"Duplicate detected",
                    extra_data={
                        "duplicate_type": dup_result['duplicate_type'],
                        "original_id": dup_result['original_id']
                    }
                )

                # Get original media for reference
                original_media = db.query(models.Media).filter(
                    models.Media.id == dup_result["original_id"]
                ).first()

                # Upload to R2 even for duplicates (for consistency)
                save_file(filepath, storage_key)

                # Still save but mark as duplicate
                db_media = models.Media(
                    url=storage_key,  # Use normalized storage key
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

        # Upload to R2 if enabled
        save_file(filepath, storage_key)

        # Save to DB (not a duplicate)
        db_media = models.Media(
            url=storage_key,  # Use normalized storage key
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

    except (IOError, OSError) as e:
        logger.error(f"File error saving upload", extra_data={"filepath": filepath, "error": str(e)})
        _cleanup_file(filepath)
        return None, None
    except SQLAlchemyError as e:
        log_error(logger, e, context={"filename": filename, "filepath": filepath})
        db.rollback()
        _cleanup_file(filepath)
        return None, None


def _cleanup_file(filepath: str) -> None:
    """Safely remove a file if it exists."""
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.debug(f"Cleaned up file", extra_data={"filepath": filepath})
        except OSError as e:
            logger.warning(f"Failed to cleanup file", extra_data={"filepath": filepath, "error": str(e)})

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
