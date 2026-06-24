from .models import AdverseEvent
from .database import SessionLocal
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_adverse_event(data: dict, db: Session):
    event = AdverseEvent(
        patient_id=data["patient_id"],
        severity=data["severity"],
        description=data["description"]
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

def list_adverse_events(db: Session):
    return db.query(AdverseEvent).all()

def get_adverse_event(event_id, db: Session):
    return db.query(AdverseEvent).filter(AdverseEvent.id == event_id).first()

def update_adverse_event(event_id, data: dict, db: Session):
    event = db.query(AdverseEvent).filter(AdverseEvent.id == event_id).first()
    if not event:
        return None
    for key, value in data.items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event

def delete_adverse_event(event_id, db: Session):
    event = db.query(AdverseEvent).filter(AdverseEvent.id == event_id).first()
    if not event:
        return False
    db.delete(event)
    db.commit()
    return True

