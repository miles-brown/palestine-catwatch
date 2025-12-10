"""
File Cleanup Job - Task #16

Cleans up orphaned files, temporary files, and old data based on configurable rules.

Usage:
    python cleanup.py --dry-run   # Show what would be deleted
    python cleanup.py --execute   # Actually delete files
"""
import os
import sys
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Literal, Tuple

# TypedDict for Python 3.8+ compatibility
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

# Structured logging
from logging_config import get_logger
logger = get_logger("cleanup")


# Type definitions for better code documentation
class DirectoryStatus(TypedDict):
    """Status of a single directory."""
    name: str
    path: str


class DirectoryError(TypedDict):
    """Error information for a directory."""
    name: str
    path: str
    error: str


class DirectoryValidationReport(TypedDict):
    """Report from validate_directories()."""
    valid: List[DirectoryStatus]
    missing: List[DirectoryStatus]
    errors: List[DirectoryError]


class CleanupSummary(TypedDict):
    """Summary statistics from cleanup operation."""
    orphaned_media_files: int
    orphaned_crop_files: int
    temp_files: int
    cache_files: int
    duplicate_files: int
    total_files: int
    bytes_freed: int
    mb_freed: float


# Configuration - paths are configurable via environment variables
MEDIA_DIR = Path(os.getenv("CLEANUP_MEDIA_DIR", "data/media"))
CROPS_DIR = Path(os.getenv("CLEANUP_CROPS_DIR", "data/crops"))
CACHE_DIR = Path(os.getenv("CLEANUP_CACHE_DIR", "data/cache"))
DOWNLOADS_DIR = Path(os.getenv("CLEANUP_DOWNLOADS_DIR", "downloads"))

# Parse TEMP_DIRS safely (handle empty strings and whitespace)
_temp_dirs_str = os.getenv("CLEANUP_TEMP_DIRS", "data/temp,data/tmp,/tmp/palestine-catwatch")
TEMP_DIRS = [d.strip() for d in _temp_dirs_str.split(",") if d.strip()]

# Cleanup thresholds (also configurable via env)
MAX_ORPHAN_AGE_DAYS = int(os.getenv("CLEANUP_MAX_ORPHAN_AGE_DAYS", "7"))
MAX_TEMP_AGE_HOURS = int(os.getenv("CLEANUP_MAX_TEMP_AGE_HOURS", "24"))
MAX_CACHE_AGE_DAYS = int(os.getenv("CLEANUP_MAX_CACHE_AGE_DAYS", "30"))


def validate_directories() -> DirectoryValidationReport:
    """
    Validate that configured cleanup directories exist and are accessible.
    Returns a report of directory status.

    This should be called at startup to warn about misconfigured paths.
    """
    report = {
        "valid": [],
        "missing": [],
        "errors": []
    }

    directories = [
        ("MEDIA_DIR", MEDIA_DIR),
        ("CROPS_DIR", CROPS_DIR),
        ("CACHE_DIR", CACHE_DIR),
        ("DOWNLOADS_DIR", DOWNLOADS_DIR),
    ]

    for name, path in directories:
        try:
            if path.exists():
                if path.is_dir():
                    report["valid"].append({"name": name, "path": str(path)})
                else:
                    report["errors"].append({
                        "name": name,
                        "path": str(path),
                        "error": "Path exists but is not a directory"
                    })
            else:
                report["missing"].append({"name": name, "path": str(path)})
        except (OSError, RuntimeError) as e:
            report["errors"].append({
                "name": name,
                "path": str(path),
                "error": str(e)
            })

    # Check temp directories
    for temp_dir in TEMP_DIRS:
        temp_path = Path(temp_dir)
        try:
            if temp_path.exists() and temp_path.is_dir():
                report["valid"].append({"name": "TEMP_DIR", "path": temp_dir})
            elif not temp_path.exists():
                report["missing"].append({"name": "TEMP_DIR", "path": temp_dir})
        except (OSError, RuntimeError) as e:
            report["errors"].append({
                "name": "TEMP_DIR",
                "path": temp_dir,
                "error": str(e)
            })

    # Log warnings for missing/error directories
    for item in report["missing"]:
        logger.warning(f"Cleanup directory does not exist: {item['name']}={item['path']}")
    for item in report["errors"]:
        logger.error(f"Cleanup directory error: {item['name']}={item['path']}: {item['error']}")

    return report

# Resolve base directories for path traversal protection
_BASE_DIRS = None

def _get_base_dirs() -> Set[Path]:
    """Get resolved base directories for path traversal validation."""
    global _BASE_DIRS
    if _BASE_DIRS is None:
        _BASE_DIRS = set()
        for d in [MEDIA_DIR, CROPS_DIR, CACHE_DIR, DOWNLOADS_DIR]:
            try:
                resolved = d.resolve()
                _BASE_DIRS.add(resolved)
            except (OSError, RuntimeError):
                pass
    return _BASE_DIRS


def is_safe_path(filepath: str) -> bool:
    """
    Validate that a file path is within expected directories.
    Prevents path traversal attacks.
    """
    try:
        resolved = Path(filepath).resolve()
        base_dirs = _get_base_dirs()

        # Check if resolved path is under any of our base directories
        for base_dir in base_dirs:
            try:
                resolved.relative_to(base_dir)
                return True
            except ValueError:
                continue

        # Log suspicious path attempts
        logger.warning(f"Path traversal attempt detected: {filepath} -> {resolved}")
        return False
    except (OSError, RuntimeError) as e:
        logger.error(f"Failed to validate path {filepath}: {e}")
        return False


class CleanupStats:
    """Track cleanup statistics."""

    def __init__(self):
        self.orphaned_media_files: List[str] = []
        self.orphaned_crop_files: List[str] = []
        self.temp_files: List[str] = []
        self.cache_files: List[str] = []
        self.duplicate_files: List[str] = []
        self.bytes_freed = 0

    def add_file(self, category: str, filepath: str, size: int = 0):
        """Add a file to the cleanup list."""
        if category == "orphaned_media":
            self.orphaned_media_files.append(filepath)
        elif category == "orphaned_crop":
            self.orphaned_crop_files.append(filepath)
        elif category == "temp":
            self.temp_files.append(filepath)
        elif category == "cache":
            self.cache_files.append(filepath)
        elif category == "duplicate":
            self.duplicate_files.append(filepath)
        self.bytes_freed += size

    def summary(self) -> CleanupSummary:
        """Return summary statistics."""
        return {
            "orphaned_media_files": len(self.orphaned_media_files),
            "orphaned_crop_files": len(self.orphaned_crop_files),
            "temp_files": len(self.temp_files),
            "cache_files": len(self.cache_files),
            "duplicate_files": len(self.duplicate_files),
            "total_files": (
                len(self.orphaned_media_files) +
                len(self.orphaned_crop_files) +
                len(self.temp_files) +
                len(self.cache_files) +
                len(self.duplicate_files)
            ),
            "bytes_freed": self.bytes_freed,
            "mb_freed": round(self.bytes_freed / (1024 * 1024), 2)
        }


def get_referenced_files(db: Session) -> Set[str]:
    """
    Get all file paths referenced in the database.
    These files should NOT be deleted.
    """
    referenced = set()

    # Media URLs (local file paths)
    media_files = db.query(models.Media.url).filter(
        models.Media.url.isnot(None)
    ).all()
    for (url,) in media_files:
        if url and not url.startswith("http"):
            abs_path = os.path.abspath(url)
            # Only add paths that pass security validation
            if is_safe_path(abs_path):
                referenced.add(abs_path)
            else:
                logger.warning(f"Skipping suspicious media path from database: {url}")

    # Officer appearance crops
    crop_files = db.query(models.OfficerAppearance.image_crop_path).filter(
        models.OfficerAppearance.image_crop_path.isnot(None)
    ).all()
    for (path,) in crop_files:
        if path:
            # Handle relative paths safely
            if path.startswith("../"):
                path = path.replace("../", "")
            abs_path = os.path.abspath(path)
            # Only add paths that pass security validation
            if is_safe_path(abs_path):
                referenced.add(abs_path)
            else:
                logger.warning(f"Skipping suspicious crop path from database: {path}")

    return referenced


def find_orphaned_files(
    directory: Path,
    referenced: Set[str],
    max_age_days: int,
    extensions: Optional[List[str]] = None
) -> List[Tuple[str, int]]:
    """
    Find files in directory that are not referenced in the database
    and are older than max_age_days.

    Returns list of (filepath, size) tuples.

    Note: Uses single stat() call to avoid TOCTOU race conditions where
    a file could be deleted between existence check and stat.
    """
    import stat as stat_module

    orphaned: List[Tuple[str, int]] = []
    cutoff = datetime.now() - timedelta(days=max_age_days)

    if not directory.exists():
        return orphaned

    for filepath in directory.rglob("*"):
        try:
            # Single stat() call to avoid TOCTOU race condition
            # File could be deleted between is_file() and stat() calls
            file_stat = filepath.stat()

            # Check if it's a regular file (not directory, symlink, etc.)
            if not stat_module.S_ISREG(file_stat.st_mode):
                continue

            # Check extension filter
            if extensions and filepath.suffix.lower() not in extensions:
                continue

            # Check if file is referenced
            abs_path = str(filepath.absolute())
            if abs_path in referenced:
                continue

            # Check file age using already-retrieved stat
            mtime = datetime.fromtimestamp(file_stat.st_mtime)
            if mtime > cutoff:
                continue  # File is too new

            orphaned.append((str(filepath), file_stat.st_size))

        except (OSError, FileNotFoundError):
            # File was deleted or became inaccessible between rglob and stat
            continue

    return orphaned


def find_temp_files(max_age_hours: int) -> List[Tuple[str, int]]:
    """
    Find temporary files older than max_age_hours.

    Returns list of (filepath, size) tuples.

    Note: Uses single stat() call to avoid TOCTOU race conditions.
    """
    import stat as stat_module

    temp_files: List[Tuple[str, int]] = []
    cutoff = datetime.now() - timedelta(hours=max_age_hours)

    for temp_dir in TEMP_DIRS:
        temp_path = Path(temp_dir)
        if not temp_path.exists():
            continue

        for filepath in temp_path.rglob("*"):
            try:
                # Single stat() call to avoid TOCTOU race condition
                file_stat = filepath.stat()

                if not stat_module.S_ISREG(file_stat.st_mode):
                    continue

                mtime = datetime.fromtimestamp(file_stat.st_mtime)
                if mtime < cutoff:
                    temp_files.append((str(filepath), file_stat.st_size))
            except (OSError, FileNotFoundError):
                continue

    return temp_files


def find_old_cache_files(max_age_days: int) -> List[Tuple[str, int]]:
    """
    Find old cache files.

    Returns list of (filepath, size) tuples.

    Note: Uses single stat() call to avoid TOCTOU race conditions.
    """
    cache_files: List[Tuple[str, int]] = []
    cutoff = datetime.now() - timedelta(days=max_age_days)

    # Analysis cache
    cache_path = CACHE_DIR / "analysis"
    if cache_path.exists():
        for filepath in cache_path.rglob("*.json"):
            try:
                # Single stat() call to avoid TOCTOU race condition
                file_stat = filepath.stat()
                mtime = datetime.fromtimestamp(file_stat.st_mtime)
                if mtime < cutoff:
                    cache_files.append((str(filepath), file_stat.st_size))
            except (OSError, FileNotFoundError):
                continue

    return cache_files


def find_duplicate_files(db: Session) -> List[tuple]:
    """
    Find files for media marked as exact duplicates that can be safely removed.
    The duplicate record links to the original, so we can delete the duplicate file.

    Returns list of (filepath, size) tuples.
    """
    duplicate_files = []

    # Get duplicate media entries with exact match
    duplicates = db.query(models.Media).filter(
        models.Media.is_duplicate == True,  # noqa: E712
        models.Media.duplicate_of_id.isnot(None)
    ).all()

    for dup in duplicates:
        if dup.url and not dup.url.startswith("http"):
            filepath = Path(dup.url)
            if filepath.exists():
                try:
                    size = filepath.stat().st_size
                    duplicate_files.append((str(filepath), size))
                except (OSError, IOError):
                    continue

    return duplicate_files


def delete_file(filepath: str) -> bool:
    """Delete a file safely with path validation."""
    # Security check: validate path before deletion
    if not is_safe_path(filepath):
        logger.error(f"Refusing to delete file outside safe directories: {filepath}")
        return False

    try:
        path = Path(filepath)
        if path.exists():
            path.unlink()
            return True
    except (OSError, IOError) as e:
        logger.error(f"Error deleting {filepath}: {e}")
    return False


def run_cleanup(dry_run: bool = True, verbose: bool = False) -> CleanupStats:
    """
    Run the cleanup process.

    Args:
        dry_run: If True, only report what would be deleted
        verbose: If True, print detailed output

    Returns:
        CleanupStats with details of cleaned files
    """
    stats = CleanupStats()
    db = SessionLocal()

    try:
        print("=" * 60)
        print(f"File Cleanup Job - {'DRY RUN' if dry_run else 'EXECUTING'}")
        print(f"Started at: {datetime.now().isoformat()}")
        print("=" * 60)

        # Get referenced files
        print("\n[1/5] Getting referenced files from database...")
        referenced = get_referenced_files(db)
        print(f"  Found {len(referenced)} referenced files")

        # Find orphaned media files
        print("\n[2/5] Scanning for orphaned media files...")
        media_extensions = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".avi", ".mov", ".webm"]
        orphaned_media = find_orphaned_files(
            MEDIA_DIR, referenced, MAX_ORPHAN_AGE_DAYS, media_extensions
        )
        for filepath, size in orphaned_media:
            stats.add_file("orphaned_media", filepath, size)
            if verbose:
                print(f"  Orphaned: {filepath} ({size} bytes)")
        print(f"  Found {len(orphaned_media)} orphaned media files")

        # Find orphaned crop files
        print("\n[3/5] Scanning for orphaned crop files...")
        orphaned_crops = find_orphaned_files(
            CROPS_DIR, referenced, MAX_ORPHAN_AGE_DAYS, [".jpg", ".jpeg", ".png"]
        )
        for filepath, size in orphaned_crops:
            stats.add_file("orphaned_crop", filepath, size)
            if verbose:
                print(f"  Orphaned crop: {filepath} ({size} bytes)")
        print(f"  Found {len(orphaned_crops)} orphaned crop files")

        # Find temp files
        print("\n[4/5] Scanning for old temp files...")
        temp_files = find_temp_files(MAX_TEMP_AGE_HOURS)
        for filepath, size in temp_files:
            stats.add_file("temp", filepath, size)
            if verbose:
                print(f"  Temp: {filepath} ({size} bytes)")
        print(f"  Found {len(temp_files)} old temp files")

        # Find old cache files
        print("\n[5/5] Scanning for old cache files...")
        cache_files = find_old_cache_files(MAX_CACHE_AGE_DAYS)
        for filepath, size in cache_files:
            stats.add_file("cache", filepath, size)
            if verbose:
                print(f"  Cache: {filepath} ({size} bytes)")
        print(f"  Found {len(cache_files)} old cache files")

        # Summary
        summary = stats.summary()
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Orphaned media files: {summary['orphaned_media_files']}")
        print(f"Orphaned crop files:  {summary['orphaned_crop_files']}")
        print(f"Temp files:           {summary['temp_files']}")
        print(f"Cache files:          {summary['cache_files']}")
        print(f"Duplicate files:      {summary['duplicate_files']}")
        print("-" * 60)
        print(f"TOTAL FILES:          {summary['total_files']}")
        print(f"SPACE TO FREE:        {summary['mb_freed']} MB")

        # Execute deletion
        if not dry_run and summary['total_files'] > 0:
            print("\n" + "=" * 60)
            print("DELETING FILES...")
            print("=" * 60)

            deleted = 0
            failed = 0

            all_files = (
                stats.orphaned_media_files +
                stats.orphaned_crop_files +
                stats.temp_files +
                stats.cache_files +
                stats.duplicate_files
            )

            for filepath in all_files:
                if delete_file(filepath):
                    deleted += 1
                    if verbose:
                        print(f"  Deleted: {filepath}")
                else:
                    failed += 1

            print(f"\nDeleted: {deleted} files")
            print(f"Failed:  {failed} files")
        elif dry_run:
            print("\nDRY RUN - No files were deleted")
            print("Run with --execute to actually delete files")

        print("\n" + "=" * 60)
        print(f"Completed at: {datetime.now().isoformat()}")
        print("=" * 60)

    finally:
        db.close()

    return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up orphaned and temporary files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be deleted without deleting (default)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete the files"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )

    args = parser.parse_args()

    # --execute overrides --dry-run
    dry_run = not args.execute

    stats = run_cleanup(dry_run=dry_run, verbose=args.verbose)

    # Return exit code based on results
    summary = stats.summary()
    if summary['total_files'] > 0 and dry_run:
        sys.exit(1)  # Indicate files need cleaning
    sys.exit(0)


if __name__ == "__main__":
    main()
