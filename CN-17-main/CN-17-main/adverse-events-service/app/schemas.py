from datetime import datetime

def adverse_event_schema(event):
    return {
        "id": event.id,
        "patient_id": event.patient_id,
        "severity": event.severity,
        "description": event.description,
        "timestamp": event.timestamp.isoformat()
    }
