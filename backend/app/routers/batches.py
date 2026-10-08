from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.batch import Batch
from app.models.certificate import Certificate
from app.schemas.batch import BatchCreate, BatchResponse, BatchProgressResponse
from app.schemas.certificate import CertificateResponse
from app.services.batch_processor import generate_certificates_for_batch

router = APIRouter(prefix="/batches", tags=["batches"])

@router.post(
    "/",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bulk certificate batch and generate PDFs"
)
def create_batch(batch_in: BatchCreate, db: Session = Depends(get_db)):
    """
    Submit a list of recipients. The API will:
    1. Validate all recipients.
    2. Create the batch and certificate records.
    3. Immediately generate PDF certificates for every valid recipient.
    4. Isolated failures per-recipient are recorded in the DB without stopping the batch.
    """
    total_recipients = len(batch_in.recipients)

    new_batch = Batch(total_recipients=total_recipients)
    db.add(new_batch)
    db.flush()  # flush to get new_batch.id before certificates reference it

    seen = set()
    for recipient in batch_in.recipients:
        identifier = (recipient.recipient_email, recipient.course_name)
        if identifier in seen:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate entry in request for {recipient.recipient_email} in {recipient.course_name}"
            )
        seen.add(identifier)

        cert = Certificate(
            batch_id=new_batch.id,
            recipient_name=recipient.recipient_name,
            recipient_email=recipient.recipient_email,
            course_name=recipient.course_name
        )
        db.add(cert)

    db.commit()
    db.refresh(new_batch)

    # Trigger synchronous PDF generation — individual failures are isolated inside
    generate_certificates_for_batch(db=db, batch_id=new_batch.id)
    db.refresh(new_batch)

    return new_batch


@router.get("/", response_model=List[BatchResponse], summary="List all batches")
def list_batches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of all certificate batches, newest first.
    """
    return db.query(Batch).order_by(Batch.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{batch_id}", response_model=BatchResponse, summary="Retrieve a specific batch")
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    """
    Retrieve details and progress of a specific batch by its ID.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return batch


@router.get(
    "/{batch_id}/certificates",
    response_model=List[CertificateResponse],
    summary="List certificates in a batch"
)
def list_batch_certificates(batch_id: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all certificate records belonging to a specific batch.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    return db.query(Certificate).filter(Certificate.batch_id == batch_id).offset(skip).limit(limit).all()


@router.get(
    "/{batch_id}/progress",
    response_model=BatchProgressResponse,
    summary="Get real-time processing progress for a batch"
)
def get_batch_progress(batch_id: str, db: Session = Depends(get_db)):
    """
    Returns a lightweight snapshot of the batch's processing progress.

    Example response:
    ```json
    {
        "id": "abc-123",
        "status": "completed_with_errors",
        "total": 4,
        "processed": 4,
        "successful": 3,
        "failed": 1,
        "progress_percentage": 100.0
    }
    ```
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    return BatchProgressResponse.from_batch(batch)
