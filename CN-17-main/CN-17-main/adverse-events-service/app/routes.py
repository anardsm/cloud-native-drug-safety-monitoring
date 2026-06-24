from flask import jsonify, request
from .crud import get_db, create_adverse_event, list_adverse_events, get_adverse_event, update_adverse_event, delete_adverse_event
from .schemas import adverse_event_schema

def create():
    db = next(get_db())
    data = request.get_json()
    event = create_adverse_event(data, db)
    return jsonify(adverse_event_schema(event)), 201

def list_all():
    db = next(get_db())
    events = list_adverse_events(db)
    return jsonify([adverse_event_schema(e) for e in events]), 200

def read_one(drug_id):
    db = next(get_db())
    event = get_adverse_event(drug_id, db)
    if event:
        return jsonify(adverse_event_schema(event)), 200
    return jsonify({"message": "Not found"}), 404

def update(drug_id):
    db = next(get_db())
    data = request.get_json()
    event = update_adverse_event(drug_id, data, db)
    if event:
        return jsonify(adverse_event_schema(event)), 200
    return jsonify({"message": "Not found"}), 404

def delete(drug_id):
    db = next(get_db())
    success = delete_adverse_event(drug_id, db)
    if success:
        return '', 204
    return jsonify({"message": "Not found"}), 404

def health():
    return jsonify({"message": "Adverse Events Service is up!"}), 200
