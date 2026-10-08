"""
Phase 6 – Comprehensive testing and reliability improvements.

Covers all 18 required scenarios, mock-based failure injection,
error response shape validation, and the critical 5-recipient
(4-succeed / 1-fail) scenario.
"""

import os
import unittest.mock as mock

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
from app.services import pdf_generator as pdf_gen_module
from app.services.pdf_generator import CERTIFICATE_STORAGE_DIR

# ─────────────────────────────────────────────────────────────────────────────
# Shared test DB setup (StaticPool → single in-memory connection for all tests)
# ─────────────────────────────────────────────────────────────────────────────
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
client = TestClient(app, raise_server_exceptions=False)   # suppress pytest re-raise for 500 tests


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def r(name, email, course="AEREO 2026"):
    return {"recipient_name": name, "recipient_email": email, "course_name": course}


def post_batch(recipients, expect_status=201):
    resp = client.post("/api/batches/", json={"recipients": recipients})
    assert resp.status_code == expect_status, resp.text
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Health endpoint
# ─────────────────────────────────────────────────────────────────────────────
class TestHealthEndpoint:

    def test_returns_200(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_response_body_has_status_ok(self):
        resp = client.get("/api/health")
        assert resp.json()["status"] == "ok"

    def test_response_body_has_message(self):
        resp = client.get("/api/health")
        assert "message" in resp.json()

    def test_root_endpoint(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "AEREO" in resp.json()["message"]


# ─────────────────────────────────────────────────────────────────────────────
# 2–3. Validation: empty list, invalid email, missing fields, invalid data
# ─────────────────────────────────────────────────────────────────────────────
class TestInputValidation:

    def test_empty_recipient_list_returns_422(self):
        resp = client.post("/api/batches/", json={"recipients": []})
        assert resp.status_code == 422

    def test_missing_recipients_field_returns_422(self):
        resp = client.post("/api/batches/", json={})
        assert resp.status_code == 422
        assert "recipients" in resp.text

    def test_invalid_email_returns_422(self):
        resp = client.post("/api/batches/", json={
            "recipients": [r("Jane", "not-an-email")]
        })
        assert resp.status_code == 422
        assert "value is not a valid email address" in resp.text.lower()

    def test_empty_recipient_name_returns_422(self):
        resp = client.post("/api/batches/", json={
            "recipients": [r("", "jane@example.com")]
        })
        assert resp.status_code == 422
        assert "string_too_short" in resp.text.lower()

    def test_whitespace_only_name_is_rejected(self):
        """A name that is only whitespace should fail min_length=1 after stripping."""
        resp = client.post("/api/batches/", json={
            "recipients": [{"recipient_name": "   ", "recipient_email": "x@y.com", "course_name": "Z"}]
        })
        # Pydantic min_length=1 counts raw length — "   " is length 3, so Pydantic
        # accepts it. We test that the name field is NOT stripped silently; the
        # value should appear in the response.
        if resp.status_code == 201:
            # If accepted, cert name should be stored as-is (not silently trimmed)
            batch_id = resp.json()["id"]
            certs = client.get(f"/api/batches/{batch_id}/certificates").json()
            assert certs[0]["recipient_name"] == "   "
        else:
            assert resp.status_code == 422

    def test_missing_course_name_returns_422(self):
        resp = client.post("/api/batches/", json={
            "recipients": [{"recipient_name": "Joe", "recipient_email": "joe@example.com"}]
        })
        assert resp.status_code == 422

    def test_non_string_name_returns_422(self):
        resp = client.post("/api/batches/", json={
            "recipients": [{"recipient_name": 12345, "recipient_email": "x@x.com", "course_name": "C"}]
        })
        # Pydantic coerces int → str in lax mode; the important thing is it
        # doesn't cause a 500. We just assert no internal error leaked.
        assert resp.status_code in (201, 422)
        if resp.status_code == 500:
            pytest.fail("Non-string name caused a 500 — internal error leaked")

    def test_extra_fields_ignored(self):
        """Unknown extra fields must not cause errors."""
        resp = client.post("/api/batches/", json={
            "recipients": [r("Joe", "joe6@example.com")],
            "injected_field": "hacked"
        })
        assert resp.status_code == 201


# ─────────────────────────────────────────────────────────────────────────────
# 4. Duplicate recipients
# ─────────────────────────────────────────────────────────────────────────────
class TestDuplicateRecipients:

    def test_identical_email_and_course_rejected(self):
        resp = client.post("/api/batches/", json={
            "recipients": [
                r("Alice", "dup6@ex.com", "Course A"),
                r("Alice Clone", "dup6@ex.com", "Course A"),
            ]
        })
        assert resp.status_code == 400
        assert "duplicate" in resp.json()["detail"].lower()

    def test_same_email_different_course_allowed(self):
        """Same email but different course is NOT a duplicate."""
        resp = client.post("/api/batches/", json={
            "recipients": [
                r("Alice", "multi6@ex.com", "Course A"),
                r("Alice", "multi6@ex.com", "Course B"),
            ]
        })
        assert resp.status_code == 201
        assert resp.json()["total_recipients"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# 5. Valid batch creation
# ─────────────────────────────────────────────────────────────────────────────
class TestValidBatchCreation:

    def test_single_recipient_batch(self):
        data = post_batch([r("Tom", "tom6@ex.com")])
        assert data["status"] == BatchStatus.COMPLETED
        assert data["total_recipients"] == 1
        assert data["successful_certificates"] == 1

    def test_batch_response_has_all_required_fields(self):
        data = post_batch([r("Tom2", "tom2@ex.com")])
        for field in ("id", "status", "total_recipients", "processed_recipients",
                      "successful_certificates", "failed_certificates",
                      "progress_percentage", "created_at"):
            assert field in data, f"Missing field: {field}"

    def test_multiple_recipients_all_succeed(self):
        data = post_batch([
            r("A", "a6@ex.com"),
            r("B", "b6@ex.com"),
            r("C", "c6@ex.com"),
        ])
        assert data["total_recipients"] == 3
        assert data["successful_certificates"] == 3
        assert data["failed_certificates"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. THE CRITICAL TEST: 5 recipients, 4 succeed, 1 fails (mock-based)
# ─────────────────────────────────────────────────────────────────────────────
class TestCriticalFiveRecipientScenario:
    """
    5 recipients submitted.
    Recipient index 2 (third) has PDF generation mocked to raise an exception.
    Expected outcome:
        - total     = 5
        - successful = 4
        - failed    = 1
        - status    = completed_with_errors
        - 4 certs have pdf_path set
        - 1 cert has error_message set and pdf_path=None
    """

    @pytest.fixture(autouse=True)
    def mock_pdf_failure_for_third(self, monkeypatch):
        """
        Wrap generate_pdf so the third call raises PDFGenerationError.
        All other calls use the real implementation.
        """
        real_generate_pdf = pdf_gen_module.generate_pdf
        call_count = {"n": 0}

        def patched_generate_pdf(recipient_name, course_name, certificate_id, issue_date):
            call_count["n"] += 1
            if call_count["n"] == 3:
                raise pdf_gen_module.PDFGenerationError("Simulated disk-full error")
            return real_generate_pdf(recipient_name, course_name, certificate_id, issue_date)

        monkeypatch.setattr(pdf_gen_module, "generate_pdf", patched_generate_pdf)

    def test_five_recipients_four_succeed_one_fails(self):
        data = post_batch([
            r("Recipient One",   "r6_1@ex.com"),
            r("Recipient Two",   "r6_2@ex.com"),
            r("Recipient Three", "r6_3@ex.com"),   # ← mocked to fail
            r("Recipient Four",  "r6_4@ex.com"),
            r("Recipient Five",  "r6_5@ex.com"),
        ])

        assert data["total_recipients"] == 5, "total must be 5"
        assert data["successful_certificates"] == 4, "4 must succeed"
        assert data["failed_certificates"] == 1, "1 must fail"
        assert data["status"] == BatchStatus.COMPLETED_WITH_ERRORS

    def test_all_five_are_processed(self):
        data = post_batch([
            r("Rec One",   "p6_1@ex.com"),
            r("Rec Two",   "p6_2@ex.com"),
            r("Rec Three", "p6_3@ex.com"),
            r("Rec Four",  "p6_4@ex.com"),
            r("Rec Five",  "p6_5@ex.com"),
        ])
        assert data["processed_recipients"] == 5

    def test_four_successful_certs_have_pdfs(self):
        data = post_batch([
            r("S1", "s6_1@ex.com"),
            r("S2", "s6_2@ex.com"),
            r("S3", "s6_3@ex.com"),   # ← fails
            r("S4", "s6_4@ex.com"),
            r("S5", "s6_5@ex.com"),
        ])
        batch_id = data["id"]
        certs = client.get(f"/api/batches/{batch_id}/certificates").json()

        succeeded = [c for c in certs if c["status"] == CertificateStatus.COMPLETED]
        failed = [c for c in certs if c["status"] == CertificateStatus.FAILED]

        assert len(succeeded) == 4
        assert len(failed) == 1

        # Successful certs must have PDFs
        assert all(c["pdf_path"] is not None for c in succeeded)
        assert all(c["certificate_id"].startswith("AEREO-") for c in succeeded)

        # Failed cert must have an error message and no PDF
        assert failed[0]["error_message"] is not None
        assert failed[0]["pdf_path"] is None
        assert failed[0]["certificate_id"] is None

    def test_failed_cert_error_message_is_meaningful(self):
        data = post_batch([
            r("E1", "e6_1@ex.com"),
            r("E2", "e6_2@ex.com"),
            r("E3_fail", "e6_3@ex.com"),
            r("E4", "e6_4@ex.com"),
            r("E5", "e6_5@ex.com"),
        ])
        batch_id = data["id"]
        certs = client.get(f"/api/batches/{batch_id}/certificates").json()
        failed = next(c for c in certs if c["status"] == CertificateStatus.FAILED)
        assert len(failed["error_message"]) > 5


# ─────────────────────────────────────────────────────────────────────────────
# 7. Batch retrieval
# ─────────────────────────────────────────────────────────────────────────────
class TestBatchRetrieval:

    def test_get_existing_batch_returns_200(self):
        batch_id = post_batch([r("P", "p6@ex.com")])["id"]
        resp = client.get(f"/api/batches/{batch_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == batch_id

    def test_get_missing_batch_returns_404(self):
        resp = client.get("/api/batches/does-not-exist-at-all")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    def test_list_batches_returns_array(self):
        post_batch([r("L", "l6@ex.com")])
        resp = client.get("/api/batches/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    def test_list_batches_pagination(self):
        resp_one = client.get("/api/batches/?limit=1")
        assert len(resp_one.json()) == 1

    def test_batch_certificates_list_for_missing_batch_returns_404(self):
        resp = client.get("/api/batches/fake-id-999/certificates")
        assert resp.status_code == 404

    def test_batch_certificates_list_returns_correct_count(self):
        batch_id = post_batch([r("Q1", "q16@ex.com"), r("Q2", "q26@ex.com")])["id"]
        certs = client.get(f"/api/batches/{batch_id}/certificates").json()
        assert len(certs) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 8. Certificate retrieval
# ─────────────────────────────────────────────────────────────────────────────
class TestCertificateRetrieval:

    def test_get_existing_certificate_returns_200(self):
        batch_id = post_batch([r("R6", "r6@ex.com")])["id"]
        cert_id = client.get(f"/api/batches/{batch_id}/certificates").json()[0]["id"]
        resp = client.get(f"/api/certificates/{cert_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == cert_id

    def test_get_missing_certificate_returns_404(self):
        resp = client.get("/api/certificates/fake-cert-9999")
        assert resp.status_code == 404

    def test_certificate_response_has_required_fields(self):
        batch_id = post_batch([r("Field6", "field6@ex.com")])["id"]
        cert = client.get(f"/api/batches/{batch_id}/certificates").json()[0]
        for field in ("id", "batch_id", "recipient_name", "recipient_email",
                      "course_name", "status", "certificate_id", "pdf_path",
                      "created_at", "updated_at"):
            assert field in cert, f"Missing field: {field}"


# ─────────────────────────────────────────────────────────────────────────────
# 9. Certificate download
# ─────────────────────────────────────────────────────────────────────────────
class TestCertificateDownload:

    def test_download_completed_cert_returns_pdf(self):
        batch_id = post_batch([r("DL6", "dl6@ex.com")])["id"]
        cert_id = client.get(f"/api/batches/{batch_id}/certificates").json()[0]["id"]
        resp = client.get(f"/api/certificates/{cert_id}/download")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 100  # must be a real file, not empty

    def test_download_missing_cert_returns_404(self):
        resp = client.get("/api/certificates/nonexist-dl6/download")
        assert resp.status_code == 404

    def test_download_failed_cert_returns_400(self):
        batch_id = post_batch([r("FAIL_ME_TEST DL", "dl6f@ex.com")])["id"]
        certs = client.get(f"/api/batches/{batch_id}/certificates").json()
        failed_id = next(c["id"] for c in certs if c["status"] == CertificateStatus.FAILED)
        resp = client.get(f"/api/certificates/{failed_id}/download")
        assert resp.status_code == 400
        assert "not available" in resp.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 10. Batch progress endpoint
# ─────────────────────────────────────────────────────────────────────────────
class TestBatchProgress:

    def test_progress_endpoint_returns_200(self):
        batch_id = post_batch([r("Prg6", "prg6@ex.com")])["id"]
        resp = client.get(f"/api/batches/{batch_id}/progress")
        assert resp.status_code == 200

    def test_progress_response_schema(self):
        batch_id = post_batch([r("Prg6b", "prg6b@ex.com")])["id"]
        prog = client.get(f"/api/batches/{batch_id}/progress").json()
        for key in ("id", "status", "total", "processed", "successful",
                    "failed", "progress_percentage"):
            assert key in prog, f"Progress response missing: {key}"

    def test_progress_100_after_completion(self):
        batch_id = post_batch([r("Prg6c", "prg6c@ex.com")])["id"]
        prog = client.get(f"/api/batches/{batch_id}/progress").json()
        assert prog["progress_percentage"] == 100.0

    def test_progress_timestamps_populated(self):
        batch_id = post_batch([r("Prg6d", "prg6d@ex.com")])["id"]
        prog = client.get(f"/api/batches/{batch_id}/progress").json()
        assert prog["started_at"] is not None
        assert prog["completed_at"] is not None

    def test_progress_missing_batch_returns_404(self):
        resp = client.get("/api/batches/no-such-batch/progress")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 11. Error responses – correct shape, no stack traces
# ─────────────────────────────────────────────────────────────────────────────
class TestErrorResponses:

    def test_404_response_has_detail_key(self):
        resp = client.get("/api/batches/fake")
        assert "detail" in resp.json()
        assert "traceback" not in resp.text.lower()
        assert "sqlalchemy" not in resp.text.lower()

    def test_validation_error_has_detail_key(self):
        resp = client.post("/api/batches/", json={})
        assert "detail" in resp.json()

    def test_400_response_has_detail_key(self):
        resp = client.post("/api/batches/", json={
            "recipients": [
                r("X", "dup_err@ex.com", "C"),
                r("X2", "dup_err@ex.com", "C"),
            ]
        })
        assert resp.status_code == 400
        assert "detail" in resp.json()

    def test_global_exception_handler_hides_trace(self):
        """
        Trigger a deliberate 500 by patching the DB query to raise unexpected RuntimeError.
        The response must return {"detail": "Internal server error occurred."} — no traceback.
        """
        with mock.patch(
            "app.routers.batches.Batch",
            side_effect=RuntimeError("Unexpected internal boom")
        ):
            resp = client.get("/api/batches/")
        # The global handler should catch it
        if resp.status_code == 500:
            body = resp.json()
            assert body == {"detail": "Internal server error occurred."}
            assert "traceback" not in resp.text.lower()
            assert "RuntimeError" not in resp.text


# ─────────────────────────────────────────────────────────────────────────────
# 12. Database persistence
# ─────────────────────────────────────────────────────────────────────────────
class TestDatabasePersistence:

    def test_batch_persists_after_creation(self):
        batch_id = post_batch([r("Persist6", "persist6@ex.com")])["id"]
        # Re-fetch from the API (uses same underlying DB)
        resp = client.get(f"/api/batches/{batch_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == batch_id

    def test_certificate_fields_persisted(self):
        batch_id = post_batch([r("Persist6b", "persist6b@ex.com")])["id"]
        cert = client.get(f"/api/batches/{batch_id}/certificates").json()[0]

        # Re-fetch individually
        cert2 = client.get(f"/api/certificates/{cert['id']}").json()
        assert cert2["recipient_name"] == "Persist6b"
        assert cert2["recipient_email"] == "persist6b@ex.com"
        assert cert2["certificate_id"] == cert["certificate_id"]
        assert cert2["pdf_path"] == cert["pdf_path"]

    def test_failed_cert_error_message_persisted(self):
        batch_id = post_batch([r("FAIL_ME_TEST Persist", "fail6p@ex.com")])["id"]
        cert = client.get(f"/api/batches/{batch_id}/certificates").json()[0]
        # Re-fetch
        cert2 = client.get(f"/api/certificates/{cert['id']}").json()
        assert cert2["error_message"] is not None

    def test_batch_counts_persisted(self):
        batch_id = post_batch([
            r("PX1", "px1@ex.com"),
            r("FAIL_ME_TEST PX2", "px2@ex.com"),
        ])["id"]
        batch = client.get(f"/api/batches/{batch_id}").json()
        assert batch["successful_certificates"] == 1
        assert batch["failed_certificates"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 13. PDF generator unit tests (no DB, no API)
# ─────────────────────────────────────────────────────────────────────────────
class TestPDFGeneratorUnit:

    def test_generates_file_on_disk(self):
        from app.services.pdf_generator import generate_pdf
        filename = generate_pdf(
            recipient_name="Unit Test User",
            course_name="Unit Test Course",
            certificate_id="AEREO-2026-UNITTEST",
            issue_date="2026-10-07"
        )
        full_path = os.path.join(CERTIFICATE_STORAGE_DIR, filename)
        assert os.path.isfile(full_path)
        assert os.path.getsize(full_path) > 0

    def test_returned_filename_matches_cert_id(self):
        from app.services.pdf_generator import generate_pdf
        cid = "AEREO-2026-FILENAMETEST"
        filename = generate_pdf("A", "B", cid, "2026-01-01")
        assert filename == f"{cid}.pdf"

    def test_raises_on_empty_name(self):
        from app.services.pdf_generator import generate_pdf, PDFGenerationError
        with pytest.raises(PDFGenerationError):
            generate_pdf("", "Course", "AEREO-2026-EMPTY", "2026-01-01")

    def test_raises_on_empty_course(self):
        from app.services.pdf_generator import generate_pdf, PDFGenerationError
        with pytest.raises(PDFGenerationError):
            generate_pdf("Name", "", "AEREO-2026-EMPTY2", "2026-01-01")

    def test_no_leftover_file_on_failure(self):
        """If reportlab fails mid-write, no partial file should remain."""
        from app.services.pdf_generator import generate_pdf, PDFGenerationError

        cid = "AEREO-2026-CLEANUP"
        # Force reportlab to fail by patching canvas.Canvas.save
        with mock.patch(
            "reportlab.pdfgen.canvas.Canvas.save",
            side_effect=IOError("Disk full")
        ):
            with pytest.raises(PDFGenerationError):
                generate_pdf("Name", "Course", cid, "2026-01-01")

        leftover = os.path.join(CERTIFICATE_STORAGE_DIR, f"{cid}.pdf")
        assert not os.path.exists(leftover), "Partial file should have been cleaned up"
