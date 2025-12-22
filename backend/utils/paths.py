"""
Utility functions for standardizing file paths across the application.

The problem: Paths are stored inconsistently throughout the codebase:
- Some are absolute: /Users/.../data/frames/1/face_0.jpg
- Some are relative to backend: data/frames/1/face_0.jpg
- Some have ../data prefix: ../data/frames/1/face_0.jpg

This module provides functions to normalize paths for:
1. Database storage (always relative to data/ directory)
2. Filesystem operations (absolute paths)
3. Web URLs (paths served via FastAPI static files or R2)

When R2 is enabled, files are stored in Cloudflare R2 and URLs point to R2.
When R2 is disabled, files are stored locally and served via FastAPI.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Base directories
BACKEND_DIR = Path(__file__).parent.parent.absolute()
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"

# Ensure data directories exist (still needed for temporary local processing)
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


# ============================================================================
# R2-aware storage functions
# ============================================================================

def save_file(local_path: str, storage_key: str = None) -> str:
    """
    Save a file to storage (R2 if enabled, otherwise keep local).

    Args:
        local_path: Path to the local file
        storage_key: Key for storage. If not provided, derives from local path.

    Returns:
        Storage key (path) that can be used to retrieve the file
    """
    from utils.r2_storage import R2_ENABLED, upload_file

    # Normalize the storage key
    if not storage_key:
        storage_key = normalize_for_storage(local_path)

    if R2_ENABLED:
        result = upload_file(local_path, storage_key)
        if result:
            logger.info(f"Saved {local_path} to R2 as {storage_key}")
            return storage_key
        else:
            logger.warning(f"Failed to upload to R2, keeping local: {local_path}")
            return storage_key
    else:
        # Local storage - file is already saved
        logger.debug(f"R2 disabled, using local storage: {storage_key}")
        return storage_key


def save_bytes(data: bytes, storage_key: str, content_type: str = "application/octet-stream") -> str:
    """
    Save bytes to storage (R2 if enabled, otherwise save locally).

    Args:
        data: Bytes to save
        storage_key: Key for storage (e.g., "data/frames/1/face_0.jpg")
        content_type: MIME type

    Returns:
        Storage key
    """
    from utils.r2_storage import R2_ENABLED, upload_bytes

    if R2_ENABLED:
        result = upload_bytes(data, storage_key, content_type)
        if result:
            return storage_key

    # Fall back to local storage
    local_path = get_absolute_path(storage_key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, 'wb') as f:
        f.write(data)
    return storage_key


def get_file_url(storage_key: str) -> str:
    """
    Get a URL to access a file.

    If R2 is enabled and has a public URL, returns the R2 URL.
    Otherwise returns the local static files URL.

    Args:
        storage_key: Storage key (e.g., "data/frames/1/face_0.jpg")

    Returns:
        URL to access the file, or None if storage_key is None/empty
    """
    # Handle None or empty storage keys
    if not storage_key or storage_key == 'None':
        return None

    from utils.r2_storage import R2_ENABLED, R2_PUBLIC_URL, get_public_url

    if R2_ENABLED and R2_PUBLIC_URL:
        return get_public_url(storage_key)
    else:
        # Use local URL
        return get_web_url(storage_key)


def delete_storage_file(storage_key: str) -> bool:
    """
    Delete a file from storage.

    Args:
        storage_key: Storage key

    Returns:
        True if deleted successfully
    """
    from utils.r2_storage import R2_ENABLED, delete_file as r2_delete

    success = True

    # Try to delete from R2
    if R2_ENABLED:
        r2_delete(storage_key)

    # Also delete local file if it exists
    local_path = get_absolute_path(storage_key)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except OSError as e:
            logger.warning(f"Failed to delete local file {local_path}: {e}")
            success = False

    return success


def file_exists_in_storage(storage_key: str) -> bool:
    """
    Check if a file exists in storage.

    Args:
        storage_key: Storage key

    Returns:
        True if file exists
    """
    from utils.r2_storage import R2_ENABLED, file_exists as r2_exists

    if R2_ENABLED:
        return r2_exists(storage_key)

    # Check local
    local_path = get_absolute_path(storage_key)
    return os.path.exists(local_path)


# ============================================================================
# Officer appearance crop URL helpers
# ============================================================================

def get_best_crop_url(appearance) -> str:
    """
    Get the best available crop URL from an officer appearance.

    Priority order:
        1. face_crop_path - Close-up face (preferred for officer cards)
        2. body_crop_path - Full body shot (good for uniform/equipment evidence)
        3. image_crop_path - Legacy field (backwards compatibility only)

    Args:
        appearance: OfficerAppearance model instance or dict with crop paths

    Returns:
        URL string for the best available crop, or None if no crops exist
    """
    if appearance is None:
        return None

    # Handle both model instances and dicts
    if hasattr(appearance, 'face_crop_path'):
        face = appearance.face_crop_path
        body = appearance.body_crop_path
        legacy = appearance.image_crop_path
    else:
        face = appearance.get('face_crop_path')
        body = appearance.get('body_crop_path')
        legacy = appearance.get('image_crop_path')

    # Return first available with priority
    for path in [face, body, legacy]:
        if path:
            return get_file_url(path)

    return None


def get_all_crop_urls(appearance) -> dict:
    """
    Get all crop URLs from an officer appearance.

    Args:
        appearance: OfficerAppearance model instance or dict with crop paths

    Returns:
        Dict with face_crop_url, body_crop_url, and best_crop_url
    """
    if appearance is None:
        return {"face_crop_url": None, "body_crop_url": None, "best_crop_url": None}

    # Handle both model instances and dicts
    if hasattr(appearance, 'face_crop_path'):
        face_path = appearance.face_crop_path
        body_path = appearance.body_crop_path
        legacy_path = appearance.image_crop_path
    else:
        face_path = appearance.get('face_crop_path')
        body_path = appearance.get('body_crop_path')
        legacy_path = appearance.get('image_crop_path')

    face_url = get_file_url(face_path) if face_path else None
    body_url = get_file_url(body_path) if body_path else None
    legacy_url = get_file_url(legacy_path) if legacy_path else None

    return {
        "face_crop_url": face_url,
        "body_crop_url": body_url,
        "best_crop_url": face_url or body_url or legacy_url
    }
