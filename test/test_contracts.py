import json

from api.errors import PublicError
from tools.contracts import DataMode, SourceItem, ToolResult, ToolStatus


def test_contract_enums_and_json_serialization():
    assert [status.value for status in ToolStatus] == ["success", "failed", "degraded"]
    assert [mode.value for mode in DataMode] == ["live", "demo"]

    result = ToolResult(
        status=ToolStatus.SUCCESS,
        source="zhihu",
        mode=DataMode.LIVE,
        duration_ms=12,
        items=[SourceItem(title="Source", source="zhihu", url="https://example.invalid")],
    )

    assert json.loads(result.model_dump_json())["items"][0]["title"] == "Source"


def test_failed_result_has_no_items_and_retryable_error():
    error = PublicError(
        code="UPSTREAM_TIMEOUT",
        message="The search service timed out.",
        retryable=True,
        source="zhihu",
    )
    result = ToolResult(
        status=ToolStatus.FAILED,
        source="zhihu",
        mode=DataMode.LIVE,
        duration_ms=0,
        error=error,
    )

    assert result.items == []
    assert result.error is not None
    assert result.error.retryable is True
    assert result.model_dump(mode="json")["error"]["code"] == "UPSTREAM_TIMEOUT"
