"""
Tests for duplicate detection module.

Covers:
- Content hash computation (SHA256)
- Perceptual hash computation (pHash)
- Video hash extraction
- Hamming distance calculation
- Perceptual similarity detection
- Duplicate detection logic
- Batched query processing
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.duplicate_detector import (
    compute_content_hash,
    compute_perceptual_hash,
    compute_video_hash,
    compute_hamming_distance,
    is_perceptually_similar,
    get_file_size,
    DuplicateDetector,
    PHASH_AVAILABLE,
)


class TestContentHash:
    """Test SHA256 content hash computation."""

    def test_compute_hash_for_text_file(self):
        """Test hash computation for a simple text file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello, World!")
            temp_path = f.name

        try:
            hash_result = compute_content_hash(temp_path)
            assert hash_result is not None
            assert len(hash_result) == 64  # SHA256 produces 64 hex chars
            # Known SHA256 of "Hello, World!"
            assert hash_result == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        finally:
            os.unlink(temp_path)

    def test_compute_hash_for_binary_file(self):
        """Test hash computation for binary content."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
            f.write(b'\x00\x01\x02\x03\x04\x05')
            temp_path = f.name

        try:
            hash_result = compute_content_hash(temp_path)
            assert hash_result is not None
            assert len(hash_result) == 64
        finally:
            os.unlink(temp_path)

    def test_identical_files_produce_same_hash(self):
        """Test that identical files produce identical hashes."""
        content = b"Test content for hashing"

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
            f2.write(content)
            path2 = f2.name

        try:
            hash1 = compute_content_hash(path1)
            hash2 = compute_content_hash(path2)
            assert hash1 == hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_different_files_produce_different_hashes(self):
        """Test that different files produce different hashes."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f1:
            f1.write(b"Content A")
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
            f2.write(b"Content B")
            path2 = f2.name

        try:
            hash1 = compute_content_hash(path1)
            hash2 = compute_content_hash(path2)
            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_nonexistent_file_returns_none(self):
        """Test that a nonexistent file returns None."""
        result = compute_content_hash("/nonexistent/path/to/file.txt")
        assert result is None

    def test_permission_error_returns_none(self):
        """Test that permission errors are handled gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_path = f.name

        try:
            # Remove read permissions
            os.chmod(temp_path, 0o000)
            result = compute_content_hash(temp_path)
            assert result is None
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_path, 0o644)
            os.unlink(temp_path)


class TestHammingDistance:
    """Test Hamming distance calculations."""

    def test_identical_hashes_have_zero_distance(self):
        """Test that identical hashes have distance 0."""
        hash1 = "abcd1234"
        hash2 = "abcd1234"
        assert compute_hamming_distance(hash1, hash2) == 0

    def test_completely_different_hashes(self):
        """Test distance between completely different hashes."""
        # All 0s vs all Fs (maximum difference for hex)
        hash1 = "00000000"
        hash2 = "ffffffff"
        distance = compute_hamming_distance(hash1, hash2)
        assert distance == 32  # Each hex char differs by 4 bits, 8 chars = 32 bits

    def test_single_bit_difference(self):
        """Test distance for single bit difference."""
        hash1 = "00000000"
        hash2 = "00000001"  # One bit different
        assert compute_hamming_distance(hash1, hash2) == 1

    def test_different_length_hashes_return_negative(self):
        """Test that different length hashes return -1."""
        hash1 = "abcd"
        hash2 = "abcdef"
        assert compute_hamming_distance(hash1, hash2) == -1

    def test_invalid_hex_returns_negative(self):
        """Test that invalid hex strings return -1."""
        hash1 = "abcd1234"
        hash2 = "xxxx1234"  # Invalid hex
        assert compute_hamming_distance(hash1, hash2) == -1


class TestPerceptualSimilarity:
    """Test perceptual similarity detection."""

    def test_identical_hashes_are_similar(self):
        """Test that identical hashes are considered similar."""
        hash1 = "a" * 64
        hash2 = "a" * 64
        assert is_perceptually_similar(hash1, hash2) is True

    def test_very_different_hashes_not_similar(self):
        """Test that very different hashes are not similar."""
        hash1 = "0" * 64
        hash2 = "f" * 64
        assert is_perceptually_similar(hash1, hash2) is False

    def test_none_hash_returns_false(self):
        """Test that None hashes return False."""
        assert is_perceptually_similar(None, "abcd") is False
        assert is_perceptually_similar("abcd", None) is False
        assert is_perceptually_similar(None, None) is False

    def test_empty_hash_returns_false(self):
        """Test that empty hashes return False."""
        assert is_perceptually_similar("", "abcd") is False
        assert is_perceptually_similar("abcd", "") is False

    def test_custom_threshold(self):
        """Test similarity with custom threshold."""
        hash1 = "00000000"
        hash2 = "00000003"  # 2 bits different

        # Should be similar with threshold 5
        assert is_perceptually_similar(hash1, hash2, threshold=5) is True
        # Should not be similar with threshold 1
        assert is_perceptually_similar(hash1, hash2, threshold=1) is False


class TestFileSize:
    """Test file size retrieval."""

    def test_get_file_size(self):
        """Test getting file size."""
        content = b"Test content" * 100
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            size = get_file_size(temp_path)
            assert size == len(content)
        finally:
            os.unlink(temp_path)

    def test_nonexistent_file_returns_none(self):
        """Test that nonexistent file returns None."""
        size = get_file_size("/nonexistent/file.txt")
        assert size is None


class TestDuplicateDetector:
    """Test DuplicateDetector class."""

    def test_check_exact_duplicate(self):
        """Test detection of exact duplicates by content hash."""
        # Create mock database session
        mock_db = Mock()
        mock_media = Mock()
        mock_media.id = 42
        mock_media.content_hash = None
        mock_media.perceptual_hash = None

        # Mock query to return existing media with same hash
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_media

        detector = DuplicateDetector(mock_db)

        # Create a test file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.jpg') as f:
            f.write(b"fake image content")
            temp_path = f.name

        try:
            # Compute hash for our test file
            expected_hash = compute_content_hash(temp_path)
            mock_media.content_hash = expected_hash

            # Now test detection
            result = detector.check_for_duplicate(temp_path, "image")

            assert result["content_hash"] is not None
            assert result["file_size"] is not None
        finally:
            os.unlink(temp_path)

    def test_no_duplicate_found(self):
        """Test when no duplicate exists."""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        detector = DuplicateDetector(mock_db)

        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.jpg') as f:
            f.write(b"unique image content")
            temp_path = f.name

        try:
            result = detector.check_for_duplicate(temp_path, "image")
            assert result["is_duplicate"] is False
            assert result["duplicate_type"] is None
            assert result["original_id"] is None
        finally:
            os.unlink(temp_path)


class TestVideoHash:
    """Test video hash computation."""

    def test_video_hash_returns_content_hash(self):
        """Test that video hash always returns content hash."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.mp4') as f:
            # Write some fake video content
            f.write(b"fake video content" * 100)
            temp_path = f.name

        try:
            content_hash, frame_hash = compute_video_hash(temp_path)
            # Content hash should always work
            assert content_hash is not None
            assert len(content_hash) == 64
            # Frame hash may be None if video can't be opened
        finally:
            os.unlink(temp_path)

    @patch('ai.duplicate_detector.cv2.VideoCapture')
    def test_video_capture_always_released(self, mock_video_capture):
        """Test that VideoCapture is always released even on error."""
        mock_cap = Mock()
        mock_video_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = Exception("Read error")

        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.mp4') as f:
            f.write(b"fake video")
            temp_path = f.name

        try:
            compute_video_hash(temp_path)
            # Verify release was called even though an exception occurred
            mock_cap.release.assert_called_once()
        finally:
            os.unlink(temp_path)


@pytest.mark.skipif(not PHASH_AVAILABLE, reason="imagehash not installed")
class TestPerceptualHash:
    """Test perceptual hash computation (requires imagehash)."""

    def test_compute_perceptual_hash_for_image(self):
        """Test perceptual hash for a valid image."""
        # Create a simple image using PIL
        from PIL import Image

        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as f:
            temp_path = f.name

        try:
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(temp_path)

            phash = compute_perceptual_hash(temp_path)
            assert phash is not None
            assert len(phash) > 0
        finally:
            os.unlink(temp_path)

    def test_similar_images_have_similar_hash(self):
        """Test that similar images produce similar hashes."""
        from PIL import Image

        # Create two similar images (same color, different sizes)
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as f1:
            path1 = f1.name
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as f2:
            path2 = f2.name

        try:
            img1 = Image.new('RGB', (100, 100), color='blue')
            img1.save(path1)

            img2 = Image.new('RGB', (200, 200), color='blue')
            img2.save(path2)

            hash1 = compute_perceptual_hash(path1)
            hash2 = compute_perceptual_hash(path2)

            # Similar solid color images should have similar hashes
            assert is_perceptually_similar(hash1, hash2, threshold=20)
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_invalid_image_returns_none(self):
        """Test that invalid image files return None."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as f:
            f.write(b"not a valid image")
            temp_path = f.name

        try:
            result = compute_perceptual_hash(temp_path)
            assert result is None
        finally:
            os.unlink(temp_path)
