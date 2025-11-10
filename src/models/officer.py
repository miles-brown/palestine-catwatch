from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Officer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collar_number = db.Column(db.String(50), unique=True, nullable=False)
    breed = db.Column(db.String(100), nullable=False)  # Police force/constabulary
    photo_url = db.Column(db.String(255))
    description = db.Column(db.Text)
    role = db.Column(db.String(100))  # e.g., Liaison Officer, TSG
    equipment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to events through EventOfficer
    event_officers = db.relationship('EventOfficer', back_populates='officer', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Officer {self.collar_number} - {self.breed}>'

    def to_dict(self):
        return {
            'id': self.id,
            'collar_number': self.collar_number,
            'breed': self.breed,
            'photo_url': self.photo_url,
            'description': self.description,
            'role': self.role,
            'equipment': self.equipment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to officers through EventOfficer
    event_officers = db.relationship('EventOfficer', back_populates='event', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Event {self.name} - {self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'date': self.date.isoformat() if self.date else None,
            'location': self.location,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class EventOfficer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('officer.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    activity_log = db.Column(db.Text)  # What the officer was documented doing
    source_links = db.Column(db.Text)  # JSON string of source links
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    officer = db.relationship('Officer', back_populates='event_officers')
    event = db.relationship('Event', back_populates='event_officers')
    
    # Ensure unique officer-event combinations
    __table_args__ = (db.UniqueConstraint('officer_id', 'event_id', name='unique_officer_event'),)

    def __repr__(self):
        return f'<EventOfficer Officer:{self.officer_id} Event:{self.event_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'officer_id': self.officer_id,
            'event_id': self.event_id,
            'activity_log': self.activity_log,
            'source_links': self.source_links,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'officer': self.officer.to_dict() if self.officer else None,
            'event': self.event.to_dict() if self.event else None
        }

