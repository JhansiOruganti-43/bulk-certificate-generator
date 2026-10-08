from pydantic import BaseModel, Field, ConfigDict, computed_field
from datetime import datetime
from typing import Optional, List
from app.models.enums import BatchStatus
from app.schemas.certificate import CertificateBase


class BatchBase(BaseModel):
    status: BatchStatus = BatchStatus.PENDING
    total_recipients: int = 0
    processed_recipients: int = 0
    successful_certificates: int = 0
    failed_certificates: int = 0


class BatchCreate(BaseModel):
    recipients: List[CertificateBase] = Field(
        ...,
        min_length=1,
        description="A list of recipients to generate certificates for. Must contain at least one recipient."
    )


class BatchResponse(BatchBase):
    id: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @computed_field
    @property
    def progress_percentage(self) -> float:
        """Percentage of recipients that have been processed (0–100)."""
        if self.total_recipients == 0:
            return 0.0
        return round((self.processed_recipients / self.total_recipients) * 100, 1)

    model_config = ConfigDict(from_attributes=True)


class BatchProgressResponse(BaseModel):
    """Lightweight progress snapshot returned by GET /batches/{id}/progress."""
    id: str
    status: BatchStatus
    total: int
    processed: int
    successful: int
    failed: int
    progress_percentage: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_batch(cls, batch) -> "BatchProgressResponse":
        total = batch.total_recipients or 0
        processed = batch.processed_recipients or 0
        pct = round((processed / total) * 100, 1) if total else 0.0
        return cls(
            id=batch.id,
            status=batch.status,
            total=total,
            processed=processed,
            successful=batch.successful_certificates or 0,
            failed=batch.failed_certificates or 0,
            progress_percentage=pct,
            started_at=batch.started_at,
            completed_at=batch.completed_at,
        )
