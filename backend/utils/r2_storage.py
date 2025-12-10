"""
Cloudflare R2 Storage Integration

This module provides functions for uploading, downloading, and managing files
in Cloudflare R2 object storage. R2 is S3-compatible, so we use boto3.

Environment Variables Required:
- R2_ACCOUNT_ID: Cloudflare account ID
- R2_ACCESS_KEY_ID: R2 API token access key
- R2_SECRET_ACCESS_KEY: R2 API token secret key
- R2_BUCKET_NAME: Name of the R2 bucket
- R2_PUBLIC_URL: Public URL for the bucket (optional, for custom domains)
"""

import os
import io
import logging
from pathlib import Path
from typing import Optional, BinaryIO, Union
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# R2 Configuration
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")  # e.g., https://pub-xxx.r2.dev or custom domain

# Check if R2 is configured
R2_ENABLED = all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME])


@lru_cache(maxsize=1)
def get_r2_client():
    """
    Get a cached boto3 S3 client configured for Cloudflare R2.
    """
    if not R2_ENABLED:
        logger.warning("R2 storage not configured - using local storage")
        return None

    endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "adaptive"}
        ),
        region_name="auto"  # R2 uses "auto" for region
    )


def upload_file(
    file_path: str,
    r2_key: Optional[str] = None,
    content_type: Optional[str] = None
) -> Optional[str]:
    """
    Upload a local file to R2.

    Args:
        file_path: Path to the local file
        r2_key: Key (path) in R2. If not provided, uses the relative path from data/
        content_type: MIME type of the file

    Returns:
        The R2 key if successful, None if failed
    """
    client = get_r2_client()
    if not client:
        return None

    # Determine the R2 key
    if not r2_key:
        # Use relative path from data/ directory
        path = Path(file_path)
        if "data" in path.parts:
            idx = path.parts.index("data")
            r2_key = "/".join(path.parts[idx:])
        else:
            r2_key = f"data/{path.name}"

    # Guess content type if not provided
    if not content_type:
        ext = Path(file_path).suffix.lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mov": "video/quicktime",
        }
        content_type = content_types.get(ext, "application/octet-stream")

    try:
        extra_args = {"ContentType": content_type}
        client.upload_file(file_path, R2_BUCKET_NAME, r2_key, ExtraArgs=extra_args)
        logger.info(f"Uploaded {file_path} to R2 as {r2_key}")
        return r2_key
    except ClientError as e:
        logger.error(f"Failed to upload {file_path} to R2: {e}")
        return None


def upload_bytes(
    data: Union[bytes, BinaryIO],
    r2_key: str,
    content_type: str = "application/octet-stream"
) -> Optional[str]:
    """
    Upload bytes or a file-like object directly to R2.

    Args:
        data: Bytes or file-like object to upload
        r2_key: Key (path) in R2
        content_type: MIME type of the data

    Returns:
        The R2 key if successful, None if failed
    """
    client = get_r2_client()
    if not client:
        return None

    try:
        if isinstance(data, bytes):
            data = io.BytesIO(data)

        client.upload_fileobj(
            data,
            R2_BUCKET_NAME,
            r2_key,
            ExtraArgs={"ContentType": content_type}
        )
        logger.info(f"Uploaded bytes to R2 as {r2_key}")
        return r2_key
    except ClientError as e:
        logger.error(f"Failed to upload bytes to R2: {e}")
        return None


def download_file(r2_key: str, local_path: str) -> bool:
    """
    Download a file from R2 to local storage.

    Args:
        r2_key: Key (path) in R2
        local_path: Local path to save the file

    Returns:
        True if successful, False otherwise
    """
    client = get_r2_client()
    if not client:
        return False

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        client.download_file(R2_BUCKET_NAME, r2_key, local_path)
        logger.info(f"Downloaded {r2_key} from R2 to {local_path}")
        return True
    except ClientError as e:
        logger.error(f"Failed to download {r2_key} from R2: {e}")
        return False


def download_bytes(r2_key: str) -> Optional[bytes]:
    """
    Download a file from R2 as bytes.

    Args:
        r2_key: Key (path) in R2

    Returns:
        File contents as bytes, or None if failed
    """
    client = get_r2_client()
    if not client:
        return None

    try:
        response = client.get_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
        return response["Body"].read()
    except ClientError as e:
        logger.error(f"Failed to download {r2_key} from R2: {e}")
        return None


def delete_file(r2_key: str) -> bool:
    """
    Delete a file from R2.

    Args:
        r2_key: Key (path) in R2

    Returns:
        True if successful, False otherwise
    """
    client = get_r2_client()
    if not client:
        return False

    try:
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
        logger.info(f"Deleted {r2_key} from R2")
        return True
    except ClientError as e:
        logger.error(f"Failed to delete {r2_key} from R2: {e}")
        return False


def file_exists(r2_key: str) -> bool:
    """
    Check if a file exists in R2.

    Args:
        r2_key: Key (path) in R2

    Returns:
        True if exists, False otherwise
    """
    client = get_r2_client()
    if not client:
        return False

    try:
        client.head_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
        return True
    except ClientError:
        return False


def get_public_url(r2_key: str) -> str:
    """
    Get the public URL for a file in R2.

    If R2_PUBLIC_URL is configured, uses that as the base.
    Otherwise, returns a path that should be proxied through the backend.

    Args:
        r2_key: Key (path) in R2

    Returns:
        Public URL for the file
    """
    if R2_PUBLIC_URL:
        # Use the public bucket URL or custom domain
        base = R2_PUBLIC_URL.rstrip("/")
        return f"{base}/{r2_key}"
    else:
        # Fall back to backend proxy route
        return f"/r2/{r2_key}"


def get_presigned_url(r2_key: str, expires_in: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL for temporary access to a private file.

    Args:
        r2_key: Key (path) in R2
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        Presigned URL, or None if failed
    """
    client = get_r2_client()
    if not client:
        return None

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": R2_BUCKET_NAME, "Key": r2_key},
            ExpiresIn=expires_in
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for {r2_key}: {e}")
        return None


def list_files(prefix: str = "", max_keys: int = 1000) -> list[dict]:
    """
    List files in R2 with a given prefix.

    Args:
        prefix: Key prefix to filter by (e.g., "data/frames/1/")
        max_keys: Maximum number of keys to return

    Returns:
        List of file info dicts with 'key', 'size', 'last_modified'
    """
    client = get_r2_client()
    if not client:
        return []

    try:
        response = client.list_objects_v2(
            Bucket=R2_BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=max_keys
        )

        files = []
        for obj in response.get("Contents", []):
            files.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"]
            })

        return files
    except ClientError as e:
        logger.error(f"Failed to list files with prefix {prefix}: {e}")
        return []


def sync_local_to_r2(local_dir: str, r2_prefix: str = "") -> int:
    """
    Sync a local directory to R2.

    Args:
        local_dir: Local directory to sync
        r2_prefix: Prefix for R2 keys

    Returns:
        Number of files uploaded
    """
    if not R2_ENABLED:
        logger.warning("R2 not enabled, skipping sync")
        return 0

    uploaded = 0
    local_path = Path(local_dir)

    for file_path in local_path.rglob("*"):
        if file_path.is_file():
            relative = file_path.relative_to(local_path)
            r2_key = f"{r2_prefix}/{relative}" if r2_prefix else str(relative)
            r2_key = r2_key.replace("\\", "/")

            if upload_file(str(file_path), r2_key):
                uploaded += 1

    logger.info(f"Synced {uploaded} files from {local_dir} to R2")
    return uploaded


# Convenience function to check R2 status
def get_r2_status() -> dict:
    """
    Get R2 configuration status.

    Returns:
        Dict with enabled status, bucket name, and public URL
    """
    return {
        "enabled": R2_ENABLED,
        "bucket": R2_BUCKET_NAME if R2_ENABLED else None,
        "public_url": R2_PUBLIC_URL if R2_ENABLED else None,
        "configured": {
            "account_id": bool(R2_ACCOUNT_ID),
            "access_key": bool(R2_ACCESS_KEY_ID),
            "secret_key": bool(R2_SECRET_ACCESS_KEY),
            "bucket_name": bool(R2_BUCKET_NAME),
        }
    }
