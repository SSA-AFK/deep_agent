from pathlib import Path

from fastapi.testclient import TestClient

from api.server import app, output_dir


client = TestClient(app)


def test_file_list_returns_relative_paths_only():
    session = output_dir / "session_test-file-api"
    session.mkdir(parents=True, exist_ok=True)
    (session / "report.md").write_text("report", encoding="utf-8")

    response = client.get("/api/files", params={"path": "session_test-file-api"})

    assert response.status_code == 200
    assert response.json()["files"][0]["path"] == "session_test-file-api/report.md"
    assert not Path(response.json()["files"][0]["path"]).is_absolute()


def test_file_api_rejects_traversal():
    assert "error" in client.get("/api/files", params={"path": "../"}).json()
    assert "error" in client.get("/api/download", params={"path": "C:/outside.txt"}).json()
