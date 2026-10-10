import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Index
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.enums import CertificateStatus

def get_utc_now():
    return datetime.now(timezone.utc)

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=True, index=True)
    
    student_id = Column(String, ForeignKey("students.id"), nullable=True, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=True, index=True)
    enrollment_id = Column(String, ForeignKey("enrollments.id"), nullable=True, index=True)
    
    course_start_date = Column(DateTime(timezone=True), nullable=True)
    course_end_date = Column(DateTime(timezone=True), nullable=True)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    issue_date = Column(DateTime(timezone=True), default=get_utc_now)
    
    recipient_name = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False, index=True)
    course_name = Column(String, nullable=False)
    
    # Meaningful recognizable unique certificate ID (e.g., AEREO-2023-XXXX)
    certificate_id = Column(String, nullable=True, unique=True, index=True)
    
    status = Column(Enum(CertificateStatus), default=CertificateStatus.PENDING, index=True)
    
    pdf_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    batch = relationship("Batch", back_populates="certificates")
    student = relationship("Student", back_populates="certificates")
    course = relationship("Course", back_populates="certificates")
    enrollment = relationship("Enrollment", back_populates="certificates")

    __table_args__ = (
        Index('ix_cert_batch_status', 'batch_id', 'status'),
        Index('ix_cert_student_course', 'student_id', 'course_id'),
    )
