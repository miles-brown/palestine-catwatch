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
