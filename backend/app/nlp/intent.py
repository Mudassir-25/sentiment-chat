"""Table-driven intent detection: weighted regex rules plus a small sentiment modifier."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.nlp.preprocessing import Processed
from app.schemas import IntentResult, SentimentAnalysis

INTENTS = ["greeting", "farewell", "gratitude", "question", "good_news", "frustration", "sadness_stress",
           "excitement", "encouragement", "general", "unknown"]
PRIORITY = ["encouragement", "sadness_stress", "frustration", "good_news", "excitement", "gratitude",
            "farewell", "greeting", "question"]


@dataclass(frozen=True)
class Rule:
    intent: str
    name: str
    pattern: re.Pattern
    weight: float


def _r(intent: str, name: str, pat: str, w: float) -> Rule:
    return Rule(intent, name, re.compile(pat, re.I), w)


RULES = [
    _r("greeting", "greeting-start", r"^(hi|hello|hey|hiya|yo|good (morning|afternoon|evening)|greetings)\b", 3.0),
    _r("farewell", "farewell", r"\b(bye|goodbye|see you|good night|talk (to you )?later|gtg|take care|catch you later)\b", 3.0),
    _r("gratitude", "thanks", r"\b(thank you|thanks|thank|appreciate (it|that|you)|much obliged)\b", 3.0),
    _r("question", "question-mark", r"\?\s*$", 2.0),
    _r("question", "wh-word", r"^(what|why|how|when|where|who|which|can you|could you|do you|are you|is it|should i|would you)\b", 1.5),
    _r("good_news", "achievement", r"\b(passed|got (the|a|into)|promoted|won|accepted|graduat\w*|finished|completed|achieved|nailed|got engaged|got married|made the team|landed)\b", 2.5),
    _r("excitement", "excited-words", r"\b(excited|can not wait|thrilled|pumped|stoked|yay|hooray|elated)\b", 2.2),
    _r("excitement", "joy-words", r"\b(happy|glad|delighted|proud|relieved|pleased|joy)\b", 2.0),
    _r("excitement", "exclaim", r"!{2,}", 1.5),
    _r("frustration", "frustration-words", r"\b(failed|fail|annoy\w*|frustrat\w*|angry|furious|fed up|hate|hated|terrible|waste of|ridiculous|disappoint\w*|unfair|sick of|sucks|irritat\w*|useless|still failed)\b", 2.2),
    _r("sadness_stress", "sad-stress-words", r"\b(sad|depress\w*|lonely|anxious|anxiety|stress\w*|overwhelm\w*|worried|worry|nervous|scared|afraid|exhaust\w*|burnt out|burnout|cry\w*|hopeless|struggl\w*|heartbroken|miserable|down lately)\b", 2.2),
    _r("encouragement", "asks-support", r"\b(encourage\w*|motivat\w*|cheer me up|pep talk|give me hope|tell me (it|i)\b|i can not do this|any advice|need (some )?(support|help)|believe in me)\b", 4.0),
]


def detect_intent(p: Processed, s: SentimentAnalysis) -> IntentResult:
    text = p.normalized
    if p.empty:
        return IntentResult(intent="unknown", ambiguous=True, secondary=[], evidence=["no analysable words"])
    scores: dict[str, float] = {}
    evidence: dict[str, list[str]] = {}
    for rule in RULES:
        if rule.pattern.search(text):
            w = rule.weight
            if rule.intent == "greeting" and len(p.words) > 6:
                w = 1.0
            scores[rule.intent] = scores.get(rule.intent, 0.0) + w
            evidence.setdefault(rule.intent, []).append(rule.name)
    # sentiment modifiers
    if s.label == "negative":
        for k in ("frustration", "sadness_stress"):
            if k in scores:
                scores[k] += 0.75
        if "good_news" in scores:
            scores["good_news"] *= 0.3
        if "excitement" in scores and not s.mixed:
            scores["excitement"] *= 0.5
    if s.label == "positive":
        for k in ("good_news", "excitement"):
            if k in scores:
                scores[k] += 0.75
    if not scores:
        alpha = sum(1 for ch in text if ch.isalpha())
        ratio = alpha / max(1, len(text.replace(" ", "")))
        if len(p.words) <= 1 and not s.rules.cues or ratio < 0.5 or p.empty:
            return IntentResult(intent="unknown", ambiguous=True, secondary=[], evidence=["no matching pattern"])
        return IntentResult(intent="general", ambiguous=False, secondary=[], evidence=["no specific pattern"])
    ranked = sorted(scores, key=lambda k: (-scores[k], PRIORITY.index(k) if k in PRIORITY else 99))
    top = ranked[0]
    secondary = [k for k in ranked[1:] if scores[top] - scores[k] <= 1.0]
    ambiguous = any(scores[top] - scores[k] <= 0.5 for k in ranked[1:])
    return IntentResult(intent=top, ambiguous=ambiguous, secondary=secondary, evidence=evidence[top])
