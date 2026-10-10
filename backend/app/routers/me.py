from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus
from app.schemas.student import StudentRead
from app.schemas.certificate import CertificateResponse
from app.routers.deps import get_current_student

router = APIRouter(prefix="/me", tags=["me"])

@router.get("/", response_model=StudentRead, summary="Get current authenticated student profile")
def get_profile(current_student: Student = Depends(get_current_student)):
    return current_student

@router.get("/enrollments", response_model=List[dict], summary="List student's enrollments")
def list_enrollments(db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == current_student.id).all()
    return [
        {
            "id": e.id,
            "course_id": e.course_id,
            "status": e.status.value,
            "enrollment_date": e.enrollment_date,
            "completion_date": e.completion_date,
        }
        for e in enrollments
    ]

@router.get("/certificates", response_model=List[CertificateResponse], summary="List student's certificates")
def list_certificates(db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    certs = db.query(Certificate).filter(Certificate.student_id == current_student.id).all()
    return certs
