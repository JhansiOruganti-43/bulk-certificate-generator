from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.enums import CertificateStatus

class CertificateBase(BaseModel):
    recipient_name: str = Field(..., min_length=1, description="Full name of the certificate recipient")
    recipient_email: EmailStr = Field(..., description="Valid email address of the recipient")
    course_name: str = Field(..., min_length=1, description="Name of the course, event, or program")

class CertificateCreate(CertificateBase):
    batch_id: str

class CertificateResponse(CertificateBase):
    id: str
    batch_id: str
    certificate_id: Optional[str] = None
    status: CertificateStatus
    pdf_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
