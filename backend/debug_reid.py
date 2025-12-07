try:
    import numpy
    print(f"Numpy: {numpy.__version__}")
    import torch
    print(f"Torch: {torch.__version__}")
    from facenet_pytorch import InceptionResnetV1
    print("Success!")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    import traceback
    traceback.print_exc()
