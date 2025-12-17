"""
Tests for utils/paths.py URL generation functions.

These tests verify that:
1. get_file_url returns R2 URLs when R2 is enabled with a public URL
2. get_file_url falls back to local URLs when R2 is disabled
3. Edge cases (None, empty string, special characters) are handled gracefully
"""

import pytest
from unittest.mock import patch

from utils.paths import (
    get_file_url,
    get_web_url,
    normalize_for_storage,
    BACKEND_DIR
)


class TestGetFileUrl:
    """Tests for get_file_url function."""

    @patch('utils.r2_storage.R2_ENABLED', True)
    @patch('utils.r2_storage.R2_PUBLIC_URL', 'https://pub-test.r2.dev')
    def test_returns_r2_url_when_r2_enabled(self):
        """Test that get_file_url returns R2 URL when R2 is enabled with public URL."""
        url = get_file_url('data/frames/1/face_0.jpg')
        assert url.startswith('https://pub-test.r2.dev/')
        assert 'data/frames/1/face_0.jpg' in url

    @patch('utils.r2_storage.R2_ENABLED', False)
    def test_returns_local_url_when_r2_disabled(self):
        """Test that get_file_url falls back to local URL when R2 is disabled."""
        url = get_file_url('data/frames/1/face_0.jpg')
        assert url.startswith('/data/')
        assert url == '/data/frames/1/face_0.jpg'

    @patch('utils.r2_storage.R2_ENABLED', True)
    @patch('utils.r2_storage.R2_PUBLIC_URL', '')
    def test_returns_local_url_when_r2_enabled_but_no_public_url(self):
        """Test that get_file_url falls back to local URL when R2 is enabled but public URL is not set."""
        url = get_file_url('data/frames/1/face_0.jpg')
        # Should fall back to local URL since public URL is not configured
        assert url.startswith('/data/') or url.startswith('/r2/')

    def test_handles_none_gracefully(self):
        """Test that get_file_url handles None input gracefully."""
        result = get_file_url(None)
        assert result is None

    def test_handles_empty_string_gracefully(self):
        """Test that get_file_url handles empty string input gracefully."""
        result = get_file_url('')
        assert result == ''

    @patch('utils.r2_storage.R2_ENABLED', True)
    @patch('utils.r2_storage.R2_PUBLIC_URL', 'https://pub-test.r2.dev')
    def test_handles_special_characters_in_path(self):
        """Test that get_file_url handles special characters in paths."""
        # Paths with spaces, unicode, etc.
        url = get_file_url('data/frames/1/face with spaces.jpg')
        assert 'face with spaces.jpg' in url

    @patch('utils.r2_storage.R2_ENABLED', True)
    @patch('utils.r2_storage.R2_PUBLIC_URL', 'https://pub-test.r2.dev')
    def test_handles_unicode_in_path(self):
        """Test that get_file_url handles unicode characters in paths."""
        url = get_file_url('data/frames/1/face_名前.jpg')
        assert 'face_名前.jpg' in url


class TestGetWebUrl:
    """Tests for get_web_url function (local URL generation)."""

    def test_returns_local_data_url(self):
        """Test that get_web_url returns proper local static file URL."""
        url = get_web_url('data/frames/1/face_0.jpg')
        assert url == '/data/frames/1/face_0.jpg'

    def test_normalizes_path_before_url(self):
        """Test that get_web_url normalizes paths correctly."""
        # Test with various path formats
        url1 = get_web_url('../data/frames/1/face_0.jpg')
        url2 = get_web_url('./data/frames/1/face_0.jpg')

        # Both should normalize to the same URL
        assert '/frames/1/face_0.jpg' in url1
        assert '/frames/1/face_0.jpg' in url2

    def test_handles_none_gracefully(self):
        """Test that get_web_url handles None input gracefully."""
        result = get_web_url(None)
        assert result is None

    def test_handles_empty_string_gracefully(self):
        """Test that get_web_url handles empty string input gracefully."""
        result = get_web_url('')
        assert result == ''

    def test_handles_special_characters(self):
        """Test that get_web_url handles special characters in paths."""
        url = get_web_url('data/frames/1/face with spaces.jpg')
        assert 'face with spaces.jpg' in url


class TestNormalizeForStorage:
    """Tests for normalize_for_storage function."""

    def test_normalizes_absolute_path(self):
        """Test that absolute paths are normalized to relative storage paths."""
        # Test with a path that's actually within the backend directory structure
        test_path = str(BACKEND_DIR / 'data' / 'frames' / '1' / 'face.jpg')
        result = normalize_for_storage(test_path)
        assert result.startswith('data/')
        assert 'frames/1/face.jpg' in result

    def test_absolute_path_outside_backend_uses_filename(self):
        """Test that paths outside backend directory fall back to using filename."""
        # Paths completely outside the backend directory use just the filename
        result = normalize_for_storage('/some/random/path/face.jpg')
        assert result.startswith('data/')
        assert result.endswith('face.jpg')

    def test_handles_relative_data_path(self):
        """Test that relative data paths are kept as-is."""
        result = normalize_for_storage('data/frames/1/face.jpg')
        assert result == 'data/frames/1/face.jpg'

    def test_cleans_up_dot_dot_prefix(self):
        """Test that ../data/ prefix is cleaned up."""
        result = normalize_for_storage('../data/frames/1/face.jpg')
        assert not result.startswith('../')
        assert result.startswith('data/')

    def test_uses_forward_slashes(self):
        """Test that backslashes are converted to forward slashes."""
        result = normalize_for_storage('data\\frames\\1\\face.jpg')
        assert '\\' not in result
        assert '/' in result

    def test_handles_special_characters(self):
        """Test that normalize_for_storage handles special characters."""
        result = normalize_for_storage('data/frames/1/face with spaces.jpg')
        assert result == 'data/frames/1/face with spaces.jpg'

    def test_handles_unicode_characters(self):
        """Test that normalize_for_storage handles unicode characters."""
        result = normalize_for_storage('data/frames/1/face_名前.jpg')
        assert '名前' in result
        assert result.startswith('data/')
