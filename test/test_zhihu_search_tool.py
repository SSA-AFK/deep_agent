import httpx
import pytest

from tools.contracts import DataMode, ToolStatus
from tools.zhihu_search_tool import ZHIHU_SEARCH_URL, ZhihuSearchClient


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
