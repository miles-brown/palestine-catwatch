from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float, LargeBinary
from sqlalchemy.orm import relationship, backref
from datetime import datetime, timezone
from database import Base


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account for authentication and authorization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="viewer", nullable=False)  # viewer, contributor, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
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

    # Account lockout fields (for brute force protection)
    failed_login_attempts = Column(Integer, default=0)  # Count of consecutive failed logins
    locked_until = Column(DateTime, nullable=True)  # Account locked until this time
    last_failed_login = Column(DateTime, nullable=True)  # Time of last failed login

    # Token versioning for revocation
    token_version = Column(Integer, default=0)  # Increment to invalidate all existing tokens

    # Track user actions for audit
    # Note: foreign_keys must reference the column on the other side of the relationship
    uploads = relationship("Media", back_populates="uploaded_by_user", foreign_keys="[Media.uploaded_by]")


class Protest(Base):
    __tablename__ = "protests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    date = Column(DateTime)
    location = Column(String)
    city = Column(String, index=True, nullable=True)
    country = Column(String, index=True, nullable=True, default="United Kingdom")
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Enhanced protest details
    organizer = Column(String, nullable=True)  # e.g., "Palestine Solidarity Campaign"
    estimated_attendance = Column(Integer, nullable=True)
    police_force = Column(String, nullable=True)  # Primary force present
    event_type = Column(String, nullable=True)  # march, rally, vigil, encampment, etc.

    # Status and metadata
    status = Column(String, default="documented")  # documented, under_review, verified
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Cover image for dashboard display
    cover_image_url = Column(String, nullable=True)

    media = relationship("Media", back_populates="protest")

class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)  # URL or local path
    type = Column(String)  # 'image' or 'video'
    protest_id = Column(Integer, ForeignKey("protests.id"))
    timestamp = Column(DateTime, default=utc_now)
    processed = Column(Boolean, default=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Track who uploaded

    # Duplicate detection fields
    content_hash = Column(String(64), index=True, nullable=True)  # SHA256 of file content
    perceptual_hash = Column(String(64), index=True, nullable=True)  # pHash for visual similarity
    file_size = Column(Integer, nullable=True)  # File size in bytes
    is_duplicate = Column(Boolean, default=False)  # Marked as duplicate
    duplicate_of_id = Column(Integer, ForeignKey("media.id"), nullable=True)  # Original media if duplicate

    # Provenance tracking fields - source attribution for scraped media
    source_url = Column(String, nullable=True, index=True)  # Original article URL
    source_name = Column(String(100), nullable=True, index=True)  # Publisher name: "BBC News", "The Guardian"
    caption = Column(Text, nullable=True)  # Photo caption from article
    rights_holder = Column(String(200), nullable=True)  # Copyright holder: "PA Images", "Reuters"
    photographer = Column(String(200), nullable=True)  # Individual photographer credit
    article_headline = Column(String(500), nullable=True)  # Article title for context
    article_summary = Column(Text, nullable=True)  # Brief article summary
    scraped_at = Column(DateTime, nullable=True)  # When the media was scraped

    protest = relationship("Protest", back_populates="media")
    appearances = relationship("OfficerAppearance", back_populates="media")
    uploaded_by_user = relationship("User", back_populates="uploads", foreign_keys=[uploaded_by])
    duplicate_of = relationship("Media", remote_side=[id], foreign_keys=[duplicate_of_id])

class Officer(Base):
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    badge_number = Column(String, index=True, nullable=True)  # OCR findings
    force = Column(String, nullable=True)  # e.g. Met Police
    visual_id = Column(String, index=False, nullable=True)  # Face encoding hash - DO NOT INDEX (Too large for B-Tree)
    notes = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Chain of command - self-referential relationship
    supervisor_id = Column(Integer, ForeignKey("officers.id"), nullable=True)
    rank = Column(String, nullable=True)  # Constable, Sergeant, Inspector, Chief Inspector, etc.

    # Officer name (from uniform label, e.g., "PC WILLIAMS")
    name = Column(String, nullable=True, index=True)  # Final name (override or AI)
    ai_name = Column(String, nullable=True)  # AI-detected name from uniform label
    ai_name_confidence = Column(Float, nullable=True)  # Confidence 0-1

    # Manual overrides (user corrections take precedence over AI)
    name_override = Column(String, nullable=True)  # Manual name correction
    badge_override = Column(String, nullable=True)  # Manual badge correction
    force_override = Column(String, nullable=True)  # Manual force correction
    rank_override = Column(String, nullable=True)  # Manual rank correction

    # Face embedding for re-identification and merge detection
    face_embedding = Column(LargeBinary, nullable=True)  # numpy array as bytes

    # Best photo for display
    primary_crop_path = Column(String, nullable=True)

    # Merge tracking - officers can be merged if they're the same person
    merged_into_id = Column(Integer, ForeignKey("officers.id"), nullable=True)
    merge_confidence = Column(Float, nullable=True)  # Confidence that merge is correct
    merged_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    appearances = relationship("OfficerAppearance", back_populates="officer")

    # Self-referential relationships for chain of command
    supervisor = relationship("Officer", remote_side=[id], backref="subordinates", foreign_keys=[supervisor_id])

    # Self-referential relationship for merges
    merged_into = relationship("Officer", remote_side=[id], backref="merged_from", foreign_keys=[merged_into_id])

    @property
    def effective_name(self):
        """Get the effective name (override takes precedence over AI)."""
        return self.name_override or self.ai_name or self.name

    @property
    def effective_badge(self):
        """Get the effective badge number (override takes precedence)."""
        return self.badge_override or self.badge_number

    @property
    def effective_force(self):
        """Get the effective force (override takes precedence)."""
        return self.force_override or self.force

    @property
    def effective_rank(self):
        """Get the effective rank (override takes precedence)."""
        return self.rank_override or self.rank

    @property
    def is_merged(self):
        """Check if this officer has been merged into another."""
        return self.merged_into_id is not None

class OfficerAppearance(Base):
    __tablename__ = "officer_appearances"

    id = Column(Integer, primary_key=True, index=True)
    officer_id = Column(Integer, ForeignKey("officers.id"), index=True)
    media_id = Column(Integer, ForeignKey("media.id"), index=True)

    timestamp_in_video = Column(String, nullable=True)  # e.g. "00:12:34"
    frame_number = Column(Integer, nullable=True)  # Frame number in video

    # Dual crop paths for officer documentation
    face_crop_path = Column(String, nullable=True)  # Close-up face crop for Officer Card
    body_crop_path = Column(String, nullable=True)  # Full body crop (head to toe) for evidence
    image_crop_path = Column(String, nullable=True)  # Legacy: kept for backwards compatibility

    # Face embedding for this specific appearance (for merge suggestions)
    face_embedding = Column(LargeBinary, nullable=True)  # numpy array as bytes

    role = Column(String, nullable=True)  # e.g. "Medic", "Commander"
    action = Column(Text, nullable=True)  # AI described action: "Kettling", "Arresting"

    # Confidence calibration fields
    confidence = Column(Float, nullable=True, default=None)  # 0-1 confidence score
    confidence_factors = Column(Text, nullable=True)  # JSON string with breakdown: face_quality, ocr_quality, etc.

    # OCR results - badge number
    ocr_badge_result = Column(String, nullable=True)  # OCR-detected badge/shoulder number
    ocr_badge_confidence = Column(Float, nullable=True)  # OCR confidence 0-1

    # OCR results - officer name (from uniform label)
    ocr_name_result = Column(String, nullable=True)  # OCR-detected name (e.g., "PC WILLIAMS")
    ocr_name_confidence = Column(Float, nullable=True)  # OCR confidence 0-1

    # AI detection results (from Claude Vision or other AI)
    ai_force = Column(String, nullable=True)  # AI-detected police force
    ai_force_confidence = Column(Float, nullable=True)
    ai_rank = Column(String, nullable=True)  # AI-detected rank
    ai_rank_confidence = Column(Float, nullable=True)
    ai_name = Column(String, nullable=True)  # AI-detected name from uniform label
    ai_name_confidence = Column(Float, nullable=True)

    # Verification status
    verified = Column(Boolean, default=False)  # Manual verification flag
    verified_at = Column(DateTime(timezone=True), nullable=True)  # When verified
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who verified

    # Manual overrides (user corrections take precedence over AI/OCR)
    badge_override = Column(String, nullable=True)  # Manual badge correction
    name_override = Column(String, nullable=True)  # Manual name correction
    force_override = Column(String, nullable=True)  # Manual force correction
    rank_override = Column(String, nullable=True)  # Manual rank correction
    role_override = Column(String, nullable=True)  # Manual role/unit correction (e.g., "PSU, Evidence Gatherer")
    notes = Column(Text, nullable=True)  # Observer notes about this appearance

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    officer = relationship("Officer", back_populates="appearances")
    media = relationship("Media", back_populates="appearances")
    equipment_detections = relationship("EquipmentDetection", back_populates="appearance", cascade="all, delete-orphan")
    uniform_analysis = relationship("UniformAnalysis", back_populates="appearance", uselist=False, cascade="all, delete-orphan")
    verified_by_user = relationship("User", foreign_keys=[verified_by])

    @property
    def effective_badge(self):
        """Get the effective badge (override > OCR > AI)."""
        return self.badge_override or self.ocr_badge_result

    @property
    def effective_name(self):
        """Get the effective name (override > OCR > AI)."""
        return self.name_override or self.ocr_name_result or self.ai_name

    @property
    def effective_force(self):
        """Get the effective force (override > AI)."""
        return self.force_override or self.ai_force

    @property
    def effective_rank(self):
        """Get the effective rank (override > AI)."""
        return self.rank_override or self.ai_rank

    @property
    def effective_role(self):
        """Get the effective role (override > detected)."""
        return self.role_override or self.role


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
    analyzed_at = Column(DateTime, default=utc_now)
    api_cost_tokens = Column(Integer, nullable=True)  # Track API usage
    image_hash = Column(String, nullable=True, index=True)  # SHA256 for caching

    appearance = relationship("OfficerAppearance", back_populates="uniform_analysis")


class OfficerMerge(Base):
    """
    Tracks merge history for officers.
    Used for audit trail and to enable unmerge functionality.
    """
    __tablename__ = "officer_merges"

    id = Column(Integer, primary_key=True, index=True)

    # The officer that remains after merge (primary)
    primary_officer_id = Column(Integer, ForeignKey("officers.id"), index=True)

    # The officer that was merged into the primary (may be soft-deleted)
    merged_officer_id = Column(Integer, ForeignKey("officers.id"), index=True)

    # Merge metadata
    merge_confidence = Column(Float, nullable=True)  # Embedding similarity score
    auto_merged = Column(Boolean, default=False)  # True if system auto-merged (>95% confidence)
    merged_at = Column(DateTime(timezone=True), default=utc_now)
    merged_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who approved merge

    # For unmerge capability
    unmerged = Column(Boolean, default=False)  # True if this merge was reversed
    unmerged_at = Column(DateTime(timezone=True), nullable=True)
    unmerged_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    primary_officer = relationship("Officer", foreign_keys=[primary_officer_id])
    merged_officer = relationship("Officer", foreign_keys=[merged_officer_id])
    merged_by_user = relationship("User", foreign_keys=[merged_by])
    unmerged_by_user = relationship("User", foreign_keys=[unmerged_by])


class FinalizedReport(Base):
    """
    Stores finalized reports - immutable snapshots created after user verification.
    Once finalized, the report data is frozen and cannot be changed.
    """
    __tablename__ = "finalized_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_uuid = Column(String, unique=True, index=True)  # Public identifier (e.g., "RPT-2024-1214-001")
    media_id = Column(Integer, ForeignKey("media.id"), index=True)

    # Snapshot of data at finalization time (JSON)
    officers_data = Column(Text, nullable=True)  # JSON: Frozen copy of all verified officers
    stats_data = Column(Text, nullable=True)  # JSON: Frozen statistics
    timeline_data = Column(Text, nullable=True)  # JSON: Frozen timeline

    # Report metadata
    title = Column(String, nullable=True)  # Custom report title
    notes = Column(Text, nullable=True)  # User notes about the report

    # Finalization info
    finalized_at = Column(DateTime(timezone=True), default=utc_now)
    finalized_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Export tracking
    pdf_path = Column(String, nullable=True)  # Path to generated PDF
    pdf_generated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    media = relationship("Media")
    finalized_by_user = relationship("User", foreign_keys=[finalized_by])
