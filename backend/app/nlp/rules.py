"""Lexicon/rule layer: negation, intensifiers, emoji, contrast. Independent of the ML model."""
from __future__ import annotations

import math

from app.nlp.lexicon import DIMINISHERS, INTENSIFIERS, lookup
from app.nlp.preprocessing import CONTRAST, Processed
from app.schemas import Cue, RuleResult

NEGATION_FLIP = -0.7
BEFORE_CONTRAST = 0.8
AFTER_CONTRAST = 1.2
NEUTRAL_LOGIT_NO_CUES = 1.6
NEUTRAL_LOGIT_WITH_CUES = 0.6
LABELS = ("negative", "neutral", "positive")


def _softmax(zs: list[float]) -> list[float]:
    m = max(zs)
    es = [math.exp(z - m) for z in zs]
    s = sum(es)
    return [e / s for e in es]


def analyze_rules(p: Processed) -> RuleResult:
    toks = p.tokens
    contrast_idx = next((i for i, t in enumerate(toks) if t in CONTRAST), None)
    cues: list[Cue] = []
    pos = neg = 0.0
    for i, t in enumerate(toks):
        base = lookup(t)
        if base is None:
            continue
        val = base
        start = i
        for back in (1, 2):
            j = i - back
            if j < 0:
                break
            w = toks[j]
            if w in INTENSIFIERS:
                val *= INTENSIFIERS[w]
                start = min(start, j)
            elif w in DIMINISHERS:
                val *= DIMINISHERS[w]
                start = min(start, j)
        negated = i in p.negated
        if negated:
            val *= NEGATION_FLIP
            start = min(start, p.negated[i])
        if contrast_idx is not None and t not in CONTRAST:
            val *= BEFORE_CONTRAST if i < contrast_idx else AFTER_CONTRAST
        phrase = " ".join(x for x in toks[start : i + 1] if x[0].isalpha())
        if t.startswith("xxemo"):
            phrase = "😊 (positive emoji/emoticon)" if base > 0 else "😞 (negative emoji/emoticon)"
        cue = Cue(text=phrase, polarity="positive" if val > 0 else "negative",
                  weight=round(abs(val), 2), negated=negated)
        cues.append(cue)
        if val > 0:
            pos += val
        else:
            neg += -val
    if cues and any(t.startswith("!") for t in toks):
        pos, neg = pos * 1.1, neg * 1.1
    neutral_logit = NEUTRAL_LOGIT_WITH_CUES if cues else NEUTRAL_LOGIT_NO_CUES
    probs = _softmax([neg, neutral_logit, pos])
    label = LABELS[max(range(3), key=lambda k: probs[k])]
    cues.sort(key=lambda c: -c.weight)
    return RuleResult(
        label=label,  # type: ignore[arg-type]
        probabilities={k: round(v, 4) for k, v in zip(LABELS, probs)},
        positive_mass=round(pos, 3),
        negative_mass=round(neg, 3),
        cues=cues[:8],
    )
