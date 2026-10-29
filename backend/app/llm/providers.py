"""OpenAI-compatible, Anthropic and local Ollama adapters over httpx (no vendor SDK needed)."""
from __future__ import annotations

import httpx
from pydantic import SecretStr

from app.llm.base import LLMProvider, ProviderError, classify_status


class _HttpProvider(LLMProvider):
    def __init__(self, key: SecretStr | None, model: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None):
        self._key = key
        self.model = model
        self._timeout = timeout
        self._transport = transport

    async def _request(self, method: str, url: str, headers: dict | None = None, body: dict | None = None) -> dict:
        headers = headers or {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as c:
                if method.upper() == "GET":
                    r = await c.get(url, headers=headers)
                else:
                    r = await c.post(url, headers=headers, json=body or {})
        except httpx.TimeoutException:
            raise ProviderError("timeout", "The provider request timed out.") from None
        except httpx.HTTPError:
            raise ProviderError("network", "Could not reach the provider.") from None
        if r.status_code >= 400:
            raise classify_status(r.status_code)
        try:
            return r.json()
        except ValueError:
            raise ProviderError("provider_error", "The provider returned invalid JSON.") from None

    async def _post(self, url: str, headers: dict, body: dict) -> dict:
        return await self._request("POST", url, headers, body)


class OpenAIProvider(_HttpProvider):
    id, label = "openai", "OpenAI-compatible"

    def __init__(self, key, model, timeout, base_url="https://api.openai.com/v1", transport=None):
        super().__init__(key, model, timeout, transport)
        self._base = base_url.rstrip("/")

    async def generate(self, system, messages, max_tokens=300):
        data = await self._post(
            f"{self._base}/chat/completions",
            {"Authorization": "Bearer " + self._key.get_secret_value()},
            {"model": self.model, "max_tokens": max_tokens,
             "messages": [{"role": "system", "content": system}, *messages]},
        )
        try:
            return str(data["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError):
            raise ProviderError("provider_error", "Unexpected provider response shape.") from None


class AnthropicProvider(_HttpProvider):
    id, label = "anthropic", "Anthropic"

    async def generate(self, system, messages, max_tokens=300):
        data = await self._post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self._key.get_secret_value(), "anthropic-version": "2023-06-01"},
            {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": messages},
        )
        try:
            return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError, AttributeError):
            raise ProviderError("provider_error", "Unexpected provider response shape.") from None


class GroqProvider(OpenAIProvider):
    id, label = "groq", "Groq"

    def __init__(self, key: SecretStr, model: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None):
        super().__init__(key, model, timeout, "https://api.groq.com/openai/v1", transport)


class OllamaProvider(_HttpProvider):
    id, label = "ollama", "Ollama"

    def __init__(self, base_url: str, model: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None):
        super().__init__(None, model, timeout, transport)
        self._base = base_url.rstrip("/")

    async def list_models(self) -> list[str]:
        data = await self._request("GET", f"{self._base}/api/tags")
        models = data.get("models", []) if isinstance(data, dict) else []
        return [str(item.get("name", "")) for item in models if isinstance(item, dict) and item.get("name")]

    async def generate(self, system, messages, max_tokens=300):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        data = await self._post(f"{self._base}/api/chat", {}, payload)
        try:
            content = data["message"]["content"]
            if isinstance(content, list):
                return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
            return str(content or "")
        except (KeyError, TypeError, AttributeError):
            raise ProviderError("provider_error", "Unexpected Ollama response shape.") from None


class GeminiProvider(_HttpProvider):
    id, label = "gemini", "Google Gemini"

    def __init__(self, key: SecretStr, model: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None):
        super().__init__(key, model, timeout, transport)
        self._base = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, system, messages, max_tokens=300):
        contents = [
            {"role": "model" if message["role"] == "assistant" else "user",
             "parts": [{"text": message["content"]}]}
            for message in messages
        ]
        data = await self._post(
            f"{self._base}/models/{self.model}:generateContent",
            {"x-goog-api-key": self._key.get_secret_value()},
            {"systemInstruction": {"parts": [{"text": system}]},
             "contents": contents, "generationConfig": {"maxOutputTokens": max_tokens}},
        )
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
        except (KeyError, IndexError, TypeError):
            raise ProviderError("provider_error", "Unexpected Gemini response shape.") from None
