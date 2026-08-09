from fastapi.testclient import TestClient

from api.server import app


client = TestClient(app)


def test_task_requires_confirmation_before_running():
    created = client.post("/api/task", json={"query": "research", "thread_id": "test-lifecycle"})
    assert created.status_code == 200
    assert created.json()["status"] == "waiting_confirmation"

    snapshot = client.get("/api/tasks/test-lifecycle")
    assert snapshot.json()["state"] == "waiting_confirmation"

    cancelled = client.post("/api/tasks/test-lifecycle/cancel")
    assert cancelled.json()["status"] == "cancelled"
