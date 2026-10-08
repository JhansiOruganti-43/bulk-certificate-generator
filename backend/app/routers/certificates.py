import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus
from app.schemas.certificate import CertificateResponse
from app.services.pdf_generator import CERTIFICATE_STORAGE_DIR

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get(
    "/{certificate_id}",
    response_model=CertificateResponse,
    summary="Retrieve a specific certificate record"
)
def get_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the details and generation status of a specific individual certificate.
    """
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return cert


@router.get(
    "/{certificate_id}/download",
    summary="Download a generated certificate PDF",
    response_class=FileResponse
)
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Download the generated PDF for a completed certificate.
    Returns 404 if the certificate doesn't exist.
    Returns 400 if the certificate has not been successfully generated yet.
    """
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if cert.status != CertificateStatus.COMPLETED or not cert.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate PDF is not available. Current status: {cert.status}"
        )

    # Resolve the safe absolute path server-side; never expose it to the client
    safe_path = os.path.join(CERTIFICATE_STORAGE_DIR, cert.pdf_path)
    if not os.path.isfile(safe_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate PDF file not found on server."
        )

    download_name = f"certificate_{cert.certificate_id}.pdf"
    return FileResponse(
        path=safe_path,
        media_type="application/pdf",
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
    )
