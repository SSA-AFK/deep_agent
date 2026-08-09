"""Common structured results for live and deterministic demo tools."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from api.errors import PublicError


class ToolStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"


class DataMode(StrEnum):
    LIVE = "live"
    DEMO = "demo"


class SourceItem(BaseModel):
    title: str
    source: str
    url: str | None = None
    snippet: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    status: ToolStatus
    source: str
    mode: DataMode
    duration_ms: int = Field(ge=0)
    items: list[SourceItem] = Field(default_factory=list)
    error: PublicError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
