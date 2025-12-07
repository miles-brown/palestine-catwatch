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
    # protext will be loaded if needed, handle circular refs or separate schemas
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

