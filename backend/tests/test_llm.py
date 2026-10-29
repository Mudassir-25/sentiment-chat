import asyncio
import logging

import httpx
import pytest
from pydantic import SecretStr

from app.llm.base import ProviderError
from app.llm.prompt import sanitize
from app.llm.providers import AnthropicProvider, GeminiProvider, GroqProvider, OllamaProvider, OpenAIProvider
from tests.conftest import SECRET, FakeProvider, chat, make_client

KEY = SecretStr(SECRET)


def run(coro):
    return asyncio.run(coro)


def openai_with(handler):
    return OpenAIProvider(KEY, "m", 5, transport=httpx.MockTransport(handler))


# ---- provider adapters (mock transport; no real network) ---------------------
def test_openai_success_and_auth_header():
    seen = {}

    def h(req):
        seen["auth"] = req.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi!"}}]})

    assert run(openai_with(h).generate("s", [{"role": "user", "content": "x"}])) == "hi!"
    assert seen["auth"].startswith("Bearer " ) and seen["auth"].endswith(SECRET)


@pytest.mark.parametrize("status,cat", [(401, "invalid_key"), (403, "invalid_key"), (429, "rate_limited"),
                                        (500, "provider_error")])
def test_openai_error_categories(status, cat):
    p = openai_with(lambda r: httpx.Response(status, json={"error": SECRET}))
    with pytest.raises(ProviderError) as e:
        run(p.generate("s", []))
    assert e.value.category == cat and SECRET not in e.value.public_message


def test_groq_uses_chat_completions_api():
    def h(req):
        assert req.url.host == "api.groq.com"
        assert req.url.path == "/openai/v1/chat/completions"
        assert req.headers["authorization"].startswith("Bearer " ) and req.headers["authorization"].endswith(SECRET)
        assert req.read() and b'"model":"llama-model"' in req.content
        return httpx.Response(200, json={"choices": [{"message": {"content": "groq reply"}}]})

    p = GroqProvider(KEY, "llama-model", 5, transport=httpx.MockTransport(h))
    assert run(p.generate("system", [{"role": "user", "content": "hello"}])) == "groq reply"


def test_groq_rate_limit_is_reported_safely():
    p = GroqProvider(KEY, "llama-model", 5,
                     transport=httpx.MockTransport(lambda req: httpx.Response(429, text=SECRET)))
    with pytest.raises(ProviderError) as error:
        run(p.generate("system", []))
    assert error.value.category == "rate_limited"
    assert SECRET not in error.value.public_message


def test_gemini_uses_generate_content_api_without_query_secret():
    def h(req):
        assert req.url.host == "generativelanguage.googleapis.com"
        assert req.url.path == "/v1beta/models/gemini-test:generateContent"
        assert req.url.query == b""
        assert req.headers["x-goog-api-key"] == SECRET
        payload = req.read().decode()
        assert '"systemInstruction"' in payload and '"maxOutputTokens":17' in payload
        assert '"role":"model"' in payload
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "gemini "}, {"text": "reply"}]}}]})

    p = GeminiProvider(KEY, "gemini-test", 5, transport=httpx.MockTransport(h))
    messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "previous"}]
    assert run(p.generate("system", messages, max_tokens=17)) == "gemini reply"


def test_gemini_rejects_bad_credentials_without_leaking_response():
    p = GeminiProvider(KEY, "gemini-test", 5,
                       transport=httpx.MockTransport(lambda req: httpx.Response(401, text=SECRET)))
    with pytest.raises(ProviderError) as error:
        run(p.generate("system", []))
    assert error.value.category == "invalid_key"
    assert SECRET not in error.value.public_message


def test_ollama_chat_api():
    def h(req):
        assert req.url.path == "/api/chat"
        assert req.headers.get("authorization") is None
        assert req.read() and b'"model":"local-model"' in req.content
        return httpx.Response(200, json={"message": {"content": "local reply"}})

    p = OllamaProvider("http://ollama.test", "local-model", 5, transport=httpx.MockTransport(h))
    assert run(p.generate("system", [{"role": "user", "content": "hello"}])) == "local reply"


def test_ollama_unavailable_model_has_safe_message():
    p = OllamaProvider("http://ollama.test", "missing-model", 5,
                       transport=httpx.MockTransport(lambda req: httpx.Response(404)))
    with pytest.raises(ProviderError) as error:
        run(p.generate("system", []))
    assert error.value.category == "model_unavailable"
    assert "model name" in error.value.public_message


def test_provider_model_and_request_errors_are_safe():
    for status, category in ((404, "model_unavailable"), (400, "invalid_request")):
        p = openai_with(lambda req: httpx.Response(status, text=SECRET))
        with pytest.raises(ProviderError) as error:
            run(p.generate("system", []))
        assert error.value.category == category
        assert SECRET not in error.value.public_message


def test_timeout_and_network_errors():
    def boom(exc):
        def h(req):
            raise exc
        return h

    with pytest.raises(ProviderError) as e:
        run(openai_with(boom(httpx.ReadTimeout("t"))).generate("s", []))
    assert e.value.category == "timeout"
    with pytest.raises(ProviderError) as e:
        run(openai_with(boom(httpx.ConnectError("c"))).generate("s", []))
    assert e.value.category == "network"


def test_malformed_response_shape():
    with pytest.raises(ProviderError):
        run(openai_with(lambda r: httpx.Response(200, json={"nope": 1})).generate("s", []))


def test_anthropic_success():
    def h(req):
        assert req.headers["x-api-key"] == SECRET
        return httpx.Response(200, json={"content": [{"type": "text", "text": "hello"}]})

    p = AnthropicProvider(KEY, "m", 5, transport=httpx.MockTransport(h))
    assert run(p.generate("s", [{"role": "user", "content": "x"}])) == "hello"


def test_sanitize():
    assert sanitize("<script>x</script>hi\x00") == "xhi"
    assert len(sanitize("word " * 1000)) <= 905
    assert sanitize("   ") == ""


# ---- mode selection ----------------------------------------------------------
def test_missing_key_runs_local_in_every_mode(client):
    for mode in ("automatic", "local_only"):
        j = chat(client, "I feel great today", mode=mode)
        assert j["reply_source"] == "local" and j["fallback"]["used"] is False
    j = chat(client, "I feel great today", mode="ai_enhanced")
    assert j["reply_source"] == "local" and j["fallback"]["reason"] == "no_provider_configured"


def test_local_only_never_calls_llm(ai_client):
    for m in ["hi", "I failed", "thanks"]:
        j = chat(ai_client, m, mode="local_only")
        assert j["reply_source"] == "local" and j["fallback"]["used"] is False
    assert ai_client.fake.calls == 0


@pytest.mark.parametrize("mode", ["automatic", "ai_enhanced"])
def test_ai_mode_uses_provider(ai_client, mode):
    j = chat(ai_client, "I passed my exam!", mode=mode)
    assert j["reply_source"] == "llm" and j["provider"] == "openai" and j["fallback"]["used"] is False
    assert j["reply"] == "AI reply about your day."
    assert ai_client.fake.calls == 1


def test_prompt_contains_analysis_hints_and_context(ai_client):
    chat(ai_client, "I passed my exam!")
    chat(ai_client, "I'm happy about it")
    msgs = ai_client.fake.last_messages
    assert msgs[-1]["role"] == "user" and "analysis hints" in msgs[-1]["content"]
    assert any(m["role"] == "assistant" for m in msgs)  # recent context passed


@pytest.mark.parametrize("cat", ["invalid_key", "timeout", "rate_limited", "network", "provider_error"])
def test_provider_failure_falls_back_to_local(ai_client, cat):
    ai_client.fake.error = ProviderError(cat, "safe message")
    j = chat(ai_client, "I passed my exam!", mode="ai_enhanced")
    assert j["reply_source"] == "local" and j["provider"] is None
    assert j["fallback"] == {"used": True, "reason": cat, "detail": "safe message"}
    st = next(p for p in ai_client.get("/api/capabilities").json()["providers"] if p["id"] == "openai")
    assert st["connection"] == "failed"
    metrics = ai_client.get("/api/analytics").json()
    assert metrics["success_count"] == 1 and metrics["failure_count"] == 0
    assert metrics["fallback_count"] == 1 and metrics["provider_failure_count"] == 1
    assert metrics["source_counts"]["local"] == 1


def test_empty_llm_reply_falls_back(ai_client):
    ai_client.fake.reply = "   "
    j = chat(ai_client, "hello", mode="automatic")
    assert j["reply_source"] == "local" and j["fallback"]["reason"] == "empty_response"


def test_success_marks_connection_ok_not_just_configured(ai_client):
    def status():
        return next(p for p in ai_client.get("/api/capabilities").json()["providers"] if p["id"] == "openai")

    assert status()["configured"] and status()["connection"] == "untested"
    chat(ai_client, "hello", mode="automatic")
    assert status()["connection"] == "ok"


def test_connection_test_endpoint(ai_client):
    r = ai_client.post("/api/llm/openai/test")
    assert r.status_code == 200 and r.json()["connection"] == "ok"
    ai_client.fake.error = ProviderError("invalid_key", "The provider rejected the API key.")
    r = ai_client.post("/api/llm/openai/test").json()
    assert r["connection"] == "failed" and "rejected" in r["last_error"]
    assert ai_client.post("/api/llm/anthropic/test").status_code == 404


def test_capabilities_list_providers_without_exposing_credentials(client):
    status = client.get("/api/capabilities").json()
    providers = {provider["id"]: provider for provider in status["providers"]}
    assert set(providers) == {"openai", "anthropic", "groq", "gemini", "ollama"}
    assert all(not provider["configured"] for provider in providers.values())
    assert client.post("/api/llm/groq/test").status_code == 404
    assert client.post("/api/llm/gemini/test").status_code == 404


def test_explicit_unconfigured_provider_does_not_use_another_provider(trained_engine):
    client, _ = make_client(trained_engine, openai_api_key=SECRET)
    response = chat(client, "hello", mode="ai_enhanced", provider="gemini")
    assert response["reply_source"] == "local"
    assert response["provider"] is None
    assert response["fallback"]["reason"] == "provider_not_configured"


def test_secret_never_logged_on_failure(trained_engine, caplog):
    c, app = make_client(trained_engine, openai_api_key=SECRET)
    app.state.orchestrator.registry.providers["openai"] = OpenAIProvider(
        KEY, "m", 5, transport=httpx.MockTransport(lambda r: httpx.Response(401, text=SECRET)))
    with caplog.at_level(logging.DEBUG, logger="sentiment_chat"):
        j = chat(c, "hello", mode="ai_enhanced")
    assert j["fallback"]["reason"] == "invalid_key"
    assert SECRET not in caplog.text and SECRET not in str(j)


def test_provider_preference_and_selection(trained_engine):
    c, app = make_client(trained_engine, openai_api_key="k1-aaaaaaaa", anthropic_api_key="k2-bbbbbbbb",
                         llm_provider="anthropic")
    reg = app.state.orchestrator.registry
    assert reg.default_provider == "anthropic"
    assert reg.resolve("openai").id == "openai"
