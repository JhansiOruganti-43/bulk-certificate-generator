"""
Phase 4 Tests – Certificate PDF generation, failure isolation, and download endpoint.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db, Base
from app.models.batch import Batch
from app.models.certificate import Certificate
from app.models.enums import BatchStatus, CertificateStatus
from app.services.pdf_generator import CERTIFICATE_STORAGE_DIR

# ── In-memory SQLite (StaticPool keeps the same connection across threads) ──────
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────────────────

def post_batch(recipients: list) -> dict:
    """Helper: POST /api/batches/ and return parsed JSON."""
    resp = client.post("/api/batches/", json={"recipients": recipients})
    assert resp.status_code == 201, resp.text
    return resp.json()


ONE_RECIPIENT = [
    {
        "recipient_name": "Alice Smith",
        "recipient_email": "alice@example.com",
        "course_name": "Python Fundamentals",
    }
]

MIXED_RECIPIENTS = [
    {
        "recipient_name": "Bob Jones",
        "recipient_email": "bob@example.com",
        "course_name": "Data Science 101",
    },
    {
        # Special marker triggers intentional failure in batch_processor
        "recipient_name": "FAIL_ME_TEST User",
        "recipient_email": "fail@example.com",
        "course_name": "Data Science 101",
    },
]


# ── Tests ────────────────────────────────────────────────────────────────────────

class TestPDFGeneration:
    """Tests that verify real PDF creation."""

    def test_successful_generation_status(self):
        """Batch with one valid recipient should complete with status=completed."""
        data = post_batch(ONE_RECIPIENT)
        assert data["status"] == BatchStatus.COMPLETED
        assert data["successful_certificates"] == 1
        assert data["failed_certificates"] == 0

    def test_certificate_record_updated_after_generation(self):
        """After generation, the certificate row should store certificate_id and pdf_path."""
        batch_data = post_batch(ONE_RECIPIENT)
        batch_id = batch_data["id"]

        certs = client.get(f"/api/batches/{batch_id}/certificates").json()
        assert len(certs) == 1
        cert = certs[0]

        assert cert["status"] == CertificateStatus.COMPLETED
        assert cert["certificate_id"] is not None
        assert cert["certificate_id"].startswith("AEREO-")
        assert cert["pdf_path"] is not None
        assert cert["pdf_path"].endswith(".pdf")

    def test_generated_unique_certificate_id(self):
        """Each certificate should get a unique AEREO-YYYY-XXXXXXXX ID."""
        batch1 = post_batch(ONE_RECIPIENT)
        batch2 = post_batch([
            {
                "recipient_name": "Carol White",
                "recipient_email": "carol@example.com",
                "course_name": "Python Fundamentals",
            }
        ])

        cid1 = client.get(f"/api/batches/{batch1['id']}/certificates").json()[0]["certificate_id"]
        cid2 = client.get(f"/api/batches/{batch2['id']}/certificates").json()[0]["certificate_id"]

        assert cid1 != cid2, "Certificate IDs must be unique across recipients"

    def test_pdf_file_exists_on_disk(self):
        """The PDF file referenced in the DB must physically exist in the storage dir."""
        batch_data = post_batch(ONE_RECIPIENT)
        batch_id = batch_data["id"]

        cert = client.get(f"/api/batches/{batch_id}/certificates").json()[0]
        pdf_filename = cert["pdf_path"]

        full_path = os.path.join(CERTIFICATE_STORAGE_DIR, pdf_filename)
        assert os.path.isfile(full_path), f"Expected PDF file at {full_path}"
        assert os.path.getsize(full_path) > 0, "PDF file should not be empty"


class TestFailureIsolation:
    """Tests that verify a single failure never stops the rest of the batch."""

    def test_individual_failure_does_not_stop_batch(self):
        """Mixed batch: one valid + one with FAIL_ME_TEST. Both should be processed."""
        data = post_batch(MIXED_RECIPIENTS)

        assert data["status"] == BatchStatus.COMPLETED_WITH_ERRORS
        assert data["total_recipients"] == 2
        assert data["successful_certificates"] == 1
        assert data["failed_certificates"] == 1

    def test_failed_certificate_stores_error_message(self):
        """The failed cert row should have an error_message and status=failed."""
        batch_data = post_batch(MIXED_RECIPIENTS)
        batch_id = batch_data["id"]

        certs = client.get(f"/api/batches/{batch_id}/certificates").json()
        failed = [c for c in certs if c["status"] == CertificateStatus.FAILED]
        succeeded = [c for c in certs if c["status"] == CertificateStatus.COMPLETED]

        assert len(failed) == 1
        assert len(succeeded) == 1

        assert failed[0]["error_message"] is not None
        assert len(failed[0]["error_message"]) > 0
        # The successful one should still have a PDF
        assert succeeded[0]["pdf_path"] is not None

    def test_failed_certificate_has_no_pdf(self):
        """A failed certificate should have no pdf_path stored."""
        batch_data = post_batch(MIXED_RECIPIENTS)
        batch_id = batch_data["id"]

        certs = client.get(f"/api/batches/{batch_id}/certificates").json()
        failed = next(c for c in certs if c["status"] == CertificateStatus.FAILED)

        assert failed["pdf_path"] is None
        assert failed["certificate_id"] is None


class TestDownloadEndpoint:
    """Tests for GET /api/certificates/{id}/download."""

    def test_download_completed_certificate(self):
        """A completed certificate should return a 200 with content-type application/pdf."""
        batch_data = post_batch(ONE_RECIPIENT)
        batch_id = batch_data["id"]

        cert_id = client.get(f"/api/batches/{batch_id}/certificates").json()[0]["id"]
        resp = client.get(f"/api/certificates/{cert_id}/download")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 0, "PDF response body should not be empty"

    def test_download_not_found_certificate(self):
        """Downloading a non-existent certificate ID should return 404."""
        resp = client.get("/api/certificates/does-not-exist/download")
        assert resp.status_code == 404

    def test_download_failed_certificate_returns_400(self):
        """Attempting to download a certificate that failed should return 400."""
        batch_data = post_batch(MIXED_RECIPIENTS)
        batch_id = batch_data["id"]

        certs = client.get(f"/api/batches/{batch_id}/certificates").json()
        failed_cert_id = next(c["id"] for c in certs if c["status"] == CertificateStatus.FAILED)

        resp = client.get(f"/api/certificates/{failed_cert_id}/download")
        assert resp.status_code == 400
        assert "not available" in resp.json()["detail"].lower()
