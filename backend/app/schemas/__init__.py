"""Typed API contracts shared by the NLP engine, orchestrator and routes."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Sentiment = Literal["positive", "neutral", "negative"]
Mode = Literal["automatic", "local_only", "ai_enhanced"]
SESSION_RE = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")


class Cue(BaseModel):
    text: str
    polarity: Literal["positive", "negative"]
    weight: float
    negated: bool = False
    source: Literal["rule"] = "rule"


class FeatureContribution(BaseModel):
    feature: str
    contribution: float


class ClassifierResult(BaseModel):
    """Output of the trained TF-IDF + Logistic Regression model only."""
    label: Sentiment
    probabilities: dict[str, float]
    top_features: list[FeatureContribution]


class RuleResult(BaseModel):
    """Output of the lexicon/rule layer only (negation, intensifiers, emoji, contrast)."""
    label: Sentiment
    probabilities: dict[str, float]
    positive_mass: float
    negative_mass: float
    cues: list[Cue]


class EngineInfo(BaseModel):
    id: Literal["tfidf-logreg+rules", "rules-fallback"]
    name: str
    classifier_loaded: bool
    note: str


class SentimentAnalysis(BaseModel):
    label: Sentiment
    confidence: float = Field(description="Model confidence estimate, not a calibrated probability.")
    probabilities: dict[str, float]
    mixed: bool
    uncertain: bool
    uncertainty_reasons: list[str]
    explanation: str
    engine: EngineInfo
    classifier: ClassifierResult | None
    rules: RuleResult
    truncated: bool = False


class IntentResult(BaseModel):
    intent: str
    ambiguous: bool
    secondary: list[str]
    evidence: list[str]


class Topic(BaseModel):
    phrase: str
    ref: str
    kind: Literal["noun_phrase", "keyword", "name", "activity"]
    from_context: bool = False


class ContextInfo(BaseModel):
    is_followup: bool
    previous_sentiment: Sentiment | None
    sentiment_shift: bool
    continued_topics: list[str]
    turns_in_memory: int


class Analysis(BaseModel):
    sentiment: SentimentAnalysis
    intent: IntentResult
    topics: list[Topic]
    topic_method: str = "lexical heuristics (determiner-led noun chunks, keyword list, capitalised names)"
    context: ContextInfo | None = None


class AnalyzeRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    mode: Mode = "automatic"
    provider: str | None = None

    @field_validator("session_id")
    @classmethod
    def _sid(cls, v: str) -> str:
        if not SESSION_RE.match(v):
            raise ValueError("session_id must be 8-64 chars of letters, digits, '-' or '_'")
        return v

    @field_validator("message")
    @classmethod
    def _msg(cls, v: str) -> str:
        return v.strip()


class Fallback(BaseModel):
    used: bool
    reason: str | None = None
    detail: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    reply_source: Literal["local", "llm"]
    provider: str | None
    mode_requested: Mode
    fallback: Fallback
    safety_response: bool = False
    analysis: Analysis


class ProviderStatus(BaseModel):
    id: str
    label: str
    configured: bool
    model: str
    connection: Literal["untested", "ok", "failed"]
    last_error: str | None = None


class Capabilities(BaseModel):
    version: str
    engine: EngineInfo
    modes: list[Mode]
    default_mode: Mode
    providers: list[ProviderStatus]
    default_provider: str | None
    max_message_chars: int
    local_requires_network: bool = False


class AnalyticsActivity(BaseModel):
    hour: str
    requests: int
    failures: int


class AnalyticsSnapshot(BaseModel):
    total_requests: int
    success_count: int
    failure_count: int
    fallback_count: int
    provider_failure_count: int
    average_latency_ms: float | None
    sentiment_counts: dict[Sentiment, int]
    source_counts: dict[str, int]
    provider_usage: dict[str, int]
    mode_usage: dict[str, int]
    activity: list[AnalyticsActivity]
    retention_limit: int
