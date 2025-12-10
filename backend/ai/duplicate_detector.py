"""
Duplicate Detection System for Media Files

Detects duplicate uploads using:
1. SHA256 content hash (exact duplicates)
2. Perceptual hash / pHash (visually similar images)
3. File size comparison (quick pre-filter)

For videos, uses first frame hash plus duration/size.
"""
import hashlib
import os
import sys
from typing import Optional, Tuple, List, Dict, Any, Literal
from pathlib import Path

# TypedDict for Python 3.8+ compatibility
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class DuplicateResult(TypedDict):
    """Type definition for duplicate detection result."""
    is_duplicate: bool
    duplicate_type: Optional[Literal["exact", "similar"]]
    original_id: Optional[int]
    content_hash: Optional[str]
    perceptual_hash: Optional[str]
    file_size: Optional[int]
    similarity_score: Optional[int]


class DuplicateGroup(TypedDict):
    """Type definition for duplicate group in find_all_duplicates."""
    type: Literal["exact"]
    hash: str
    original_id: int
    duplicate_ids: List[int]


class BackfillStats(TypedDict):
    """Type definition for backfill operation statistics."""
    processed: int
    success: int
    failed: int


class HashComparisonError(Exception):
    """Exception raised when hash comparison fails."""
    pass


class HashLengthMismatchError(HashComparisonError):
    """Exception raised when hashes have different lengths."""
    def __init__(self, len1: int, len2: int):
        self.len1 = len1
        self.len2 = len2
        super().__init__(f"Hash length mismatch: {len1} vs {len2}")


class InvalidHashError(HashComparisonError):
    """Exception raised when hash string is invalid (not valid hex)."""
    def __init__(self, hash_value: str):
        self.hash_value = hash_value
        super().__init__(f"Invalid hex hash: {hash_value[:20]}...")

import cv2
import numpy as np

# Structured logging
from logging_config import get_logger
logger = get_logger("duplicate_detector")

# Try to import imagehash for perceptual hashing
try:
    from PIL import Image
    import imagehash
    PHASH_AVAILABLE = True
except ImportError:
    PHASH_AVAILABLE = False
    logger.warning("imagehash not installed. Perceptual hashing disabled. Install with: pip install imagehash Pillow")


def compute_content_hash(file_path: str) -> Optional[str]:
    """
    Compute SHA256 hash of file content.
    Returns None if file cannot be read.
    """
    try:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (IOError, OSError, PermissionError) as e:
        logger.error(f"Error computing content hash for {file_path}: {e}")
        return None


def compute_perceptual_hash(file_path: str, hash_size: int = 16) -> Optional[str]:
    """
    Compute perceptual hash (pHash) for an image.
    Uses DCT-based hashing which is robust to scaling, compression, and minor edits.

    Args:
        file_path: Path to image file
        hash_size: Size of hash (default 16 = 256 bits)

    Returns:
        Hex string of perceptual hash, or None on error
    """
    if not PHASH_AVAILABLE:
        return None

    try:
        img = Image.open(file_path)
        # Use pHash (DCT-based perceptual hash)
        phash = imagehash.phash(img, hash_size=hash_size)
        return str(phash)
    except (IOError, OSError, PermissionError) as e:
        logger.error(f"Error computing perceptual hash for {file_path}: {e}")
        return None
    except Exception as e:
        # Catch PIL-specific errors (corrupt image, unsupported format)
        logger.warning(f"Failed to compute perceptual hash for {file_path}: {e}")
        return None


def compute_video_hash(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Compute hashes for video file.

    Returns:
        Tuple of (content_hash, first_frame_perceptual_hash)
    """
    content_hash = compute_content_hash(file_path)

    # Extract first frame for perceptual hash
    first_frame_hash = None
    cap = None
    try:
        cap = cv2.VideoCapture(file_path)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                # Convert to PIL Image for hashing
                if PHASH_AVAILABLE:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(frame_rgb)
                    first_frame_hash = str(imagehash.phash(pil_img))
    except (IOError, OSError) as e:
        logger.error(f"Error extracting video frame for hashing: {e}")
    except Exception as e:
        logger.warning(f"Failed to extract video frame for hashing: {e}")
    finally:
        # Always release VideoCapture to prevent resource leak
        if cap is not None:
            cap.release()

    return content_hash, first_frame_hash


def get_file_size(file_path: str) -> Optional[int]:
    """Get file size in bytes."""
    try:
        return os.path.getsize(file_path)
    except (OSError, FileNotFoundError) as e:
        logger.debug(f"Could not get file size for {file_path}: {e}")
        return None


def compute_hamming_distance(hash1: str, hash2: str, raise_on_error: bool = False) -> int:
    """
    Compute Hamming distance between two hex hash strings.
    Lower distance = more similar.

    Args:
        hash1: First hex hash string
        hash2: Second hex hash string
        raise_on_error: If True, raise exceptions on invalid input.
                        If False (default), return -1 for backwards compatibility.

    Returns:
        Hamming distance (number of differing bits), or -1 on error if raise_on_error=False

    Raises:
        HashLengthMismatchError: If hashes have different lengths (when raise_on_error=True)
        InvalidHashError: If hash is not valid hex (when raise_on_error=True)
    """
    if len(hash1) != len(hash2):
        if raise_on_error:
            raise HashLengthMismatchError(len(hash1), len(hash2))
        return -1

    try:
        # Convert hex strings to integers and XOR
        int1 = int(hash1, 16)
        int2 = int(hash2, 16)
        xor = int1 ^ int2

        # Count bits that differ
        return bin(xor).count('1')
    except ValueError:
        if raise_on_error:
            # Determine which hash is invalid
            try:
                int(hash1, 16)
                raise InvalidHashError(hash2)
            except ValueError:
                raise InvalidHashError(hash1)
        return -1


def is_perceptually_similar(hash1: str, hash2: str, threshold: int = 10) -> bool:
    """
    Check if two perceptual hashes indicate visually similar images.

    Args:
        hash1: First perceptual hash (hex string)
        hash2: Second perceptual hash (hex string)
        threshold: Maximum Hamming distance to consider similar (default 10)
                   Lower = stricter matching

    Returns:
        True if images are likely visually similar
    """
    if not hash1 or not hash2:
        return False

    distance = compute_hamming_distance(hash1, hash2)

    # compute_hamming_distance returns -1 on error (different lengths, invalid hex)
    # Explicitly handle this case rather than relying on range check
    if distance < 0:
        return False

    return distance <= threshold


class DuplicateDetector:
    """
    Detects duplicate media files in the database.

    Usage:
        detector = DuplicateDetector(db_session)
        result = detector.check_for_duplicate(file_path, media_type)
        if result['is_duplicate']:
            print(f"Duplicate of media ID: {result['original_id']}")
    """

    def __init__(self, db_session, similarity_threshold: int = 10):
        """
        Initialize duplicate detector.

        Args:
            db_session: SQLAlchemy database session
            similarity_threshold: Perceptual hash distance threshold (default 10)
        """
        self.db = db_session
        self.similarity_threshold = similarity_threshold

    def check_for_duplicate(
        self,
        file_path: str,
        media_type: str = "image"
    ) -> DuplicateResult:
        """
        Check if a file is a duplicate of existing media.

        Args:
            file_path: Path to the uploaded file
            media_type: 'image' or 'video'

        Returns:
            Dict with:
                - is_duplicate: bool
                - duplicate_type: 'exact' | 'similar' | None
                - original_id: ID of original media (if duplicate)
                - content_hash: SHA256 of file
                - perceptual_hash: pHash of file
                - file_size: Size in bytes
                - similarity_score: Hamming distance (for similar matches)
        """
        import models

        result = {
            "is_duplicate": False,
            "duplicate_type": None,
            "original_id": None,
            "content_hash": None,
            "perceptual_hash": None,
            "file_size": None,
            "similarity_score": None
        }

        # Compute hashes
        file_size = get_file_size(file_path)
        result["file_size"] = file_size

        if media_type == "video":
            content_hash, perceptual_hash = compute_video_hash(file_path)
        else:
            content_hash = compute_content_hash(file_path)
            perceptual_hash = compute_perceptual_hash(file_path)

        result["content_hash"] = content_hash
        result["perceptual_hash"] = perceptual_hash

        # Step 1: Check for exact duplicates (same content hash)
        if content_hash:
            exact_match = self.db.query(models.Media).filter(
                models.Media.content_hash == content_hash,
                models.Media.is_duplicate == False  # noqa: E712
            ).first()

            if exact_match:
                result["is_duplicate"] = True
                result["duplicate_type"] = "exact"
                result["original_id"] = exact_match.id
                return result

        # Step 2: Check for visually similar images (perceptual hash)
        # Use batched processing with yield_per for memory-efficient streaming
        if perceptual_hash and media_type == "image":
            # Use yield_per for server-side cursor to avoid loading all results into memory
            # This streams results in batches directly from the database
            YIELD_BATCH_SIZE = 500
            MAX_CANDIDATES = 100000  # Safety limit to prevent runaway queries
            candidates_checked = 0

            query = self.db.query(
                models.Media.id,
                models.Media.perceptual_hash
            ).filter(
                models.Media.perceptual_hash.isnot(None),
                models.Media.is_duplicate == False,  # noqa: E712
                models.Media.type == "image"
            ).yield_per(YIELD_BATCH_SIZE)

            for candidate_id, candidate_hash in query:
                candidates_checked += 1

                # Safety limit to prevent excessive scanning
                if candidates_checked > MAX_CANDIDATES:
                    logger.warning(
                        f"Perceptual hash search truncated at {candidates_checked} images",
                        extra_data={"max_limit": MAX_CANDIDATES}
                    )
                    break

                if is_perceptually_similar(
                    perceptual_hash,
                    candidate_hash,
                    self.similarity_threshold
                ):
                    distance = compute_hamming_distance(
                        perceptual_hash,
                        candidate_hash
                    )
                    result["is_duplicate"] = True
                    result["duplicate_type"] = "similar"
                    result["original_id"] = candidate_id
                    result["similarity_score"] = distance
                    return result

        return result

    def find_all_duplicates(self) -> List[DuplicateGroup]:
        """
        Scan database and identify all duplicate media.

        Returns:
            List of duplicate groups with original and duplicates
        """
        import models

        # Group by content hash
        from sqlalchemy import func

        duplicate_groups = []

        # Find content hash duplicates
        hash_counts = self.db.query(
            models.Media.content_hash,
            func.count(models.Media.id).label('count')
        ).filter(
            models.Media.content_hash.isnot(None)
        ).group_by(
            models.Media.content_hash
        ).having(
            func.count(models.Media.id) > 1
        ).all()

        for content_hash, count in hash_counts:
            media_items = self.db.query(models.Media).filter(
                models.Media.content_hash == content_hash
            ).order_by(models.Media.timestamp).all()

            if media_items:
                duplicate_groups.append({
                    "type": "exact",
                    "hash": content_hash,
                    "original_id": media_items[0].id,
                    "duplicate_ids": [m.id for m in media_items[1:]]
                })

        return duplicate_groups

    def compute_and_store_hashes(self, media_id: int) -> bool:
        """
        Compute and store hashes for a media item.

        Args:
            media_id: ID of media item to hash

        Returns:
            True if successful
        """
        import models

        media = self.db.query(models.Media).filter(
            models.Media.id == media_id
        ).first()

        if not media or not media.url:
            return False

        file_path = media.url
        if not os.path.exists(file_path):
            return False

        # Compute hashes
        media.file_size = get_file_size(file_path)

        if media.type == "video":
            content_hash, perceptual_hash = compute_video_hash(file_path)
        else:
            content_hash = compute_content_hash(file_path)
            perceptual_hash = compute_perceptual_hash(file_path)

        media.content_hash = content_hash
        media.perceptual_hash = perceptual_hash

        self.db.commit()
        return True

    def backfill_hashes(self, batch_size: int = 100) -> BackfillStats:
        """
        Backfill hashes for existing media without hashes.

        Args:
            batch_size: Number of items to process per batch

        Returns:
            Dict with counts: processed, success, failed
        """
        import models

        stats = {"processed": 0, "success": 0, "failed": 0}

        media_items = self.db.query(models.Media).filter(
            models.Media.content_hash.is_(None)
        ).limit(batch_size).all()

        for media in media_items:
            stats["processed"] += 1
            if self.compute_and_store_hashes(media.id):
                stats["success"] += 1
            else:
                stats["failed"] += 1

        return stats
