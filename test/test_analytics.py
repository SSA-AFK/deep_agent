from datetime import datetime, timezone

from analytics.events import ProductEvent
from analytics.events import append_event
from analytics.report import funnel


def test_funnel_counts_privacy_safe_events():
    events = [ProductEvent(name="task_submitted", task_id="task-1", timestamp=datetime.now(timezone.utc)), ProductEvent(name="task_completed", task_id="task-1", timestamp=datetime.now(timezone.utc), source_modes=["live", "demo"])]
    assert funnel(events)["task_completed"] == 1


def test_event_persistence_contains_metadata_only(tmp_path):
    path = tmp_path / "events.jsonl"
    append_event(path, ProductEvent(name="feedback_submitted", task_id="task-2", timestamp=datetime.now(timezone.utc)))
    content = path.read_text(encoding="utf-8")
    assert "feedback_submitted" in content
    assert "prompt" not in content
    assert "file_content" not in content
