import cv2
import os
import shutil
import json
import numpy as np
import models
from database import SessionLocal

FRAMES_DIR = "../data/frames"
os.makedirs(FRAMES_DIR, exist_ok=True)

def process_media(media_id: int):
    db = SessionLocal()
    media_item = db.query(models.Media).filter(models.Media.id == media_id).first()
    
    if not media_item:
        print(f"Media {media_id} not found.")
        return

    print(f"Processing media {media_id}: {media_item.url}")
    
    media_frames_dir = os.path.join(FRAMES_DIR, str(media_item.id))
    os.makedirs(media_frames_dir, exist_ok=True)
    
    if media_item.type == "video":
        extract_frames(media_item, media_frames_dir)
    else:
        # For images, treat as a single frame
        target_path = os.path.join(media_frames_dir, "frame_0000.jpg")
        # Handle if path is relative or absolute
        # media_item.url might be "../data/media/..."
        # shutil.copy2 likely works if Cwd is correct
        try:
             shutil.copy2(media_item.url, target_path)
             print(f"Copied image to {target_path}")
        except Exception as e:
            print(f"Error copying image: {e}")
            return

    # Run AI Analysis
    analyze_frames(media_item, media_frames_dir)

    media_item.processed = True
    db.commit()
    print(f"Media {media_id} marked as processed.")

def extract_frames(media_item, media_frames_dir, interval_seconds=1):
    cap = cv2.VideoCapture(media_item.url)
    if not cap.isOpened():
        print(f"Error opening video file {media_item.url}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30 # Default fallback
        
    frame_interval = int(fps * interval_seconds)
    count = 0
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if count % frame_interval == 0:
            frame_path = os.path.join(media_frames_dir, f"frame_{frame_count:04d}.jpg")
            cv2.imwrite(frame_path, frame)
            print(f"Saved {frame_path}")
            frame_count += 1
            
        count += 1

    cap.release()
    print(f"Extracted {frame_count} frames.")

def analyze_frames(media_item, media_frames_dir):
    from ai import process_image_ai
    
    print("Running AI analysis on frames...")
    
    db = SessionLocal()
    # Re-fetch media item to ensure session attachment if needed, though we passed it.
    # But best to use ID if unsure.
    media_item = db.merge(media_item)

    frames = sorted([os.path.join(media_frames_dir, f) for f in os.listdir(media_frames_dir) if f.endswith(".jpg")])
    
    existing_officers = db.query(models.Officer).all()
    
    for frame_path in frames:
        results = process_image_ai(frame_path, media_frames_dir)
        
        for res in results:
            print(f"Found officer in {frame_path}")
            
            matched_officer = None
            
            # 1. Try matching by badge
            if res.get('badge'):
                badge = res['badge']
                if len(badge) > 2: # validation
                    matched_officer = db.query(models.Officer).filter(models.Officer.badge_number.like(f"%{badge}%")).first()
                    if matched_officer:
                        print(f"Matched by badge: {badge}")
            
            # 2. Try matching by face encoding
            # (Deferred/Implementing basic shim)
            encoding = res.get('encoding')
            if not matched_officer and encoding is not None:
                # Compare logic would go here
                pass
            
            # 3. Create new if not found
            if not matched_officer:
                # print("Creating new officer") 
                # (Commented out to reduce noise if many faces, but for test it's fine)
                matched_officer = models.Officer(
                    badge_number=res.get('badge'),
                    visual_id=None, # No encoding yet
                    force="Unknown",
                    notes="Auto-detected"
                )
                db.add(matched_officer)
                db.commit()
                db.refresh(matched_officer)
                existing_officers.append(matched_officer)
            
            # Create Appearance
            appearance = models.OfficerAppearance(
                officer_id=matched_officer.id,
                media_id=media_item.id,
                timestamp_in_video="00:00:00", 
                image_crop_path=res['crop_path'],
                role=res['role'],
                action=res['action']
            )
            db.add(appearance)
            
    db.commit()
    print("AI Analysis complete.")

if __name__ == "__main__":
    # Test run: Find unprocessed media
    db = SessionLocal()
    unprocessed = db.query(models.Media).filter(models.Media.processed == False).all()
    print(f"Found {len(unprocessed)} unprocessed items.")
    for item in unprocessed:
        process_media(item.id)
