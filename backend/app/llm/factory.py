"""Builds configured providers from settings and tracks their connection-test status."""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.llm.base import LLMProvider, ProviderError
from app.llm.providers import AnthropicProvider, GeminiProvider, GroqProvider, OllamaProvider, OpenAIProvider
from app.schemas import ProviderStatus

LABELS = {
    "openai": "OpenAI-compatible", "anthropic": "Anthropic", "groq": "Groq",
    "gemini": "Google Gemini", "ollama": "Ollama",
}


@dataclass
class _State:
    connection: str = "untested"
    last_error: str | None = None


class LLMRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.providers: dict[str, LLMProvider] = {}
        t = settings.llm_timeout_seconds
        if settings.openai_api_key.get_secret_value():
            self.providers["openai"] = OpenAIProvider(settings.openai_api_key, settings.openai_model, t,
                                                      settings.openai_base_url)
        if settings.anthropic_api_key.get_secret_value():
            self.providers["anthropic"] = AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model, t)
        if settings.groq_api_key.get_secret_value():
            self.providers["groq"] = GroqProvider(settings.groq_api_key, settings.groq_model, t)
        if settings.gemini_api_key.get_secret_value():
            self.providers["gemini"] = GeminiProvider(settings.gemini_api_key, settings.gemini_model, t)
        if settings.ollama_base_url:
            self.providers["ollama"] = OllamaProvider(settings.ollama_base_url, settings.ollama_model, t)
        self._state = {k: _State() for k in LABELS}

    @property
    def default_provider(self) -> str | None:
        pref = self.settings.llm_provider
        if pref in self.providers:
            return pref
        return next(iter(self.providers), None)

    def resolve(self, requested: str | None) -> LLMProvider | None:
        if requested:
            return self.providers.get(requested)
        return self.providers.get(self.default_provider or "")

    def status(self) -> list[ProviderStatus]:
        models = {
            "openai": self.settings.openai_model,
            "anthropic": self.settings.anthropic_model,
            "groq": self.settings.groq_model,
            "gemini": self.settings.gemini_model,
            "ollama": self.settings.ollama_model,
        }
        return [ProviderStatus(id=k, label=LABELS[k], configured=k in self.providers, model=models[k],
                               connection=self._state[k].connection,
                               last_error=self._state[k].last_error) for k in LABELS]

    def record_ok(self, pid: str) -> None:
        self._state[pid] = _State("ok")

    def record_error(self, pid: str, err: ProviderError) -> None:
        self._state[pid] = _State("failed", err.public_message)

    async def test(self, pid: str) -> ProviderStatus:
        prov = self.providers.get(pid)
        if prov is None:
            raise KeyError(pid)
        try:
            await prov.generate("Reply with the single word: ok", [{"role": "user", "content": "ping"}], max_tokens=5)
            self.record_ok(pid)
        except ProviderError as e:
            self.record_error(pid, e)
        return next(s for s in self.status() if s.id == pid)
