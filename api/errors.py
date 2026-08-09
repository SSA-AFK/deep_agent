"""Stable, user-safe errors returned by API and tool boundaries."""

from pydantic import BaseModel


class PublicError(BaseModel):
    code: str
    message: str
    source: str
    user_action: str | None = None
    retryable: bool = False
