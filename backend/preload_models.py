import os
import torch
from ultralytics import YOLO
from facenet_pytorch import InceptionResnetV1

def preload():
    print("Pre-loading AI models...")
    
    # 1. YOLOv8n
    # This will download 'yolov8n.pt' to the current directory
    print("Downloading YOLOv8n...")
    model = YOLO("yolov8n.pt")
    
    # 2. InceptionResnetV1 (vggface2)
    # This downloads weights to torch cache
    print("Downloading InceptionResnetV1 (vggface2)...")
    resnet = InceptionResnetV1(pretrained='vggface2').eval()
    
    print("Models successfully downloaded.")

if __name__ == "__main__":
    preload()
