"""Provider adapter interface. Add a provider by subclassing LLMProvider and registering it in factory.py."""
from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Safe-to-display failure. Never contains keys or raw provider bodies."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.public_message = message


class LLMProvider(ABC):
    id: str
    label: str
    model: str

    @abstractmethod
    async def generate(self, system: str, messages: list[dict[str, str]], max_tokens: int = 300) -> str:
        """Return the assistant text or raise ProviderError."""


def classify_status(status: int) -> ProviderError:
    if status in (401, 403):
        return ProviderError("invalid_key", "The provider rejected the API key.")
    if status == 429:
        return ProviderError("rate_limited", "The provider rate limit was reached.")
    if status in (408, 504):
        return ProviderError("timeout", "The provider request timed out.")
    if status == 404:
        return ProviderError("model_unavailable", "The provider could not find this model. Check the configured model name.")
    if status == 400:
        return ProviderError("invalid_request", "The provider rejected the request. Check the configured model and request limits.")
    if status >= 500:
        return ProviderError("provider_error", "The provider had a server error.")
    return ProviderError("provider_error", f"The provider returned HTTP {status}.")
