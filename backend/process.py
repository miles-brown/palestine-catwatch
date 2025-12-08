import cv2
import os
import shutil
import json
import numpy as np
import models
import json
from scipy.spatial.distance import euclidean
from database import SessionLocal

FRAMES_DIR = "data/frames"
os.makedirs(FRAMES_DIR, exist_ok=True)

def process_media(media_id: int, status_callback=None):
    db = SessionLocal()
    try:
        if status_callback:
            status_callback("log", f"Starting processing for media {media_id}")
            
        media_item = db.query(models.Media).filter(models.Media.id == media_id).first()
        
        if not media_item:
            print(f"Media {media_id} not found.")
            return

        print(f"Processing media {media_id}: {media_item.url}")
        if status_callback:
             status_callback("log", f"Processing file: {os.path.basename(media_item.url)}")
        
        media_frames_dir = os.path.join(FRAMES_DIR, str(media_item.id))
        os.makedirs(media_frames_dir, exist_ok=True)
        
        if media_item.type == "video":
            if status_callback: status_callback("log", "Extracting frames...")
            extract_frames(media_item, media_frames_dir)
        else:
            # For images, treat as a single frame
            target_path = os.path.join(media_frames_dir, "frame_0000.jpg")
            try:
                 shutil.copy2(media_item.url, target_path)
                 print(f"Copied image to {target_path}")
            except Exception as e:
                print(f"Error copying image: {e}")
                return

        analyze_frames(media_item.id, media_frames_dir, status_callback) # Pass ID instead of object
        
        # Mark as processed
        media_item.processed = True
        db.commit()
    finally:
        db.close()



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

def get_timestamp_str(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

def analyze_frames(media_id, media_frames_dir, status_callback=None):
    from ai import analyzer
    
    print("Running AI analysis on frames...")
    if status_callback: status_callback("log", "Running AI analysis on frames...")
    
    db = SessionLocal()
    try:
        media_item = db.query(models.Media).filter(models.Media.id == media_id).first()
        if not media_item:
             print(f"Media {media_id} not found during analysis.")
             return

        frames = sorted([
            os.path.join(media_frames_dir, f) 
            for f in os.listdir(media_frames_dir) 
            if f.endswith(".jpg") and not f.startswith("face_") and not f.startswith("crop_")
        ])
        
        existing_officers = db.query(models.Officer).all()
        
        for frame_path in frames:
            # Calculate timestamp from filename (frame_XXXX.jpg -> XXXX seconds)
            frame_filename = os.path.basename(frame_path)
            try:
                frame_idx = int(frame_filename.split('_')[1].split('.')[0])
                timestamp_str = get_timestamp_str(frame_idx) # Assuming 1s interval
            except Exception:
                timestamp_str = "00:00:00"

            if status_callback: status_callback("status_update", "Thinking")
            results = analyzer.process_image_ai(frame_path, media_frames_dir)
            
            # Log summary to UI
            if len(results) == 0:
                 if status_callback: 
                     status_callback("log", f"AI Scan: No targets detected in {os.path.basename(frame_path)}")
                     status_callback("status_update", "Scanning")
            else:
                 if status_callback: 
                     status_callback("log", f"AI Scan: Found {len(results)} targets in {os.path.basename(frame_path)}")
                     status_callback("status_update", "Havesting")
            
            for i, res in enumerate(results):
                if res.get('is_scene_summary'):
                    # Just log the context objects
                    objs = ", ".join(res.get('objects', []))
                    print(f"Scene summary for {frame_path}: {objs}")
                    if status_callback: status_callback("log", f"AI Context: Detected {objs}")
                    continue

                print(f"Found officer in {frame_path} at {timestamp_str}")
                if status_callback:
                    # Construct URL for the crop
                    # Assuming crop_path is relative to project root or absolute
                    # If relative to project root (e.g. data/frames/...), URL is /data/frames/...
                    # We need to ensure paths are correct. 
                    # analyzer.process_image_ai returns paths. Let's assume they are relative to CWD if created there.
                    # Safe bet: relative path from 'data' folder.
                    
                    crop_rel_path = os.path.relpath(res['crop_path'], start=os.getcwd())
                    image_url = f"/data/{os.path.relpath(res['crop_path'], start='data')}"
                    
                    status_callback("candidate_officer", {
                        "image_url": image_url,
                        "timestamp": timestamp_str,
                        "confidence": res.get('confidence', 0.9),
                        "badge": res.get('badge'),
                        "quality": res.get('quality'),
                        "meta": {
                            "uniform_guess": "Metropolitan Police" if "London" in "London" else "Unknown", # Mock logic
                            "rank_guess": "Constable" # Mock logic
                        }
                    })
                    status_callback("log", f"Found officer at {timestamp_str}")
                
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
    
                # 5. Extract Text (Badge Number)
                badge_text = analyzer.extract_text(res['crop_path'])
                badge_str = ", ".join(badge_text) if badge_text else None
                if badge_str:
                    print(f"OCR found text: {badge_str}")
                    # Ideally update officer badge number if confident
                
                # 6. Object Detection (Context)
                objects = analyzer.detect_objects(frame_path)
                relevant_objects = [obj for obj in objects if obj in ['baseball bat', 'knife', 'cell phone', 'handbag', 'backpack']]
                action_desc = "Observed"
                if relevant_objects:
                    action_desc += f"; Holding: {', '.join(relevant_objects)}"
                    print(f"Detected objects: {relevant_objects}")
    
                # 7. Record Appearance
                appearance = models.OfficerAppearance(
                    officer_id=officer.id,
                    media_id=media_item.id,
                    timestamp_in_video=timestamp_str,
                    image_crop_path=res['crop_path'], # Use the full crop_path
                    role="Unknown",
                    action=action_desc
                )
                db.add(appearance)
                db.commit()
    
        db.commit()
        print("AI Analysis complete.")
    finally:
        db.close()
if __name__ == "__main__":
    # Test run: Find unprocessed media
    db = SessionLocal()
    unprocessed = db.query(models.Media).filter(models.Media.processed == False).all()
    print(f"Found {len(unprocessed)} unprocessed items.")
    for item in unprocessed:
        process_media(item.id)
