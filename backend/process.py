import cv2
import os
import shutil
import json
import numpy as np
import models
from scipy.spatial.distance import euclidean, cosine
from database import SessionLocal
from sqlalchemy import select
from sqlalchemy.orm import Session
from contextlib import contextmanager

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Face matching configuration
# Euclidean distance threshold: Lower = stricter matching
FACE_MATCH_THRESHOLD_EUCLIDEAN = 0.7

# Cosine similarity threshold: Higher = stricter matching
FACE_MATCH_THRESHOLD_COSINE = 0.6

# Frame extraction settings
DEFAULT_FRAME_INTERVAL_SECONDS = 1
DEFAULT_VIDEO_FPS = 30

# Processing limits
MAX_FRAMES_PER_VIDEO = 500
MIN_IMAGE_SIZE_BYTES = 5000

# Uniform Analysis configuration
# Set ENABLE_AUTO_UNIFORM_ANALYSIS=true in environment to enable automatic analysis
ENABLE_AUTO_UNIFORM_ANALYSIS = os.environ.get('ENABLE_AUTO_UNIFORM_ANALYSIS', 'false').lower() == 'true'
UNIFORM_ANALYSIS_RATE_LIMIT = int(os.environ.get('UNIFORM_ANALYSIS_RATE_LIMIT', '10'))  # per minute


def calculate_face_similarity(embedding1, embedding2):
    """
    Calculate similarity between two face embeddings.
    Returns (is_match, confidence, distance_euclidean, similarity_cosine)
    """
    if embedding1 is None or embedding2 is None:
        return False, 0.0, float('inf'), 0.0

    # Convert to numpy arrays if needed
    emb1 = np.array(embedding1)
    emb2 = np.array(embedding2)

    # Calculate Euclidean distance
    dist_euclidean = euclidean(emb1, emb2)

    # Calculate cosine similarity (1 - cosine distance)
    sim_cosine = 1 - cosine(emb1, emb2)

    # Determine if it's a match using both metrics
    # Both must pass their thresholds for a confident match
    euclidean_match = dist_euclidean < FACE_MATCH_THRESHOLD_EUCLIDEAN
    cosine_match = sim_cosine > FACE_MATCH_THRESHOLD_COSINE

    is_match = euclidean_match and cosine_match

    # Calculate confidence as a combination of both metrics
    # Normalize Euclidean distance to 0-1 range (inverse, so lower distance = higher confidence)
    euclidean_conf = max(0, 1 - (dist_euclidean / 2.0))  # Assume max meaningful distance is ~2.0
    cosine_conf = sim_cosine

    # Combined confidence (weighted average)
    confidence = (euclidean_conf * 0.4 + cosine_conf * 0.6)

    return is_match, confidence, dist_euclidean, sim_cosine

FRAMES_DIR = "data/frames"
os.makedirs(FRAMES_DIR, exist_ok=True)


def run_uniform_analysis(appearance_id: int, image_path: str, db: Session, status_callback=None):
    """
    Run Claude Vision uniform analysis on an officer appearance.
    Only runs if ENABLE_AUTO_UNIFORM_ANALYSIS is True and ANTHROPIC_API_KEY is set.
    """
    if not ENABLE_AUTO_UNIFORM_ANALYSIS:
        return

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Uniform analysis skipped: ANTHROPIC_API_KEY not set")
        return

    try:
        from ai.uniform_analyzer import UniformAnalyzer

        if status_callback:
            status_callback("log", "Running uniform analysis...")

        analyzer = UniformAnalyzer(api_key=api_key, rate_limit=UNIFORM_ANALYSIS_RATE_LIMIT)
        result = analyzer.analyze_uniform_sync(image_path)

        if not result.get('success'):
            print(f"Uniform analysis failed: {result.get('error')}")
            return

        # Parse to DB format
        db_data = analyzer.parse_to_db_format(result, appearance_id)
        if not db_data:
            return

        # Save uniform analysis
        uniform_analysis = models.UniformAnalysis(**db_data)
        db.add(uniform_analysis)

        # Save equipment detections
        equipment_items = analyzer.extract_equipment(result)
        for eq_item in equipment_items:
            # Find equipment by name
            equip = db.query(models.Equipment).filter(
                models.Equipment.name == eq_item['name']
            ).first()

            if equip:
                detection = models.EquipmentDetection(
                    appearance_id=appearance_id,
                    equipment_id=equip.id,
                    confidence=eq_item.get('confidence')
                )
                db.add(detection)

        # Update officer force if high confidence
        analysis_data = result.get('analysis', {})
        force_info = analysis_data.get('force', {})
        if force_info.get('confidence', 0) >= 0.8 and force_info.get('name'):
            appearance = db.query(models.OfficerAppearance).filter(
                models.OfficerAppearance.id == appearance_id
            ).first()
            if appearance:
                officer = db.query(models.Officer).filter(
                    models.Officer.id == appearance.officer_id
                ).first()
                if officer and (not officer.force or officer.force == 'Unknown'):
                    officer.force = force_info['name']
                    print(f"Updated officer force to: {force_info['name']}")

        db.commit()

        if status_callback:
            force_name = force_info.get('name', 'Unknown')
            status_callback("log", f"Uniform analysis complete: {force_name}")

        print(f"Uniform analysis saved for appearance {appearance_id}")

    except ImportError as e:
        print(f"Uniform analysis skipped: {e}")
    except Exception as e:
        print(f"Uniform analysis error: {e}")

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



def extract_frames(media_item, media_frames_dir, interval_seconds=None):
    """
    Extract frames from video at specified interval.
    Uses context manager pattern to ensure VideoCapture is always released.
    """
    if interval_seconds is None:
        interval_seconds = DEFAULT_FRAME_INTERVAL_SECONDS

    cap = cv2.VideoCapture(media_item.url)
    try:
        if not cap.isOpened():
            print(f"Error opening video file {media_item.url}")
            return 0

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            fps = DEFAULT_VIDEO_FPS

        frame_interval = int(fps * interval_seconds)
        if frame_interval < 1:
            frame_interval = 1

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

                # Safety limit to prevent processing extremely long videos
                if frame_count >= MAX_FRAMES_PER_VIDEO:
                    print(f"Reached max frame limit ({MAX_FRAMES_PER_VIDEO})")
                    break

            count += 1

        print(f"Extracted {frame_count} frames.")
        return frame_count
    finally:
        cap.release()

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

            # Emit the current frame for the frontend visualizer
            if status_callback:
                # Construct relative URL for the frame. 
                # Assuming FRAMES_DIR is "data/frames", file is "data/frames/123/frame_001.jpg"
                # URL should be "/data/frames/123/frame_001.jpg"
                frame_rel_path = os.path.relpath(frame_path, start=os.getcwd())
                frame_url = f"/{frame_rel_path}"
                
                status_callback("analyzing_frame", {
                    "url": frame_url,
                    "timestamp": timestamp_str,
                    "frame_id": frame_filename
                })
                
                status_callback("status_update", "Scanning")

            results = analyzer.process_image_ai(frame_path, media_frames_dir)
            
            # Log summary to UI (skip empty frames to reduce spam)
            if len(results) > 0:
                 if status_callback: 
                     status_callback("log", f"AI Scan: Found {len(results)} targets in {os.path.basename(frame_path)}")
                     status_callback("status_update", "Harvesting")
            
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
                    image_url = f"/data/{os.path.relpath(res['crop_path'], start='data')}"

                    status_callback("candidate_officer", {
                        "image_url": image_url,
                        "timestamp": timestamp_str,
                        "confidence": res.get('confidence', 0.9),
                        "badge": res.get('badge'),
                        "quality": res.get('quality'),
                    })
                    status_callback("log", f"Found officer at {timestamp_str}")
                
                matched_officer = None
                best_match_confidence = 0.0

                embedding = analyzer.generate_embedding(res['crop_path'])

                # Match with existing officers using improved algorithm
                if embedding is not None:
                    # Fetch all officers with embeddings
                    existing_officers_with_embeddings = db.query(models.Officer).filter(models.Officer.visual_id.isnot(None)).all()

                    for off in existing_officers_with_embeddings:
                        try:
                            off_emb = json.loads(off.visual_id)
                            is_match, confidence, dist_euc, sim_cos = calculate_face_similarity(embedding, off_emb)

                            if is_match and confidence > best_match_confidence:
                                best_match_confidence = confidence
                                matched_officer = off
                                print(f"Face {i}: Potential match with Officer {off.id} "
                                      f"(conf={confidence:.3f}, dist={dist_euc:.3f}, cos_sim={sim_cos:.3f})")

                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode visual_id for officer {off.id}")
                            continue
                        except Exception as e:
                            print(f"Error comparing embeddings for officer {off.id}: {e}")
                            continue

                    if matched_officer:
                        print(f"Face {i}: Best match is Officer {matched_officer.id} with confidence {best_match_confidence:.3f}")
                    else:
                        print(f"Face {i}: No matching officer found (new face)")
    
                if matched_officer:
                    print(f"Matched existing Officer {matched_officer.id} (Confidence: {best_match_confidence:.4f})")
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
                # Extract labels from detection dicts and filter for relevant items
                relevant_labels = [obj['label'] for obj in objects if obj['label'] in ['baseball bat', 'knife', 'cell phone', 'handbag', 'backpack', 'umbrella', 'tie']]
                action_desc = "Observed"
                if relevant_labels:
                    action_desc += f"; Holding: {', '.join(relevant_labels)}"
                    print(f"Detected objects: {relevant_labels}")
    
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
                db.refresh(appearance)

                # 8. Optional: Run uniform analysis (if enabled)
                if res['crop_path'] and os.path.exists(res['crop_path']):
                    run_uniform_analysis(appearance.id, res['crop_path'], db, status_callback)
    
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
