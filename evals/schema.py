"""Validation contracts for safe, reproducible Agent evaluations."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


Category = Literal["network", "database", "multi_agent", "ambiguous_error"]
_UNSAFE_MARKERS = ("sk-", "api_key=", "password=", "c:\\users\\", "/home/", "e:\\")


def _safe_text(value: str) -> str:
    if any(marker in value.lower() for marker in _UNSAFE_MARKERS):
        raise ValueError("Evaluation content must not contain secrets or absolute paths.")
    return value


class EvalCase(BaseModel):
    id: str
    category: Category
    prompt: str
    expected_agents: list[str] = Field(min_length=1)
    required_facts: list[str] = Field(min_length=1)
    forbidden_behavior: list[str] = Field(min_length=1)
    grading_notes: str

    @field_validator("id", "prompt", "grading_notes")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _safe_text(value)


class AgentTrace(BaseModel):
    agent: str
    tool: str | None = None
    source_mode: Literal["live", "demo"] | None = None
    duration_ms: int = Field(ge=0)


class EvalRun(BaseModel):
    case_id: str
    prompt_version: Literal["v1", "v2", "v3"]
    completed: bool
    traces: list[AgentTrace] = Field(default_factory=list)
    answer: str = ""
    duration_ms: int = Field(ge=0)
    error_code: str | None = None
    error_message: str | None = None


class GradeResult(BaseModel):
    case_id: str
    intent_correct: bool
    route_correct: bool
    required_fact_coverage: float = Field(ge=0, le=1)
    citation_supported: bool
    score: float = Field(ge=0, le=5)
