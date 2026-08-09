from datetime import datetime, timezone

from analytics.events import ProductEvent
from analytics.report import funnel


def test_funnel_counts_privacy_safe_events():
    events = [ProductEvent(name="task_submitted", task_id="task-1", timestamp=datetime.now(timezone.utc)), ProductEvent(name="task_completed", task_id="task-1", timestamp=datetime.now(timezone.utc), source_modes=["live", "demo"])]
    assert funnel(events)["task_completed"] == 1
