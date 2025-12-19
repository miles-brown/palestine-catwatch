"""
Tests for crop URL helper functions in utils/paths.py

These tests verify the priority fallback pattern:
1. face_crop_path (preferred)
2. body_crop_path (secondary)
3. image_crop_path (legacy fallback)
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGetBestCropUrl:
    """Tests for get_best_crop_url function."""

    @patch('utils.paths.get_file_url')
    def test_returns_face_crop_when_all_present(self, mock_get_file_url):
        """Test that face_crop_path takes priority over others."""
        from utils.paths import get_best_crop_url

        mock_get_file_url.side_effect = lambda x: f"https://r2.dev/{x}"

        appearance = MagicMock()
        appearance.face_crop_path = "data/frames/1/face.jpg"
        appearance.body_crop_path = "data/frames/1/body.jpg"
        appearance.image_crop_path = "data/frames/1/legacy.jpg"

        result = get_best_crop_url(appearance)

        assert "face.jpg" in result
        mock_get_file_url.assert_called_once_with("data/frames/1/face.jpg")

    @patch('utils.paths.get_file_url')
    def test_returns_body_crop_when_face_missing(self, mock_get_file_url):
        """Test that body_crop_path is used when face is missing."""
        from utils.paths import get_best_crop_url

        mock_get_file_url.side_effect = lambda x: f"https://r2.dev/{x}"

        appearance = MagicMock()
        appearance.face_crop_path = None
        appearance.body_crop_path = "data/frames/1/body.jpg"
        appearance.image_crop_path = "data/frames/1/legacy.jpg"

        result = get_best_crop_url(appearance)

        assert "body.jpg" in result
        mock_get_file_url.assert_called_once_with("data/frames/1/body.jpg")

    @patch('utils.paths.get_file_url')
    def test_returns_legacy_crop_when_others_missing(self, mock_get_file_url):
        """Test that image_crop_path is used as last resort."""
        from utils.paths import get_best_crop_url

        mock_get_file_url.side_effect = lambda x: f"https://r2.dev/{x}"

        appearance = MagicMock()
        appearance.face_crop_path = None
        appearance.body_crop_path = None
        appearance.image_crop_path = "data/frames/1/legacy.jpg"

        result = get_best_crop_url(appearance)

        assert "legacy.jpg" in result
        mock_get_file_url.assert_called_once_with("data/frames/1/legacy.jpg")

    def test_returns_none_when_no_crops(self):
        """Test that None is returned when all crops are missing."""
        from utils.paths import get_best_crop_url

        appearance = MagicMock()
        appearance.face_crop_path = None
        appearance.body_crop_path = None
        appearance.image_crop_path = None

        result = get_best_crop_url(appearance)

        assert result is None

    def test_returns_none_for_none_appearance(self):
        """Test that None is returned for None input."""
        from utils.paths import get_best_crop_url

        result = get_best_crop_url(None)

        assert result is None

    @patch('utils.paths.get_file_url')
    def test_handles_dict_input(self, mock_get_file_url):
        """Test that dict input (not model) is handled correctly."""
        from utils.paths import get_best_crop_url

        mock_get_file_url.side_effect = lambda x: f"https://r2.dev/{x}"

        appearance = {
            "face_crop_path": "data/frames/1/face.jpg",
            "body_crop_path": "data/frames/1/body.jpg",
            "image_crop_path": "data/frames/1/legacy.jpg"
        }

        result = get_best_crop_url(appearance)

        assert "face.jpg" in result


class TestGetAllCropUrls:
    """Tests for get_all_crop_urls function."""

    @patch('utils.paths.get_file_url')
    def test_returns_all_urls(self, mock_get_file_url):
        """Test that all crop URLs are returned."""
        from utils.paths import get_all_crop_urls

        mock_get_file_url.side_effect = lambda x: f"https://r2.dev/{x}"

        appearance = MagicMock()
        appearance.face_crop_path = "data/frames/1/face.jpg"
        appearance.body_crop_path = "data/frames/1/body.jpg"
        appearance.image_crop_path = "data/frames/1/legacy.jpg"

        result = get_all_crop_urls(appearance)

        assert "face.jpg" in result["face_crop_url"]
        assert "body.jpg" in result["body_crop_url"]
        assert "face.jpg" in result["best_crop_url"]  # face takes priority

    @patch('utils.paths.get_file_url')
    def test_best_crop_uses_priority(self, mock_get_file_url):
        """Test that best_crop_url follows priority order."""
        from utils.paths import get_all_crop_urls

        mock_get_file_url.side_effect = lambda x: f"https://r2.dev/{x}"

        appearance = MagicMock()
        appearance.face_crop_path = None
        appearance.body_crop_path = "data/frames/1/body.jpg"
        appearance.image_crop_path = "data/frames/1/legacy.jpg"

        result = get_all_crop_urls(appearance)

        assert result["face_crop_url"] is None
        assert "body.jpg" in result["body_crop_url"]
        assert "body.jpg" in result["best_crop_url"]  # body is best available

    def test_returns_nulls_for_none_appearance(self):
        """Test that nulls are returned for None input."""
        from utils.paths import get_all_crop_urls

        result = get_all_crop_urls(None)

        assert result["face_crop_url"] is None
        assert result["body_crop_url"] is None
        assert result["best_crop_url"] is None
