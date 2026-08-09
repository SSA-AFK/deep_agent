from fastapi.testclient import TestClient

from api.server import app


client = TestClient(app)


def test_upload_rejects_unsafe_thread_and_filename():
    response = client.post("/api/upload", data={"thread_id": "../escape"}, files={"files": ("note.txt", b"hello", "text/plain")})
    assert response.status_code == 422

    response = client.post("/api/upload", data={"thread_id": "test-upload"}, files={"files": ("../../outside.txt", b"hello", "text/plain")})
    assert response.status_code == 422
