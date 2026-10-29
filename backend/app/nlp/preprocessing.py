"""Non-destructive text preprocessing.

Keeps negators, contrast words, intensifiers and emoji signal. Produces:
  * tokens  - lower-cased tokens incl. clause punctuation (used by rules, intent, topics)
  * negated - token index -> index of the negator whose scope covers it
  * model_text - string fed to TF-IDF (negated tokens become ``neg_<tok>``)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_CHARS_ANALYSED = 2000

CONTRACTIONS = {
    "won't": "will not", "can't": "can not", "cannot": "can not", "shan't": "shall not",
    "ain't": "is not", "i'm": "i am", "it's": "it is", "that's": "that is", "there's": "there is",
    "he's": "he is", "she's": "she is", "i've": "i have", "i'll": "i will", "i'd": "i would",
    "we're": "we are", "they're": "they are", "you're": "you are", "let's": "let us",
    "what's": "what is", "gonna": "going to", "wanna": "want to", "gotta": "got to",
    "dunno": "do not know",
}
SLANG = {
    "u": "you", "ur": "your", "thx": "thanks", "ty": "thank you", "gr8": "great", "luv": "love",
    "pls": "please", "plz": "please", "tho": "though", "cuz": "because", "cos": "because",
    "rn": "right now", "awsm": "awesome", "gud": "good", "bad af": "very bad", "im": "i am",
    "ive": "i have", "dont": "do not", "doesnt": "does not", "didnt": "did not", "wasnt": "was not",
    "isnt": "is not", "cant": "can not", "wont": "will not", "couldnt": "could not",
    "shouldnt": "should not", "havent": "have not", "hasnt": "has not", "arent": "are not",
}

EMOJI_POS = set("😀😃😄😁😆😊🙂😍🥰😎🎉👍❤💖💕🤩😂🥳✨🙌👏😇🤗😌💪🔥")
EMOJI_NEG = set("😢😭😞😔😡😠😤👎💔😟😰😨😱🤬😩😫😖😣😒🙁☹😕🥺")
EMOTICON_POS = re.compile(r"(?::|=|;)-?[)D]|<3|\^_\^|:\]")
EMOTICON_NEG = re.compile(r"(?::|=)'?-?[(\[]|>:\(|T_T|:/(?!/)")

NEGATORS = {"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "hardly",
            "barely", "without", "cannot"}
CONTRAST = {"but", "however", "although", "though", "yet", "except"}
CLAUSE_PUNCT = {",", ".", ";", ":", "!", "?"}
NEGATION_WINDOW = 3

_TOKEN_RE = re.compile(r"xxemopos|xxemoneg|[a-z]+(?:'[a-z]+)?|\d+|[!?]+|[,.;:]")
_ELONG_RE = re.compile(r"(.)\1{2,}")


@dataclass
class Processed:
    raw: str
    normalized: str
    tokens: list[str]
    negated: dict[int, int] = field(default_factory=dict)
    model_text: str = ""
    truncated: bool = False
    empty: bool = True

    @property
    def words(self) -> list[str]:
        return [t for t in self.tokens if t[0].isalpha() or t[0].isdigit()]


def _mark_emoji(text: str) -> str:
    text = text.replace("\ufe0f", "")
    out = []
    for ch in text:
        if ch in EMOJI_POS:
            out.append(" xxemopos ")
        elif ch in EMOJI_NEG:
            out.append(" xxemoneg ")
        else:
            out.append(ch)
    text = "".join(out)
    text = EMOTICON_POS.sub(" xxemopos ", text)
    text = EMOTICON_NEG.sub(" xxemoneg ", text)
    return text


def normalize(text: object) -> tuple[str, bool]:
    """Return (normalised text, truncated). Never raises on odd input."""
    if text is None:
        return "", False
    if not isinstance(text, str):
        text = str(text)
    truncated = len(text) > MAX_CHARS_ANALYSED
    text = text[:MAX_CHARS_ANALYSED]
    text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t ")
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = _mark_emoji(text)
    text = text.lower()
    text = _ELONG_RE.sub(r"\1\1", text)
    for k, v in CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(k)}\b", v, text)
    text = re.sub(r"\b(\w+)n't\b", r"\1 not", text)
    text = re.sub(r"\b(\w+)'(ll|re|ve|d)\b", r"\1", text)
    text = re.sub(r"\b(\w+)'s\b", r"\1", text)
    words = text.split()
    text = " ".join(SLANG.get(w.strip(".,!?"), w) if w.strip(".,!?") in SLANG else w for w in words)
    text = re.sub(r"\s+", " ", text).strip()
    return text, truncated


def _negation_scopes(tokens: list[str]) -> dict[int, int]:
    scopes: dict[int, int] = {}
    i = 0
    while i < len(tokens):
        if tokens[i] in NEGATORS:
            j = i + 1
            count = 0
            while j < len(tokens) and count < NEGATION_WINDOW:
                t = tokens[j]
                if t in CLAUSE_PUNCT or t in CONTRAST or t[0] in "!?":
                    break
                if t in NEGATORS:
                    break
                if t[0].isalpha():
                    scopes[j] = i
                    count += 1
                j += 1
        i += 1
    return scopes


def preprocess(text: object) -> Processed:
    norm, truncated = normalize(text)
    tokens = _TOKEN_RE.findall(norm)
    negated = _negation_scopes(tokens)
    parts: list[str] = []
    for i, t in enumerate(tokens):
        if t in (",", ".", ";", ":"):
            continue
        if t[0] in "!?":
            parts.append("excl" if t[0] == "!" else "qmark")
        elif i in negated and t not in NEGATORS:
            parts.append(f"neg_{t}")
        else:
            parts.append(t)
    return Processed(
        raw=text if isinstance(text, str) else ("" if text is None else str(text)),
        normalized=norm,
        tokens=tokens,
        negated=negated,
        model_text=" ".join(parts),
        truncated=truncated,
        empty=not any(t[0].isalpha() for t in tokens),
    )
