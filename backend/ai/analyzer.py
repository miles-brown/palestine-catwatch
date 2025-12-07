import cv2
import os
import easyocr
import numpy as np
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# buffer
# Initialize EasyOCR
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# EASYOCR_MODELS_DIR = os.path.join(CURRENT_DIR, "easyocr_models")
# try:
#     reader = easyocr.Reader(['en'], gpu=False, model_storage_directory=EASYOCR_MODELS_DIR)
# except Exception as e:
#     print(f"Warning: OCR Init failed: {e}")
reader = None

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
    Returns a list of class names found (e.g., ['person', 'baseball bat']).
    """
    if yolo_model is None:
        return []
        
    try:
        results = yolo_model(image_path, verbose=False)
        detected_classes = []
        for r in results:
            for c in r.boxes.cls:
                class_name = yolo_model.names[int(c)]
                detected_classes.append(class_name)
        
        return list(set(detected_classes)) # Unique items
    except Exception as e:
        print(f"Object Detection Error: {e}")
        return []

def extract_text(image_input):
    """
    Extracts text from the image (path or numpy array) using EasyOCR.
    """
    if reader is None:
        return []
        
    try:
        # reader.readtext accepts file path or numpy array
        results = reader.readtext(image_input)
        # Filter for text with reasonable confidence
        texts = [res[1] for res in results if res[2] > 0.3]
        return texts
    except Exception as e:
        print(f"OCR Error: {e}")
        return []

def get_body_roi(img, face_box):
    """
    Returns a crop of the body area (shoulders/chest) based on face location.
    """
    x, y, w, h = face_box
    h_img, w_img = img.shape[:2]
    
    # Heuristic: Badge is usually on shoulders (epaulettes) or chest
    # Region: Start from slightly below face, extend down 2.5x face height
    # Widen: Extend left/right by 1x face width to catch shoulders
    
    roi_y1 = min(h_img, y + int(h * 0.8)) # Start from chin/neck area
    roi_y2 = min(h_img, y + int(h * 3.5)) # Down to mid-chest
    roi_x1 = max(0, x - int(w * 0.8))     # Extend left
    roi_x2 = min(w_img, x + w + int(w * 0.8)) # Extend right
    
    if roi_y2 <= roi_y1 or roi_x2 <= roi_x1:
        return None
        
    return img[roi_y1:roi_y2, roi_x1:roi_x2]

def filter_badge_number(texts):
    """
     heuristics to identify the most likely badge number from text list.
    """
    candidates = []
    for t in texts:
        # Clean string
        clean = t.replace(" ", "").upper()
        # UK Badge numbers are typically 2-6 digits, sometimes with 1-2 letters prefix
        # Regex equivalent check
        digit_count = sum(c.isdigit() for c in clean)
        if digit_count >= 2 and len(clean) <= 8:
            candidates.append(clean)
            
    # Return the best candidate (longest digit sequence? or just all joined?)
    # For transparency, let's return all likely candidates joined
    return ", ".join(candidates) if candidates else None

def process_image_ai(image_path, output_dir):
    """
    Runs full analysis pipeline on an image.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Analyzing {image_path}...")
    
    detections = detect_faces(image_path)
    
    analyzed_data = []
    
    img = cv2.imread(image_path)
    if img is None: 
        return []

    for i, det in enumerate(detections):
        x, y, w, h = det['box']
        
        # Clamp coordinates
        h_img, w_img = img.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        
        if w <= 0 or h <= 0:
            continue
            
        face_img = img[y:y+h, x:x+w]
        
        # 1. Quality Check
        blur_score = calculate_blur(face_img)
        is_blurry = blur_score < 100 # Threshold
        
        # 2. Focused OCR on Body
        body_crop = get_body_roi(img, (x, y, w, h))
        badge_text = None
        if body_crop is not None and body_crop.size > 0:
            raw_text = extract_text(body_crop)
            badge_text = filter_badge_number(raw_text)
        
        face_filename = f"face_{os.path.basename(image_path)}_{i}.jpg"
        face_path = os.path.join(output_dir, face_filename)
        cv2.imwrite(face_path, face_img)
        
        analyzed_data.append({
            "crop_path": face_path,
            "role": "Officer",
            "action": "Detected", 
            "badge": badge_text, # Result from focused OCR
            "encoding": None,
            "quality": {
                "blur_score": float(blur_score),
                "is_blurry": is_blurry,
                "resolution": f"{w}x{h}"
            }
        })
        
    return analyzed_data
