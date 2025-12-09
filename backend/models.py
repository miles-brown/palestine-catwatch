from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    """User account for authentication and authorization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="viewer", nullable=False)  # viewer, contributor, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Extended profile fields
    full_name = Column(String(255), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    # Consent and verification
    consent_given = Column(Boolean, default=False)  # User consented to T&Cs
    consent_date = Column(DateTime, nullable=True)  # When consent was given
    email_verified = Column(Boolean, default=False)  # Email has been verified
    email_verification_token = Column(String(255), nullable=True)  # Token for email verification
    email_verification_sent_at = Column(DateTime, nullable=True)  # When verification email was sent

    # Track user actions for audit
    uploads = relationship("Media", back_populates="uploaded_by_user", foreign_keys="Media.uploaded_by")

class Protest(Base):
    __tablename__ = "protests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    date = Column(DateTime)
    location = Column(String)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    media = relationship("Media", back_populates="protest")

class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)  # URL or local path
    type = Column(String)  # 'image' or 'video'
    protest_id = Column(Integer, ForeignKey("protests.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Track who uploaded

    # Duplicate detection fields
    content_hash = Column(String(64), index=True, nullable=True)  # SHA256 of file content
    perceptual_hash = Column(String(64), index=True, nullable=True)  # pHash for visual similarity
    file_size = Column(Integer, nullable=True)  # File size in bytes
    is_duplicate = Column(Boolean, default=False)  # Marked as duplicate
    duplicate_of_id = Column(Integer, ForeignKey("media.id"), nullable=True)  # Original media if duplicate

    protest = relationship("Protest", back_populates="media")
    appearances = relationship("OfficerAppearance", back_populates="media")
    uploaded_by_user = relationship("User", back_populates="uploads", foreign_keys=[uploaded_by])
    duplicate_of = relationship("Media", remote_side=[id], foreign_keys=[duplicate_of_id])

class Officer(Base):
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    badge_number = Column(String, index=True, nullable=True) # OCR findings
    force = Column(String, nullable=True) # e.g. Met Police
    visual_id = Column(String, index=False, nullable=True) # Face encoding hash - DO NOT INDEX (Too large for B-Tree)
    notes = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Chain of command - self-referential relationship
    supervisor_id = Column(Integer, ForeignKey("officers.id"), nullable=True)
    rank = Column(String, nullable=True)  # Constable, Sergeant, Inspector, Chief Inspector, etc.

    appearances = relationship("OfficerAppearance", back_populates="officer")

    # Self-referential relationships for chain of command
    supervisor = relationship("Officer", remote_side=[id], backref="subordinates", foreign_keys=[supervisor_id])

class OfficerAppearance(Base):
    __tablename__ = "officer_appearances"

    id = Column(Integer, primary_key=True, index=True)
    officer_id = Column(Integer, ForeignKey("officers.id"))
    media_id = Column(Integer, ForeignKey("media.id"))

    timestamp_in_video = Column(String, nullable=True) # e.g. "00:12:34"
    image_crop_path = Column(String, nullable=True) # Path to the cropped face/body image

    role = Column(String, nullable=True) # e.g. "Medic", "Commander"
    action = Column(Text, nullable=True) # AI described action: "Kettling", "Arresting"

    # Confidence calibration fields
    confidence = Column(Float, nullable=True, default=None)  # 0-100 confidence score
    confidence_factors = Column(Text, nullable=True)  # JSON string with breakdown: face_quality, ocr_quality, etc.
    verified = Column(Boolean, default=False)  # Manual verification flag

    officer = relationship("Officer", back_populates="appearances")
    media = relationship("Media", back_populates="appearances")
    equipment_detections = relationship("EquipmentDetection", back_populates="appearance", cascade="all, delete-orphan")
    uniform_analysis = relationship("UniformAnalysis", back_populates="appearance", uselist=False, cascade="all, delete-orphan")


class Equipment(Base):
    """Reference table for police equipment types"""
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)  # "Long Shield", "NATO Helmet"
    category = Column(String, index=True)  # "defensive", "offensive", "identification", "restraint", "communication"
    description = Column(Text, nullable=True)

    detections = relationship("EquipmentDetection", back_populates="equipment")


class EquipmentDetection(Base):
    """Junction table linking detected equipment to officer appearances"""
    __tablename__ = "equipment_detections"

    id = Column(Integer, primary_key=True, index=True)
    appearance_id = Column(Integer, ForeignKey("officer_appearances.id"), index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), index=True)
    confidence = Column(Float, nullable=True)  # 0-1 confidence score
    bounding_box = Column(String, nullable=True)  # JSON: {"x": 0, "y": 0, "width": 100, "height": 100}

    appearance = relationship("OfficerAppearance", back_populates="equipment_detections")
    equipment = relationship("Equipment", back_populates="detections")


class UniformAnalysis(Base):
    """Stores Claude Vision analysis results for officer uniforms"""
    __tablename__ = "uniform_analyses"

    id = Column(Integer, primary_key=True, index=True)
    appearance_id = Column(Integer, ForeignKey("officer_appearances.id"), unique=True, index=True)

    # Force detection
    detected_force = Column(String, nullable=True)  # "Metropolitan Police Service", "City of London Police"
    force_confidence = Column(Float, nullable=True)
    force_indicators = Column(Text, nullable=True)  # JSON array of indicators

    # Unit type detection
    unit_type = Column(String, nullable=True)  # "TSG", "FIT", "Level 2 PSU", "Standard"
    unit_confidence = Column(Float, nullable=True)

    # Rank detection
    detected_rank = Column(String, nullable=True)  # "Constable", "Sergeant", "Inspector"
    rank_confidence = Column(Float, nullable=True)
    rank_indicators = Column(Text, nullable=True)  # JSON: {"chevrons": 3, "pips": 0}

    # Shoulder number
    shoulder_number = Column(String, nullable=True)  # e.g., "U1234"
    shoulder_number_confidence = Column(Float, nullable=True)

    # Uniform classification
    uniform_type = Column(String, nullable=True)  # "hi_vis", "dark_operational", "riot_gear", "ceremonial"

    # Analysis metadata
    raw_analysis = Column(Text, nullable=True)  # Full Claude JSON response
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    api_cost_tokens = Column(Integer, nullable=True)  # Track API usage
    image_hash = Column(String, nullable=True, index=True)  # SHA256 for caching

    appearance = relationship("OfficerAppearance", back_populates="uniform_analysis")
