# app/crud.py

from .models import Notification
from .database import SessionLocal
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_notification(data: dict, db: Session):
    notification = Notification(
        severity=data["severity"],
        description=data["description"]
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

def list_notifications(db: Session):
    return db.query(Notification).all()
