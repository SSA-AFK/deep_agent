import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import api.server as server
from api.task_manager import TaskState, task_manager


def test_offline_task_websocket_feedback_files_and_export(monkeypatch, tmp_path):
    thread_id = "test-backend-e2e"
    monkeypatch.setattr(server, "output_dir", tmp_path)

    async def fake_agent(query: str, session_id: str) -> None:
        assert query == "compare agent platforms"
        session = server.output_dir / f"session_{session_id}"
        session.mkdir(parents=True, exist_ok=True)
        (session / "report.pdf").write_bytes(b"%PDF-1.4\n% offline fixture")
        await task_manager.transition(session_id, TaskState.SUCCEEDED, {"result": "Sourced offline result (demo)."})

    monkeypatch.setattr(server, "run_deep_agent", fake_agent)

    with TestClient(server.app) as client:
        created = client.post("/api/task", json={"query": "compare agent platforms", "thread_id": thread_id})
        assert created.status_code == 200

        with client.websocket_connect(f"/ws/{thread_id}") as websocket:
            websocket.send_text("ping")
            assert websocket.receive_json()["type"] == "pong"

        confirmed = client.post(f"/api/tasks/{thread_id}/confirm")
        assert confirmed.status_code == 200

        for _ in range(20):
            snapshot = client.get(f"/api/tasks/{thread_id}").json()
            if snapshot["state"] == "succeeded":
                break
            asyncio.run(asyncio.sleep(0.01))
        assert snapshot["result"] == "Sourced offline result (demo)."
        assert [event["sequence"] for event in snapshot["events"]] == sorted(event["sequence"] for event in snapshot["events"])

        files = client.get("/api/files", params={"path": f"session_{thread_id}"}).json()["files"]
        assert files[0]["path"] == f"session_{thread_id}/report.pdf"
        assert not Path(files[0]["path"]).is_absolute()

        assert client.post(f"/api/tasks/{thread_id}/feedback", json={"helpful": True}).json()["status"] == "recorded"
        assert client.post(f"/api/tasks/{thread_id}/export").json()["status"] == "recorded"
        downloaded = client.get("/api/download", params={"path": files[0]["path"]})
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF")

        analytics = (tmp_path / "analytics.jsonl").read_text(encoding="utf-8")
        for name in ("task_submitted", "plan_confirmed", "task_completed", "feedback_submitted", "report_exported"):
            assert f'"name":"{name}"' in analytics
