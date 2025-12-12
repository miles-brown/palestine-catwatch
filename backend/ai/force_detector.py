"""
Rule-Based UK Police Force Detector

Provides fallback force detection when Claude Vision API is unavailable or returns
low confidence results. Uses badge prefix patterns, uniform characteristics, and
visual indicators to identify UK police forces.
"""
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass


# =============================================================================
# UK POLICE FORCE BADGE PREFIX MAPPING
# =============================================================================
# UK police shoulder numbers follow predictable patterns based on force
# Format: 1-2 letter prefix + 2-5 digit number (e.g., U1234, AB123)

BADGE_PREFIX_FORCES = {
    # Metropolitan Police Service (MPS)
    # Uses single letters for boroughs/units
    "A": "Metropolitan Police Service",  # Westminster
    "B": "Metropolitan Police Service",  # Chelsea & Kensington (merged with Westminster)
    "C": "Metropolitan Police Service",  # Central (St James's)
    "D": "Metropolitan Police Service",  # Ealing
    "E": "Metropolitan Police Service",  # Enfield
    "F": "Metropolitan Police Service",  # Hammersmith & Fulham
    "G": "Metropolitan Police Service",  # Greenwich
    "H": "Metropolitan Police Service",  # Hackney
    "I": "Metropolitan Police Service",  # Islington
    "J": "Metropolitan Police Service",  # Hounslow (merged)
    "K": "Metropolitan Police Service",  # Kingston
    "L": "Metropolitan Police Service",  # Lambeth
    "M": "Metropolitan Police Service",  # Merton
    "N": "Metropolitan Police Service",  # Newham
    "P": "Metropolitan Police Service",  # Lewisham
    "Q": "Metropolitan Police Service",  # Brent
    "R": "Metropolitan Police Service",  # Redbridge
    "S": "Metropolitan Police Service",  # Southwark
    "T": "Metropolitan Police Service",  # Havering
    "U": "Metropolitan Police Service",  # Specialist operations / TSG
    "V": "Metropolitan Police Service",  # Wandsworth
    "W": "Metropolitan Police Service",  # Waltham Forest
    "X": "Metropolitan Police Service",  # Hillingdon
    "Y": "Metropolitan Police Service",  # Croydon
    "Z": "Metropolitan Police Service",  # Tower Hamlets

    # City of London Police
    "EC": "City of London Police",  # EC prefix
    "CO": "City of London Police",  # City Operations

    # British Transport Police
    "BX": "British Transport Police",
    "BTP": "British Transport Police",

    # Ministry of Defence Police
    "QK": "Ministry of Defence Police",
    "MDP": "Ministry of Defence Police",

    # Regional Forces
    "CE": "Kent Police",
    "KE": "Kent Police",

    "EX": "Essex Police",
    "ES": "Essex Police",

    "SX": "Sussex Police",
    "SU": "Sussex Police",

    "SR": "Surrey Police",

    "TH": "Thames Valley Police",
    "TV": "Thames Valley Police",

    "HA": "Hampshire Constabulary",
    "HC": "Hampshire Constabulary",

    "WL": "Wiltshire Police",

    "DV": "Devon and Cornwall Police",
    "DC": "Devon and Cornwall Police",

    "DO": "Dorset Police",

    "AS": "Avon and Somerset Police",
    "AV": "Avon and Somerset Police",

    "GM": "Greater Manchester Police",
    "GMP": "Greater Manchester Police",

    "WM": "West Midlands Police",
    "WMP": "West Midlands Police",

    "WY": "West Yorkshire Police",
    "WYP": "West Yorkshire Police",

    "SY": "South Yorkshire Police",
    "SYP": "South Yorkshire Police",

    "NY": "North Yorkshire Police",
    "NYP": "North Yorkshire Police",

    "HU": "Humberside Police",

    "MS": "Merseyside Police",
    "MER": "Merseyside Police",

    "CH": "Cheshire Constabulary",

    "LA": "Lancashire Constabulary",

    "CU": "Cumbria Constabulary",

    "DU": "Durham Constabulary",

    "NB": "Northumbria Police",
    "NU": "Northumbria Police",

    "CL": "Cleveland Police",

    "NF": "Norfolk Constabulary",

    "SF": "Suffolk Constabulary",

    "CB": "Cambridgeshire Constabulary",

    "LI": "Lincolnshire Police",

    "NM": "Northamptonshire Police",

    "LE": "Leicestershire Police",

    "NT": "Nottinghamshire Police",

    "DB": "Derbyshire Constabulary",

    "ST": "Staffordshire Police",

    "WA": "Warwickshire Police",

    "WS": "West Mercia Police",
    "WR": "West Mercia Police",

    "GL": "Gloucestershire Constabulary",

    "HW": "Hertfordshire Constabulary",
    "HF": "Hertfordshire Constabulary",

    "BD": "Bedfordshire Police",

    # Welsh Forces
    "SW": "South Wales Police",
    "SWP": "South Wales Police",

    "GW": "Gwent Police",
    "GWP": "Gwent Police",

    "DY": "Dyfed-Powys Police",
    "DP": "Dyfed-Powys Police",

    "NW": "North Wales Police",
    "NWP": "North Wales Police",

    # Scotland
    "PS": "Police Scotland",
    "SC": "Police Scotland",

    # Northern Ireland
    "PSNI": "Police Service of Northern Ireland",
}


# =============================================================================
# UNIT TYPE PATTERNS
# =============================================================================

UNIT_INDICATORS = {
    "TSG": {
        "patterns": ["tsg", "territorial support", "u\\d{3,4}"],
        "equipment": ["nato helmet", "riot shield", "shield", "baton"],
        "uniform": ["dark operational", "no hi-vis", "black tactical"]
    },
    "FIT": {
        "patterns": ["fit", "forward intelligence", "evidence gatherer"],
        "equipment": ["camera", "video camera", "tabard"],
        "uniform": ["blue tabard", "evidence gatherer vest"]
    },
    "Level 2 PSU": {
        "patterns": ["psu", "level 2", "public order"],
        "equipment": ["shield", "helmet", "body armor"],
        "uniform": ["riot gear", "protective equipment"]
    },
    "SCO19": {
        "patterns": ["sco19", "firearms", "armed"],
        "equipment": ["firearm", "rifle", "pistol", "ballistic vest"],
        "uniform": ["armed response", "ballistic"]
    },
    "Dog Unit": {
        "patterns": ["dog", "k9", "canine"],
        "equipment": ["dog lead", "muzzle"],
        "uniform": []
    },
    "Mounted": {
        "patterns": ["mounted", "horse"],
        "equipment": ["horse", "riding helmet"],
        "uniform": ["mounted branch"]
    },
    "Standard": {
        "patterns": [],
        "equipment": [],
        "uniform": ["hi-vis", "high visibility", "yellow jacket"]
    }
}


# =============================================================================
# RANK INDICATORS
# =============================================================================

RANK_INDICATORS = {
    "Police Constable": {
        "chevrons": 0,
        "pips": 0,
        "crown": False,
        "pattern": r"^PC\s*\d+"
    },
    "Sergeant": {
        "chevrons": 3,
        "pips": 0,
        "crown": False,
        "pattern": r"^(PS|SGT)\s*\d+"
    },
    "Inspector": {
        "chevrons": 0,
        "pips": 2,
        "crown": False,
        "pattern": r"^(INSP|INS)\s*\d+"
    },
    "Chief Inspector": {
        "chevrons": 0,
        "pips": 3,
        "crown": False,
        "pattern": r"^(CI|CHINSP)\s*\d+"
    },
    "Superintendent": {
        "chevrons": 0,
        "pips": 0,
        "crown": True,
        "pattern": r"^(SUPT)\s*\d+"
    },
    "PCSO": {
        "chevrons": 0,
        "pips": 0,
        "crown": False,
        "pattern": r"^PCSO\s*\d+"
    }
}


@dataclass
class ForceDetectionResult:
    """Result of force detection analysis."""
    force: Optional[str]
    force_confidence: float
    force_indicators: List[str]
    unit_type: Optional[str]
    unit_confidence: float
    rank: Optional[str]
    rank_confidence: float
    shoulder_number: Optional[str]
    shoulder_number_confidence: float
    method: str  # "badge_prefix", "ocr_pattern", "combined"


class ForceDetector:
    """
    Rule-based UK police force detector.

    Uses badge number prefixes and pattern matching to identify:
    - Police force
    - Unit type (TSG, FIT, PSU, etc.)
    - Rank (PC, Sergeant, Inspector, etc.)
    """

    def __init__(self):
        # Compile badge patterns for efficiency
        self.badge_patterns = [
            re.compile(r'^([A-Z]{1,4})(\d{2,5})$'),  # Standard: U1234, BTP123
            re.compile(r'^(PC|PS|PCSO)(\d{3,5})$'),  # Rank prefix: PC4567
            re.compile(r'^(\d{4,6})$'),               # Numbers only: 1234
        ]

    def extract_badge_prefix(self, badge_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract prefix and number from badge text.

        Args:
            badge_text: Raw badge/shoulder number text

        Returns:
            Tuple of (prefix, number) or (None, None) if no match
        """
        if not badge_text:
            return None, None

        # Clean and normalize
        cleaned = badge_text.strip().upper().replace(" ", "").replace("-", "")

        for pattern in self.badge_patterns:
            match = pattern.match(cleaned)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return groups[0], groups[1]
                elif len(groups) == 1:
                    # Numbers only
                    return None, groups[0]

        return None, None

    def detect_force_from_badge(self, badge_text: str) -> Tuple[Optional[str], float, List[str]]:
        """
        Detect police force from badge/shoulder number.

        Args:
            badge_text: Raw badge text from OCR

        Returns:
            Tuple of (force_name, confidence, indicators)
        """
        prefix, number = self.extract_badge_prefix(badge_text)

        if not prefix:
            return None, 0.0, []

        # Check progressively shorter prefixes
        for length in range(len(prefix), 0, -1):
            test_prefix = prefix[:length]
            if test_prefix in BADGE_PREFIX_FORCES:
                force = BADGE_PREFIX_FORCES[test_prefix]
                # Confidence based on prefix length match
                confidence = min(0.95, 0.7 + (length * 0.1))
                indicators = [f"Badge prefix '{test_prefix}' matches {force}"]

                # Higher confidence for longer, more specific prefixes
                if length >= 2:
                    confidence = min(0.98, confidence + 0.1)
                    indicators.append(f"Full prefix match: {prefix}")

                return force, confidence, indicators

        return None, 0.0, []

    def detect_unit_type(
        self,
        badge_text: Optional[str] = None,
        equipment_list: Optional[List[str]] = None,
        uniform_description: Optional[str] = None
    ) -> Tuple[Optional[str], float, List[str]]:
        """
        Detect unit type from available indicators.

        Args:
            badge_text: Badge/shoulder number
            equipment_list: List of detected equipment
            uniform_description: Description of uniform

        Returns:
            Tuple of (unit_type, confidence, indicators)
        """
        scores: Dict[str, Tuple[float, List[str]]] = {}

        for unit_type, indicators in UNIT_INDICATORS.items():
            score = 0.0
            matched_indicators = []

            # Check badge patterns
            if badge_text:
                badge_lower = badge_text.lower()
                for pattern in indicators["patterns"]:
                    if re.search(pattern, badge_lower):
                        score += 0.4
                        matched_indicators.append(f"Badge matches {unit_type} pattern")
                        break

            # Check equipment
            if equipment_list:
                equipment_lower = [e.lower() for e in equipment_list]
                for equip in indicators["equipment"]:
                    if any(equip in e for e in equipment_lower):
                        score += 0.2
                        matched_indicators.append(f"Equipment: {equip}")

            # Check uniform description
            if uniform_description:
                uniform_lower = uniform_description.lower()
                for uniform_pattern in indicators["uniform"]:
                    if uniform_pattern in uniform_lower:
                        score += 0.3
                        matched_indicators.append(f"Uniform: {uniform_pattern}")

            if score > 0:
                scores[unit_type] = (score, matched_indicators)

        if not scores:
            return "Standard", 0.3, ["Default to standard patrol"]

        # Return highest scoring unit
        best_unit = max(scores.keys(), key=lambda k: scores[k][0])
        best_score, best_indicators = scores[best_unit]

        # Cap confidence at 0.9 for rule-based detection
        return best_unit, min(0.9, best_score), best_indicators

    def detect_rank_from_badge(self, badge_text: str) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """
        Detect rank from badge prefix patterns.

        Args:
            badge_text: Badge/shoulder number text

        Returns:
            Tuple of (rank, confidence, indicators_dict)
        """
        if not badge_text:
            return None, 0.0, {}

        badge_upper = badge_text.upper().replace(" ", "")

        for rank, indicators in RANK_INDICATORS.items():
            pattern = indicators.get("pattern")
            if pattern and re.match(pattern, badge_upper):
                return (
                    rank,
                    0.85,
                    {
                        "pattern_match": True,
                        "chevrons": indicators["chevrons"],
                        "pips": indicators["pips"],
                        "crown": indicators["crown"]
                    }
                )

        # Default to PC for standard numbered badges
        prefix, number = self.extract_badge_prefix(badge_text)
        if prefix and number:
            # Single letter prefix is typically PC
            if len(prefix) == 1 and prefix.isalpha():
                return "Police Constable", 0.5, {"inferred": True}

        return None, 0.0, {}

    def analyze(
        self,
        badge_text: Optional[str] = None,
        equipment_list: Optional[List[str]] = None,
        uniform_description: Optional[str] = None,
        ocr_texts: Optional[List[str]] = None
    ) -> ForceDetectionResult:
        """
        Comprehensive force detection using all available inputs.

        Args:
            badge_text: Primary badge/shoulder number
            equipment_list: List of detected equipment
            uniform_description: Description of uniform
            ocr_texts: Additional OCR text from image

        Returns:
            ForceDetectionResult with all detection results
        """
        # Try badge-based force detection
        force, force_conf, force_indicators = None, 0.0, []
        shoulder_number, shoulder_conf = None, 0.0

        # Primary badge text
        if badge_text:
            force, force_conf, force_indicators = self.detect_force_from_badge(badge_text)
            prefix, number = self.extract_badge_prefix(badge_text)
            if prefix or number:
                shoulder_number = badge_text.upper().replace(" ", "")
                shoulder_conf = 0.8

        # Try OCR texts if primary badge didn't work
        if not force and ocr_texts:
            for text in ocr_texts:
                f, fc, fi = self.detect_force_from_badge(text)
                if fc > force_conf:
                    force, force_conf, force_indicators = f, fc, fi
                    prefix, number = self.extract_badge_prefix(text)
                    if prefix or number:
                        shoulder_number = text.upper().replace(" ", "")
                        shoulder_conf = 0.6

        # Detect unit type
        unit_type, unit_conf, _ = self.detect_unit_type(
            badge_text=badge_text,
            equipment_list=equipment_list,
            uniform_description=uniform_description
        )

        # Detect rank
        rank, rank_conf, _ = self.detect_rank_from_badge(badge_text or "")

        # Determine method used
        method = "none"
        if force_conf > 0:
            method = "badge_prefix"
        if unit_conf > 0.3 or rank_conf > 0:
            method = "combined" if method == "badge_prefix" else "pattern_match"

        return ForceDetectionResult(
            force=force,
            force_confidence=force_conf,
            force_indicators=force_indicators,
            unit_type=unit_type,
            unit_confidence=unit_conf,
            rank=rank,
            rank_confidence=rank_conf,
            shoulder_number=shoulder_number,
            shoulder_number_confidence=shoulder_conf,
            method=method
        )


def combine_detections(
    vision_result: Optional[Dict[str, Any]],
    rule_result: ForceDetectionResult,
    vision_confidence_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Combine Claude Vision API results with rule-based detection.

    Strategy:
    - Vision result takes precedence if confidence > threshold
    - Rule-based fills in gaps or low-confidence vision results
    - Conflicts logged for review

    Args:
        vision_result: Results from Claude Vision API (or None)
        rule_result: Results from ForceDetector
        vision_confidence_threshold: Minimum confidence to prefer vision results

    Returns:
        Combined detection dict with best results from both methods
    """
    combined = {
        "force": None,
        "force_confidence": 0.0,
        "force_indicators": [],
        "force_source": None,
        "unit_type": None,
        "unit_confidence": 0.0,
        "rank": None,
        "rank_confidence": 0.0,
        "shoulder_number": None,
        "shoulder_number_confidence": 0.0,
        "detection_method": "none"
    }

    # Process force detection
    vision_force = None
    vision_force_conf = 0.0

    if vision_result and vision_result.get("success"):
        analysis = vision_result.get("analysis", {})
        force_info = analysis.get("force", {})
        vision_force = force_info.get("name")
        vision_force_conf = force_info.get("confidence", 0.0)

    # Choose best force detection
    if vision_force and vision_force_conf >= vision_confidence_threshold:
        combined["force"] = vision_force
        combined["force_confidence"] = vision_force_conf
        combined["force_indicators"] = vision_result.get("analysis", {}).get("force", {}).get("indicators", [])
        combined["force_source"] = "claude_vision"
        combined["detection_method"] = "vision"
    elif rule_result.force:
        combined["force"] = rule_result.force
        combined["force_confidence"] = rule_result.force_confidence
        combined["force_indicators"] = rule_result.force_indicators
        combined["force_source"] = "rule_based"
        combined["detection_method"] = rule_result.method

    # If both have results but disagree, note it
    if vision_force and rule_result.force and vision_force != rule_result.force:
        combined["force_indicators"].append(
            f"Note: Vision detected '{vision_force}' but badge suggests '{rule_result.force}'"
        )

    # Process unit type (prefer vision if available and confident)
    if vision_result and vision_result.get("success"):
        unit_info = vision_result.get("analysis", {}).get("unit", {})
        unit_type = unit_info.get("type")
        unit_conf = unit_info.get("confidence", 0.0)

        if unit_type and unit_conf >= vision_confidence_threshold:
            combined["unit_type"] = unit_type
            combined["unit_confidence"] = unit_conf
        elif rule_result.unit_type:
            combined["unit_type"] = rule_result.unit_type
            combined["unit_confidence"] = rule_result.unit_confidence
    elif rule_result.unit_type:
        combined["unit_type"] = rule_result.unit_type
        combined["unit_confidence"] = rule_result.unit_confidence

    # Process rank
    if vision_result and vision_result.get("success"):
        rank_info = vision_result.get("analysis", {}).get("rank", {})
        rank = rank_info.get("name")
        rank_conf = rank_info.get("confidence", 0.0)

        if rank and rank_conf >= vision_confidence_threshold:
            combined["rank"] = rank
            combined["rank_confidence"] = rank_conf
        elif rule_result.rank:
            combined["rank"] = rule_result.rank
            combined["rank_confidence"] = rule_result.rank_confidence
    elif rule_result.rank:
        combined["rank"] = rule_result.rank
        combined["rank_confidence"] = rule_result.rank_confidence

    # Shoulder number - prefer rule-based as it's more reliable for OCR
    if rule_result.shoulder_number:
        combined["shoulder_number"] = rule_result.shoulder_number
        combined["shoulder_number_confidence"] = rule_result.shoulder_number_confidence
    elif vision_result and vision_result.get("success"):
        shoulder_info = vision_result.get("analysis", {}).get("shoulder_number", {})
        if shoulder_info.get("text"):
            combined["shoulder_number"] = shoulder_info["text"]
            combined["shoulder_number_confidence"] = shoulder_info.get("confidence", 0.0)

    return combined


# Singleton instance
_detector = None


def get_detector() -> ForceDetector:
    """Get singleton ForceDetector instance."""
    global _detector
    if _detector is None:
        _detector = ForceDetector()
    return _detector


def detect_force(
    badge_text: Optional[str] = None,
    equipment_list: Optional[List[str]] = None,
    uniform_description: Optional[str] = None,
    ocr_texts: Optional[List[str]] = None
) -> ForceDetectionResult:
    """
    Convenience function for force detection.

    Args:
        badge_text: Primary badge/shoulder number
        equipment_list: List of detected equipment
        uniform_description: Description of uniform
        ocr_texts: Additional OCR text from image

    Returns:
        ForceDetectionResult
    """
    return get_detector().analyze(
        badge_text=badge_text,
        equipment_list=equipment_list,
        uniform_description=uniform_description,
        ocr_texts=ocr_texts
    )
