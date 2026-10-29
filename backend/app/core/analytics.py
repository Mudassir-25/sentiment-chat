"""Bounded in-memory operational metrics. User messages and provider secrets are never retained."""
from __future__ import annotations

import json
import time
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Any

from app.schemas import AnalyticsActivity, AnalyticsSnapshot


class AnalyticsStore:
    def __init__(self, retention_limit: int = 2000) -> None:
        self.retention_limit = retention_limit
        self._events: deque[dict[str, Any]] = deque(maxlen=retention_limit)

    def record(self, path: str, status: int, elapsed_ms: float, body: bytes) -> None:
        analysis: dict[str, Any] = {}
        source = provider = mode = fallback_reason = None
        if status < 400:
            try:
                payload = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                payload = {}
            if isinstance(payload, dict):
                raw_analysis = payload.get("analysis", payload)
                analysis = raw_analysis if isinstance(raw_analysis, dict) else {}
                if path == "/api/chat":
                    source = payload.get("reply_source")
                    provider = payload.get("provider")
                    mode = payload.get("mode_requested")
                    fallback = payload.get("fallback")
                    if isinstance(fallback, dict) and fallback.get("used") is True:
                        fallback_reason = fallback.get("reason")
        raw_sentiment = analysis.get("sentiment")
        sentiment = raw_sentiment.get("label") if isinstance(raw_sentiment, dict) else None
        self._events.append({
            "timestamp": datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0),
            "success": status < 400,
            "latency_ms": max(0.0, elapsed_ms),
            "sentiment": sentiment if sentiment in ("positive", "neutral", "negative") else None,
            "source": source if source in ("local", "llm") else None,
            "provider": provider if isinstance(provider, str) and provider else ("local" if source == "local" else None),
            "mode": mode if isinstance(mode, str) else None,
            "fallback_reason": fallback_reason if isinstance(fallback_reason, str) else None,
        })

    def snapshot(self) -> AnalyticsSnapshot:
        events = list(self._events)
        successes = [event for event in events if event["success"]]
        sentiments = Counter(event["sentiment"] for event in successes if event["sentiment"])
        sources = Counter(event["source"] for event in successes if event["source"])
        providers = Counter(event["provider"] for event in successes if event["provider"])
        modes = Counter(event["mode"] for event in successes if event["mode"])
        hourly: dict[datetime, list[int]] = {}
        for event in events:
            counts = hourly.setdefault(event["timestamp"], [0, 0])
            counts[0] += 1
            counts[1] += int(not event["success"])
        return AnalyticsSnapshot(
            total_requests=len(events),
            success_count=len(successes),
            failure_count=len(events) - len(successes),
            fallback_count=sum(bool(event["fallback_reason"]) for event in successes),
            provider_failure_count=sum(
                event["fallback_reason"] not in (None, "no_provider_configured", "provider_not_configured")
                for event in successes
            ),
            average_latency_ms=round(sum(event["latency_ms"] for event in events) / len(events), 2) if events else None,
            sentiment_counts={name: sentiments[name] for name in ("positive", "neutral", "negative")},
            source_counts={name: sources[name] for name in ("local", "llm")},
            provider_usage=dict(sorted(providers.items())),
            mode_usage=dict(sorted(modes.items())),
            activity=[AnalyticsActivity(hour=hour.isoformat(), requests=counts[0], failures=counts[1])
                      for hour, counts in sorted(hourly.items())],
            retention_limit=self.retention_limit,
        )


class AnalyticsMiddleware:
    def __init__(self, app, metrics: AnalyticsStore) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope, receive, send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or path not in ("/api/chat", "/api/analyze"):
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status = 500
        response_body = bytearray()

        async def capture(message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body" and len(response_body) < 1_000_000:
                response_body.extend(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            self.metrics.record(path, status, (time.perf_counter() - started) * 1000, bytes(response_body))
