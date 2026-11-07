from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_rejects_unsupported_extension():
    response = client.post(
        "/api/process",
        files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400
