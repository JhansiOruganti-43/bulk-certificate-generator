import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.session import get_db, Base
from app.models.batch import Batch
from app.models.certificate import Certificate
from app.models.enums import BatchStatus

# Setup in-memory sqlite test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_health_check_again():
    response = client.get("/api/health")
    assert response.status_code == 200

def test_missing_fields_validation():
    # Empty JSON payload
    response = client.post("/api/batches/", json={})
    assert response.status_code == 422
    assert "recipients" in response.text

def test_empty_batch_validation():
    # Empty list of recipients
    response = client.post("/api/batches/", json={"recipients": []})
    assert response.status_code == 422

def test_invalid_email_validation():
    response = client.post("/api/batches/", json={
        "recipients": [
            {
                "recipient_name": "Test User",
                "recipient_email": "not-an-email",
                "course_name": "Course A"
            }
        ]
    })
    assert response.status_code == 422
    assert "value is not a valid email address" in response.text.lower()

def test_empty_recipient_name_validation():
    response = client.post("/api/batches/", json={
        "recipients": [
            {
                "recipient_name": "",
                "recipient_email": "test@example.com",
                "course_name": "Course A"
            }
        ]
    })
    assert response.status_code == 422
    assert "string_too_short" in response.text.lower()

def create_valid_batch():
    response = client.post("/api/batches/", json={
        "recipients": [
            {
                "recipient_name": "John Doe",
                "recipient_email": "john.valid@example.com",
                "course_name": "Course A"
            }
        ]
    })
    return response

def test_valid_batch_creation():
    response = create_valid_batch()
    assert response.status_code == 201
    data = response.json()
    # Generation is synchronous: status transitions PENDING → PROCESSING → COMPLETED
    assert data["status"] == BatchStatus.COMPLETED
    assert data["total_recipients"] == 1
    assert data["successful_certificates"] == 1


def test_duplicate_recipients_validation():
    response = client.post("/api/batches/", json={
        "recipients": [
            {
                "recipient_name": "John Doe",
                "recipient_email": "dup@example.com",
                "course_name": "Course A"
            },
            {
                "recipient_name": "John Doe Copy",
                "recipient_email": "dup@example.com",
                "course_name": "Course A"
            }
        ]
    })
    assert response.status_code == 400
    assert "duplicate" in response.text.lower()

def test_batch_retrieval():
    # First create a batch
    batch_id = create_valid_batch().json()["id"]
    
    response = client.get(f"/api/batches/{batch_id}")
    assert response.status_code == 200
    assert response.json()["id"] == batch_id

def test_missing_batch_retrieval():
    response = client.get("/api/batches/not-a-real-id")
    assert response.status_code == 404

def test_list_batch_certificates():
    batch_id = create_valid_batch().json()["id"]
    response = client.get(f"/api/batches/{batch_id}/certificates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["batch_id"] == batch_id
    assert data[0]["recipient_name"] == "John Doe"

def test_individual_certificate_retrieval():
    batch_id = create_valid_batch().json()["id"]
    
    # Get the certificate ID inside this batch
    resp_certs = client.get(f"/api/batches/{batch_id}/certificates")
    cert_id = resp_certs.json()[0]["id"]
    
    # Fetch individually
    response = client.get(f"/api/certificates/{cert_id}")
    assert response.status_code == 200
    assert response.json()["id"] == cert_id
    assert response.json()["batch_id"] == batch_id

def test_missing_certificate_retrieval():
    response = client.get("/api/certificates/fake-cert-id")
    assert response.status_code == 404
