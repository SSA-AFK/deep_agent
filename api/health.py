"""Cached, public service-readiness checks."""

from __future__ import annotations

import time
from dataclasses import dataclass

from agent.llm import probe_model
from api.settings import Settings, get_settings


@dataclass
class ServiceRegistry:
    settings: Settings
    ttl_seconds: float = 30.0
    _cached_at: float = 0.0
    _cached_result: dict | None = None

    def check(self, *, refresh: bool = False) -> dict:
        if not refresh and self._cached_result and time.monotonic() - self._cached_at < self.ttl_seconds:
            return self._cached_result

        model_error = probe_model(self.settings)
        services = {
            "llm": {"status": "unavailable" if model_error else "available", "mode": "required"},
            "zhihu": {"status": "available" if self.settings.zhihu_access_secret else "unavailable", "mode": "live" if self.settings.zhihu_access_secret else "demo"},
            "mysql": {"status": "configured" if self.settings.mysql_user else "unavailable", "mode": "demo"},
            "word": {"status": "available", "mode": "local"},
        }
        result = {"overall": "blocked" if model_error else "ready", "services": services}
        if model_error:
            result["error"] = model_error.model_dump(mode="json")
        self._cached_at = time.monotonic()
        self._cached_result = result
        return result


_registry: ServiceRegistry | None = None


def get_service_registry() -> ServiceRegistry:
    global _registry
    if _registry is None:
        _registry = ServiceRegistry(get_settings())
    return _registry
