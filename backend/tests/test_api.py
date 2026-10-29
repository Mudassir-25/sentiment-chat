import json
import logging

from tests.conftest import SECRET, SID, chat, make_client


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_capabilities_local_only_without_key(client):
    c = client.get("/api/capabilities").json()
    assert c["engine"]["id"] == "tfidf-logreg+rules"
    assert c["local_requires_network"] is False
    assert all(p["configured"] is False for p in c["providers"])
    assert c["default_provider"] is None
    assert set(c["modes"]) == {"automatic", "local_only", "ai_enhanced"}


def test_capabilities_reports_fallback_engine_without_model(tmp_path):
    from app.nlp.sentiment import SentimentEngine
    c, _ = make_client(SentimentEngine.load(tmp_path / "missing.joblib"))
    j = c.get("/api/capabilities").json()
    assert j["engine"]["id"] == "rules-fallback" and j["engine"]["classifier_loaded"] is False
    assert chat(c, "I love this")["analysis"]["sentiment"]["engine"]["id"] == "rules-fallback"


def test_no_secrets_in_any_endpoint(ai_client):
    for path in ("/api/health", "/api/capabilities"):
        assert SECRET not in ai_client.get(path).text
    body = chat(ai_client, "hello there", mode="local_only")
    assert SECRET not in json.dumps(body)
    cap = ai_client.get("/api/capabilities").json()
    assert next(p for p in cap["providers"] if p["id"] == "openai")["configured"] is True
    assert "key" not in json.dumps(cap).lower().replace("keyboard", "")


def test_empty_and_whitespace_rejected(client):
    for m in ["", "   ", "\n\t"]:
        assert client.post("/api/chat", json={"session_id": SID, "message": m}).status_code == 422
        assert client.post("/api/analyze", json={"text": m}).status_code == 422


def test_length_limit(client):
    r = client.post("/api/chat", json={"session_id": SID, "message": "a" * 1001})
    assert r.status_code == 422 and "too long" in r.json()["detail"]


def test_invalid_session_and_mode_rejected(client):
    assert client.post("/api/chat", json={"session_id": "x", "message": "hi"}).status_code == 422
    assert client.post("/api/chat", json={"session_id": SID, "message": "hi", "mode": "bogus"}).status_code == 422
    assert client.delete("/api/sessions/bad!id").status_code == 422


def test_analyze_endpoint(client):
    j = client.post("/api/analyze", json={"text": "The movie was not bad."}).json()
    assert j["sentiment"]["label"] in ("positive", "neutral")
    assert "classifier" in j["sentiment"] and "rules" in j["sentiment"]


def test_chat_local_without_key(client):
    j = chat(client, "I finally passed my exam!")
    assert j["reply_source"] == "local" and j["provider"] is None and j["fallback"]["used"] is False
    assert j["analysis"]["sentiment"]["label"] == "positive"
    assert j["analysis"]["intent"]["intent"] == "good_news"
    assert "exam" in j["reply"].lower()


def test_failed_exam_is_not_congratulated(client):
    j = chat(client, "I studied for weeks and still failed.")
    assert j["analysis"]["sentiment"]["label"] == "negative"
    assert "congrat" not in j["reply"].lower()


def test_reply_relevance_uses_topic(client):
    j = chat(client, "I got into my first-choice course and I'm thrilled")
    assert j["analysis"]["sentiment"]["label"] == "positive"


def test_mixed_reply_mentions_both_sides(client):
    j = chat(client, "I'm happy about my result, but nervous about tomorrow.")
    assert "happy" in j["reply"] and "nervous" in j["reply"]


def test_followups_use_context(client):
    chat(client, "I passed my exam.")
    j = chat(client, "I'm really happy about it.")
    assert j["analysis"]["context"]["is_followup"] is True
    assert "exam" in j["analysis"]["context"]["continued_topics"]
    j3 = chat(client, "But I was scared yesterday.")
    assert j3["analysis"]["context"]["is_followup"] is True
    assert j3["analysis"]["context"]["previous_sentiment"] == "positive"


def test_session_isolation(client):
    chat(client, "I passed my exam.", sid="session-one-1111")
    j = chat(client, "I'm really happy about it.", sid="session-two-2222")
    assert j["analysis"]["context"]["turns_in_memory"] == 0
    assert j["analysis"]["context"]["continued_topics"] == []


def test_session_clear(client):
    chat(client, "I passed my exam.")
    assert client.delete(f"/api/sessions/{SID}").json()["cleared"] is True
    assert chat(client, "hello")["analysis"]["context"]["turns_in_memory"] == 0


def test_replies_vary(client):
    replies = {chat(client, "ok so the bus leaves at noon")["reply"] for _ in range(6)}
    assert len(replies) > 1


def test_crisis_message_gets_safe_reply_and_no_llm(ai_client):
    j = chat(ai_client, "I want to end my life", mode="ai_enhanced")
    assert j["safety_response"] is True and j["reply_source"] == "local"
    assert ai_client.fake.calls == 0


def test_raw_messages_not_logged(client, caplog):
    with caplog.at_level(logging.DEBUG, logger="sentiment_chat"):
        chat(client, "my very private sentence about Zebulon")
    assert "Zebulon" not in caplog.text


def test_analytics_reports_real_requests_and_failures_without_messages(client):
        private_text = "A private message about the uncommon word Caledonia"
        analyzed = client.post("/api/analyze", json={"text": "I feel happy about work"})
        assert analyzed.status_code == 200
        reply = chat(client, private_text, mode="local_only")
        assert reply["reply_source"] == "local"
        failed = client.post("/api/chat", json={"session_id": SID, "message": " "})
        assert failed.status_code == 422

        response = client.get("/api/analytics")
        assert response.status_code == 200
        metrics = response.json()
        assert metrics["total_requests"] == 3
        assert metrics["success_count"] == 2 and metrics["failure_count"] == 1
        assert metrics["fallback_count"] == 0 and metrics["provider_failure_count"] == 0
        assert metrics["average_latency_ms"] >= 0
        assert sum(metrics["sentiment_counts"].values()) == 2
        assert metrics["source_counts"]["local"] == 1
        assert metrics["mode_usage"]["local_only"] == 1
        assert metrics["activity"] and metrics["activity"][0]["requests"] == 3
        assert "Caledonia" not in response.text and private_text not in response.text
