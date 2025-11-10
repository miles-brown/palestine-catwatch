from flask import Blueprint, request, jsonify
from src.models.officer import db, Officer, Event, EventOfficer
from datetime import datetime
import json

officer_bp = Blueprint('officer', __name__)

# Officer routes
@officer_bp.route('/officers', methods=['GET'])
def get_officers():
    try:
        officers = Officer.query.all()
        return jsonify([officer.to_dict() for officer in officers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/officers/<int:officer_id>', methods=['GET'])
def get_officer(officer_id):
    try:
        officer = Officer.query.get_or_404(officer_id)
        officer_data = officer.to_dict()
        
        # Add event history
        event_history = []
        for event_officer in officer.event_officers:
            event_data = event_officer.event.to_dict()
            event_data['activity_log'] = event_officer.activity_log
            event_data['source_links'] = event_officer.source_links
            event_history.append(event_data)
        
        officer_data['event_history'] = event_history
        return jsonify(officer_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/officers', methods=['POST'])
def create_officer():
    try:
        data = request.get_json()
        
        # Check if officer with collar number already exists
        existing_officer = Officer.query.filter_by(collar_number=data['collar_number']).first()
        if existing_officer:
            return jsonify({'error': 'Officer with this collar number already exists'}), 400
        
        officer = Officer(
            collar_number=data['collar_number'],
            breed=data['breed'],
            photo_url=data.get('photo_url'),
            description=data.get('description'),
            role=data.get('role'),
            equipment=data.get('equipment')
        )
        
        db.session.add(officer)
        db.session.flush()  # Flush to get the officer ID
        
        # Handle event associations if provided
        event_ids = data.get('event_ids', [])
        if event_ids:
            for event_id in event_ids:
                # Verify the event exists
                event = Event.query.get(event_id)
                if event:
                    event_officer = EventOfficer(
                        officer_id=officer.id,
                        event_id=event_id,
                        activity_log=None,  # Can be updated later
                        source_links=None  # Can be updated later
                    )
                    db.session.add(event_officer)
        
        db.session.commit()
        
        return jsonify(officer.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/officers/<int:officer_id>', methods=['PUT'])
def update_officer(officer_id):
    try:
        officer = Officer.query.get_or_404(officer_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'collar_number' in data:
            officer.collar_number = data['collar_number']
        if 'breed' in data:
            officer.breed = data['breed']
        if 'photo_url' in data:
            officer.photo_url = data['photo_url']
        if 'description' in data:
            officer.description = data['description']
        if 'role' in data:
            officer.role = data['role']
        if 'equipment' in data:
            officer.equipment = data['equipment']
        
        officer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(officer.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/officers/<int:officer_id>', methods=['DELETE'])
def delete_officer(officer_id):
    try:
        officer = Officer.query.get_or_404(officer_id)
        db.session.delete(officer)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Search routes
@officer_bp.route('/search/collar/<collar_number>', methods=['GET'])
def search_by_collar(collar_number):
    try:
        officer = Officer.query.filter_by(collar_number=collar_number).first()
        if not officer:
            return jsonify({'error': 'Officer not found'}), 404
        return jsonify(officer.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/search/breed/<breed>', methods=['GET'])
def search_by_breed(breed):
    try:
        officers = Officer.query.filter(Officer.breed.ilike(f'%{breed}%')).all()
        return jsonify([officer.to_dict() for officer in officers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Event routes
@officer_bp.route('/events', methods=['GET'])
def get_events():
    try:
        events = Event.query.all()
        return jsonify([event.to_dict() for event in events])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        event_data = event.to_dict()
        
        # Add officers present at this event
        officers_present = []
        for event_officer in event.event_officers:
            officer_data = event_officer.officer.to_dict()
            officer_data['activity_log'] = event_officer.activity_log
            officer_data['source_links'] = event_officer.source_links
            officers_present.append(officer_data)
        
        event_data['officers_present'] = officers_present
        return jsonify(event_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/events', methods=['POST'])
def create_event():
    try:
        data = request.get_json()
        
        event = Event(
            name=data['name'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            location=data['location'],
            description=data.get('description')
        )
        
        db.session.add(event)
        db.session.commit()
        
        return jsonify(event.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# EventOfficer routes (linking officers to events)
@officer_bp.route('/event-officers', methods=['POST'])
def create_event_officer():
    try:
        data = request.get_json()
        
        # Check if this officer-event combination already exists
        existing = EventOfficer.query.filter_by(
            officer_id=data['officer_id'],
            event_id=data['event_id']
        ).first()
        
        if existing:
            return jsonify({'error': 'This officer is already linked to this event'}), 400
        
        event_officer = EventOfficer(
            officer_id=data['officer_id'],
            event_id=data['event_id'],
            activity_log=data.get('activity_log'),
            source_links=data.get('source_links')
        )
        
        db.session.add(event_officer)
        db.session.commit()
        
        return jsonify(event_officer.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

