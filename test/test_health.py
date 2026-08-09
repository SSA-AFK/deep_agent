from api.health import ServiceRegistry
from api.errors import PublicError
from api.settings import Settings


def test_unconfigured_model_blocks_health(monkeypatch):
    for name in ("LLM_QWEN_MAX", "OPENAI_API_KEY", "OPENAI_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    monkeypatch.setattr("api.health.probe_model", lambda _: PublicError(code="LLM_NOT_CONFIGURED", message="missing", source="llm"))

    result = ServiceRegistry(settings).check()

    assert result["overall"] == "blocked"
    assert result["services"]["llm"]["status"] == "unavailable"
    assert "ragflow" not in result["services"]


def test_health_result_is_cached(monkeypatch):
    settings = Settings(_env_file=None, llm_qwen_max="model", openai_api_key="key", openai_base_url="https://example.invalid")
    calls = 0

    def successful_probe(_):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr("api.health.probe_model", successful_probe)
    registry = ServiceRegistry(settings)

    assert registry.check()["overall"] == "ready"
    assert registry.check()["overall"] == "ready"
    assert calls == 1
