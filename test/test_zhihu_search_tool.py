import httpx
import pytest

from tools.contracts import DataMode, ToolStatus
from tools.zhihu_search_tool import ZHIHU_SEARCH_URL, ZhihuSearchClient
from tools.zhihu_search_tool import internet_search
from api.monitor import monitor


class StubResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"Code": 0, "Data": []}

    def json(self):
        return self._payload


def test_search_sends_bounded_request_and_normalizes_html(monkeypatch):
    captured = {}

    def fake_get(self, url, *, params, headers, timeout):
        captured.update(url=url, params=params, headers=headers, timeout=timeout)
        return StubResponse(payload={"Code": 0, "Data": [{
            "Title": "<em>Agent</em> research",
            "Url": "https://example.invalid/item",
            "ContentText": "A <em>safe</em> result",
            "ContentType": None,
            "Author": {"Name": "Author", "BadgeText": "verified"},
            "AuthorityLevel": 2,
            "VoteUpCount": 3,
            "CommentCount": 4,
            "EditTime": 5,
        }]})

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    result = ZhihuSearchClient("secret", timeout_seconds=3).search("agent research", count=99)

    assert captured["url"] == ZHIHU_SEARCH_URL
    assert captured["params"] == {"Query": "agent research", "Count": 20, "SearchDB": "all"}
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["headers"]["X-Request-Timestamp"].isdigit()
    assert captured["timeout"] == 3
    assert result.status is ToolStatus.SUCCESS
    assert result.mode is DataMode.LIVE
    assert result.items[0].title == "Agent research"
    assert result.items[0].snippet == "A safe result"
    assert result.items[0].metadata["content_type"] == "unknown"


def test_search_accepts_current_data_items_envelope(monkeypatch):
    def fake_get(self, *args, **kwargs):
        return StubResponse(payload={"Code": 0, "Data": {"Items": [{"Title": "Current response"}]}})

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    result = ZhihuSearchClient("secret").search("agent")

    assert result.status is ToolStatus.SUCCESS
    assert result.mode is DataMode.LIVE
    assert [item.title for item in result.items] == ["Current response"]


def test_live_search_records_public_source_urls(monkeypatch):
    def fake_get(self, *args, **kwargs):
        return StubResponse(payload={"Code": 0, "Data": [{"Title": "Source", "Url": "https://example.invalid/source"}]})

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    monkeypatch.setattr("tools.zhihu_search_tool.get_settings", lambda: type("Settings", (), {"zhihu_access_secret": "secret", "request_timeout_seconds": 3})())
    recorded = []
    monkeypatch.setattr("tools.zhihu_search_tool.monitor.record_source_urls", lambda urls, thread_id=None: recorded.extend(urls))

    internet_search.invoke({"query": "agent", "max_results": 1}, config={"configurable": {"thread_id": "test-citation"}})

    assert recorded == ["https://example.invalid/source"]


@pytest.mark.parametrize("response", [
    httpx.TimeoutException("timeout"),
    StubResponse(status_code=401),
    StubResponse(status_code=429),
    StubResponse(status_code=502),
    StubResponse(payload={"Code": 1}),
    StubResponse(payload=ValueError("invalid json")),
])
def test_search_degrades_to_deterministic_demo_data(monkeypatch, response):
    def fake_get(self, *args, **kwargs):
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    result = ZhihuSearchClient("secret", retries=0).search("agent")

    assert result.status is ToolStatus.DEGRADED
    assert result.mode is DataMode.DEMO
    assert result.items
    assert result.error is not None
    assert result.error.code


def test_internet_search_guards_single_real_search_per_thread(monkeypatch):
    """同一线程只放行一次真实检索，后续调用返回汇总提示且不重复请求。"""
    import json
    from api import context

    calls = {"n": 0}

    def fake_get(self, *args, **kwargs):
        calls["n"] += 1
        return StubResponse(payload={"Code": 0, "Data": [{"Title": "Once", "Url": "https://example.invalid/once"}]})

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    monkeypatch.setattr("tools.zhihu_search_tool.get_settings", lambda: type("Settings", (), {"zhihu_access_secret": "secret", "request_timeout_seconds": 3})())

    tid = "test-once-guard"
    monitor.clear_search_flag(tid)
    token = context.set_thread_context(tid)
    try:
        first = json.loads(internet_search.invoke({"query": "q", "max_results": 1}))
        second = json.loads(internet_search.invoke({"query": "q", "max_results": 1}))
    finally:
        context._thread_id_ctx.reset(token)

    assert first["status"] == "success"
    assert first["items"][0]["title"] == "Once"
    assert second["metadata"]["already_searched"] is True
    assert calls["n"] == 1
