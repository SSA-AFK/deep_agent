"""Privacy-safe product event contracts and local JSONL persistence."""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator


EventName = Literal[
    "task_submitted", "plan_confirmed", "task_completed", "task_failed",
    "feedback_submitted", "report_exported", "source_clicked",
    "follow_up_submitted", "task_retried",
]


class ProductEvent(BaseModel):
    name: EventName
    task_id: str
    timestamp: datetime
    source_modes: list[Literal["live", "demo"]] = []

    @field_validator("task_id")
    @classmethod
    def reject_sensitive_content(cls, value: str) -> str:
        if "/" in value or "\\" in value or len(value) > 100:
            raise ValueError("task_id must not contain content or paths")
        return value


def append_event(path: Path, event: ProductEvent) -> None:
    """Append contract-approved metadata without prompt or file content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(event.model_dump_json() + "\n")
