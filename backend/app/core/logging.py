"""Logging setup. Raw user messages are never logged; known secrets are redacted defensively."""
from __future__ import annotations

import logging
import re

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{8,}", re.I),
    re.compile(r"(x-api-key['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9_\-]{8,}", re.I),
]


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: list[str] | None = None) -> None:
        super().__init__()
        self._secrets = [s for s in (secrets or []) if len(s) >= 6]

    def redact(self, text: str) -> str:
        for s in self._secrets:
            text = text.replace(s, "[REDACTED]")
        for p in _PATTERNS:
            text = p.sub("[REDACTED]", text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.redact(record.getMessage())
        record.args = ()
        return True


def configure_logging(level: str = "INFO", secrets: list[str] | None = None) -> None:
    root = logging.getLogger("sentiment_chat")
    root.setLevel(level.upper())
    for f in [f for f in root.filters if isinstance(f, RedactingFilter)]:
        root.removeFilter(f)
    root.addFilter(RedactingFilter(secrets))
    if not root.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(h)
