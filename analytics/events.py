"""Privacy-safe product event contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


EventName = Literal["task_submitted", "plan_confirmed", "task_completed", "task_failed", "feedback_submitted", "report_exported"]


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
