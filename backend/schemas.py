from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# Protest schemas
class ProtestBase(BaseModel):
    name: str
    date: datetime
    location: str
    city: Optional[str] = None
    country: Optional[str] = "United Kingdom"
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    description: Optional[str] = None
    organizer: Optional[str] = None
    estimated_attendance: Optional[int] = None
    police_force: Optional[str] = None
    event_type: Optional[str] = None  # march, rally, vigil, encampment
    cover_image_url: Optional[str] = None


class ProtestCreate(ProtestBase):
    pass


class ProtestUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    description: Optional[str] = None
    organizer: Optional[str] = None
    estimated_attendance: Optional[int] = None
    police_force: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    cover_image_url: Optional[str] = None

class MediaBase(BaseModel):
    url: str
    type: str

class MediaCreate(MediaBase):
    protest_id: int

# Forward references
class Media(MediaBase):
    id: int
    processed: bool
    timestamp: datetime
    # protest will be loaded if needed, handle circular refs or separate schemas
    model_config = ConfigDict(from_attributes=True)

class Protest(ProtestBase):
    id: int
    status: Optional[str] = "documented"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    media: List[Media] = []
    model_config = ConfigDict(from_attributes=True)


class ProtestWithStats(Protest):
    """Protest with computed statistics for dashboard display."""
    media_count: int = 0
    officer_count: int = 0
    verified_count: int = 0

# Update Media to include Protest
class MediaWithProtest(Media):
    protest: Protest

class OfficerAppearanceBase(BaseModel):
    """
    Base schema for officer appearance data.

    Crop Path Priority: When displaying officer images, use this fallback order:
        1. face_crop_path - Close-up face (preferred for officer cards)
        2. body_crop_path - Full body shot (good for uniform/equipment evidence)
        3. image_crop_path - Legacy field (backwards compatibility only)

    Example:
        crop_url = appearance.face_crop_path or appearance.body_crop_path or appearance.image_crop_path
    """
    timestamp_in_video: Optional[str] = None
    face_crop_path: Optional[str] = None  # Close-up face crop for Officer Card
    body_crop_path: Optional[str] = None  # Full body crop (head to toe) for evidence
    image_crop_path: Optional[str] = None  # Legacy: kept for backwards compatibility
    role: Optional[str] = None
    action: Optional[str] = None
    confidence: Optional[float] = None
    confidence_factors: Optional[str] = None
    verified: bool = False

class OfficerBase(BaseModel):
    badge_number: Optional[str] = None
    force: Optional[str] = None
    visual_id: Optional[str] = None
    notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class OfficerAppearance(OfficerAppearanceBase):
    id: int
    officer_id: int
    media_id: int
    media: Optional[Media] = None # Use Media, not MediaWithProtest to avoid deep circular recursion unless needed
    model_config = ConfigDict(from_attributes=True)

class Officer(OfficerBase):
    id: int
    appearances: List[OfficerAppearance] = []
    model_config = ConfigDict(from_attributes=True)


# Equipment schemas
class EquipmentBase(BaseModel):
    name: str
    category: str  # "defensive", "offensive", "identification", "restraint", "communication"
    description: Optional[str] = None

class EquipmentCreate(EquipmentBase):
    pass

class Equipment(EquipmentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class EquipmentWithCount(Equipment):
    detection_count: int = 0


# Equipment Detection schemas
class EquipmentDetectionBase(BaseModel):
    equipment_id: int
    confidence: Optional[float] = None
    bounding_box: Optional[str] = None  # JSON string

class EquipmentDetectionCreate(EquipmentDetectionBase):
    appearance_id: int

class EquipmentDetection(EquipmentDetectionBase):
    id: int
    appearance_id: int
    equipment: Optional[Equipment] = None
    model_config = ConfigDict(from_attributes=True)


# Uniform Analysis schemas
class UniformAnalysisBase(BaseModel):
    detected_force: Optional[str] = None
    force_confidence: Optional[float] = None
    force_indicators: Optional[str] = None
    unit_type: Optional[str] = None
    unit_confidence: Optional[float] = None
    detected_rank: Optional[str] = None
    rank_confidence: Optional[float] = None
    rank_indicators: Optional[str] = None
    shoulder_number: Optional[str] = None
    shoulder_number_confidence: Optional[float] = None
    uniform_type: Optional[str] = None

class UniformAnalysisCreate(UniformAnalysisBase):
    appearance_id: int
    raw_analysis: Optional[str] = None
    api_cost_tokens: Optional[int] = None
    image_hash: Optional[str] = None

class UniformAnalysis(UniformAnalysisBase):
    id: int
    appearance_id: int
    raw_analysis: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    api_cost_tokens: Optional[int] = None
    image_hash: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# Extended appearance with uniform analysis
class OfficerAppearanceWithUniform(OfficerAppearance):
    uniform_analysis: Optional[UniformAnalysis] = None
    equipment_detections: List[EquipmentDetection] = []


# Request/Response schemas for API
class AnalyzeUniformRequest(BaseModel):
    force_reanalyze: bool = False  # Re-analyze even if cached

class AnalyzeUniformResponse(BaseModel):
    success: bool
    analysis: Optional[UniformAnalysis] = None
    cached: bool = False
    error: Optional[str] = None

class ForceStatsResponse(BaseModel):
    force: str
    count: int
    avg_confidence: float

class AppearanceVerifyRequest(BaseModel):
    verified: bool
    confidence: Optional[float] = None


# ============================================
# Officer Merge/Unmerge Schemas
# ============================================

class MergeRequest(BaseModel):
    """Request to merge multiple officers into one."""
    officer_ids: List[int]  # List of officer IDs to merge (first becomes primary)
    confidence: float = 0.0  # Merge confidence score
    auto_merged: bool = False  # True if auto-merged by system


class UnmergeRequest(BaseModel):
    """Request to unmerge specific appearances back to a new officer."""
    appearance_ids: List[int]  # Appearance IDs to split into new officer


class MergeSuggestion(BaseModel):
    """A suggested merge between two officers based on face embedding similarity."""
    officer_a_id: int
    officer_b_id: int
    appearance_a_id: int
    appearance_b_id: int
    confidence: float  # Embedding similarity 0-1
    auto_merge: bool  # True if confidence >= 0.95
    crop_a: Optional[str] = None  # Path to officer A's crop
    crop_b: Optional[str] = None  # Path to officer B's crop


class MergeSuggestionsResponse(BaseModel):
    """Response containing merge suggestions for a media item."""
    suggestions: List[MergeSuggestion]


class MergeResponse(BaseModel):
    """Response after merging officers."""
    primary_officer_id: int
    merged_count: int
    total_appearances: int


class UnmergeResponse(BaseModel):
    """Response after unmerging an officer."""
    new_officer_id: int
    appearances_moved: int
    original_officer_id: int


# ============================================
# Officer Update/Verification Schemas
# ============================================

class OfficerUpdate(BaseModel):
    """Update for a single officer appearance during verification."""
    appearance_id: int
    verified: bool = False
    badge_override: Optional[str] = None
    name_override: Optional[str] = None
    force_override: Optional[str] = None
    rank_override: Optional[str] = None
    role_override: Optional[str] = None
    notes: Optional[str] = None


class BatchOfficerUpdateRequest(BaseModel):
    """Request to update multiple officers at once."""
    updates: List[OfficerUpdate]


class BatchOfficerUpdateResponse(BaseModel):
    """Response after batch updating officers."""
    updated: int


# ============================================
# Extended Officer Schemas with New Fields
# ============================================

class OfficerAppearanceDetailed(BaseModel):
    """Detailed officer appearance with all detection and override fields."""
    id: int
    officer_id: int
    media_id: int
    timestamp_in_video: Optional[str] = None
    frame_number: Optional[int] = None

    # Crop paths
    face_crop_path: Optional[str] = None
    body_crop_path: Optional[str] = None
    image_crop_path: Optional[str] = None

    # Detection confidence
    confidence: Optional[float] = None

    # OCR results
    ocr_badge_result: Optional[str] = None
    ocr_badge_confidence: Optional[float] = None
    ocr_name_result: Optional[str] = None
    ocr_name_confidence: Optional[float] = None

    # AI detection results
    ai_force: Optional[str] = None
    ai_force_confidence: Optional[float] = None
    ai_rank: Optional[str] = None
    ai_rank_confidence: Optional[float] = None
    ai_name: Optional[str] = None
    ai_name_confidence: Optional[float] = None

    # Verification
    verified: bool = False
    verified_at: Optional[datetime] = None

    # Manual overrides
    badge_override: Optional[str] = None
    name_override: Optional[str] = None
    force_override: Optional[str] = None
    rank_override: Optional[str] = None
    role_override: Optional[str] = None
    notes: Optional[str] = None

    # Computed effective values
    effective_badge: Optional[str] = None
    effective_name: Optional[str] = None
    effective_force: Optional[str] = None
    effective_rank: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OfficerDetailed(BaseModel):
    """Detailed officer with all fields including merge status."""
    id: int
    badge_number: Optional[str] = None
    force: Optional[str] = None
    rank: Optional[str] = None
    notes: Optional[str] = None

    # Name fields
    name: Optional[str] = None
    ai_name: Optional[str] = None
    ai_name_confidence: Optional[float] = None

    # Manual overrides
    name_override: Optional[str] = None
    badge_override: Optional[str] = None
    force_override: Optional[str] = None
    rank_override: Optional[str] = None

    # Best photo
    primary_crop_path: Optional[str] = None

    # Merge status
    merged_into_id: Optional[int] = None
    is_merged: bool = False
    merge_confidence: Optional[float] = None

    # Computed effective values
    effective_name: Optional[str] = None
    effective_badge: Optional[str] = None
    effective_force: Optional[str] = None
    effective_rank: Optional[str] = None

    # Related data
    appearances: List[OfficerAppearanceDetailed] = []
    total_appearances: int = 0

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Report Finalization Schemas
# ============================================

class FinalizeReportRequest(BaseModel):
    """Request to finalize a report."""
    title: Optional[str] = None
    notes: Optional[str] = None
    generate_pdf: bool = False


class FinalizeReportResponse(BaseModel):
    """Response after finalizing a report."""
    report_id: int
    report_uuid: str
    pdf_url: Optional[str] = None


class FinalizedReportSummary(BaseModel):
    """Summary of a finalized report."""
    id: int
    report_uuid: str
    media_id: int
    title: Optional[str] = None
    finalized_at: datetime
    pdf_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

