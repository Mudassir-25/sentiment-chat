"""Minimal safety net: self-harm language gets a fixed, careful reply (never sent to an LLM, never stored)."""
import re

_CRISIS = re.compile(
    r"\b(kill myself|killing myself|end my life|ending my life|want to die|wanna die|suicid\w*|"
    r"hurt myself|harm myself|self[- ]harm|no reason to live|better off dead)\b", re.I)

SAFETY_REPLY = (
    "I'm really sorry you're carrying this much pain right now. I'm a simple chat tool and can't give you the support "
    "you deserve, but you don't have to face this alone. If you might act on these thoughts or are in immediate danger, "
    "please contact your local emergency number now. In India you can call Tele-MANAS at 14416 (or 1-800-891-4416); "
    "elsewhere, findahelpline.com lists free lines by country. If you can, tell someone you trust how you're feeling "
    "tonight. I'm here to keep talking, too."
)


def is_crisis(text: str) -> bool:
    return bool(_CRISIS.search(text or ""))
