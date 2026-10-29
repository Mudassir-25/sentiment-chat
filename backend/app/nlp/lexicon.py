"""Small hand-built sentiment lexicon (original work, MIT-licensed with the project).

Weights are rough magnitudes (about 0.8 weak .. 2.8 strong), not measured values.
"""
POSITIVE = {
    "good": 1.5, "great": 2.2, "excellent": 2.6, "amazing": 2.6, "awesome": 2.5, "fantastic": 2.6,
    "wonderful": 2.5, "love": 2.4, "loved": 2.4, "loving": 2.0, "liked": 1.3, "enjoy": 1.8,
    "enjoyed": 1.9, "enjoyable": 1.8, "happy": 2.2, "glad": 1.8, "thrilled": 2.6, "excited": 2.2,
    "proud": 2.2, "pleased": 1.8, "delighted": 2.4, "nice": 1.5, "lovely": 2.0, "beautiful": 2.0,
    "brilliant": 2.4, "perfect": 2.5, "best": 2.2, "better": 1.2, "fun": 1.8, "cool": 1.4,
    "lit": 1.6, "relieved": 1.8, "relief": 1.5, "grateful": 2.0, "thankful": 2.0, "success": 1.8,
    "successful": 1.9, "win": 1.6, "won": 1.8, "passed": 1.6, "promoted": 2.0, "improved": 1.5,
    "impressive": 2.0, "impressed": 2.0, "fine": 0.8, "calm": 1.2, "hopeful": 1.5, "confident": 1.7,
    "comfortable": 1.3, "smile": 1.4, "smiling": 1.5, "yay": 2.0, "congrats": 2.0,
    "congratulations": 2.0, "worth": 1.2, "recommend": 1.5, "recommended": 1.5, "smooth": 1.2,
    "easy": 1.0, "helpful": 1.8, "friendly": 1.5, "delicious": 2.2, "tasty": 1.8, "favorite": 1.8,
    "favourite": 1.8, "joy": 2.2, "joyful": 2.2, "cheerful": 1.8, "incredible": 2.5, "superb": 2.5,
    "outstanding": 2.5, "epic": 2.0, "solid": 1.2, "stoked": 2.0, "pumped": 2.0, "elated": 2.5,
    "hooray": 2.0, "lucky": 1.7, "blessed": 1.9, "motivated": 1.6, "inspired": 1.8, "thanks": 1.0,
    "thank": 1.0, "xxemopos": 1.6,
}
NEGATIVE = {
    "bad": -1.8, "terrible": -2.6, "awful": -2.6, "horrible": -2.6, "worst": -2.8, "worse": -1.8,
    "hate": -2.5, "hated": -2.5, "sad": -2.0, "upset": -2.0, "angry": -2.2, "furious": -2.6,
    "annoyed": -1.8, "annoying": -1.9, "frustrated": -2.1, "frustrating": -2.1,
    "disappointed": -2.2, "disappointing": -2.2, "disappointment": -2.2, "unhappy": -2.1,
    "depressed": -2.5, "miserable": -2.5, "lonely": -2.0, "anxious": -1.9, "nervous": -1.4,
    "scared": -1.8, "afraid": -1.7, "worried": -1.6, "stressed": -1.8, "stressful": -1.8,
    "stress": -1.5, "overwhelmed": -2.0, "exhausted": -1.7, "tired": -1.0, "failed": -2.2,
    "fail": -1.8, "failure": -2.2, "lost": -1.6, "lose": -1.4, "broken": -1.6, "broke": -1.3,
    "boring": -1.5, "bored": -1.4, "waste": -1.8, "useless": -2.2, "poor": -1.5, "rude": -1.8,
    "slow": -1.0, "ugly": -1.6, "dirty": -1.4, "painful": -1.8, "hurt": -1.8, "hurts": -1.8,
    "cry": -1.6, "crying": -1.8, "cried": -1.6, "devastated": -2.7, "heartbroken": -2.7,
    "hopeless": -2.5, "guilty": -1.6, "ashamed": -1.8, "regret": -1.8, "unfair": -1.8,
    "ridiculous": -1.6, "mess": -1.4, "sucks": -2.0, "sucked": -2.0, "trash": -2.0,
    "garbage": -2.0, "worthless": -2.4, "disgusting": -2.4, "nightmare": -2.2, "rejected": -2.0,
    "ignored": -1.6, "struggling": -1.7, "struggle": -1.5, "burnout": -2.0, "problem": -1.0,
    "problems": -1.0, "issue": -0.8, "issues": -0.8, "buggy": -1.6, "crashed": -1.6, "late": -0.8,
    "missed": -1.3, "panic": -1.8, "dread": -2.0, "jealous": -1.2, "unfortunately": -1.0,
    "xxemoneg": -1.6,
}
LEXICON = {**POSITIVE, **NEGATIVE}

INTENSIFIERS = {
    "very": 1.4, "really": 1.4, "so": 1.3, "extremely": 1.7, "super": 1.5, "absolutely": 1.6,
    "totally": 1.4, "incredibly": 1.6, "quite": 1.2, "pretty": 1.15, "too": 1.2, "deeply": 1.5,
    "completely": 1.5, "utterly": 1.6,
}
DIMINISHERS = {"slightly": 0.6, "somewhat": 0.7, "kinda": 0.7, "bit": 0.7, "little": 0.7,
               "fairly": 0.85, "mildly": 0.6}


def lookup(token: str) -> float | None:
    if token in LEXICON:
        return LEXICON[token]
    return None
