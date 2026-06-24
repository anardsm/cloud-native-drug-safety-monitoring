from sqlalchemy import Column, Integer, String, DateTime
from .database import Base
from datetime import datetime

class AdverseEvent(Base):
    __tablename__ = "adverse_events"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    description = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
