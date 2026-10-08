from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "AEREO Certificate Generator API is running smoothly!"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to AEREO Bulk Certificate Generator API" in response.json()["message"]
