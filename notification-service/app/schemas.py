# app/schemas.py

from datetime import datetime

def notification_schema(notification):
    return {
        "id": notification.id,
        "severity": notification.severity,
        "description": notification.description,
        "timestamp": notification.timestamp.isoformat()
    }
