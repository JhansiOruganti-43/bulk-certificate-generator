import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.enums import BatchStatus

def get_utc_now():
    return datetime.now(timezone.utc)

class Batch(Base):
    __tablename__ = "batches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    status = Column(Enum(BatchStatus), default=BatchStatus.PENDING, index=True)
    
    total_recipients = Column(Integer, default=0)
    processed_recipients = Column(Integer, default=0)
    successful_certificates = Column(Integer, default=0)
    failed_certificates = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    certificates = relationship("Certificate", back_populates="batch", cascade="all, delete-orphan")
