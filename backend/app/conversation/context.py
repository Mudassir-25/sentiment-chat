"""Session-scoped, in-memory, temporary conversation context. Nothing is written to disk."""
from __future__ import annotations

import re
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field

from app.schemas import Analysis, ContextInfo, Topic

MAX_TURNS = 8
MAX_SESSIONS = 500
TTL_SECONDS = 3600
ANAPHORA = re.compile(r"\b(it|that|this|them|those|these|there)\b", re.I)
CONTINUERS = re.compile(r"^(but|and|also|so|because|though|still|yet|however)\b", re.I)


@dataclass
class Turn:
    user_text: str
    reply: str
    sentiment: str
    intent: str
    topics: list[Topic]


@dataclass
class Session:
    turns: deque = field(default_factory=lambda: deque(maxlen=MAX_TURNS))
    recent_templates: deque = field(default_factory=lambda: deque(maxlen=6))
    touched: float = field(default_factory=time.monotonic)

    def last(self) -> Turn | None:
        return self.turns[-1] if self.turns else None

    def last_topics(self) -> list[Topic]:
        for t in reversed(self.turns):
            if t.topics:
                return t.topics
        return []


class SessionStore:
    def __init__(self, max_sessions: int = MAX_SESSIONS, ttl: float = TTL_SECONDS) -> None:
        self._s: OrderedDict[str, Session] = OrderedDict()
        self.max_sessions, self.ttl = max_sessions, ttl

    def get(self, sid: str) -> Session:
        now = time.monotonic()
        for k in [k for k, v in self._s.items() if now - v.touched > self.ttl]:
            del self._s[k]
        s = self._s.get(sid)
        if s is None:
            s = Session()
            self._s[sid] = s
            while len(self._s) > self.max_sessions:
                self._s.popitem(last=False)
        s.touched = now
        self._s.move_to_end(sid)
        return s

    def clear(self, sid: str) -> bool:
        return self._s.pop(sid, None) is not None

    def __len__(self) -> int:
        return len(self._s)


def apply_context(session: Session, text: str, analysis: Analysis) -> Analysis:
    """Annotate analysis with follow-up info; borrow earlier topics when the message continues them."""
    prev = session.last()
    words = text.split()
    own = analysis.topics
    standalone = analysis.intent.intent in ("greeting", "farewell", "gratitude", "question", "unknown")
    followup = bool(prev) and not standalone and (bool(CONTINUERS.match(text.strip())) or
                               (bool(ANAPHORA.search(text)) and not own) or (not own and len(words) <= 6))
    continued: list[str] = []
    if followup and not own:
        borrowed = session.last_topics()
        analysis.topics = [t.model_copy(update={"from_context": True}) for t in borrowed[:2]]
        continued = [t.phrase for t in analysis.topics]
    shift = followup and bool(prev) and prev.sentiment != analysis.sentiment.label and "neutral" not in (prev.sentiment, analysis.sentiment.label)
    analysis.context = ContextInfo(is_followup=followup, previous_sentiment=prev.sentiment if prev else None,  # type: ignore[arg-type]
                                   sentiment_shift=shift, continued_topics=continued, turns_in_memory=len(session.turns))
    return analysis
