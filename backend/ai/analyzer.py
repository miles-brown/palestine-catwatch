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

# Load Face Detector
# We assume the model files are in the same directory as this script or known location
# We downloaded them to backend/ai/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
prototxt_path = os.path.join(CURRENT_DIR, "deploy.prototxt")
model_path = os.path.join(CURRENT_DIR, "res10_300x300_ssd_iter_140000.caffemodel")

print(f"Loading Face Detector from {model_path}...")
net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)

def detect_faces(image_path):
    """
    Detects faces using OpenCV DNN.
    Returns list of dicts: {'box': (x, y, w, h), 'encoding': None}
    """
    image = cv2.imread(image_path)
    if image is None:
        return []
    
    (h, w) = image.shape[:2]
    # Resize to 300x300 for the model
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
        (300, 300), (104.0, 177.0, 123.0))
 
    net.setInput(blob)
    detections = net.forward()
    
    results = []
    # Loop over detections
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        
        # Filter weak detections
        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            
            width = endX - startX
            height = endY - startY
            
            results.append({
                "box": (startX, startY, width, height),
                "encoding": None # No recognition yet
            })
            
    return results

def extract_text(image_path):
    """
    Extracts text from the image using EasyOCR.
    """
    if reader is None:
        return []
        
    try:
        results = reader.readtext(image_path)
        texts = [res[1] for res in results if res[2] > 0.3]
        return texts
    except Exception as e:
        print(f"OCR Error: {e}")
        return []

def process_image_ai(image_path, output_dir):
    """
    Runs full analysis pipeline on an image.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Analyzing {image_path}...")
    
    detections = detect_faces(image_path)
    
    # Run OCR
    detected_text = extract_text(image_path)
    badge_text = ", ".join(detected_text) if detected_text else None
    
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
        face_filename = f"face_{os.path.basename(image_path)}_{i}.jpg"
        face_path = os.path.join(output_dir, face_filename)
        cv2.imwrite(face_path, face_img)
        
        analyzed_data.append({
            "crop_path": face_path,
            "role": "Officer",
            "action": "Detected", 
            "badge": badge_text,
            "encoding": None
        })
        
    return analyzed_data
