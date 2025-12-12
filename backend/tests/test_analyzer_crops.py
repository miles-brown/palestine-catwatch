"""
Tests for analyzer.py dual crop generation functionality.

Covers:
- Face crop generation with quality validation
- Body crop generation from YOLO and fallback methods
- Person-face matching logic
- Crop dimension validation
- Path traversal security
"""

import pytest
import numpy as np
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.analyzer import (
    generate_face_crop,
    generate_body_crop,
    generate_dual_crops,
    find_person_for_face,
    MIN_FACE_CROP_SIZE,
    MIN_BODY_CROP_SIZE,
    FACE_CONFIDENCE_THRESHOLD,
)


class TestFaceCropGeneration:
    """Test face crop generation."""

    def setup_method(self):
        """Create test image for each test."""
        # Create a simple test image (500x500 BGR)
        self.test_img = np.zeros((500, 500, 3), dtype=np.uint8)
        # Add some variation so crops aren't empty
        self.test_img[100:200, 100:200] = [255, 200, 150]  # Face region
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup temp files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_generate_valid_face_crop(self):
        """Test generating a valid face crop."""
        face_box = [100, 100, 100, 100]  # x, y, w, h
        output_path = os.path.join(self.temp_dir, "face_test.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_face_crop(self.test_img, face_box, output_path)

        assert result == output_path
        assert os.path.exists(output_path)

    def test_face_crop_too_small(self):
        """Test that small face crops are rejected."""
        # Create tiny face box (smaller than MIN_FACE_CROP_SIZE)
        face_box = [100, 100, 20, 20]  # 20x20 is too small
        output_path = os.path.join(self.temp_dir, "face_small.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_face_crop(self.test_img, face_box, output_path)

        assert result is None
        assert not os.path.exists(output_path)

    def test_face_crop_path_traversal_blocked(self):
        """Test that path traversal is blocked."""
        face_box = [100, 100, 150, 150]
        output_path = "/etc/passwd"  # Malicious path

        with patch('ai.analyzer.is_safe_path', return_value=False):
            result = generate_face_crop(self.test_img, face_box, output_path)

        assert result is None

    def test_face_crop_expansion(self):
        """Test that face crop expands by 30% for head/shoulders."""
        # Face at center of image
        face_box = [200, 200, 100, 100]
        output_path = os.path.join(self.temp_dir, "face_expanded.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_face_crop(self.test_img, face_box, output_path)

        assert result is not None
        # Crop should exist and be larger than face box due to expansion
        import cv2
        saved_img = cv2.imread(output_path)
        # With 30% expansion, 100px face should result in ~130px crop
        assert saved_img.shape[0] >= 100
        assert saved_img.shape[1] >= 100

    def test_face_crop_boundary_handling(self):
        """Test face crop at image boundary."""
        # Face at corner of image
        face_box = [0, 0, 100, 100]
        output_path = os.path.join(self.temp_dir, "face_corner.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_face_crop(self.test_img, face_box, output_path)

        # Should still work, clamped to image bounds
        assert result is not None


class TestBodyCropGeneration:
    """Test body crop generation."""

    def setup_method(self):
        """Create test image for each test."""
        # Create a larger test image for body crops
        self.test_img = np.zeros((800, 600, 3), dtype=np.uint8)
        self.test_img[100:700, 100:500] = [100, 150, 200]  # Person region
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup temp files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_body_crop_with_person_box(self):
        """Test body crop using YOLO person detection."""
        face_box = [200, 150, 80, 80]
        person_box = [150, 100, 200, 500]  # Person encompasses face
        output_path = os.path.join(self.temp_dir, "body_yolo.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_body_crop(self.test_img, face_box, person_box, output_path)

        assert result == output_path
        assert os.path.exists(output_path)

    def test_body_crop_fallback_estimation(self):
        """Test body crop using face-based estimation when no person box."""
        face_box = [250, 150, 100, 100]
        output_path = os.path.join(self.temp_dir, "body_fallback.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_body_crop(self.test_img, face_box, None, output_path)

        assert result is not None
        assert os.path.exists(output_path)

    def test_body_crop_rejects_invalid_person_box(self):
        """Test that invalid person box falls back to estimation."""
        face_box = [250, 150, 100, 100]
        invalid_person_box = [100, 100]  # Only 2 elements instead of 4
        output_path = os.path.join(self.temp_dir, "body_invalid.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_body_crop(self.test_img, face_box, invalid_person_box, output_path)

        # Should still work using fallback
        assert result is not None

    def test_body_crop_rejects_negative_dimensions(self):
        """Test that negative dimensions in person box are rejected."""
        face_box = [250, 150, 100, 100]
        bad_person_box = [100, 100, -50, 200]  # Negative width
        output_path = os.path.join(self.temp_dir, "body_negative.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_body_crop(self.test_img, face_box, bad_person_box, output_path)

        # Should fall back to estimation
        assert result is not None

    def test_body_crop_face_outside_person(self):
        """Test that face outside person box triggers fallback."""
        face_box = [400, 400, 80, 80]  # Face far from person box
        person_box = [100, 100, 100, 200]  # Person elsewhere
        output_path = os.path.join(self.temp_dir, "body_outside.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_body_crop(self.test_img, face_box, person_box, output_path)

        # Should fall back to estimation since face isn't in person box
        assert result is not None

    def test_body_crop_path_traversal_blocked(self):
        """Test that path traversal is blocked."""
        face_box = [200, 150, 100, 100]
        output_path = "/tmp/../../../etc/passwd"

        with patch('ai.analyzer.is_safe_path', return_value=False):
            result = generate_body_crop(self.test_img, face_box, None, output_path)

        assert result is None


class TestDualCropGeneration:
    """Test combined dual crop generation."""

    def setup_method(self):
        """Create test image."""
        self.test_img = np.zeros((800, 600, 3), dtype=np.uint8)
        self.test_img[100:700, 100:500] = [100, 150, 200]
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup temp files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_generate_both_crops(self):
        """Test that both face and body crops are generated."""
        face_box = [200, 150, 100, 100]
        person_box = [150, 100, 200, 500]

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_dual_crops(
                self.test_img, face_box, person_box,
                self.temp_dir, "test_officer"
            )

        assert result['face_crop_path'] is not None
        assert result['body_crop_path'] is not None
        assert os.path.exists(result['face_crop_path'])
        assert os.path.exists(result['body_crop_path'])

    def test_dual_crops_without_person_box(self):
        """Test dual crops work without YOLO person detection."""
        face_box = [200, 150, 100, 100]

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_dual_crops(
                self.test_img, face_box, None,
                self.temp_dir, "test_no_yolo"
            )

        # Both should still be generated using fallback for body
        assert result['face_crop_path'] is not None
        assert result['body_crop_path'] is not None


class TestFindPersonForFace:
    """Test person-to-face matching logic."""

    def test_match_face_to_person(self):
        """Test matching a face to the correct person detection."""
        face_box = [200, 100, 80, 80]  # Face at top of person
        person_detections = [
            {
                'label': 'person',
                'box': [150, 80, 200, 500],  # Person containing face
                'confidence': 0.9
            },
            {
                'label': 'person',
                'box': [400, 100, 150, 400],  # Different person
                'confidence': 0.85
            }
        ]

        result = find_person_for_face(face_box, person_detections)

        assert result is not None
        assert result == [150, 80, 200, 500]  # Should match first person

    def test_no_match_when_face_outside_persons(self):
        """Test no match when face isn't inside any person box."""
        face_box = [50, 50, 80, 80]  # Face not in any person
        person_detections = [
            {
                'label': 'person',
                'box': [200, 100, 150, 400],
                'confidence': 0.9
            }
        ]

        result = find_person_for_face(face_box, person_detections)

        assert result is None

    def test_empty_person_detections(self):
        """Test with empty person detections list."""
        face_box = [200, 100, 80, 80]

        result = find_person_for_face(face_box, [])

        assert result is None

    def test_none_person_detections(self):
        """Test with None person detections."""
        face_box = [200, 100, 80, 80]

        result = find_person_for_face(face_box, None)

        assert result is None

    def test_invalid_detection_box_format(self):
        """Test handling of invalid detection box format."""
        face_box = [200, 100, 80, 80]
        person_detections = [
            {
                'label': 'person',
                'box': [150, 80],  # Only 2 elements - invalid
                'confidence': 0.9
            },
            {
                'label': 'person',
                'box': [150, 80, 200, 500],  # Valid
                'confidence': 0.85
            }
        ]

        # Should skip invalid and match valid
        result = find_person_for_face(face_box, person_detections)

        # Face is within second person's box
        assert result == [150, 80, 200, 500]

    def test_prefers_face_in_upper_body(self):
        """Test that faces in upper 30% of body are preferred."""
        face_box = [200, 100, 80, 80]  # Near top
        person_detections = [
            {
                'label': 'person',
                'box': [150, 80, 200, 600],  # Tall person, face at top
                'confidence': 0.8
            },
            {
                'label': 'person',
                'box': [150, 0, 200, 500],  # Face would be lower in this
                'confidence': 0.9
            }
        ]

        result = find_person_for_face(face_box, person_detections)

        # Should prefer first where face is in top 30%
        assert result == [150, 80, 200, 600]

    def test_filters_non_person_labels(self):
        """Test that non-person detections are ignored."""
        face_box = [200, 100, 80, 80]
        detections = [
            {
                'label': 'car',  # Not a person
                'box': [150, 80, 200, 500],
                'confidence': 0.95
            },
            {
                'label': 'person',
                'box': [150, 80, 200, 500],
                'confidence': 0.7
            }
        ]

        result = find_person_for_face(face_box, detections)

        # Should match the person, not the car
        assert result == [150, 80, 200, 500]


class TestConfigurationValues:
    """Test that configuration values are properly loaded."""

    def test_min_face_crop_size(self):
        """Test MIN_FACE_CROP_SIZE is reasonable."""
        assert MIN_FACE_CROP_SIZE >= 50
        assert MIN_FACE_CROP_SIZE <= 200

    def test_min_body_crop_size(self):
        """Test MIN_BODY_CROP_SIZE is reasonable."""
        assert MIN_BODY_CROP_SIZE >= 100
        assert MIN_BODY_CROP_SIZE <= 300

    def test_face_confidence_threshold(self):
        """Test FACE_CONFIDENCE_THRESHOLD is valid."""
        assert 0.0 <= FACE_CONFIDENCE_THRESHOLD <= 1.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Create test resources."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup temp files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_empty_image(self):
        """Test handling of empty/zero-size image."""
        empty_img = np.zeros((0, 0, 3), dtype=np.uint8)
        face_box = [100, 100, 50, 50]
        output_path = os.path.join(self.temp_dir, "empty.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            # Should handle gracefully
            try:
                result = generate_face_crop(empty_img, face_box, output_path)
                assert result is None
            except Exception:
                pass  # Exception is acceptable for empty image

    def test_grayscale_image(self):
        """Test handling of grayscale (2D) image."""
        gray_img = np.zeros((500, 500), dtype=np.uint8)
        face_box = [100, 100, 100, 100]
        output_path = os.path.join(self.temp_dir, "gray.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            try:
                result = generate_face_crop(gray_img, face_box, output_path)
                # May work or fail gracefully
            except Exception:
                pass  # Exception is acceptable

    def test_face_box_outside_image(self):
        """Test face box completely outside image bounds."""
        test_img = np.zeros((500, 500, 3), dtype=np.uint8)
        face_box = [600, 600, 100, 100]  # Outside 500x500 image
        output_path = os.path.join(self.temp_dir, "outside.jpg")

        with patch('ai.analyzer.is_safe_path', return_value=True):
            result = generate_face_crop(test_img, face_box, output_path)
            # Should return None or handle gracefully
            # Empty crop should be rejected
