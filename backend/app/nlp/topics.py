"""Lightweight lexical topic extraction. No semantic understanding is claimed.

Sources: determiner-led noun chunks ("my math exam"), a keyword list of common topic nouns,
capitalised mid-sentence words (names) and a few activity words.
"""
from __future__ import annotations

import re

from app.nlp.lexicon import LEXICON
from app.nlp.preprocessing import NEGATORS, Processed
from app.schemas import Topic

DETERMINERS = {"my", "our", "your", "his", "her", "their", "the", "this", "that", "these", "those", "a", "an"}
POSSESSIVE = {"my": "your", "our": "your", "your": "your"}
STOP = {
    "i", "me", "am", "is", "are", "was", "were", "be", "been", "being", "to", "of", "and", "or", "but", "in", "on", "at",
    "for", "with", "it", "its", "so", "very", "really", "just", "about", "as", "by", "from", "that", "this", "have",
    "has", "had", "do", "does", "did", "will", "would", "can", "could", "should", "not", "no", "yes", "if", "then",
    "than", "too", "also", "still", "finally", "even", "all", "some", "any", "what", "why", "how", "when", "where",
    "who", "which", "there", "here", "they", "them", "we", "you", "he", "she", "up", "out", "over", "into", "like",
    "much", "more", "most", "many", "feel", "feeling", "think", "thing", "things", "got", "get", "going", "went",
    "yesterday", "today", "tomorrow", "tonight", "now", "again", "ever", "never", "always", "week", "weeks",
}
TOPIC_NOUNS = {
    "exam", "test", "quiz", "job", "interview", "project", "presentation", "deadline", "meeting", "result", "results",
    "grade", "grades", "class", "course", "degree", "family", "friend", "friends", "boss", "manager", "team", "partner",
    "girlfriend", "boyfriend", "wife", "husband", "mother", "father", "mom", "dad", "sister", "brother", "trip",
    "vacation", "holiday", "move", "house", "apartment", "flat", "health", "doctor", "money", "rent", "bills",
    "game", "match", "race", "workout", "movie", "film", "book", "show", "song", "concert", "party", "wedding",
    "birthday", "school", "college", "university", "work", "career", "promotion", "assignment", "essay", "thesis",
    "coding", "code", "app", "software", "phone", "laptop", "weather", "food", "dinner", "lunch", "breakfast",
}
ACTIVITIES = {"studied": "studying", "study": "studying", "studying": "studying", "practiced": "practice",
              "practicing": "practice", "trained": "training", "training": "training", "worked": "working hard",
              "revised": "revising", "revising": "revising", "prepared": "preparing", "preparing": "preparing"}
_CAP_RE = re.compile(r"(?<!^)(?<![.!?]\s)\b([A-Z][a-z]{2,})\b")


def _content(tok: str) -> bool:
    return tok.isalpha() and len(tok) >= 3 and tok not in STOP and tok not in LEXICON \
        and tok not in NEGATORS and tok not in DETERMINERS


def extract_topics(p: Processed, limit: int = 4) -> list[Topic]:
    toks = p.tokens
    found: list[Topic] = []
    seen: set[str] = set()

    def add(phrase: str, ref: str, kind: str) -> None:
        if phrase not in seen and len(found) < limit:
            seen.add(phrase)
            found.append(Topic(phrase=phrase, ref=ref, kind=kind))  # type: ignore[arg-type]

    i = 0
    while i < len(toks):
        if toks[i] in DETERMINERS and i + 1 < len(toks):
            j = i + 1
            chunk: list[str] = []
            while j < len(toks) and len(chunk) < 3:
                t = toks[j]
                if t in LEXICON and not chunk:  # skip leading sentiment adjectives ("my terrible boss")
                    j += 1
                    continue
                if not _content(t) or t in ACTIVITIES:
                    break
                chunk.append(t)
                j += 1
            if chunk:
                det = toks[i]
                phrase = " ".join(chunk)
                ref = f"{POSSESSIVE.get(det, 'the' if det in {'the', 'this', 'that', 'these', 'those', 'a', 'an'} else det)} {phrase}"
                add(phrase, ref, "noun_phrase")
            i = max(j, i + 1)
        else:
            i += 1
    for t in toks:
        if t in TOPIC_NOUNS and t not in seen and not any(t in s.split() for s in seen):
            add(t, f"the {t}", "keyword")
    for m in _CAP_RE.finditer(p.raw or ""):
        name = m.group(1)
        if name.lower() not in STOP and name.lower() not in LEXICON and name.lower() not in TOPIC_NOUNS:
            add(name, name, "name")
    for t in toks:
        if t in ACTIVITIES and ACTIVITIES[t] not in seen:
            add(ACTIVITIES[t], f"your {ACTIVITIES[t]}", "activity")
            break
    return found
