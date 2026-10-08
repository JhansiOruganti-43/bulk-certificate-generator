"""
Phase 5 Tests – Bulk processing, progress tracking, and status semantics.
"""
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

# ── Recipient fixtures ────────────────────────────────────────────────────────

def make_recipient(name: str, email: str, course: str = "AEREO Internship 2026"):
    return {"recipient_name": name, "recipient_email": email, "course_name": course}

ALL_VALID = [
    make_recipient("Alice Smith",   "alice5@example.com"),
    make_recipient("Bob Jones",     "bob5@example.com"),
    make_recipient("Carol White",   "carol5@example.com"),
    make_recipient("Dave Brown",    "dave5@example.com"),
]

# recipient 3 (index 2) will fail because of the FAIL_ME_TEST hook in batch_processor
MIXED_4 = [
    make_recipient("Recipient One",       "r1@example.com"),
    make_recipient("Recipient Two",       "r2@example.com"),
    make_recipient("FAIL_ME_TEST Three",  "r3@example.com"),  # intentional fail
    make_recipient("Recipient Four",      "r4@example.com"),
]

ALL_FAIL = [
    make_recipient("FAIL_ME_TEST Alpha", "fa@example.com"),
    make_recipient("FAIL_ME_TEST Beta",  "fb@example.com"),
]


def post_batch(recipients) -> dict:
    r = client.post("/api/batches/", json={"recipients": recipients})
    assert r.status_code == 201, r.text
    return r.json()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestAllSuccessfulBatch:

    def test_all_recipients_generate_certificates(self):
        data = post_batch(ALL_VALID)
        assert data["total_recipients"] == 4
        assert data["successful_certificates"] == 4
        assert data["failed_certificates"] == 0

    def test_batch_status_is_completed(self):
        data = post_batch(ALL_VALID)
        assert data["status"] == BatchStatus.COMPLETED

    def test_progress_percentage_is_100(self):
        data = post_batch(ALL_VALID)
        assert data["progress_percentage"] == 100.0

    def test_processed_equals_total(self):
        data = post_batch(ALL_VALID)
        assert data["processed_recipients"] == data["total_recipients"]

    def test_certificates_are_all_completed(self):
        data = post_batch(ALL_VALID)
        certs = client.get(f"/api/batches/{data['id']}/certificates").json()
        assert all(c["status"] == CertificateStatus.COMPLETED for c in certs)

    def test_progress_endpoint_all_success(self):
        data = post_batch(ALL_VALID)
        prog = client.get(f"/api/batches/{data['id']}/progress").json()
        assert prog["total"] == 4
        assert prog["successful"] == 4
        assert prog["failed"] == 0
        assert prog["progress_percentage"] == 100.0
        assert prog["status"] == BatchStatus.COMPLETED


class TestMixedBatch:
    """Critical: Recipient 3 fails, recipients 1, 2, 4 must still succeed."""

    def test_one_failure_does_not_stop_remaining_recipients(self):
        data = post_batch(MIXED_4)
        # All 4 must be processed even though #3 fails
        assert data["processed_recipients"] == 4

    def test_correct_success_and_failure_counts(self):
        data = post_batch(MIXED_4)
        assert data["successful_certificates"] == 3
        assert data["failed_certificates"] == 1

    def test_batch_status_is_completed_with_errors(self):
        data = post_batch(MIXED_4)
        assert data["status"] == BatchStatus.COMPLETED_WITH_ERRORS

    def test_failed_recipient_has_error_message(self):
        data = post_batch(MIXED_4)
        certs = client.get(f"/api/batches/{data['id']}/certificates").json()
        failed = [c for c in certs if c["status"] == CertificateStatus.FAILED]
        assert len(failed) == 1
        assert failed[0]["error_message"] not in (None, "")

    def test_successful_recipients_have_pdfs(self):
        data = post_batch(MIXED_4)
        certs = client.get(f"/api/batches/{data['id']}/certificates").json()
        succeeded = [c for c in certs if c["status"] == CertificateStatus.COMPLETED]
        assert len(succeeded) == 3
        assert all(c["pdf_path"] is not None for c in succeeded)
        assert all(c["certificate_id"].startswith("AEREO-") for c in succeeded)

    def test_failed_recipient_has_no_pdf(self):
        data = post_batch(MIXED_4)
        certs = client.get(f"/api/batches/{data['id']}/certificates").json()
        failed = next(c for c in certs if c["status"] == CertificateStatus.FAILED)
        assert failed["pdf_path"] is None
        assert failed["certificate_id"] is None

    def test_progress_endpoint_mixed_batch(self):
        data = post_batch(MIXED_4)
        prog = client.get(f"/api/batches/{data['id']}/progress").json()
        assert prog["total"] == 4
        assert prog["processed"] == 4
        assert prog["successful"] == 3
        assert prog["failed"] == 1
        assert prog["progress_percentage"] == 100.0
        assert prog["status"] == BatchStatus.COMPLETED_WITH_ERRORS


class TestAllFailBatch:
    """When every single recipient fails the batch status must be FAILED."""

    def test_all_fail_status_is_failed(self):
        data = post_batch(ALL_FAIL)
        assert data["status"] == BatchStatus.FAILED

    def test_all_fail_counts(self):
        data = post_batch(ALL_FAIL)
        assert data["successful_certificates"] == 0
        assert data["failed_certificates"] == 2


class TestProgressEndpoint:

    def test_progress_endpoint_404_for_missing_batch(self):
        r = client.get("/api/batches/nonexistent-id/progress")
        assert r.status_code == 404

    def test_progress_response_shape(self):
        """Verify all required keys are present in the progress response."""
        data = post_batch(ALL_VALID)
        prog = client.get(f"/api/batches/{data['id']}/progress").json()
        for key in ("id", "status", "total", "processed", "successful", "failed", "progress_percentage"):
            assert key in prog, f"Missing key: {key}"

    def test_timestamps_present_after_completion(self):
        data = post_batch(ALL_VALID)
        prog = client.get(f"/api/batches/{data['id']}/progress").json()
        assert prog["started_at"] is not None
        assert prog["completed_at"] is not None


class TestMultipleBatches:
    """Batches must be independent — progress is per-batch, not global."""

    def test_multiple_concurrent_batches_independent(self):
        batch_a = post_batch(ALL_VALID)
        batch_b = post_batch(MIXED_4)

        prog_a = client.get(f"/api/batches/{batch_a['id']}/progress").json()
        prog_b = client.get(f"/api/batches/{batch_b['id']}/progress").json()

        assert prog_a["successful"] == 4
        assert prog_b["successful"] == 3
        assert prog_a["id"] != prog_b["id"]
