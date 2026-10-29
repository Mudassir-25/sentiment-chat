"""Runtime configuration. Secrets live only here (backend) and are never serialised to clients."""
from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    app_version: str = "1.0.0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_message_chars: int = 1000
    model_path: str = "models/sentiment.joblib"
    log_level: str = "INFO"

    # Optional LLM providers. Keys are optional; the app works without them.
    llm_provider: str = ""  # optional preferred default provider
    llm_timeout_seconds: float = 20.0
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_model: str = "claude-sonnet-4-6"
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.5-flash"
    ollama_base_url: str = ""
    ollama_model: str = "gemma3:1b"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_model_path(self) -> Path:
        p = Path(self.model_path)
        return p if p.is_absolute() else BACKEND_DIR / p

    def secret_values(self) -> list[str]:
        vals = [self.openai_api_key.get_secret_value(), self.anthropic_api_key.get_secret_value(),
                self.groq_api_key.get_secret_value(), self.gemini_api_key.get_secret_value()]
        return [v for v in vals if v]
