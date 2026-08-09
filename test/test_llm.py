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
