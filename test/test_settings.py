from api.settings import Settings


def test_public_summary_never_exposes_secrets():
    settings = Settings(
        _env_file=None,
        llm_qwen_max="qwen-max",
        openai_api_key="model-secret",
        openai_base_url="https://example.invalid/v1",
        zhihu_access_secret="search-secret",
    )

    summary = str(settings.public_summary())

    assert "model-secret" not in summary
    assert "search-secret" not in summary
    assert settings.model_configured is True


def test_missing_model_key_is_not_ready(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    settings = Settings(_env_file=None, llm_qwen_max="qwen-max")

    assert settings.model_configured is False
