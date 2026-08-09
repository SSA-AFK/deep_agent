"""Typed, import-safe configuration for the API and external services."""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or the local `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    llm_qwen_max: str | None = Field(default=None, validation_alias="LLM_QWEN_MAX")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    zhihu_access_secret: str | None = Field(default=None, validation_alias="ZHIHU_ACCESS_SECRET")

    mysql_host: str = Field(default="localhost", validation_alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, validation_alias="MYSQL_PORT")
    mysql_user: str | None = Field(default=None, validation_alias="MYSQL_USER")
    mysql_password: str | None = Field(default=None, validation_alias="MYSQL_PASSWORD")
    mysql_database: str | None = Field(default=None, validation_alias="MYSQL_DATABASE")
    ragflow_api_key: str | None = Field(default=None, validation_alias="RAGFLOW_API_KEY")
    ragflow_api_url: str | None = Field(default=None, validation_alias="RAGFLOW_API_URL")

    cors_origins: list[str] = Field(default_factory=lambda: ["*"], validation_alias="CORS_ORIGINS")
    upload_max_files: int = Field(default=10, validation_alias="UPLOAD_MAX_FILES")
    upload_max_bytes: int = Field(default=20 * 1024 * 1024, validation_alias="UPLOAD_MAX_BYTES")
    request_timeout_seconds: float = Field(default=10.0, validation_alias="REQUEST_TIMEOUT_SECONDS")

    @property
    def model_configured(self) -> bool:
        return bool(self.llm_qwen_max and self.openai_api_key and self.openai_base_url)

    def public_summary(self) -> dict[str, object]:
        """Return configuration state without including credentials or full URLs."""
        return {
            "model_configured": self.model_configured,
            "model_name_configured": bool(self.llm_qwen_max),
            "openai_endpoint_host": _hostname(self.openai_base_url),
            "zhihu_configured": bool(self.zhihu_access_secret),
            "mysql_configured": bool(self.mysql_user and self.mysql_password and self.mysql_database),
            "mysql_host": self.mysql_host,
            "ragflow_configured": bool(self.ragflow_api_key and self.ragflow_api_url),
            "ragflow_endpoint_host": _hostname(self.ragflow_api_url),
        }


def _hostname(value: str | None) -> str | None:
    return urlparse(value).hostname if value else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
