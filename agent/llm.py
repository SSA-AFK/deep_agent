"""Lazy construction and readiness probing for the required chat model."""

from functools import lru_cache

from langchain.chat_models import init_chat_model

from api.errors import PublicError
from api.settings import Settings, get_settings


@lru_cache
def _get_default_model():
    return _build_model(get_settings())


def get_model(settings: Settings | None = None):
    """Create the chat model only when an Agent needs it."""
    return _get_default_model() if settings is None else _build_model(settings)


def _build_model(settings: Settings):
    if not settings.model_configured:
        raise RuntimeError("LLM is not configured")
    options = {}
    # Only disable thinking mode when the active route is actually DeepSeek.
    # An explicit LLM_MODEL override (e.g. qwen3.8-max via DashScope) must not
    # inherit DeepSeek-specific request shapes just because DEEPSEEK_API_KEY is
    # also present in the environment.
    using_deepseek_route = (
        settings.deepseek_api_key
        and not settings.llm_model
        and settings.active_model == settings.deepseek_model
        and settings.active_base_url == settings.deepseek_base_url
        and settings.active_api_key == settings.deepseek_api_key
    )
    if using_deepseek_route:
        options["extra_body"] = {"thinking": {"type": "disabled"}}
    return init_chat_model(
        model=settings.active_model,
        model_provider="openai",
        api_key=settings.active_api_key,
        base_url=settings.active_base_url,
        **options,
    )


def probe_model(settings: Settings | None = None) -> PublicError | None:
    """Perform a minimal request and return only a public, sanitized error."""
    settings = settings or get_settings()
    if not settings.model_configured:
        return PublicError(
            code="LLM_NOT_CONFIGURED",
            message="The required language model is not configured.",
            source="llm",
            user_action="Configure the model credentials and endpoint.",
        )
    try:
        get_model(settings).invoke("ping")
    except Exception:
        return PublicError(
            code="LLM_AUTH_FAILED",
            message="The language model could not be authenticated or reached.",
            source="llm",
            user_action="Check the model configuration and try again.",
        )
    return None
