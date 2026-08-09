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


def test_numbered_env_file_is_supported(tmp_path):
    env_file = tmp_path / "(1).env"
    env_file.write_text(
        "LLM_QWEN_MAX=qwen-max\nOPENAI_API_KEY=test-key\nOPENAI_BASE_URL=https://example.invalid/v1\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=env_file)
    assert settings.model_configured is True


def test_dashscope_key_alias_configures_openai_compatible_model():
    settings = Settings(
        _env_file=None,
        llm_qwen_max="qwen-max",
        DASHSCOPE_API_KEY="test-key",
        openai_base_url="https://example.invalid/v1",
    )
    assert settings.model_configured is True


def test_active_model_prefers_explicit_then_qwen3():
    settings = Settings(
        _env_file=None,
        llm_model="explicit-model",
        llm_qwen_3="qwen3-model",
        llm_qwen_max="qwen-max-model",
    )
    assert settings.active_model == "explicit-model"

    qwen3_settings = Settings(
        _env_file=None,
        llm_qwen_3="qwen3-model",
        llm_qwen_max="qwen-max-model",
    )
    assert qwen3_settings.active_model == "qwen3-model"
