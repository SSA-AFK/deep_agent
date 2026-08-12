from agent.llm import _build_model
from api.settings import Settings


def test_deepseek_model_disables_thinking_for_tool_compatibility(monkeypatch):
    captured = {}

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("agent.llm.init_chat_model", fake_init_chat_model)
    _build_model(Settings(_env_file=None, deepseek_api_key="test-key"))

    assert captured["model"] == "deepseek-v4-flash"
    assert captured["extra_body"] == {"thinking": {"type": "disabled"}}


def test_explicit_qwen_model_via_dashscope_does_not_get_deepseek_thinking_body(monkeypatch):
    captured = {}

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("agent.llm.init_chat_model", fake_init_chat_model)
    _build_model(
        Settings(
            _env_file=None,
            llm_model="qwen3.8-max",
            openai_api_key="dashscope-key",
            openai_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            # DeepSeek key also present – must not leak into DashScope requests
            deepseek_api_key="deepseek-key",
        )
    )

    assert captured["model"] == "qwen3.8-max"
    assert captured["api_key"] == "dashscope-key"
    assert captured["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert "extra_body" not in captured


def test_qwen3_candidate_also_skips_deepseek_thinking_body(monkeypatch):
    captured = {}

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("agent.llm.init_chat_model", fake_init_chat_model)
    _build_model(
        Settings(
            _env_file=None,
            deepseek_api_key=None,
            llm_qwen_3="qwen3-32b",
            openai_api_key="dashscope-key",
            openai_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    )

    assert captured["model"] == "qwen3-32b"
    assert "extra_body" not in captured
