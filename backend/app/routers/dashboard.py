from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.batch import Batch
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard", summary="Get dashboard statistics")
def get_dashboard(db: Session = Depends(get_db)):
    """Returns aggregate statistics for the dashboard."""
    total_batches = db.query(func.count(Batch.id)).scalar() or 0
    total_certs = db.query(func.count(Certificate.id)).scalar() or 0
    successful_certs = db.query(func.count(Certificate.id)).filter(
        Certificate.status == CertificateStatus.COMPLETED
    ).scalar() or 0
    failed_certs = db.query(func.count(Certificate.id)).filter(
        Certificate.status == CertificateStatus.FAILED
    ).scalar() or 0
    success_rate = round((successful_certs / total_certs) * 100, 1) if total_certs > 0 else 0.0

    return {
        "total_batches": total_batches,
        "total_certificates": total_certs,
        "successful_certificates": successful_certs,
        "failed_certificates": failed_certs,
        "success_rate": success_rate,
    }
