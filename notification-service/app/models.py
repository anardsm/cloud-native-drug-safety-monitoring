# app/models.py

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    severity = Column(String, nullable=False)
    description = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
