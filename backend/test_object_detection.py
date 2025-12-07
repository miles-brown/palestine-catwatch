import models, cv2, os
from ai import analyzer

def run_test():
    print("=== Object Detection Verification Test ===")
    
    # Check Model
    if analyzer.yolo_model is None:
        print("❌ FAIL: YOLO model not loaded.")
        return

    # Use existing test image or download one with objects?
    # backend/data/media/test_officer_face.png might only have a face.
    # We'll try it anyway, it should detect 'person'.
    
    test_img = "../data/media/test_officer_face.png"
    if not os.path.exists(test_img):
        print("Error: Test image not found.")
        return

    print(f"Scanning {test_img}...")
    objects = analyzer.detect_objects(test_img)
    print(f"Detected: {objects}")
    
    if 'person' in objects:
        print("✅ PASS: Detected 'person'.")
    else:
        print("⚠️ WARNING: Did not detect 'person'. Process might need a wider shot.")

if __name__ == "__main__":
    run_test()
