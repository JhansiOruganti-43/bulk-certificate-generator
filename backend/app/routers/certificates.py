import uuid
from datetime import datetime
import os
from app.models.student import Student
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.schemas.certificate import CertificateResponse
from app.services.pdf_generator import generate_pdf, CERTIFICATE_STORAGE_DIR
from app.routers.deps import get_current_student

router = APIRouter(prefix="/certificates", tags=["certificates"])

@router.post("/generate", response_model=CertificateResponse, summary="Generate a certificate for an eligible enrollment")
def generate_certificate(enrollment_id: str, db: Session = Depends(get_db), current_student: "Student" = Depends(get_current_student)):
    # Verify enrollment exists and belongs to student
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")
    if enrollment.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this enrollment")
    if enrollment.status != EnrollmentStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enrollment not completed")
    # Check if certificate already exists for this enrollment
    existing_cert = db.query(Certificate).filter(Certificate.enrollment_id == enrollment.id).first()
    if existing_cert:
        # If PDF file missing, regenerate on the fly
        if not existing_cert.pdf_path or not os.path.isfile(os.path.join(CERTIFICATE_STORAGE_DIR, existing_cert.pdf_path)):
            try:
                pdf_filename = generate_pdf(
                    recipient_name=existing_cert.recipient_name,
                    course_name=existing_cert.course_name,
                    certificate_id=existing_cert.certificate_id,
                    issue_date=existing_cert.issue_date.strftime('%Y-%m-%d'),
                    course_start=existing_cert.course_start_date.strftime('%Y-%m-%d') if existing_cert.course_start_date else None,
                    course_end=existing_cert.course_end_date.strftime('%Y-%m-%d') if existing_cert.course_end_date else None,
                    completion_date=existing_cert.completion_date.strftime('%Y-%m-%d') if existing_cert.completion_date else None,
                )
                existing_cert.pdf_path = pdf_filename
                existing_cert.status = CertificateStatus.COMPLETED
                db.add(existing_cert)
                db.commit()
            except Exception as e:
                existing_cert.status = CertificateStatus.FAILED
                existing_cert.error_message = str(e)
                db.add(existing_cert)
                db.commit()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate certificate PDF")
        return existing_cert
    # Create certificate record
    cert = Certificate(
        student_id=current_student.id,
        course_id=enrollment.course_id,
        enrollment_id=enrollment.id,
        recipient_name=current_student.full_name,
        recipient_email=current_student.email,
        course_name=enrollment.course.course_name,
        course_start_date=enrollment.course.start_date,
        course_end_date=enrollment.course.end_date,
        completion_date=enrollment.completion_date,
        issue_date=datetime.utcnow(),
        status=CertificateStatus.PENDING,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    # Generate unique certificate ID
    cert.certificate_id = f"{cert.course_name[:4].upper()}-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"
    # Generate PDF
    try:
        pdf_filename = generate_pdf(
            recipient_name=cert.recipient_name,
            course_name=cert.course_name,
            certificate_id=cert.certificate_id,
            issue_date=cert.issue_date.strftime('%Y-%m-%d'),
            course_start=cert.course_start_date.strftime('%Y-%m-%d') if cert.course_start_date else None,
            course_end=cert.course_end_date.strftime('%Y-%m-%d') if cert.course_end_date else None,
            completion_date=cert.completion_date.strftime('%Y-%m-%d') if cert.completion_date else None,
        )
        cert.pdf_path = pdf_filename
        cert.status = CertificateStatus.COMPLETED
    except Exception as e:
        cert.status = CertificateStatus.FAILED
        cert.error_message = str(e)
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert

# Existing get and download endpoints remain unchanged
@router.get("/{certificate_id}", response_model=CertificateResponse, summary="Retrieve a specific certificate record")
def get_certificate(certificate_id: str, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return cert

@router.get("/{certificate_id}/download", summary="Download a generated certificate PDF", response_class=FileResponse)
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    # Ensure PDF exists; regenerate if missing
    if not cert.pdf_path or not os.path.isfile(os.path.join(CERTIFICATE_STORAGE_DIR, cert.pdf_path)):
        try:
            pdf_filename = generate_pdf(
                recipient_name=cert.recipient_name,
                course_name=cert.course_name,
                certificate_id=cert.certificate_id,
                issue_date=cert.issue_date.strftime('%Y-%m-%d'),
                course_start=cert.course_start_date.strftime('%Y-%m-%d') if cert.course_start_date else None,
                course_end=cert.course_end_date.strftime('%Y-%m-%d') if cert.course_end_date else None,
                completion_date=cert.completion_date.strftime('%Y-%m-%d') if cert.completion_date else None,
            )
            cert.pdf_path = pdf_filename
            cert.status = CertificateStatus.COMPLETED
            db.add(cert)
            db.commit()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate certificate PDF")
    if cert.status != CertificateStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Certificate PDF is not available. Current status: {cert.status}")
    safe_path = os.path.join(CERTIFICATE_STORAGE_DIR, cert.pdf_path)
    download_name = f"certificate_{cert.certificate_id}.pdf"
    return FileResponse(path=safe_path, media_type="application/pdf", filename=download_name, headers={"Content-Disposition": f'attachment; filename="{download_name}"'})

