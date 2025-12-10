"""
File-based cache for uniform analysis results.

Uses SHA256 image hashes as keys to prevent re-analyzing identical images.
Supports TTL-based expiration.
"""
import os
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any


class AnalysisCache:
    """
    Simple file-based cache for uniform analysis results.

    Features:
    - SHA256 hash-based keys
    - Configurable TTL (default 30 days)
    - JSON storage format
    - Automatic cleanup of expired entries
    """

    def __init__(
        self,
        cache_dir: str,
        ttl_days: int = 30
    ):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache files
            ttl_days: Time-to-live in days (default 30)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_days * 24 * 60 * 60
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, image_hash: str) -> Path:
        """Get the cache file path for an image hash."""
        # Use first 2 chars as subdirectory for better filesystem performance
        subdir = image_hash[:2]
        cache_subdir = self.cache_dir / subdir
        cache_subdir.mkdir(exist_ok=True)
        return cache_subdir / f"{image_hash}.json"

    def get(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached analysis result.

        Args:
            image_hash: SHA256 hash of the image

        Returns:
            Cached analysis dict or None if not found/expired
        """
        cache_path = self._get_cache_path(image_hash)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cache_entry = json.load(f)

            # Check TTL
            cached_at = cache_entry.get("cached_at", 0)
            if time.time() - cached_at > self.ttl_seconds:
                # Expired, remove the file
                cache_path.unlink(missing_ok=True)
                return None

            return cache_entry.get("analysis")

        except (json.JSONDecodeError, IOError):
            # Corrupted cache entry, remove it
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, image_hash: str, analysis: Dict[str, Any]) -> bool:
        """
        Store analysis result in cache.

        Args:
            image_hash: SHA256 hash of the image
            analysis: Analysis result dict to cache

        Returns:
            True if successfully cached
        """
        cache_path = self._get_cache_path(image_hash)

        cache_entry = {
            "image_hash": image_hash,
            "cached_at": time.time(),
            "cached_at_iso": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis
        }

        try:
            with open(cache_path, "w") as f:
                json.dump(cache_entry, f, indent=2)
            return True
        except IOError:
            return False

    def delete(self, image_hash: str) -> bool:
        """
        Remove an entry from the cache.

        Args:
            image_hash: SHA256 hash of the image

        Returns:
            True if entry was deleted
        """
        cache_path = self._get_cache_path(image_hash)
        try:
            cache_path.unlink(missing_ok=True)
            return True
        except IOError:
            return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        count = 0
        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for cache_file in subdir.glob("*.json"):
                    cache_file.unlink(missing_ok=True)
                    count += 1
        return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns:
            Number of entries removed
        """
        count = 0
        current_time = time.time()

        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for cache_file in subdir.glob("*.json"):
                    try:
                        with open(cache_file, "r") as f:
                            cache_entry = json.load(f)
                        cached_at = cache_entry.get("cached_at", 0)
                        if current_time - cached_at > self.ttl_seconds:
                            cache_file.unlink()
                            count += 1
                    except (json.JSONDecodeError, IOError):
                        # Corrupted, remove it
                        cache_file.unlink(missing_ok=True)
                        count += 1

        return count

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        total_entries = 0
        total_size = 0
        expired_count = 0
        current_time = time.time()

        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for cache_file in subdir.glob("*.json"):
                    total_entries += 1
                    total_size += cache_file.stat().st_size

                    try:
                        with open(cache_file, "r") as f:
                            cache_entry = json.load(f)
                        cached_at = cache_entry.get("cached_at", 0)
                        if current_time - cached_at > self.ttl_seconds:
                            expired_count += 1
                    except (json.JSONDecodeError, IOError):
                        expired_count += 1

        return {
            "total_entries": total_entries,
            "expired_entries": expired_count,
            "valid_entries": total_entries - expired_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "ttl_days": self.ttl_seconds // (24 * 60 * 60),
            "cache_dir": str(self.cache_dir)
        }
