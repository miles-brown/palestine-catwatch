from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

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

    protest = relationship("Protest", back_populates="media")
    appearances = relationship("OfficerAppearance", back_populates="media")

class Officer(Base):
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    badge_number = Column(String, index=True, nullable=True) # OCR findings
    force = Column(String, nullable=True) # e.g. Met Police
    visual_id = Column(String, index=False, nullable=True) # Face encoding hash - DO NOT INDEX (Too large for B-Tree)
    notes = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    appearances = relationship("OfficerAppearance", back_populates="officer")

class OfficerAppearance(Base):
    __tablename__ = "officer_appearances"

    id = Column(Integer, primary_key=True, index=True)
    officer_id = Column(Integer, ForeignKey("officers.id"))
    media_id = Column(Integer, ForeignKey("media.id"))
    
    timestamp_in_video = Column(String, nullable=True) # e.g. "00:12:34"
    image_crop_path = Column(String, nullable=True) # Path to the cropped face/body image
    
    role = Column(String, nullable=True) # e.g. "Medic", "Commander"
    action = Column(Text, nullable=True) # AI described action: "Kettling", "Arresting"
    
    officer = relationship("Officer", back_populates="appearances")
    media = relationship("Media", back_populates="appearances")
