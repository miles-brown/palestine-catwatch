from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Media
class ProtestBase(BaseModel):
    name: str
    date: datetime
    location: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    description: Optional[str] = None

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
    class Config:
        from_attributes = True

class Protest(ProtestBase):
    id: int
    media: List[Media] = []
    class Config:
        from_attributes = True

# Update Media to include Protest
class MediaWithProtest(Media):
    protest: Protest

class OfficerAppearanceBase(BaseModel):
    timestamp_in_video: Optional[str] = None
    image_crop_path: Optional[str] = None
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
    class Config:
        from_attributes = True

class Officer(OfficerBase):
    id: int
    appearances: List[OfficerAppearance] = []
    class Config:
        from_attributes = True


# Equipment schemas
class EquipmentBase(BaseModel):
    name: str
    category: str  # "defensive", "offensive", "identification", "restraint", "communication"
    description: Optional[str] = None

class EquipmentCreate(EquipmentBase):
    pass

class Equipment(EquipmentBase):
    id: int
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True


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
    class Config:
        from_attributes = True


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

