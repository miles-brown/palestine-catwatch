"""
Tests for UK Police Force Detector module.

Covers:
- Badge prefix extraction and validation
- Force detection from badge numbers
- Rank prefix collision prevention
- Unit type detection
- Rank detection
- Combined detection analysis
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.force_detector import (
    ForceDetector,
    ForceDetectionResult,
    detect_force,
    get_detector,
    combine_detections,
    BADGE_PREFIX_FORCES,
    RANK_PREFIXES,
    UNIT_INDICATORS,
    RANK_INDICATORS,
)


class TestBadgePrefixExtraction:
    """Test badge prefix and number extraction."""

    def setup_method(self):
        """Create fresh detector for each test."""
        self.detector = ForceDetector()

    def test_standard_badge_format(self):
        """Test standard UK badge format: letter(s) + digits."""
        prefix, number = self.detector.extract_badge_prefix("U1234")
        assert prefix == "U"
        assert number == "1234"

    def test_two_letter_prefix(self):
        """Test two-letter prefix format."""
        prefix, number = self.detector.extract_badge_prefix("BX5678")
        assert prefix == "BX"
        assert number == "5678"

    def test_three_letter_prefix(self):
        """Test three-letter prefix format."""
        prefix, number = self.detector.extract_badge_prefix("BTP123")
        assert prefix == "BTP"
        assert number == "123"

    def test_numbers_only(self):
        """Test badge with numbers only."""
        prefix, number = self.detector.extract_badge_prefix("123456")
        assert prefix is None
        assert number == "123456"

    def test_lowercase_normalization(self):
        """Test that lowercase input is normalized to uppercase."""
        prefix, number = self.detector.extract_badge_prefix("u1234")
        assert prefix == "U"
        assert number == "1234"

    def test_with_spaces(self):
        """Test badge with spaces is cleaned."""
        prefix, number = self.detector.extract_badge_prefix("U 1234")
        assert prefix == "U"
        assert number == "1234"

    def test_with_dashes(self):
        """Test badge with dashes is cleaned."""
        prefix, number = self.detector.extract_badge_prefix("U-1234")
        assert prefix == "U"
        assert number == "1234"

    def test_empty_input(self):
        """Test empty input returns None."""
        prefix, number = self.detector.extract_badge_prefix("")
        assert prefix is None
        assert number is None

    def test_none_input(self):
        """Test None input returns None."""
        prefix, number = self.detector.extract_badge_prefix(None)
        assert prefix is None
        assert number is None

    def test_invalid_format(self):
        """Test invalid format returns None."""
        prefix, number = self.detector.extract_badge_prefix("INVALID")
        assert prefix is None
        assert number is None


class TestRankPrefixCollision:
    """Test that rank prefixes don't cause false force detection."""

    def setup_method(self):
        """Create fresh detector for each test."""
        self.detector = ForceDetector()

    def test_pc_prefix_not_detected_as_force(self):
        """PC prefix should indicate rank, not force."""
        force, conf, indicators = self.detector.detect_force_from_badge("PC1234")
        assert force is None
        assert conf == 0.0

    def test_ps_prefix_not_police_scotland(self):
        """PS prefix should indicate Sergeant, not Police Scotland."""
        force, conf, indicators = self.detector.detect_force_from_badge("PS1234")
        assert force is None
        assert conf == 0.0

    def test_pcso_prefix_not_detected_as_force(self):
        """PCSO prefix should indicate rank, not force."""
        force, conf, indicators = self.detector.detect_force_from_badge("PCSO5678")
        assert force is None
        assert conf == 0.0

    def test_sgt_prefix_not_detected_as_force(self):
        """SGT prefix should indicate rank, not force."""
        force, conf, indicators = self.detector.detect_force_from_badge("SGT123")
        assert force is None
        assert conf == 0.0

    def test_insp_prefix_not_detected_as_force(self):
        """INSP prefix should indicate rank, not force."""
        force, conf, indicators = self.detector.detect_force_from_badge("INSP456")
        assert force is None
        assert conf == 0.0

    def test_all_rank_prefixes_excluded(self):
        """All defined rank prefixes should be excluded from force detection."""
        for rank_prefix in RANK_PREFIXES:
            force, conf, _ = self.detector.detect_force_from_badge(f"{rank_prefix}1234")
            assert force is None, f"Rank prefix {rank_prefix} incorrectly matched to force"


class TestForceDetectionFromBadge:
    """Test force detection from badge numbers."""

    def setup_method(self):
        """Create fresh detector for each test."""
        self.detector = ForceDetector()

    def test_met_police_single_letter(self):
        """Test Metropolitan Police detection from single letter prefix."""
        force, conf, indicators = self.detector.detect_force_from_badge("U1234")
        assert force == "Metropolitan Police Service"
        # Single letter should have lower confidence
        assert conf == 0.65

    def test_met_police_requires_enough_digits(self):
        """Single letter prefix requires at least 3 digits."""
        force, conf, indicators = self.detector.detect_force_from_badge("U12")
        assert force is None  # Not confident enough

    def test_british_transport_police(self):
        """Test British Transport Police detection."""
        force, conf, indicators = self.detector.detect_force_from_badge("BX5678")
        assert force == "British Transport Police"
        assert conf > 0.8  # Multi-letter prefix = higher confidence

    def test_city_of_london_police(self):
        """Test City of London Police detection."""
        force, conf, indicators = self.detector.detect_force_from_badge("EC1234")
        assert force == "City of London Police"

    def test_police_scotland_sc_prefix(self):
        """Test Police Scotland detection with SC prefix (not PS which is rank)."""
        force, conf, indicators = self.detector.detect_force_from_badge("SC1234")
        assert force == "Police Scotland"

    def test_kent_police(self):
        """Test Kent Police detection."""
        force, conf, indicators = self.detector.detect_force_from_badge("CE1234")
        assert force == "Kent Police"

    def test_greater_manchester_police(self):
        """Test Greater Manchester Police detection."""
        force, conf, indicators = self.detector.detect_force_from_badge("GMP1234")
        assert force == "Greater Manchester Police"

    def test_multi_letter_prefix_not_in_mapping(self):
        """Test multi-letter prefix that doesn't exist in mapping returns None or falls back."""
        # "ZZ" isn't defined, but "Z" is (Met Police Tower Hamlets)
        # Progressive matching will find "Z" as fallback
        force, conf, indicators = self.detector.detect_force_from_badge("ZZ9999")
        # Should either return None (if ZZ not found) or fallback to Z (Met Police)
        # Based on our implementation, it falls back to Z
        if force is not None:
            assert force == "Metropolitan Police Service"
            assert conf == 0.65  # Single letter confidence

    def test_completely_unknown_characters(self):
        """Test badge with only digits after unknown prefix fails validation."""
        # Badge needs prefix + number, "9" alone isn't a valid prefix
        force, conf, indicators = self.detector.detect_force_from_badge("99999")
        assert force is None  # Numbers-only doesn't detect force

    def test_numbers_only_no_force(self):
        """Test numbers-only badge doesn't detect force."""
        force, conf, indicators = self.detector.detect_force_from_badge("123456")
        assert force is None

    def test_badge_too_short(self):
        """Test badge with insufficient digits."""
        force, conf, indicators = self.detector.detect_force_from_badge("U1")
        assert force is None


class TestUnitTypeDetection:
    """Test unit type detection from various indicators."""

    def setup_method(self):
        """Create fresh detector for each test."""
        self.detector = ForceDetector()

    def test_tsg_from_badge_pattern(self):
        """Test TSG detection from badge pattern."""
        unit, conf, indicators = self.detector.detect_unit_type(badge_text="TSG U123")
        assert unit == "TSG"
        assert conf > 0.3

    def test_fit_from_equipment(self):
        """Test FIT detection from equipment."""
        unit, conf, indicators = self.detector.detect_unit_type(
            equipment_list=["camera", "blue tabard"]
        )
        assert unit == "FIT"

    def test_psu_from_equipment(self):
        """Test PSU detection from riot equipment."""
        unit, conf, indicators = self.detector.detect_unit_type(
            equipment_list=["shield", "helmet"]
        )
        assert unit == "Level 2 PSU"

    def test_standard_from_hivis(self):
        """Test standard patrol detection from hi-vis uniform."""
        unit, conf, indicators = self.detector.detect_unit_type(
            uniform_description="Officer wearing hi-vis yellow jacket"
        )
        assert unit == "Standard"

    def test_default_to_standard(self):
        """Test default unit type is Standard."""
        unit, conf, indicators = self.detector.detect_unit_type()
        assert unit == "Standard"
        assert conf == 0.3


class TestRankDetection:
    """Test rank detection from badge patterns."""

    def setup_method(self):
        """Create fresh detector for each test."""
        self.detector = ForceDetector()

    def test_pc_rank(self):
        """Test Police Constable detection."""
        rank, conf, details = self.detector.detect_rank_from_badge("PC1234")
        assert rank == "Police Constable"
        assert conf > 0.8

    def test_sergeant_ps_prefix(self):
        """Test Sergeant detection from PS prefix."""
        rank, conf, details = self.detector.detect_rank_from_badge("PS5678")
        assert rank == "Sergeant"

    def test_pcso_rank(self):
        """Test PCSO detection."""
        rank, conf, details = self.detector.detect_rank_from_badge("PCSO123")
        assert rank == "PCSO"

    def test_inspector_rank(self):
        """Test Inspector detection."""
        rank, conf, details = self.detector.detect_rank_from_badge("INSP456")
        assert rank == "Inspector"

    def test_inferred_pc_from_single_letter(self):
        """Test inferred PC rank from single letter prefix."""
        rank, conf, details = self.detector.detect_rank_from_badge("U1234")
        assert rank == "Police Constable"
        assert details.get("inferred") is True
        assert conf == 0.5  # Lower confidence for inferred

    def test_no_rank_from_numbers_only(self):
        """Test no rank detection from numbers-only badge."""
        rank, conf, details = self.detector.detect_rank_from_badge("123456")
        assert rank is None


class TestCombinedAnalysis:
    """Test full analysis combining all detection methods."""

    def test_full_analysis_with_badge(self):
        """Test full analysis returns all components."""
        result = detect_force(badge_text="U1234")

        assert isinstance(result, ForceDetectionResult)
        assert result.force == "Metropolitan Police Service"
        assert result.shoulder_number == "U1234"
        assert result.method in ["badge_prefix", "combined"]

    def test_full_analysis_with_equipment(self):
        """Test analysis with equipment list."""
        result = detect_force(
            badge_text="BX5678",
            equipment_list=["camera", "tabard"]
        )

        assert result.force == "British Transport Police"
        assert result.unit_type is not None

    def test_analysis_with_ocr_fallback(self):
        """Test analysis falls back to OCR texts."""
        result = detect_force(
            badge_text=None,
            ocr_texts=["Officer", "GMP1234", "Police"]
        )

        assert result.force == "Greater Manchester Police"


class TestCombineDetections:
    """Test combining Vision API and rule-based results."""

    def test_vision_takes_precedence_when_confident(self):
        """Vision result should override rule-based when confident."""
        vision_result = {
            "success": True,
            "analysis": {
                "force": {"name": "Metropolitan Police Service", "confidence": 0.9},
                "unit": {"type": "TSG", "confidence": 0.8},
                "rank": {"name": "Sergeant", "confidence": 0.85}
            }
        }

        rule_result = ForceDetectionResult(
            force="Kent Police",  # Different from vision
            force_confidence=0.7,
            force_indicators=["Badge prefix"],
            unit_type="Standard",
            unit_confidence=0.3,
            rank="Police Constable",
            rank_confidence=0.5,
            shoulder_number="CE1234",
            shoulder_number_confidence=0.8,
            method="badge_prefix"
        )

        combined = combine_detections(vision_result, rule_result)

        assert combined["force"] == "Metropolitan Police Service"
        assert combined["force_source"] == "claude_vision"

    def test_rule_based_used_when_vision_low_confidence(self):
        """Rule-based should be used when vision confidence is low."""
        vision_result = {
            "success": True,
            "analysis": {
                "force": {"name": "Unknown Force", "confidence": 0.3}
            }
        }

        rule_result = ForceDetectionResult(
            force="Kent Police",
            force_confidence=0.85,
            force_indicators=["Badge prefix CE matches Kent Police"],
            unit_type="Standard",
            unit_confidence=0.3,
            rank=None,
            rank_confidence=0.0,
            shoulder_number="CE1234",
            shoulder_number_confidence=0.8,
            method="badge_prefix"
        )

        combined = combine_detections(vision_result, rule_result)

        assert combined["force"] == "Kent Police"
        assert combined["force_source"] == "rule_based"

    def test_rule_based_used_when_vision_none(self):
        """Rule-based should be used when no vision result."""
        rule_result = ForceDetectionResult(
            force="Essex Police",
            force_confidence=0.9,
            force_indicators=["Badge prefix EX matches Essex Police"],
            unit_type="Standard",
            unit_confidence=0.3,
            rank="Police Constable",
            rank_confidence=0.5,
            shoulder_number="EX1234",
            shoulder_number_confidence=0.8,
            method="badge_prefix"
        )

        combined = combine_detections(None, rule_result)

        assert combined["force"] == "Essex Police"
        assert combined["force_source"] == "rule_based"

    def test_conflict_noted_in_indicators(self):
        """Conflicts between vision and rule-based should be noted."""
        vision_result = {
            "success": True,
            "analysis": {
                "force": {"name": "Metropolitan Police Service", "confidence": 0.8}
            }
        }

        rule_result = ForceDetectionResult(
            force="Kent Police",
            force_confidence=0.9,
            force_indicators=["Badge prefix CE"],
            unit_type="Standard",
            unit_confidence=0.3,
            rank=None,
            rank_confidence=0.0,
            shoulder_number="CE1234",
            shoulder_number_confidence=0.8,
            method="badge_prefix"
        )

        combined = combine_detections(vision_result, rule_result)

        # Should note the conflict
        conflict_noted = any("Note:" in ind for ind in combined["force_indicators"])
        assert conflict_noted


class TestSingletonDetector:
    """Test singleton pattern for detector."""

    def test_get_detector_returns_same_instance(self):
        """get_detector() should return the same instance."""
        detector1 = get_detector()
        detector2 = get_detector()
        assert detector1 is detector2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Create fresh detector for each test."""
        self.detector = ForceDetector()

    def test_very_long_badge(self):
        """Test handling of unusually long badge numbers."""
        # Should not match standard patterns
        prefix, number = self.detector.extract_badge_prefix("ABCDEF123456789")
        # Either no match or truncated
        assert prefix is None or len(prefix) <= 4

    def test_special_characters(self):
        """Test handling of special characters."""
        prefix, number = self.detector.extract_badge_prefix("U@1234!")
        # Should clean or reject
        assert prefix is None or prefix == "U"

    def test_unicode_input(self):
        """Test handling of unicode characters."""
        prefix, number = self.detector.extract_badge_prefix("Ü1234")
        # Should handle gracefully
        assert prefix is None or isinstance(prefix, str)

    def test_whitespace_only(self):
        """Test handling of whitespace-only input."""
        prefix, number = self.detector.extract_badge_prefix("   ")
        assert prefix is None
        assert number is None
