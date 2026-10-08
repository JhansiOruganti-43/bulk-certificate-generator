import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.batch import Batch
from app.models.certificate import Certificate
from app.models.enums import BatchStatus, CertificateStatus
from app.services.pdf_generator import generate_pdf, PDFGenerationError

logger = logging.getLogger(__name__)

UTC = timezone.utc

def generate_certificates_for_batch(db: Session, batch_id: str):
    """
    Core business logic that generates physical PDFs for a batch of certificates.
    Failures on an individual recipient strictly won't kill the batch or loop.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        logger.error(f"Batch {batch_id} not found in processor.")
        return

    batch.status = BatchStatus.PROCESSING
    batch.started_at = datetime.now(UTC)
    db.commit()

    certificates = db.query(Certificate).filter(Certificate.batch_id == batch_id).all()

    successful = 0
    failed = 0

    for cert in certificates:
        # Skip already-processed certificates (safe to resume a batch)
        if cert.status in [CertificateStatus.COMPLETED, CertificateStatus.FAILED]:
            continue

        cert.status = CertificateStatus.PROCESSING
        db.commit()

        unique_cid = f"AEREO-{datetime.now(UTC).year}-{str(uuid.uuid4())[:8].upper()}"
        issue_d = datetime.now(UTC).strftime("%Y-%m-%d")

        try:
            # Intentional-failure hook used by tests (FAIL_ME_TEST in name)
            if "FAIL_ME_TEST" in cert.recipient_name:
                raise ValueError("Simulated isolated error")

            filename = generate_pdf(
                recipient_name=cert.recipient_name,
                course_name=cert.course_name,
                certificate_id=unique_cid,
                issue_date=issue_d,
            )

            cert.certificate_id = unique_cid
            cert.pdf_path = filename
            cert.status = CertificateStatus.COMPLETED
            successful += 1

        except Exception as ex:
            logger.error(f"Failed generating PDF for cert {cert.id}: {ex}")
            cert.status = CertificateStatus.FAILED
            cert.error_message = str(ex)
            failed += 1

        db.commit()

        batch.processed_recipients += 1
        batch.successful_certificates = successful
        batch.failed_certificates = failed
        db.commit()

    # Determine final batch status:
    # - COMPLETED          → all recipients succeeded
    # - COMPLETED_WITH_ERRORS → at least one succeeded, at least one failed
    # - FAILED             → every single recipient failed
    batch.completed_at = datetime.now(UTC)
    if failed == 0:
        batch.status = BatchStatus.COMPLETED
    elif successful > 0:
        batch.status = BatchStatus.COMPLETED_WITH_ERRORS
    else:
        batch.status = BatchStatus.FAILED
    db.commit()
