import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from app.db.session import Base
from enum import Enum as PyEnum

def get_utc_now():
    return datetime.now(timezone.utc)

class EnrollmentStatus(str, PyEnum):
    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DROPPED = "dropped"

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False, index=True)
    
    status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.ENROLLED, index=True)
    
    enrollment_date = Column(DateTime(timezone=True), default=get_utc_now)
    completion_date = Column(DateTime(timezone=True), nullable=True)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    certificates = relationship("Certificate", back_populates="enrollment")

    __table_args__ = (
        Index('ix_enroll_student_course', 'student_id', 'course_id', unique=True),
    )
