from utils.citations import append_source_links, render_public_source_fallback, requests_public_sources
from api.monitor import monitor


def test_append_source_links_preserves_unique_tool_urls():
    answer = append_source_links("结论", ['{"url":"https://example.com/a"}', "https://example.com/a https://example.com/b"])

    assert answer.count("https://example.com/a") == 1
    assert answer.count("https://example.com/b") == 1
    assert "### 来源链接" in answer


def test_append_source_links_leaves_answers_without_urls_unchanged():
    assert append_source_links("结论", ["无链接工具结果"]) == "结论"


def test_monitor_returns_urls_from_child_task_scope():
    monitor.clear_source_urls("test-parent")
    monitor.record_source_urls(["https://example.com/source"], thread_id="test-parent:zhihu")

    assert monitor.take_source_urls("test-parent") == ["https://example.com/source"]


def test_requests_public_sources_only_for_explicit_source_requests():
    assert requests_public_sources("检索公开信息并附来源链接") is True
    assert requests_public_sources("总结我上传的资料") is False


def test_render_public_source_fallback_keeps_urls():
    answer = render_public_source_fallback([("Source", "Summary", "https://example.com/source")])

    assert "Agent" in answer
    assert "https://example.com/source" in answer
