"""
UK Police Uniform Analyzer using Claude Vision API.

Analyzes images of police officers to identify:
- Police force (Met, City of London, British Transport, etc.)
- Unit type (TSG, FIT, Level 2 PSU, Standard)
- Rank (Constable, Sergeant, Inspector, etc.)
- Equipment (shields, batons, tasers, etc.)
- Shoulder number (identification)

Integrates with rule-based force detection for fallback/combined detection.
"""
import os
import json
import base64
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

import anthropic

from .analysis_cache import AnalysisCache
from .force_detector import detect_force, combine_detections, ForceDetectionResult


# UK Police Force identifiers
UK_FORCES = [
    "Metropolitan Police Service",
    "City of London Police",
    "British Transport Police",
    "Greater Manchester Police",
    "West Midlands Police",
    "West Yorkshire Police",
    "Merseyside Police",
    "South Yorkshire Police",
    "Thames Valley Police",
    "Hampshire Constabulary",
    "Kent Police",
    "Essex Police",
    "Sussex Police",
    "Surrey Police",
    "Avon and Somerset Police",
    "Devon and Cornwall Police",
    "Dorset Police",
    "Wiltshire Police",
    "Ministry of Defence Police",
    "Civil Nuclear Constabulary",
]

# Specialist unit types
UNIT_TYPES = [
    "TSG (Territorial Support Group)",
    "FIT (Forward Intelligence Team)",
    "Level 1 PSU (Public Order)",
    "Level 2 PSU (Public Order)",
    "SCO19 (Specialist Firearms)",
    "Dog Unit (K9)",
    "Mounted Branch",
    "Roads Policing Unit",
    "Evidence Gatherer",
    "Police Liaison Team",
    "Standard (Neighbourhood/Response)",
]

# Rank structure
RANKS = [
    "Police Constable (PC)",
    "Sergeant (Sgt) - 3 chevrons",
    "Inspector (Insp) - 2 pips",
    "Chief Inspector (CI) - 3 pips",
    "Superintendent (Supt) - Crown",
    "Chief Superintendent (Ch Supt) - Crown with pip",
    "PCSO (Police Community Support Officer)",
]


ANALYSIS_PROMPT = """You are an expert in UK police uniforms, equipment, and organizational structure. Analyze this image of a police officer and provide detailed identification information.

Look for the following visual indicators:

**FORCE IDENTIFICATION:**
- Badge/crest design and text
- Checkered band pattern (Sillitoe tartan) colors
- "POLICE" text styling and placement
- Shoulder flash or arm badge

**UNIT TYPE:**
- TSG: Dark operational clothing, NATO helmets, shields, evidence gatherer vests
- FIT: Blue tabards, cameras, evidence gathering equipment
- PSU: Riot gear, shields, protective equipment
- Standard: Hi-vis jackets, standard uniform

**RANK INDICATORS:**
- Chevrons on epaulettes (Sergeant = 3 chevrons)
- Pips on epaulettes (Inspector = 2 pips, Chief Inspector = 3 pips)
- Crown (Superintendent and above)
- PCSO badge differences

**EQUIPMENT:**
List ALL visible equipment including:
- Protective: Helmets (type), shields (round/long), body armor, arm/leg guards
- Weapons: Batons (standard/extendable), Taser, CS spray
- Restraints: Handcuffs, zip ties
- Communication: Radio, earpiece
- Identification: Body camera, shoulder numbers

**SHOULDER NUMBER:**
Look for alphanumeric codes on epaulettes (e.g., "U1234", "AB123")

Respond with ONLY a valid JSON object in this exact format:
{
  "force": {
    "name": "Force name or null if unknown",
    "confidence": 0.0-1.0,
    "indicators": ["list", "of", "visual", "clues"]
  },
  "unit": {
    "type": "Unit type or Standard",
    "confidence": 0.0-1.0,
    "indicators": ["list", "of", "visual", "clues"]
  },
  "rank": {
    "name": "Rank name or null",
    "confidence": 0.0-1.0,
    "indicators": {"chevrons": 0, "pips": 0, "crown": false, "other": "notes"}
  },
  "uniform_type": {
    "type": "hi_vis|dark_operational|riot_gear|ceremonial|standard",
    "description": "Brief description"
  },
  "equipment": [
    {"name": "Equipment name", "confidence": 0.0-1.0, "category": "defensive|offensive|restraint|identification|communication|specialist"}
  ],
  "shoulder_number": {
    "text": "Number or null",
    "confidence": 0.0-1.0
  },
  "overall_notes": "Any additional observations about the officer or image quality"
}

Be conservative with confidence scores. Only report what you can clearly see. If an element is not visible or unclear, use null or low confidence values."""


class UniformAnalyzer:
    """
    Analyzes police officer images using Claude Vision API.

    Features:
    - Rate limiting to avoid API throttling
    - Caching to prevent duplicate analysis
    - Structured JSON output for database storage
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit: int = 10,  # requests per minute
        cache_dir: Optional[str] = None
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.rate_limit = rate_limit
        self._semaphore = asyncio.Semaphore(rate_limit)
        self._last_requests: List[datetime] = []

        # Initialize cache
        cache_path = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "analysis_cache"
        )
        self.cache = AnalysisCache(cache_path)

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """Encode image to base64 and determine media type."""
        path = Path(image_path)
        suffix = path.suffix.lower()

        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }

        media_type = media_type_map.get(suffix, "image/jpeg")

        with open(image_path, "rb") as f:
            data = f.read()

        return base64.standard_b64encode(data).decode("utf-8"), media_type

    def _compute_image_hash(self, image_path: str) -> str:
        """Compute SHA256 hash of image file for caching."""
        with open(image_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    async def _rate_limit(self):
        """Simple rate limiting using semaphore."""
        async with self._semaphore:
            now = datetime.now()
            # Clean old requests
            self._last_requests = [
                t for t in self._last_requests
                if (now - t).total_seconds() < 60
            ]

            # Wait if at limit
            if len(self._last_requests) >= self.rate_limit:
                oldest = min(self._last_requests)
                wait_time = 60 - (now - oldest).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self._last_requests.append(now)

    def analyze_uniform_sync(
        self,
        image_path: str,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for analyze_uniform.
        """
        return asyncio.run(self.analyze_uniform(image_path, force_reanalyze))

    async def analyze_uniform(
        self,
        image_path: str,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze a police officer image using Claude Vision.

        Args:
            image_path: Path to the officer image
            force_reanalyze: Skip cache and re-analyze

        Returns:
            Dict with analysis results and metadata
        """
        # Compute image hash for caching
        image_hash = self._compute_image_hash(image_path)

        # Check cache first
        if not force_reanalyze:
            cached = self.cache.get(image_hash)
            if cached:
                return {
                    "success": True,
                    "cached": True,
                    "analysis": cached,
                    "image_hash": image_hash,
                    "tokens_used": 0
                }

        # Rate limit
        await self._rate_limit()

        try:
            # Encode image
            image_data, media_type = self._encode_image(image_path)

            # Call Claude Vision API
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": ANALYSIS_PROMPT
                            }
                        ]
                    }
                ]
            )

            # Extract response text
            response_text = response.content[0].text

            # Parse JSON from response
            try:
                # Try to find JSON in the response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    analysis = {"error": "No JSON found in response", "raw": response_text}
            except json.JSONDecodeError as e:
                analysis = {"error": f"JSON parse error: {e}", "raw": response_text}

            # Calculate token usage
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Cache the result
            self.cache.set(image_hash, analysis)

            return {
                "success": True,
                "cached": False,
                "analysis": analysis,
                "image_hash": image_hash,
                "tokens_used": tokens_used,
                "raw_response": response_text
            }

        except anthropic.APIError as e:
            return {
                "success": False,
                "cached": False,
                "error": f"API error: {str(e)}",
                "image_hash": image_hash,
                "tokens_used": 0
            }
        except Exception as e:
            return {
                "success": False,
                "cached": False,
                "error": f"Analysis failed: {str(e)}",
                "image_hash": image_hash,
                "tokens_used": 0
            }

    def parse_to_db_format(
        self,
        analysis_result: Dict[str, Any],
        appearance_id: int
    ) -> Dict[str, Any]:
        """
        Parse Claude analysis result into database-ready format.

        Args:
            analysis_result: Result from analyze_uniform
            appearance_id: ID of the OfficerAppearance record

        Returns:
            Dict ready for UniformAnalysis creation
        """
        if not analysis_result.get("success"):
            return None

        analysis = analysis_result.get("analysis", {})

        # Extract force info
        force_info = analysis.get("force", {})
        unit_info = analysis.get("unit", {})
        rank_info = analysis.get("rank", {})
        shoulder_info = analysis.get("shoulder_number", {})
        uniform_info = analysis.get("uniform_type", {})

        return {
            "appearance_id": appearance_id,
            "detected_force": force_info.get("name"),
            "force_confidence": force_info.get("confidence"),
            "force_indicators": json.dumps(force_info.get("indicators", [])),
            "unit_type": unit_info.get("type"),
            "unit_confidence": unit_info.get("confidence"),
            "detected_rank": rank_info.get("name"),
            "rank_confidence": rank_info.get("confidence"),
            "rank_indicators": json.dumps(rank_info.get("indicators", {})),
            "shoulder_number": shoulder_info.get("text"),
            "shoulder_number_confidence": shoulder_info.get("confidence"),
            "uniform_type": uniform_info.get("type"),
            "raw_analysis": json.dumps(analysis),
            "api_cost_tokens": analysis_result.get("tokens_used", 0),
            "image_hash": analysis_result.get("image_hash"),
            "analyzed_at": datetime.now(timezone.utc)
        }

    def extract_equipment(
        self,
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract equipment detections from analysis result.

        Returns list of equipment items with name, confidence, and category.
        """
        if not analysis_result.get("success"):
            return []

        analysis = analysis_result.get("analysis", {})
        equipment_list = analysis.get("equipment", [])

        return [
            {
                "name": item.get("name"),
                "confidence": item.get("confidence"),
                "category": item.get("category")
            }
            for item in equipment_list
            if item.get("name")
        ]

    def analyze_with_fallback(
        self,
        image_path: str,
        badge_text: Optional[str] = None,
        ocr_texts: Optional[List[str]] = None,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze uniform with combined Claude Vision + rule-based detection.

        This method:
        1. Attempts Claude Vision analysis if API key is available
        2. Runs rule-based detection using badge/OCR data
        3. Combines results, preferring high-confidence Vision results

        Args:
            image_path: Path to officer image
            badge_text: Detected badge/shoulder number from OCR
            ocr_texts: Additional OCR texts found in image
            force_reanalyze: Skip cache and re-analyze

        Returns:
            Combined detection result with best available data
        """
        # Try Claude Vision first
        vision_result = None
        try:
            vision_result = self.analyze_uniform_sync(image_path, force_reanalyze)
        except Exception as e:
            print(f"Vision analysis failed: {e}")

        # Run rule-based detection
        equipment_list = []
        uniform_desc = None

        if vision_result and vision_result.get("success"):
            # Extract equipment names for rule-based analysis
            analysis = vision_result.get("analysis", {})
            equipment_list = [
                eq.get("name", "")
                for eq in analysis.get("equipment", [])
            ]
            uniform_info = analysis.get("uniform_type", {})
            uniform_desc = uniform_info.get("description", "")

        rule_result = detect_force(
            badge_text=badge_text,
            equipment_list=equipment_list,
            uniform_description=uniform_desc,
            ocr_texts=ocr_texts
        )

        # Combine results
        combined = combine_detections(vision_result, rule_result)

        # Add metadata
        combined["vision_success"] = vision_result.get("success", False) if vision_result else False
        combined["vision_cached"] = vision_result.get("cached", False) if vision_result else False
        combined["tokens_used"] = vision_result.get("tokens_used", 0) if vision_result else 0
        combined["rule_method"] = rule_result.method

        # Keep equipment list from vision
        if vision_result and vision_result.get("success"):
            combined["equipment"] = self.extract_equipment(vision_result)
        else:
            combined["equipment"] = []

        return combined


def analyze_officer_combined(
    image_path: str,
    badge_text: Optional[str] = None,
    ocr_texts: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    rate_limit: int = 10
) -> Dict[str, Any]:
    """
    Convenience function for combined uniform analysis.

    Uses Claude Vision when available, with rule-based fallback.

    Args:
        image_path: Path to officer image
        badge_text: Detected badge number
        ocr_texts: Additional OCR texts
        api_key: Anthropic API key (optional, uses env var)
        rate_limit: API rate limit per minute

    Returns:
        Combined analysis result
    """
    # Check if we have API key
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    if key:
        try:
            analyzer = UniformAnalyzer(api_key=key, rate_limit=rate_limit)
            return analyzer.analyze_with_fallback(
                image_path=image_path,
                badge_text=badge_text,
                ocr_texts=ocr_texts
            )
        except Exception as e:
            print(f"Combined analysis failed: {e}")

    # Fallback to pure rule-based detection
    rule_result = detect_force(
        badge_text=badge_text,
        ocr_texts=ocr_texts
    )

    return {
        "force": rule_result.force,
        "force_confidence": rule_result.force_confidence,
        "force_indicators": rule_result.force_indicators,
        "force_source": "rule_based",
        "unit_type": rule_result.unit_type,
        "unit_confidence": rule_result.unit_confidence,
        "rank": rule_result.rank,
        "rank_confidence": rule_result.rank_confidence,
        "shoulder_number": rule_result.shoulder_number,
        "shoulder_number_confidence": rule_result.shoulder_number_confidence,
        "detection_method": rule_result.method,
        "vision_success": False,
        "vision_cached": False,
        "tokens_used": 0,
        "equipment": []
    }
