import cv2
import os
import re
import time
import easyocr
import numpy as np
import ssl

# Structured logging
from logging_config import get_logger, log_performance
logger = get_logger("analyzer")

# Import path validation for security
from cleanup import is_safe_path

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Initialize EasyOCR lazily (downloads models on first use)
reader = None
_ocr_initialized = False

# UK Police Shoulder Number Patterns
# Format: 1-2 letters (division code) followed by 2-5 digits
# Examples: U1234, AB123, PC4567, E67, CO1234
UK_BADGE_PATTERNS = [
    r'^[A-Z]{1,2}\d{2,5}$',      # Standard: U1234, AB123
    r'^PC\d{3,5}$',              # PC prefix: PC4567
    r'^PS\d{3,5}$',              # PS prefix: PS1234 (Sergeant)
    r'^\d{4,6}$',                # Numbers only: 1234, 123456
    r'^[A-Z]\d{2,4}[A-Z]?$',     # Letter-numbers-optional letter: U123A
]

def _get_ocr_reader():
    """Lazy initialization of EasyOCR reader to avoid blocking startup."""
    global reader, _ocr_initialized
    if _ocr_initialized:
        return reader
    _ocr_initialized = True
    try:
        logger.info("Initializing EasyOCR (this may download models on first use)...")
        reader = easyocr.Reader(['en'], gpu=False)
        logger.info("EasyOCR initialized successfully.")
    except (ImportError, RuntimeError, OSError) as e:
        logger.warning(f"OCR Init failed: {e}")
        reader = None
    return reader

# Face Detection
# Load Face Detector
# We assume the model files are in the same directory as this script or known location
prototxt_path = os.path.join(os.path.dirname(__file__), "deploy.prototxt")
model_path = os.path.join(os.path.dirname(__file__), "res10_300x300_ssd_iter_140000.caffemodel")

net = None
if os.path.exists(prototxt_path) and os.path.exists(model_path):
    logger.info(f"Loading Face Detector from {model_path}...")
    net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
else:
    logger.warning("Face detection models not found.")

# Face Recognition (Re-ID)
resnet = None
try:
    from facenet_pytorch import InceptionResnetV1
    import torch
    import torchvision.transforms as transforms
    from PIL import Image

    # Initialize ResNet
    logger.info("Loading Face Re-ID model (InceptionResnetV1)...")
    resnet = InceptionResnetV1(pretrained='vggface2').eval()

    # Standard transform for Facenet
    face_transform = transforms.Compose([
        transforms.Resize((160, 160)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])

except ImportError:
    logger.warning("facenet-pytorch not installed. Re-ID disabled.")
except (RuntimeError, OSError) as e:
    logger.warning(f"Failed to load Re-ID model: {e}")

# Object Detection (YOLOv8)
yolo_model = None
try:
    from ultralytics import YOLO

    # Initialize YOLOv8
    # It will auto-download 'yolov8n.pt' on first use if not found
    logger.info("Loading YOLOv8 Object Detector...")
    yolo_model = YOLO("yolov8n.pt")
except ImportError:
    logger.warning("ultralytics not installed. Object Detection disabled.")
except (RuntimeError, OSError) as e:
    logger.warning(f"Failed to load YOLO model: {e}")


def detect_faces(image_path):
    """
    Detects faces in an image using OpenCV DNN.
    Returns a list of dicts: {'box': [x, y, w, h], 'confidence': float}
    """
    if net is None:
        return []

    image = cv2.imread(image_path)
    if image is None:
        return []
    
    (h, w) = image.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
        (300, 300), (104.0, 177.0, 123.0))

    net.setInput(blob)
    detections = net.forward()

    results = []
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        # Filter out weak detections
        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # Ensure coordinates are within image bounds
            startX = max(0, startX)
            startY = max(0, startY)
            endX = min(w, endX)
            endY = min(h, endY)
            
            # Avoid tiny invalid boxes
            if endX - startX > 10 and endY - startY > 10:
                results.append({
                    'box': [startX, startY, endX - startX, endY - startY],
                    'confidence': float(confidence)
                })

    return results

def generate_embedding(image_path, face_box=None):
    """
    Generates a 512-d embedding for the face in the image.
    If face_box (x, y, w, h) is provided, crops first.
    """
    if resnet is None:
        return None
        
    try:
        img = Image.open(image_path).convert('RGB')
        
        if face_box:
            x, y, w, h = face_box
            img = img.crop((x, y, x+w, y+h))
            
        # Transform and add batch dimension
        img_tensor = face_transform(img).unsqueeze(0)
        
        # Inference
        embedding = resnet(img_tensor).detach().numpy()[0]
        return embedding.tolist()
        
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return None

def detect_objects(image_path):
    """
    Detects objects using YOLOv8.
    Returns list of dicts: {'label': str, 'box': [x,y,w,h], 'confidence': float}
    """
    if yolo_model is None:
        return []
        
    try:
        results = yolo_model(image_path, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                # YOLO boxes are [x1, y1, x2, y2]
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                label = yolo_model.names[cls]
                
                detections.append({
                    'label': label,
                    'box': [int(x1), int(y1), int(x2-x1), int(y2-y1)],
                    'confidence': conf
                })
        
        return detections
    except Exception as e:
        print(f"Object Detection Error: {e}")
        return []

def extract_text(image_input):
    """
    Extracts text from the image (path or numpy array) using EasyOCR.
    """
    ocr_reader = _get_ocr_reader()
    if ocr_reader is None:
        return []

    try:
        # reader.readtext accepts file path or numpy array
        results = ocr_reader.readtext(image_input)
        # Filter for text with reasonable confidence
        texts = [res[1] for res in results if res[2] > 0.3]
        return texts
    except Exception as e:
        print(f"OCR Error: {e}")
        return []

def get_body_roi(img, face_box):
    """
    Returns a crop of the body area (shoulders/chest) based on face location.
    UK police shoulder numbers are typically on epaulettes (shoulder area).
    """
    x, y, w, h = face_box
    h_img, w_img = img.shape[:2]

    # Heuristic: Badge is usually on shoulders (epaulettes) or chest
    # Region: Start from slightly below face, extend down 2.5x face height
    # Widen: Extend left/right by 1x face width to catch shoulders

    roi_y1 = min(h_img, y + int(h * 0.8))  # Start from chin/neck area
    roi_y2 = min(h_img, y + int(h * 3.5))  # Down to mid-chest
    roi_x1 = max(0, x - int(w * 0.8))      # Extend left
    roi_x2 = min(w_img, x + w + int(w * 0.8))  # Extend right

    if roi_y2 <= roi_y1 or roi_x2 <= roi_x1:
        return None

    return img[roi_y1:roi_y2, roi_x1:roi_x2]


# =============================================================================
# DUAL CROP GENERATION
# =============================================================================
# Generate two types of crops per officer:
# 1. Face crop - Close-up for Officer Card display (head/shoulders)
# 2. Body crop - Full body (head to toe) for evidence documentation

# Minimum dimensions for quality control
MIN_FACE_CROP_SIZE = 100  # Minimum face crop dimension
MIN_BODY_CROP_SIZE = 150  # Minimum body crop dimension

# Detection thresholds from environment variables
FACE_CONFIDENCE_THRESHOLD = float(os.environ.get('FACE_DETECTION_CONFIDENCE', '0.6'))
PERSON_CONFIDENCE_THRESHOLD = float(os.environ.get('PERSON_DETECTION_CONFIDENCE', '0.4'))


def generate_face_crop(img, face_box, output_path, expand_ratio=0.3):
    """
    Generate a close-up face crop for Officer Card display.

    Args:
        img: OpenCV image (BGR numpy array)
        face_box: [x, y, w, h] of detected face
        output_path: Path to save the crop
        expand_ratio: How much to expand the box (0.3 = 30% on each side)

    Returns:
        Path to saved crop, or None if crop failed quality checks
    """
    x, y, w, h = face_box
    h_img, w_img = img.shape[:2]

    # Expand face box to include head and shoulders
    # This creates a better "portrait" style crop
    expand_x = int(w * expand_ratio)
    expand_y = int(h * expand_ratio)

    # Calculate expanded region
    crop_x1 = max(0, x - expand_x)
    crop_y1 = max(0, y - int(expand_y * 0.5))  # Less expansion above (forehead)
    crop_x2 = min(w_img, x + w + expand_x)
    crop_y2 = min(h_img, y + h + int(expand_y * 1.5))  # More expansion below (shoulders)

    # Validate minimum size
    crop_w = crop_x2 - crop_x1
    crop_h = crop_y2 - crop_y1

    if crop_w < MIN_FACE_CROP_SIZE or crop_h < MIN_FACE_CROP_SIZE:
        logger.warning(f"Face crop too small: {crop_w}x{crop_h}")
        return None

    # Extract crop
    face_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]

    if face_crop.size == 0:
        return None

    # Security: Validate output path before writing
    if not is_safe_path(output_path):
        logger.error(f"Path traversal attempt blocked for face crop: {output_path}")
        return None

    # Save crop
    try:
        cv2.imwrite(output_path, face_crop)
        logger.info(f"Saved face crop: {output_path} ({crop_w}x{crop_h})")
        return output_path
    except Exception as e:
        logger.error(f"Failed to save face crop: {e}")
        return None


def generate_body_crop(img, face_box, person_box, output_path):
    """
    Generate a full-body crop (head to toe) for evidence documentation.

    Uses YOLO person detection box if available, otherwise estimates
    from face location using body proportions.

    Args:
        img: OpenCV image (BGR numpy array)
        face_box: [x, y, w, h] of detected face
        person_box: [x, y, w, h] from YOLO person detection (or None)
        output_path: Path to save the crop

    Returns:
        Path to saved crop, or None if crop failed quality checks
    """
    h_img, w_img = img.shape[:2]
    face_x, face_y, face_w, face_h = face_box

    if person_box:
        # Validate person_box format before unpacking
        if not isinstance(person_box, (list, tuple)) or len(person_box) != 4:
            logger.warning(f"Invalid person_box format: {person_box}, using face-based estimation")
            person_box = None
        else:
            try:
                # Use YOLO person detection box
                px, py, pw, ph = [int(v) for v in person_box]

                # Validate coordinates are reasonable
                if pw <= 0 or ph <= 0 or px < 0 or py < 0:
                    logger.warning(f"Invalid person_box coordinates: {person_box}")
                    person_box = None
                else:
                    # Validate that face is within person box (sanity check)
                    face_center_x = face_x + face_w / 2
                    face_center_y = face_y + face_h / 2

                    if (px <= face_center_x <= px + pw and
                        py <= face_center_y <= py + ph):
                        # Face is within person box - use it directly
                        crop_x1, crop_y1 = px, py
                        crop_x2, crop_y2 = px + pw, py + ph
                    else:
                        # Face not in person box - use face-based estimation
                        person_box = None
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse person_box {person_box}: {e}")
                person_box = None

    if not person_box:
        # Estimate full body from face using human proportions
        # Average adult: head is ~1/7.5 to 1/8 of total height
        # We'll use 1/7 for slightly generous estimate

        estimated_height = face_h * 7
        estimated_width = face_w * 3  # Body is roughly 3x face width

        # Center the body estimate on the face
        body_center_x = face_x + face_w / 2

        crop_x1 = max(0, int(body_center_x - estimated_width / 2))
        crop_x2 = min(w_img, int(body_center_x + estimated_width / 2))
        crop_y1 = max(0, face_y - int(face_h * 0.5))  # Include top of head
        crop_y2 = min(h_img, face_y + int(estimated_height))

    # Ensure integer coordinates
    crop_x1, crop_y1 = int(crop_x1), int(crop_y1)
    crop_x2, crop_y2 = int(crop_x2), int(crop_y2)

    # Validate dimensions
    crop_w = crop_x2 - crop_x1
    crop_h = crop_y2 - crop_y1

    if crop_w < MIN_BODY_CROP_SIZE or crop_h < MIN_BODY_CROP_SIZE:
        logger.warning(f"Body crop too small: {crop_w}x{crop_h}")
        return None

    # Extract crop
    body_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]

    if body_crop.size == 0:
        return None

    # Security: Validate output path before writing
    if not is_safe_path(output_path):
        logger.error(f"Path traversal attempt blocked for body crop: {output_path}")
        return None

    # Save crop
    try:
        cv2.imwrite(output_path, body_crop)
        logger.info(f"Saved body crop: {output_path} ({crop_w}x{crop_h})")
        return output_path
    except Exception as e:
        logger.error(f"Failed to save body crop: {e}")
        return None


def generate_dual_crops(img, face_box, person_box, output_dir, base_name):
    """
    Generate both face and body crops for an officer detection.

    Args:
        img: OpenCV image (BGR numpy array)
        face_box: [x, y, w, h] of detected face
        person_box: [x, y, w, h] from YOLO (or None)
        output_dir: Directory to save crops
        base_name: Base filename (without extension)

    Returns:
        Dict with 'face_crop_path' and 'body_crop_path' (values may be None)
    """
    result = {
        'face_crop_path': None,
        'body_crop_path': None
    }

    # Generate face crop
    face_output = os.path.join(output_dir, f"face_{base_name}.jpg")
    result['face_crop_path'] = generate_face_crop(img, face_box, face_output)

    # Generate body crop
    body_output = os.path.join(output_dir, f"body_{base_name}.jpg")
    result['body_crop_path'] = generate_body_crop(img, face_box, person_box, body_output)

    return result


def find_person_for_face(face_box, person_detections, iou_threshold=0.3):
    """
    Find the YOLO person detection that best matches a face detection.

    Args:
        face_box: [x, y, w, h] of detected face
        person_detections: List of YOLO detections filtered for 'person'
        iou_threshold: Minimum overlap threshold

    Returns:
        Best matching person box [x, y, w, h] or None
    """
    if not person_detections:
        return None

    face_x, face_y, face_w, face_h = face_box
    face_center_x = face_x + face_w / 2
    face_center_y = face_y + face_h / 2

    best_match = None
    best_score = -1

    for detection in person_detections:
        if detection.get('label') != 'person':
            continue

        # Validate box exists and has correct format
        box = detection.get('box')
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            logger.warning(f"Invalid detection box format: {box}")
            continue

        try:
            px, py, pw, ph = [int(v) for v in box]
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse detection box {box}: {e}")
            continue

        # Validate coordinates are reasonable
        if pw <= 0 or ph <= 0:
            continue

        # Check if face center is within person box
        if (px <= face_center_x <= px + pw and
            py <= face_center_y <= py + ph):

            # Score based on face being in upper portion of person
            # (face should be near top of body)
            relative_y = (face_center_y - py) / ph

            # Prefer detections where face is in top 30% of body
            if relative_y < 0.3:
                score = detection.get('confidence', 0.5) * (1 - relative_y)

                if score > best_score:
                    best_score = score
                    best_match = box

    return best_match


def get_shoulder_rois(img, face_box):
    """
    Returns crops of left and right shoulder areas for targeted badge OCR.
    More precise than get_body_roi for shoulder number detection.
    """
    x, y, w, h = face_box
    h_img, w_img = img.shape[:2]

    rois = []

    # Calculate shoulder positions based on face location
    # Shoulders are typically 1.2-1.5x face width to each side
    shoulder_y_start = y + int(h * 1.0)  # Start just below face
    shoulder_y_end = min(h_img, y + int(h * 2.2))  # Shoulder area
    shoulder_width = int(w * 0.8)

    # Left shoulder
    left_x_start = max(0, x - int(w * 1.2))
    left_x_end = max(0, x - int(w * 0.3))
    if left_x_end > left_x_start and shoulder_y_end > shoulder_y_start:
        left_roi = img[shoulder_y_start:shoulder_y_end, left_x_start:left_x_end]
        if left_roi.size > 0:
            rois.append(('left_shoulder', left_roi))

    # Right shoulder
    right_x_start = min(w_img, x + w + int(w * 0.3))
    right_x_end = min(w_img, x + w + int(w * 1.2))
    if right_x_end > right_x_start and shoulder_y_end > shoulder_y_start:
        right_roi = img[shoulder_y_start:shoulder_y_end, right_x_start:right_x_end]
        if right_roi.size > 0:
            rois.append(('right_shoulder', right_roi))

    return rois


def preprocess_for_ocr(img):
    """
    Preprocess image to improve OCR accuracy for badge numbers.
    - Convert to grayscale
    - Apply adaptive thresholding
    - Denoise
    """
    if img is None or img.size == 0:
        return None

    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

    return denoised


def extract_badge_number(img, face_box):
    """
    Dedicated function to extract badge/shoulder number from officer image.
    Uses multiple ROIs and preprocessing for better accuracy.

    Performance metrics are logged for monitoring OCR enhancement effectiveness.
    """
    start_time = time.time()
    all_texts = []
    ocr_calls = 0
    ocr_successes = 0  # OCR calls that returned text

    # Track which method found the badge (for metrics)
    found_by_method = None

    # Try body ROI (broad area)
    body_crop = get_body_roi(img, face_box)
    if body_crop is not None and body_crop.size > 0:
        # Standard OCR
        texts = extract_text(body_crop)
        ocr_calls += 1
        if texts:
            ocr_successes += 1
            all_texts.extend(texts)

        # Try with preprocessing
        preprocessed = preprocess_for_ocr(body_crop)
        if preprocessed is not None:
            texts_enhanced = extract_text(preprocessed)
            ocr_calls += 1
            if texts_enhanced:
                ocr_successes += 1
                all_texts.extend(texts_enhanced)

    # Try shoulder ROIs (more precise)
    shoulder_rois = get_shoulder_rois(img, face_box)
    for location, roi in shoulder_rois:
        if roi is not None and roi.size > 100:  # Minimum size check
            texts = extract_text(roi)
            ocr_calls += 1
            if texts:
                ocr_successes += 1
                all_texts.extend(texts)

            # Try with preprocessing
            preprocessed = preprocess_for_ocr(roi)
            if preprocessed is not None:
                texts_enhanced = extract_text(preprocessed)
                ocr_calls += 1
                if texts_enhanced:
                    ocr_successes += 1
                    all_texts.extend(texts_enhanced)

    # Filter and return best badge number candidate
    result = filter_badge_number(all_texts)

    # Log performance metrics
    elapsed_ms = (time.time() - start_time) * 1000
    log_performance(
        logger,
        "badge_ocr_extraction",
        elapsed_ms,
        success=result is not None,
        details={
            "ocr_calls": ocr_calls,
            "ocr_successes": ocr_successes,
            "texts_found": len(all_texts),
            "badge_detected": result is not None,
            "badge_value": result if result else None
        }
    )

    return result

def filter_badge_number(texts):
    """
    Use heuristics to identify the most likely UK police badge/shoulder number from text list.
    UK shoulder numbers typically follow patterns like: U1234, AB123, PC4567, E67
    """
    candidates = []
    scored_candidates = []

    for t in texts:
        # Clean string - remove spaces, convert to uppercase
        clean = t.replace(" ", "").replace("-", "").upper()

        # Skip very short or very long strings
        if len(clean) < 2 or len(clean) > 8:
            continue

        # Skip common false positives
        false_positives = {'POLICE', 'UK', 'MET', 'OFFICER', 'TSG', 'FIT', 'PSU'}
        if clean in false_positives:
            continue

        # Check against UK badge patterns
        for pattern in UK_BADGE_PATTERNS:
            if re.match(pattern, clean):
                # Score based on pattern strength
                score = 100
                # Prefer letter+number combinations (most common UK format)
                if re.match(r'^[A-Z]{1,2}\d{3,4}$', clean):
                    score = 150  # Most common UK format
                scored_candidates.append((clean, score))
                break
        else:
            # Fallback: check if it looks like a badge number (alphanumeric with digits)
            digit_count = sum(c.isdigit() for c in clean)
            alpha_count = sum(c.isalpha() for c in clean)

            if digit_count >= 2 and alpha_count <= 2 and len(clean) <= 6:
                # Basic score for partial matches
                scored_candidates.append((clean, digit_count * 10))

    # Sort by score (highest first) and deduplicate
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    seen = set()
    for candidate, _ in scored_candidates:
        if candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    return candidates[0] if len(candidates) == 1 else (", ".join(candidates[:3]) if candidates else None)

def calculate_blur(image):
    """
    Computes the Laplacian variance of the image.
    Lower variance = fewer edges = blurrier.
    Typical threshold is 100.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def process_image_ai(image_path, output_dir):
    """
    Runs full analysis pipeline on an image.
    1. Detects Objects (YOLO) - Generic scene analysis & Person detection
    2. Detects Faces (SSD) - Specific officer identification
    3. Generates dual crops (face + body) for each officer

    Returns list of detections with both face_crop_path and body_crop_path.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    logger.info(f"Analyzing {image_path}...")

    analyzed_data = []

    img = cv2.imread(image_path)
    if img is None:
        return []

    h_img, w_img = img.shape[:2]
    base_filename = os.path.splitext(os.path.basename(image_path))[0]

    # 1. Object Detection (YOLO) - Run first to get person boxes for body crops
    yolo_detections = detect_objects(image_path)
    person_detections = [d for d in yolo_detections if d['label'] == 'person' and d['confidence'] > PERSON_CONFIDENCE_THRESHOLD]
    objects_found = list(set([d['label'] for d in yolo_detections]))

    # 2. Face Detection (Primary)
    face_detections = detect_faces(image_path)

    # Filter by confidence threshold
    face_detections = [d for d in face_detections if d['confidence'] >= FACE_CONFIDENCE_THRESHOLD]

    for i, det in enumerate(face_detections):
        x, y, w, h = det['box']

        # Clamp coordinates
        x = max(0, x)
        y = max(0, y)
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        if w <= 0 or h <= 0:
            continue

        face_box = [x, y, w, h]

        # Find matching person detection for body crop
        person_box = find_person_for_face(face_box, person_detections)

        # Generate dual crops
        crop_base = f"{base_filename}_{i}"
        crop_paths = generate_dual_crops(img, face_box, person_box, output_dir, crop_base)

        # Skip if we couldn't generate at least one valid crop
        if not crop_paths['face_crop_path'] and not crop_paths['body_crop_path']:
            logger.warning(f"Skipping detection {i} - no valid crops generated")
            continue

        # Quality assessment
        face_img = img[y:y+h, x:x+w]
        blur_score = calculate_blur(face_img)
        is_blurry = blur_score < 100

        # Badge/Shoulder Number OCR
        badge_text = extract_badge_number(img, face_box)

        # Use face crop as primary crop_path for backwards compatibility
        primary_crop = crop_paths['face_crop_path'] or crop_paths['body_crop_path']

        analyzed_data.append({
            "crop_path": primary_crop,
            "face_crop_path": crop_paths['face_crop_path'],
            "body_crop_path": crop_paths['body_crop_path'],
            "confidence": det['confidence'],
            "role": "Officer",
            "action": "Detected (Face)",
            "badge": badge_text,
            "encoding": None,
            "quality": {
                "blur_score": float(blur_score),
                "is_blurry": is_blurry,
                "resolution": f"{w}x{h}",
                "face_visible": True
            }
        })

    # 3. Fallback: If no faces found, use person detections
    if len(face_detections) == 0 and person_detections:
        logger.info(f"No faces detected, using {len(person_detections)} person detections as fallback")

        for i, det in enumerate(person_detections):
            x, y, w, h = det['box']

            # Validate size (ignore tiny people in background)
            if w < 50 or h < 50:
                continue

            # Clamp
            x = max(0, x)
            y = max(0, y)
            w = min(w, w_img - x)
            h = min(h, h_img - y)

            # Save full person crop as body crop
            person_img = img[y:y+h, x:x+w]
            body_filename = f"body_{base_filename}_person_{i}.jpg"
            body_path = os.path.join(output_dir, body_filename)

            # Security: Validate output path before writing
            if not is_safe_path(body_path):
                logger.error(f"Path traversal attempt blocked for person crop: {body_path}")
                continue

            cv2.imwrite(body_path, person_img)

            analyzed_data.append({
                "crop_path": body_path,
                "face_crop_path": None,
                "body_crop_path": body_path,
                "confidence": det['confidence'],
                "role": "Officer (Unidentified)",
                "action": "Detected (Body Only)",
                "badge": None,
                "encoding": None,
                "quality": {
                    "blur_score": 0.0,
                    "is_blurry": False,
                    "resolution": f"{w}x{h}",
                    "face_visible": False
                }
            })

    # Add scene summary if we have objects but no people detected
    if len(analyzed_data) == 0 and len(objects_found) > 0:
        analyzed_data.append({
            "is_scene_summary": True,
            "objects": objects_found,
            "message": f"Detected objects: {', '.join(objects_found)}"
        })

    return analyzed_data
