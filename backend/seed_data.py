from database import SessionLocal
import models
from datetime import datetime, timezone
import os

def seed():
    db = SessionLocal()
    
    # 1. Ensure protest
    protest = db.query(models.Protest).first()
    if not protest:
        protest = models.Protest(
            name="London March for Palestine",
            date=datetime.now(timezone.utc),
            location="Parliament Square, London",
            latitude="51.5007",
            longitude="-0.1246",
            description="Large demonstration calling for ceasefire."
        )
        db.add(protest)
        db.commit()
        db.refresh(protest)
        print("Seeded protest.")

    # 2. Ensure media
    # Create dummy image file
    media_dir = "../data/media"
    os.makedirs(media_dir, exist_ok=True)
    dummy_path = "../data/media/test_officer_face.png"
    # Ensure the file exists (we just copied it)
    
    media = db.query(models.Media).filter(models.Media.url.like("%test_officer_face.png%")).first()
    if not media:
        media = models.Media(
            url=dummy_path,
            type='image',
            protest_id=protest.id,
            timestamp=datetime.now(timezone.utc),
            processed=False
        )
        db.add(media)
        db.commit()
        print("Seeded media.")
    else:
        print("Media already exists. Resetting processed status for testing.")
        media.processed = False
        db.commit()

if __name__ == "__main__":
    seed()
