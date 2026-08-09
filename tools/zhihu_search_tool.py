"""Zhihu global-search adapter with deterministic demo fallback."""

from __future__ import annotations

import html
import re
import time
from typing import Any

import httpx
from langchain_core.tools import tool

from api.errors import PublicError
from api.monitor import monitor
from api.settings import get_settings
from tools.contracts import DataMode, SourceItem, ToolResult, ToolStatus
from tools.demo_sources import load_search_results


ZHIHU_SEARCH_URL = "https://developer.zhihu.com/api/v1/content/global_search"
_TAG_RE = re.compile(r"<[^>]+>")


class ZhihuSearchClient:
    def __init__(self, access_secret: str | None, *, timeout_seconds: float = 10.0, retries: int = 2):
        self.access_secret = access_secret
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    def search(self, query: str, *, count: int = 10, search_db: str = "all") -> ToolResult:
        started = time.monotonic()
        if not self.access_secret:
            return self._degraded("ZHIHU_NOT_CONFIGURED", "Zhihu search is not configured.", started)

        params = {"Query": query, "Count": max(1, min(count, 20)), "SearchDB": search_db or "all"}
        headers = {
            "Authorization": f"Bearer {self.access_secret}",
            "X-Request-Timestamp": str(int(time.time())),
        }
        for attempt in range(self.retries + 1):
            try:
                with httpx.Client() as client:
                    response = client.get(ZHIHU_SEARCH_URL, params=params, headers=headers, timeout=self.timeout_seconds)
            except httpx.RequestError:
                return self._degraded("ZHIHU_NETWORK_ERROR", "Zhihu search is temporarily unavailable.", started)

            if response.status_code in {429} or response.status_code >= 500:
                if attempt < self.retries:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                return self._degraded("ZHIHU_UPSTREAM_ERROR", "Zhihu search is temporarily unavailable.", started, retryable=True)
            if response.status_code >= 400:
                return self._degraded("ZHIHU_AUTH_OR_REQUEST_FAILED", "Zhihu search request was rejected.", started)

            try:
                payload = response.json()
            except (ValueError, TypeError):
                return self._degraded("ZHIHU_INVALID_RESPONSE", "Zhihu search returned an invalid response.", started)
            if not isinstance(payload, dict) or payload.get("Code") != 0 or not isinstance(payload.get("Data"), list):
                return self._degraded("ZHIHU_API_ERROR", "Zhihu search returned no usable results.", started)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                source="zhihu_global_search",
                mode=DataMode.LIVE,
                duration_ms=_duration_ms(started),
                items=[_normalize(item) for item in payload["Data"] if isinstance(item, dict)],
            )

        return self._degraded("ZHIHU_UPSTREAM_ERROR", "Zhihu search is temporarily unavailable.", started, retryable=True)

    def _degraded(self, code: str, message: str, started: float, *, retryable: bool = False) -> ToolResult:
        return ToolResult(
            status=ToolStatus.DEGRADED,
            source="zhihu_global_search",
            mode=DataMode.DEMO,
            duration_ms=_duration_ms(started),
            items=load_search_results(),
            error=PublicError(code=code, message=message, source="zhihu_global_search", retryable=retryable),
        )


def _normalize(item: dict[str, Any]) -> SourceItem:
    author = item.get("Author") or {}
    return SourceItem(
        title=_clean(item.get("Title") or "Untitled Zhihu result"),
        url=item.get("Url") or item.get("URL") or None,
        snippet=_clean(item.get("ContentText") or ""),
        source="zhihu_global_search",
        metadata={
            "content_type": item.get("ContentType") or "unknown",
            "author_name": author.get("Name") or item.get("AuthorName") or "unknown",
            "author_badge_text": author.get("BadgeText") or item.get("AuthorBadgeText") or "",
            "authority_level": item.get("AuthorityLevel") or 0,
            "vote_up_count": item.get("VoteUpCount") or 0,
            "comment_count": item.get("CommentCount") or 0,
            "edit_time": item.get("EditTime") or 0,
        },
    )


def _clean(value: object) -> str:
    return html.unescape(_TAG_RE.sub("", str(value))).strip()


def _duration_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


@tool
def internet_search(query: str, max_results: int = 10) -> str:
    """Search public information through Zhihu global search."""
    monitor.report_tool("知乎全网搜索", {"query": query, "max_results": max_results})
    settings = get_settings()
    result = ZhihuSearchClient(
        settings.zhihu_access_secret,
        timeout_seconds=settings.request_timeout_seconds,
    ).search(query, count=max_results)
    return result.model_dump_json()
