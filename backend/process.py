import cv2
import os
import shutil
import json
import numpy as np
import models
import json
from scipy.spatial.distance import euclidean
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
    from ai import analyzer
    
    print("Running AI analysis on frames...")
    
    db = SessionLocal()
    # Re-fetch media item to ensure session attachment if needed, though we passed it.
    # But best to use ID if unsure.
    media_item = db.merge(media_item)

    frames = sorted([
        os.path.join(media_frames_dir, f) 
        for f in os.listdir(media_frames_dir) 
        if f.endswith(".jpg") and not f.startswith("face_") and not f.startswith("crop_")
    ])
    
    existing_officers = db.query(models.Officer).all()
    
    for frame_path in frames:
        results = analyzer.process_image_ai(frame_path, media_frames_dir)
        
        for i, res in enumerate(results):
            print(f"Found officer in {frame_path}")
            
            matched_officer = None
            
            embedding = analyzer.generate_embedding(res['crop_path'])
            
            # Match with existing officers
            matched_officer = None
            min_dist = 100.0
            
            if embedding is not None: # Check if embedding was successfully generated
                # Fetch all officers with embeddings
                existing_officers_with_embeddings = db.query(models.Officer).filter(models.Officer.visual_id.isnot(None)).all()
                
                for off in existing_officers_with_embeddings:
                    try:
                        off_emb = json.loads(off.visual_id)
                        dist = euclidean(embedding, off_emb)
                        if dist < min_dist:
                            min_dist = dist
                            matched_officer = off
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode visual_id for officer {off.id}")
                        continue
                    except Exception as e:
                        print(f"Error comparing embeddings for officer {off.id}: {e}")
                        continue
                
                print(f"Face {i}: Min Dist = {min_dist}")
                # Threshold for match (e.g. 0.6 for Facenet)
                if min_dist > 0.8: # Conservative threshold
                    matched_officer = None

            if matched_officer:
                print(f"Matched existing Officer {matched_officer.id} (Dist: {min_dist:.4f})")
                officer = matched_officer
            else:
                print("Creating new Officer.")
                # Create new officer
                officer = models.Officer(
                    badge_number=None, # OCR logic below could update this
                    force="Unknown",
                    visual_id=json.dumps(embedding) if embedding is not None else None,
                    notes="Auto-detected from media."
                )
                db.add(officer)
                db.commit()
                db.refresh(officer)

            # 5. Extract Text (Badge Number) - associate with this officer if plausible
            # ... logic for OCR assignment can be refined. For now, we just log unique texts.
            
            # 6. Record Appearance
            # Calculate timestamp
            timestamp_str = "00:00:00" # Placeholder, todo: calculate from frame_idx / fps
            
            appearance = models.OfficerAppearance(
                officer_id=officer.id,
                media_id=media_item.id,
                timestamp_in_video=timestamp_str,
                image_crop_path=res['crop_path'], # Use the full crop_path
                role="Unknown",
                action="Observed"
            )
            db.add(appearance)
            db.commit()
    db.commit()
    print("AI Analysis complete.")

if __name__ == "__main__":
    # Test run: Find unprocessed media
    db = SessionLocal()
    unprocessed = db.query(models.Media).filter(models.Media.processed == False).all()
    print(f"Found {len(unprocessed)} unprocessed items.")
    for item in unprocessed:
        process_media(item.id)
