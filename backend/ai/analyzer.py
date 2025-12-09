import cv2
import os
import re
import easyocr
import numpy as np
import ssl

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
        print("Initializing EasyOCR (this may download models on first use)...")
        reader = easyocr.Reader(['en'], gpu=False)
        print("EasyOCR initialized successfully.")
    except Exception as e:
        print(f"Warning: OCR Init failed: {e}")
        reader = None
    return reader

# Face Detection
# Load Face Detector
# We assume the model files are in the same directory as this script or known location
prototxt_path = os.path.join(os.path.dirname(__file__), "deploy.prototxt")
model_path = os.path.join(os.path.dirname(__file__), "res10_300x300_ssd_iter_140000.caffemodel")

net = None
if os.path.exists(prototxt_path) and os.path.exists(model_path):
    print(f"Loading Face Detector from {model_path}...")
    net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
else:
    print("Warning: Face detection models not found.")

# Face Recognition (Re-ID)
resnet = None
try:
    from facenet_pytorch import InceptionResnetV1
    import torch
    import torchvision.transforms as transforms
    from PIL import Image
    
    # Initialize ResNet
    print("Loading Face Re-ID model (InceptionResnetV1)...")
    resnet = InceptionResnetV1(pretrained='vggface2').eval()
    
    # Standard transform for Facenet
    face_transform = transforms.Compose([
        transforms.Resize((160, 160)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])
    
except ImportError:
    print("Warning: facenet-pytorch not installed. Re-ID disabled.")
except Exception as e:
    print(f"Warning: Failed to load Re-ID model: {e}")

# Object Detection (YOLOv8)
yolo_model = None
try:
    from ultralytics import YOLO
    
    # Initialize YOLOv8
    # It will auto-download 'yolov8n.pt' on first use if not found
    print("Loading YOLOv8 Object Detector...")
    yolo_model = YOLO("yolov8n.pt")
except ImportError:
    print("Warning: ultralytics not installed. Object Detection disabled.")
except Exception as e:
    print(f"Warning: Failed to load YOLO model: {e}")


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
    """
    all_texts = []

    # Try body ROI (broad area)
    body_crop = get_body_roi(img, face_box)
    if body_crop is not None and body_crop.size > 0:
        # Standard OCR
        texts = extract_text(body_crop)
        all_texts.extend(texts)

        # Try with preprocessing
        preprocessed = preprocess_for_ocr(body_crop)
        if preprocessed is not None:
            texts_enhanced = extract_text(preprocessed)
            all_texts.extend(texts_enhanced)

    # Try shoulder ROIs (more precise)
    shoulder_rois = get_shoulder_rois(img, face_box)
    for location, roi in shoulder_rois:
        if roi is not None and roi.size > 100:  # Minimum size check
            texts = extract_text(roi)
            all_texts.extend(texts)

            # Try with preprocessing
            preprocessed = preprocess_for_ocr(roi)
            if preprocessed is not None:
                texts_enhanced = extract_text(preprocessed)
                all_texts.extend(texts_enhanced)

    # Filter and return best badge number candidate
    return filter_badge_number(all_texts)

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
    1. Detects Objects (YOLO) - Generic scene analysis & Person detection (fallback)
    2. Detects Faces (SSD) - Specific officer identification
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Analyzing {image_path}...")
    
    analyzed_data = []
    
    img = cv2.imread(image_path)
    if img is None: 
        return []
    
    h_img, w_img = img.shape[:2]

    # 1. Face Detection (Primary)
    face_detections = detect_faces(image_path)
    
    # Track covered areas to avoid duplicates if we add YOLO detections later
    # (Simplified: just track center points of faces)
    face_centers = []
    
    for i, det in enumerate(face_detections):
        x, y, w, h = det['box']
        
        # Clamp
        x = max(0, x); y = max(0, y)
        w = min(w, w_img - x); h = min(h, h_img - y)
        if w <= 0 or h <= 0: continue
        
        face_centers.append((x + w/2, y + h/2))
            
        face_img = img[y:y+h, x:x+w]
        
        # Quality
        blur_score = calculate_blur(face_img)
        is_blurry = blur_score < 100 
        
        # Badge/Shoulder Number OCR (using improved extraction)
        badge_text = extract_badge_number(img, (x, y, w, h))
        
        face_filename = f"face_{os.path.basename(image_path)}_{i}.jpg"
        face_path = os.path.join(output_dir, face_filename)
        cv2.imwrite(face_path, face_img)
        
        analyzed_data.append({
            "crop_path": face_path,
            "confidence": det['confidence'],  # Include detection confidence
            "role": "Officer",
            "action": "Detected (Face)",
            "badge": badge_text,
            "encoding": None,
            "quality": {"blur_score": float(blur_score), "is_blurry": is_blurry, "resolution": f"{w}x{h}"}
        })

    # 2. Object Detection (YOLO) - Scene Context & Person Fallback
    yolo_detections = detect_objects(image_path)
    objects_found = list(set([d['label'] for d in yolo_detections]))
    
    # Fallback: If no faces found, or to augment, crop 'person' detections
    # Only if they don't overlap with existing faces? 
    # For now: If 0 faces found, crop ALL detected persons.
    if len(face_detections) == 0:
        person_count = 0
        for det in yolo_detections:
            if det['label'] == 'person' and det['confidence'] > 0.4:
                x, y, w, h = det['box']
                # Validate size (ignore tiny people in background)
                if w < 50 or h < 50: continue
                
                # Clamp
                x = max(0, x); y = max(0, y)
                w = min(w, w_img - x); h = min(h, h_img - y)
                
                person_img = img[y:y+h, x:x+w]
                person_filename = f"person_{os.path.basename(image_path)}_{person_count}.jpg"
                person_path = os.path.join(output_dir, person_filename)
                cv2.imwrite(person_path, person_img)
                
                analyzed_data.append({
                    "crop_path": person_path,
                    "confidence": det['confidence'],  # Include detection confidence
                    "role": "Officer (Unidentified)",
                    "action": "Detected (Body)",
                    "badge": None,
                    "encoding": None,
                    "quality": {"blur_score": 0.0, "is_blurry": False, "resolution": f"{w}x{h}"}
                })
                person_count += 1

    # Add scene summary if we have objects but no crops at all
    if len(analyzed_data) == 0 and len(objects_found) > 0:
        analyzed_data.append({
            "is_scene_summary": True,
            "objects": objects_found,
            "message": f"Detected objects: {', '.join(objects_found)}"
        })
        
    return analyzed_data
