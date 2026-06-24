# app/routes.py

from flask import jsonify, request
from .crud import get_db, create_notification, list_notifications
from .schemas import notification_schema

def create():
    db = next(get_db())
    data = request.get_json()
    notification = create_notification(data, db)
    return jsonify(notification_schema(notification)), 201

def list_all():
    db = next(get_db())
    notifications = list_notifications(db)
    return jsonify([notification_schema(n) for n in notifications]), 200

def health():
    return jsonify({"message": "Notification Service is up!"}), 200
