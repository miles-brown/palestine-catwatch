"""
Tests for utils/paths.py URL generation functions.

These tests verify that:
1. get_file_url returns R2 URLs when R2 is enabled with a public URL
2. get_file_url falls back to local URLs when R2 is disabled
3. Edge cases (None, empty string) are handled gracefully
"""

import pytest
from unittest.mock import patch
import utils.r2_storage as r2_storage_module


class TestGetFileUrl:
    """Tests for get_file_url function."""

    def test_returns_r2_url_when_r2_enabled(self):
        """Test that get_file_url returns R2 URL when R2 is enabled with public URL."""
        # Patch the module-level variables in r2_storage
        original_enabled = r2_storage_module.R2_ENABLED
        original_url = r2_storage_module.R2_PUBLIC_URL
        try:
            r2_storage_module.R2_ENABLED = True
            r2_storage_module.R2_PUBLIC_URL = 'https://pub-test.r2.dev'

            from utils.paths import get_file_url
            url = get_file_url('data/frames/1/face_0.jpg')
            assert url.startswith('https://pub-test.r2.dev/')
            assert 'data/frames/1/face_0.jpg' in url
        finally:
            r2_storage_module.R2_ENABLED = original_enabled
            r2_storage_module.R2_PUBLIC_URL = original_url

    def test_returns_local_url_when_r2_disabled(self):
        """Test that get_file_url falls back to local URL when R2 is disabled."""
        original_enabled = r2_storage_module.R2_ENABLED
        try:
            r2_storage_module.R2_ENABLED = False

            from utils.paths import get_file_url
            url = get_file_url('data/frames/1/face_0.jpg')
            assert url.startswith('/data/')
            assert url == '/data/frames/1/face_0.jpg'
        finally:
            r2_storage_module.R2_ENABLED = original_enabled

    def test_returns_local_url_when_r2_enabled_but_no_public_url(self):
        """Test that get_file_url falls back to local URL when R2 is enabled but public URL is not set."""
        original_enabled = r2_storage_module.R2_ENABLED
        original_url = r2_storage_module.R2_PUBLIC_URL
        try:
            r2_storage_module.R2_ENABLED = True
            r2_storage_module.R2_PUBLIC_URL = ''

            from utils.paths import get_file_url
            url = get_file_url('data/frames/1/face_0.jpg')
            # Should fall back to local URL since public URL is not configured
            assert url.startswith('/data/') or url.startswith('/r2/')
        finally:
            r2_storage_module.R2_ENABLED = original_enabled
            r2_storage_module.R2_PUBLIC_URL = original_url

    def test_handles_none_gracefully(self):
        """Test that get_file_url handles None input gracefully."""
        from utils.paths import get_file_url

        result = get_file_url(None)
        assert result is None

    def test_handles_empty_string_gracefully(self):
        """Test that get_file_url handles empty string input gracefully."""
        from utils.paths import get_file_url

        result = get_file_url('')
        assert result == ''


class TestGetWebUrl:
    """Tests for get_web_url function (local URL generation)."""

    def test_returns_local_data_url(self):
        """Test that get_web_url returns proper local static file URL."""
        from utils.paths import get_web_url

        url = get_web_url('data/frames/1/face_0.jpg')
        assert url == '/data/frames/1/face_0.jpg'

    def test_normalizes_path_before_url(self):
        """Test that get_web_url normalizes paths correctly."""
        from utils.paths import get_web_url

        # Test with various path formats
        url1 = get_web_url('../data/frames/1/face_0.jpg')
        url2 = get_web_url('./data/frames/1/face_0.jpg')

        # Both should normalize to the same URL
        assert '/frames/1/face_0.jpg' in url1
        assert '/frames/1/face_0.jpg' in url2

    def test_handles_none_gracefully(self):
        """Test that get_web_url handles None input gracefully."""
        from utils.paths import get_web_url

        result = get_web_url(None)
        assert result is None

    def test_handles_empty_string_gracefully(self):
        """Test that get_web_url handles empty string input gracefully."""
        from utils.paths import get_web_url

        result = get_web_url('')
        assert result == ''


class TestNormalizeForStorage:
    """Tests for normalize_for_storage function."""

    def test_normalizes_absolute_path(self):
        """Test that absolute paths are normalized to relative storage paths."""
        from utils.paths import normalize_for_storage, BACKEND_DIR

        # Test with a path that's actually within the backend directory structure
        test_path = str(BACKEND_DIR / 'data' / 'frames' / '1' / 'face.jpg')
        result = normalize_for_storage(test_path)
        assert result.startswith('data/')
        assert 'frames/1/face.jpg' in result

    def test_absolute_path_outside_backend_uses_filename(self):
        """Test that paths outside backend directory fall back to using filename."""
        from utils.paths import normalize_for_storage

        # Paths completely outside the backend directory use just the filename
        result = normalize_for_storage('/some/random/path/face.jpg')
        assert result.startswith('data/')
        assert result.endswith('face.jpg')

    def test_handles_relative_data_path(self):
        """Test that relative data paths are kept as-is."""
        from utils.paths import normalize_for_storage

        result = normalize_for_storage('data/frames/1/face.jpg')
        assert result == 'data/frames/1/face.jpg'

    def test_cleans_up_dot_dot_prefix(self):
        """Test that ../data/ prefix is cleaned up."""
        from utils.paths import normalize_for_storage

        result = normalize_for_storage('../data/frames/1/face.jpg')
        assert not result.startswith('../')
        assert result.startswith('data/')

    def test_uses_forward_slashes(self):
        """Test that backslashes are converted to forward slashes."""
        from utils.paths import normalize_for_storage

        result = normalize_for_storage('data\\frames\\1\\face.jpg')
        assert '\\' not in result
        assert '/' in result
