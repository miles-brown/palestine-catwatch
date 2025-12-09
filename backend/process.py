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
from utils.paths import normalize_for_storage, get_absolute_path, get_web_url

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# =============================================================================
# FACE MATCHING CONFIGURATION
# =============================================================================
# These thresholds are calibrated for FaceNet InceptionResNetV1 embeddings (512-dim)
# Tested on UK police footage with varying lighting, angles, and occlusion

# Tiered matching thresholds (stricter = fewer false positives but may miss matches)
# STRICT: High confidence matches only - for automated linking
# MODERATE: Good balance - for suggested matches requiring review
# LOOSE: Catch more potential matches - for manual review queue

class MatchThreshold:
    """Face matching threshold configurations."""

    # Euclidean distance thresholds (lower = better match)
    # Typical same-person distances: 0.3-0.6
    # Typical different-person distances: 0.8-1.5+
    EUCLIDEAN_STRICT = 0.5
    EUCLIDEAN_MODERATE = 0.65
    EUCLIDEAN_LOOSE = 0.85

    # Cosine similarity thresholds (higher = better match)
    # Typical same-person similarity: 0.7-0.95
    # Typical different-person similarity: 0.2-0.6
    COSINE_STRICT = 0.75
    COSINE_MODERATE = 0.65
    COSINE_LOOSE = 0.55


# Environment-configurable default mode
MATCH_MODE = os.environ.get('FACE_MATCH_MODE', 'moderate').lower()

# Select thresholds based on mode
if MATCH_MODE == 'strict':
    FACE_MATCH_THRESHOLD_EUCLIDEAN = MatchThreshold.EUCLIDEAN_STRICT
    FACE_MATCH_THRESHOLD_COSINE = MatchThreshold.COSINE_STRICT
elif MATCH_MODE == 'loose':
    FACE_MATCH_THRESHOLD_EUCLIDEAN = MatchThreshold.EUCLIDEAN_LOOSE
    FACE_MATCH_THRESHOLD_COSINE = MatchThreshold.COSINE_LOOSE
else:  # moderate (default)
    FACE_MATCH_THRESHOLD_EUCLIDEAN = MatchThreshold.EUCLIDEAN_MODERATE
    FACE_MATCH_THRESHOLD_COSINE = MatchThreshold.COSINE_MODERATE

print(f"Face matching mode: {MATCH_MODE} (euclidean<{FACE_MATCH_THRESHOLD_EUCLIDEAN}, cosine>{FACE_MATCH_THRESHOLD_COSINE})")

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


def calculate_face_similarity(embedding1, embedding2, return_tier=False):
    """
    Calculate similarity between two face embeddings.

    Uses FaceNet InceptionResNetV1 512-dimensional embeddings.

    Args:
        embedding1: First face embedding (list or numpy array)
        embedding2: Second face embedding (list or numpy array)
        return_tier: If True, also return the confidence tier string

    Returns:
        (is_match, confidence, distance_euclidean, similarity_cosine)
        If return_tier=True: (is_match, confidence, distance_euclidean, similarity_cosine, tier)

    Confidence tiers:
        - "high": Very likely same person (auto-match safe)
        - "medium": Probable match (should verify)
        - "low": Possible match (needs review)
        - "none": Not a match
    """
    if embedding1 is None or embedding2 is None:
        result = (False, 0.0, float('inf'), 0.0)
        return (*result, "none") if return_tier else result

    # Convert to numpy arrays if needed
    emb1 = np.array(embedding1, dtype=np.float32)
    emb2 = np.array(embedding2, dtype=np.float32)

    # Validate embedding dimensions
    if emb1.shape != emb2.shape:
        print(f"Warning: Embedding dimension mismatch: {emb1.shape} vs {emb2.shape}")
        result = (False, 0.0, float('inf'), 0.0)
        return (*result, "none") if return_tier else result

    # Calculate Euclidean distance (L2 norm)
    dist_euclidean = float(euclidean(emb1, emb2))

    # Calculate cosine similarity (1 - cosine distance)
    # Handle edge case where vectors might be zero
    try:
        sim_cosine = float(1 - cosine(emb1, emb2))
    except Exception:
        sim_cosine = 0.0

    # Determine match tier based on both metrics
    tier = "none"
    is_match = False

    # High confidence: Both metrics strongly indicate same person
    if dist_euclidean < MatchThreshold.EUCLIDEAN_STRICT and sim_cosine > MatchThreshold.COSINE_STRICT:
        tier = "high"
        is_match = True
    # Medium confidence: Both metrics moderately indicate same person
    elif dist_euclidean < MatchThreshold.EUCLIDEAN_MODERATE and sim_cosine > MatchThreshold.COSINE_MODERATE:
        tier = "medium"
        is_match = True
    # Low confidence: Loose thresholds suggest possible match
    elif dist_euclidean < MatchThreshold.EUCLIDEAN_LOOSE and sim_cosine > MatchThreshold.COSINE_LOOSE:
        tier = "low"
        # Only count as match if configured threshold allows it
        is_match = (dist_euclidean < FACE_MATCH_THRESHOLD_EUCLIDEAN and
                    sim_cosine > FACE_MATCH_THRESHOLD_COSINE)

    # Calculate confidence score (0-1)
    # Uses sigmoid-like scaling for more intuitive scores

    # Euclidean confidence: map distance 0->1, 1.5->0
    euclidean_conf = max(0, min(1, 1 - (dist_euclidean / 1.5)))

    # Cosine confidence is already 0-1
    cosine_conf = max(0, min(1, sim_cosine))

    # Combined confidence with adaptive weighting
    # Weight cosine more heavily as it's more robust to lighting variations
    if tier == "high":
        # For high-confidence matches, boost score
        confidence = 0.8 + (euclidean_conf * 0.1 + cosine_conf * 0.1)
    elif tier == "medium":
        confidence = 0.6 + (euclidean_conf * 0.15 + cosine_conf * 0.25)
    elif tier == "low":
        confidence = 0.3 + (euclidean_conf * 0.2 + cosine_conf * 0.2)
    else:
        # No match - score based purely on metrics
        confidence = euclidean_conf * 0.4 + cosine_conf * 0.6

    confidence = min(1.0, max(0.0, confidence))  # Clamp to 0-1

    if return_tier:
        return is_match, confidence, dist_euclidean, sim_cosine, tier
    return is_match, confidence, dist_euclidean, sim_cosine


def get_match_quality_factors(dist_euclidean: float, sim_cosine: float) -> dict:
    """
    Get detailed quality factors for a face match.
    Useful for UI display and debugging.

    Returns dict with:
        - euclidean_quality: "excellent", "good", "fair", "poor"
        - cosine_quality: "excellent", "good", "fair", "poor"
        - overall_quality: "excellent", "good", "fair", "poor"
        - issues: list of potential issues
    """
    issues = []

    # Euclidean quality
    if dist_euclidean < 0.4:
        euclidean_quality = "excellent"
    elif dist_euclidean < 0.6:
        euclidean_quality = "good"
    elif dist_euclidean < 0.8:
        euclidean_quality = "fair"
    else:
        euclidean_quality = "poor"
        issues.append("High distance - possibly different lighting or angle")

    # Cosine quality
    if sim_cosine > 0.8:
        cosine_quality = "excellent"
    elif sim_cosine > 0.7:
        cosine_quality = "good"
    elif sim_cosine > 0.6:
        cosine_quality = "fair"
    else:
        cosine_quality = "poor"
        issues.append("Low similarity - significant appearance difference")

    # Overall quality
    qualities = {"excellent": 4, "good": 3, "fair": 2, "poor": 1}
    avg_quality = (qualities[euclidean_quality] + qualities[cosine_quality]) / 2

    if avg_quality >= 3.5:
        overall_quality = "excellent"
    elif avg_quality >= 2.5:
        overall_quality = "good"
    elif avg_quality >= 1.5:
        overall_quality = "fair"
    else:
        overall_quality = "poor"

    # Additional issue detection
    if dist_euclidean < 0.5 and sim_cosine < 0.6:
        issues.append("Metrics disagree - may need manual review")
    if dist_euclidean > 0.7 and sim_cosine > 0.7:
        issues.append("Metrics disagree - may need manual review")

    return {
        "euclidean_quality": euclidean_quality,
        "cosine_quality": cosine_quality,
        "overall_quality": overall_quality,
        "euclidean_distance": round(dist_euclidean, 4),
        "cosine_similarity": round(sim_cosine, 4),
        "issues": issues
    }

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
    """
    Process a media item (image or video) through the AI analysis pipeline.
    Uses short-lived DB sessions to prevent SSL connection timeouts during long operations.
    """
    # Phase 1: Load media info with a short-lived session
    db = SessionLocal()
    try:
        if status_callback:
            status_callback("log", f"Starting processing for media {media_id}")

        media_item = db.query(models.Media).filter(models.Media.id == media_id).first()

        if not media_item:
            print(f"Media {media_id} not found.")
            return

        # Extract needed data before closing session
        media_url = media_item.url
        media_type = media_item.type

        print(f"Processing media {media_id}: {media_url}")
        if status_callback:
             status_callback("log", f"Processing file: {os.path.basename(media_url)}")

    finally:
        db.close()

    # Phase 2: CPU/IO intensive work (no DB connection held)
    media_frames_dir = os.path.join(FRAMES_DIR, str(media_id))
    os.makedirs(media_frames_dir, exist_ok=True)

    if media_type == "video":
        if status_callback: status_callback("log", "Extracting frames...")
        # Need to pass url directly since we closed the session
        _extract_frames_from_url(media_url, media_frames_dir)
    else:
        # For images, treat as a single frame
        target_path = os.path.join(media_frames_dir, "frame_0000.jpg")
        try:
             shutil.copy2(media_url, target_path)
             print(f"Copied image to {target_path}")
        except Exception as e:
            print(f"Error copying image: {e}")
            return

    # Phase 3: AI analysis (uses its own sessions internally)
    analyze_frames(media_id, media_frames_dir, status_callback)

    # Phase 4: Mark as processed with a fresh session
    db = SessionLocal()
    try:
        media_item = db.query(models.Media).filter(models.Media.id == media_id).first()
        if media_item:
            media_item.processed = True
            db.commit()
            print(f"Media {media_id} marked as processed.")
    except Exception as e:
        print(f"Error marking media as processed: {e}")
        db.rollback()
    finally:
        db.close()


def _extract_frames_from_url(media_url: str, media_frames_dir: str, interval_seconds=None):
    """
    Extract frames from video URL. Wrapper for extract_frames that doesn't need DB object.
    """
    if interval_seconds is None:
        interval_seconds = DEFAULT_FRAME_INTERVAL_SECONDS

    cap = cv2.VideoCapture(media_url)
    try:
        if not cap.isOpened():
            print(f"Error opening video file {media_url}")
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

                if frame_count >= MAX_FRAMES_PER_VIDEO:
                    print(f"Reached max frame limit ({MAX_FRAMES_PER_VIDEO})")
                    break

            count += 1

        print(f"Extracted {frame_count} frames.")
        return frame_count
    finally:
        cap.release()



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

def _get_fresh_session():
    """Get a fresh database session with retry logic for connection issues."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Test the connection
            db.execute(select(1))
            return db
        except Exception as e:
            print(f"DB connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(1)
            else:
                raise


def analyze_frames(media_id, media_frames_dir, status_callback=None):
    """
    Analyze frames from a media item using AI.
    Uses short-lived DB sessions per operation to prevent SSL timeout issues.
    """
    from ai import analyzer

    print("Running AI analysis on frames...")
    if status_callback: status_callback("log", "Running AI analysis on frames...")

    # Get list of frames to process (no DB needed)
    frames = sorted([
        os.path.join(media_frames_dir, f)
        for f in os.listdir(media_frames_dir)
        if f.endswith(".jpg") and not f.startswith("face_") and not f.startswith("crop_")
    ])

    if not frames:
        print("No frames found to analyze.")
        return

    for frame_path in frames:
        # Calculate timestamp from filename (frame_XXXX.jpg -> XXXX seconds)
        frame_filename = os.path.basename(frame_path)
        try:
            frame_idx = int(frame_filename.split('_')[1].split('.')[0])
            timestamp_str = get_timestamp_str(frame_idx)
        except Exception:
            timestamp_str = "00:00:00"

        # Emit the current frame for the frontend visualizer
        if status_callback:
            frame_rel_path = os.path.relpath(frame_path, start=os.getcwd())
            frame_url = f"/{frame_rel_path}"

            status_callback("analyzing_frame", {
                "url": frame_url,
                "timestamp": timestamp_str,
                "frame_id": frame_filename
            })
            status_callback("status_update", "Scanning")

        # AI analysis (CPU intensive, no DB)
        results = analyzer.process_image_ai(frame_path, media_frames_dir)

        if len(results) > 0:
            if status_callback:
                status_callback("log", f"AI Scan: Found {len(results)} targets in {os.path.basename(frame_path)}")
                status_callback("status_update", "Harvesting")

        # Process each detection with fresh DB sessions
        for i, res in enumerate(results):
            if res.get('is_scene_summary'):
                objs = ", ".join(res.get('objects', []))
                print(f"Scene summary for {frame_path}: {objs}")
                if status_callback: status_callback("log", f"AI Context: Detected {objs}")
                continue

            print(f"Found officer in {frame_path} at {timestamp_str}")
            if status_callback:
                # Normalize path and convert to web URL
                image_url = get_web_url(normalize_for_storage(res['crop_path']))
                status_callback("candidate_officer", {
                    "image_url": image_url,
                    "timestamp": timestamp_str,
                    "confidence": res.get('confidence', 0.9),
                    "badge": res.get('badge'),
                    "quality": res.get('quality'),
                })
                status_callback("log", f"Found officer at {timestamp_str}")

            # Generate embedding (CPU intensive, no DB)
            embedding = analyzer.generate_embedding(res['crop_path'])

            # DB operation: Find matching officer or create new one
            db = _get_fresh_session()
            try:
                matched_officer = None
                matched_officer_id = None
                best_match_confidence = 0.0

                if embedding is not None:
                    existing_officers = db.query(models.Officer).filter(
                        models.Officer.visual_id.isnot(None)
                    ).all()

                    for off in existing_officers:
                        try:
                            off_emb = json.loads(off.visual_id)
                            is_match, confidence, dist_euc, sim_cos = calculate_face_similarity(embedding, off_emb)

                            if is_match and confidence > best_match_confidence:
                                best_match_confidence = confidence
                                matched_officer = off
                                matched_officer_id = off.id
                                print(f"Face {i}: Potential match with Officer {off.id} "
                                      f"(conf={confidence:.3f}, dist={dist_euc:.3f}, cos_sim={sim_cos:.3f})")

                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode visual_id for officer {off.id}")
                        except Exception as e:
                            print(f"Error comparing embeddings for officer {off.id}: {e}")

                    if matched_officer:
                        print(f"Face {i}: Best match is Officer {matched_officer_id} with confidence {best_match_confidence:.3f}")
                    else:
                        print(f"Face {i}: No matching officer found (new face)")

                if matched_officer:
                    print(f"Matched existing Officer {matched_officer_id} (Confidence: {best_match_confidence:.4f})")
                    officer_id = matched_officer_id
                else:
                    print("Creating new Officer.")
                    new_officer = models.Officer(
                        badge_number=None,
                        force="Unknown",
                        visual_id=json.dumps(embedding) if embedding is not None else None,
                        notes="Auto-detected from media."
                    )
                    db.add(new_officer)
                    db.commit()
                    db.refresh(new_officer)
                    officer_id = new_officer.id

                # Extract badge text (CPU, no DB)
                badge_text = analyzer.extract_text(res['crop_path'])
                badge_str = ", ".join(badge_text) if badge_text else None
                if badge_str:
                    print(f"OCR found text: {badge_str}")

                # Object detection (CPU, no DB)
                objects = analyzer.detect_objects(frame_path)
                relevant_labels = [obj['label'] for obj in objects if obj['label'] in
                                   ['baseball bat', 'knife', 'cell phone', 'handbag', 'backpack', 'umbrella', 'tie']]
                action_desc = "Observed"
                if relevant_labels:
                    action_desc += f"; Holding: {', '.join(relevant_labels)}"
                    print(f"Detected objects: {relevant_labels}")

                # Record appearance with normalized path for consistent storage
                normalized_crop_path = normalize_for_storage(res['crop_path'])
                appearance = models.OfficerAppearance(
                    officer_id=officer_id,
                    media_id=media_id,
                    timestamp_in_video=timestamp_str,
                    image_crop_path=normalized_crop_path,
                    role="Unknown",
                    action=action_desc
                )
                db.add(appearance)
                db.commit()
                db.refresh(appearance)
                appearance_id = appearance.id

            except Exception as e:
                print(f"Error saving detection to database: {e}")
                db.rollback()
                continue
            finally:
                db.close()

            # Run uniform analysis with its own session
            if res['crop_path'] and os.path.exists(res['crop_path']):
                try:
                    db = _get_fresh_session()
                    run_uniform_analysis(appearance_id, res['crop_path'], db, status_callback)
                    db.close()
                except Exception as e:
                    print(f"Uniform analysis error: {e}")

    print("AI Analysis complete.")
if __name__ == "__main__":
    # Test run: Find unprocessed media
    db = SessionLocal()
    unprocessed = db.query(models.Media).filter(models.Media.processed == False).all()
    print(f"Found {len(unprocessed)} unprocessed items.")
    for item in unprocessed:
        process_media(item.id)
