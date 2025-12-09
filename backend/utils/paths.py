"""
Utility functions for standardizing file paths across the application.

The problem: Paths are stored inconsistently throughout the codebase:
- Some are absolute: /Users/.../data/frames/1/face_0.jpg
- Some are relative to backend: data/frames/1/face_0.jpg
- Some have ../data prefix: ../data/frames/1/face_0.jpg

This module provides functions to normalize paths for:
1. Database storage (always relative to data/ directory)
2. Filesystem operations (absolute paths)
3. Web URLs (paths served via FastAPI static files)
"""

import os
from pathlib import Path

# Base directories
BACKEND_DIR = Path(__file__).parent.parent.absolute()
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"

# Ensure data directories exist
DATA_SUBDIRS = ["frames", "downloads", "media"]
for subdir in DATA_SUBDIRS:
    (DATA_DIR / subdir).mkdir(parents=True, exist_ok=True)


def normalize_for_storage(path: str) -> str:
    """
    Convert any path format to a consistent storage format.
    Storage format: relative path from backend directory, e.g., "data/frames/1/face.jpg"
    """
    if not path:
        return path

    # Convert to Path object for easier manipulation
    p = Path(path)

    # If it's absolute, make it relative to backend dir
    if p.is_absolute():
        try:
            p = p.relative_to(BACKEND_DIR)
        except ValueError:
            # Path is outside backend dir, try relative to project root
            try:
                p = p.relative_to(PROJECT_ROOT)
                # If in project root, check if it's in data/
                if not str(p).startswith("data"):
                    # Assume it should be in backend/data
                    p = Path("data") / p
            except ValueError:
                # Can't make relative, just use the filename in data/
                p = Path("data") / p.name

    # Clean up ../data/ prefix
    path_str = str(p)
    if path_str.startswith("../data/"):
        path_str = path_str[3:]  # Remove "../"
    elif path_str.startswith("./data/"):
        path_str = path_str[2:]  # Remove "./"

    # Ensure it starts with data/
    if not path_str.startswith("data/") and not path_str.startswith("data\\"):
        path_str = f"data/{path_str}"

    return path_str.replace("\\", "/")


def get_absolute_path(storage_path: str) -> str:
    """
    Convert a storage path to an absolute filesystem path.
    """
    if not storage_path:
        return storage_path

    # If already absolute, return as is
    if os.path.isabs(storage_path):
        return storage_path

    # Clean up the path
    normalized = normalize_for_storage(storage_path)

    # Make absolute from backend directory
    return str(BACKEND_DIR / normalized)


def get_web_url(storage_path: str) -> str:
    """
    Convert a storage path to a web-accessible URL.
    URLs are served via FastAPI static files mount at /data
    """
    if not storage_path:
        return storage_path

    normalized = normalize_for_storage(storage_path)

    # Remove the "data/" prefix since it's the mount point
    if normalized.startswith("data/"):
        normalized = normalized[5:]

    return f"/data/{normalized}"


def get_storage_path_from_url(url: str) -> str:
    """
    Convert a web URL back to a storage path.
    """
    if not url:
        return url

    # Remove leading slash and /data/ prefix
    if url.startswith("/data/"):
        return f"data/{url[6:]}"
    elif url.startswith("/"):
        return f"data{url}"

    return f"data/{url}"


def ensure_directory(path: str) -> str:
    """
    Ensure the directory for the given path exists.
    Returns the absolute path.
    """
    abs_path = get_absolute_path(path)
    directory = os.path.dirname(abs_path)
    os.makedirs(directory, exist_ok=True)
    return abs_path
