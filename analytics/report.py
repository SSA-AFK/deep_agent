from collections import Counter

from analytics.events import ProductEvent


def funnel(events: list[ProductEvent]) -> dict[str, int]:
    counts = Counter(event.name for event in events)
    return {name: counts[name] for name in ("task_submitted", "plan_confirmed", "task_completed", "feedback_submitted", "report_exported")}
