"""Builds the small, original, synthetic training dataset (CC0 / MIT with the project).

Honest scope: sentences are generated from hand-written templates plus a handful of hand-written
short phrases. It is a *baseline* dataset to make training reproducible offline, not a substitute
for a large real-world corpus. `data/handwritten_holdout.csv` is separate, hand-written and never
used for fitting; it is the more honest measure.

Leakage control: rows are split by *group* (the predicate/feeling phrase), so the same predicate
never appears in two splits. Exact duplicates are removed and cross-split overlap is asserted empty.

Run: python -m app.nlp.dataset
"""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SEED = 7

SUBJECTS = ["The movie", "My day", "The food", "The service", "This phone", "The trip", "Our meeting",
            "The concert", "That class", "The new update", "The hotel", "My coffee", "The book",
            "The game", "Her presentation", "The restaurant", "This app", "The weather",
            "My commute", "The lecture"]

POS_PRED = [
    "was wonderful", "was amazing", "made me really happy", "turned out great", "was fantastic",
    "was so much fun", "exceeded my expectations", "went really well", "was absolutely lovely",
    "was a pleasant surprise", "was excellent", "was truly impressive", "was awesome",
    "was brilliant", "was better than I hoped", "was really enjoyable", "was perfect",
    "left me delighted", "was not bad at all", "wasn't terrible", "was not disappointing",
    "was never boring", "was not a waste of time", "wasn't bad, actually good", "was surprisingly good",
    "was a real highlight", "felt great", "was so good I'd recommend it", "was lovely and relaxing",
    "was sweet and thoughtful",
]
NEG_PRED = [
    "was terrible", "was awful", "made me really upset", "turned out badly", "was horrible",
    "was so boring", "was a huge disappointment", "went really badly", "was absolutely dreadful",
    "was a waste of time", "was the worst", "was truly frustrating", "was a mess",
    "was not good", "wasn't great", "was not enjoyable", "was not worth it", "did not impress me",
    "never worked properly", "wasn't fun at all", "was really annoying", "left me angry",
    "was extremely poor", "was far from good", "didn't live up to the hype", "was so disappointing",
    "felt exhausting and pointless", "was a total letdown", "was rude and unhelpful",
    "was a nightmare",
]
NEU_PRED = [
    "was released on Tuesday", "starts at nine", "has three sections", "is located downtown",
    "was held on the second floor", "lasts about an hour", "is open on weekdays",
    "was scheduled for Monday", "has been moved to next week", "is on the main street",
    "was mentioned in the newsletter", "includes a short break", "is available in two sizes",
    "was posted on the website", "takes place in room twelve", "ends at five",
    "is described in the handbook", "was updated last month", "needs a login",
    "is run by the student office", "covers the first chapter", "was recorded yesterday",
    "is next to the station", "has twenty participants", "was shared by email",
    "requires an ID", "was listed under events", "comes with a guide", "runs twice a day",
    "was reported in the minutes",
]

POS_EVENTS = ["passed my exam", "got the job", "finished my project", "won the match", "got promoted",
              "made the team", "got into my first-choice course", "nailed the interview"]
POS_FEEL = ["I'm thrilled", "I feel amazing", "I'm so happy", "it feels great", "I'm really proud",
            "I'm over the moon", "I could not be happier", "it feels wonderful"]
NEG_EVENTS = ["failed my exam", "lost my job", "missed the deadline", "broke my phone", "lost the match",
              "got rejected", "failed the interview", "lost my wallet"]
NEG_FEEL = ["I'm devastated", "I feel awful", "I'm so upset", "it feels terrible", "I'm really disappointed",
            "I'm heartbroken", "I feel hopeless", "it hurts a lot"]
NEU_EVENTS = ["submitted my report", "went to the library", "booked a table", "joined a call",
              "moved to a new desk", "picked up a parcel", "renewed my card", "updated my calendar"]
NEU_FRAMES = ["Today I {e}.", "I {e} this morning.", "Yesterday I {e}.", "I {e} and then went home.",
              "After lunch I {e}.", "Earlier this week I {e}.", "I just {e}.", "On Friday I {e}."]

POS_ADJ = ["great", "good", "excellent", "wonderful", "lovely", "fantastic", "superb", "enjoyable", "delightful",
           "charming", "brilliant", "impressive", "refreshing", "cozy", "gorgeous", "stunning", "satisfying",
           "terrific", "pleasant", "fabulous", "uplifting", "inspiring", "heartwarming", "relaxing",
           "thrilling", "rewarding", "magical", "splendid", "neat", "cheerful"]
NEG_ADJ = ["bad", "poor", "awful", "dreadful", "unpleasant", "dull", "disappointing", "miserable", "depressing",
           "irritating", "annoying", "lousy", "sloppy", "stressful", "terrible", "painful", "tedious",
           "infuriating", "exhausting", "gloomy", "shameful", "chaotic", "heartbreaking", "disgusting",
           "pathetic", "frustrating", "sad", "ridiculous", "unbearable", "boring"]
NEU_ADJ = ["long", "short", "new", "old", "quiet", "large", "small", "blue", "early", "late", "regular",
           "standard", "typical", "ordinary", "square", "round", "open", "closed", "second", "local"]
ADJ_FRAMES = ["{S} was {a}.", "{S} was really {a}.", "I thought {s} was {a}.", "Honestly, {s} seemed {a}."]
NEG_OPEN = ["happy", "excited", "proud", "thrilled", "relaxed"]
NEG_OPEN_NEG = ["sad", "angry", "upset", "worried", "scared"]

SHORT = {
    "positive": ["loved it 😍", "best day ever 🎉", "so good :)", "lol this is awesome", "ngl that was lit",
                 "can't stop smiling 😊", "thx so much, you rock 👍", "yay!!! we did it", "soooo happy rn",
                 "this made my day <3", "10/10 would recommend", "gr8 stuff, really enjoyed it",
                 "wow, absolutely stunning!", "feeling great today!", "nailed it 💪"],
    "negative": ["hated it 😡", "worst day ever 😭", "so bad :(", "lol this sucks", "ngl that was trash",
                 "can't stop crying 😢", "ugh, so annoyed rn", "this ruined my day", "0/10 would not recommend",
                 "wow, absolutely horrible!", "feeling awful today", "i give up 😞", "total garbage tbh",
                 "so tired of this nonsense", "what a disaster!!"],
    "neutral": ["ok", "just checking in", "meeting at 3pm", "see you at 5", "sent the file",
                "it is Tuesday", "running a bit early", "at the office now", "will call later",
                "need to buy stamps", "the form is online", "room 204", "back in ten minutes",
                "reading chapter two", "lunch is at noon"],
}


def _rows() -> list[tuple[str, str, str]]:
    rnd = random.Random(SEED)
    rows: list[tuple[str, str, str]] = []
    for label, preds in (("positive", POS_PRED), ("negative", NEG_PRED), ("neutral", NEU_PRED)):
        for pred in preds:
            for subj in rnd.sample(SUBJECTS, 7):
                rows.append((f"{subj} {pred}.", label, f"pred:{pred}"))
    for label, events, feels in (("positive", POS_EVENTS, POS_FEEL), ("negative", NEG_EVENTS, NEG_FEEL)):
        for feel in feels:
            for ev in rnd.sample(events, 5):
                text = f"I {ev} and {feel[0].lower() + feel[1:] if not feel.startswith('I') else feel}."
                rows.append((text, label, f"feel:{feel}"))
    for frame in NEU_FRAMES:
        for ev in rnd.sample(NEU_EVENTS, 6):
            rows.append((frame.format(e=ev), "neutral", f"frame:{frame}"))
    for label, adjs in (("positive", POS_ADJ), ("negative", NEG_ADJ), ("neutral", NEU_ADJ)):
        for adj in adjs:
            for frame in rnd.sample(ADJ_FRAMES, 3):
                subj = rnd.choice(SUBJECTS)
                rows.append((frame.format(S=subj, s=subj[0].lower() + subj[1:], a=adj), label, f"adj:{label}:{adj}"))
    for adj in POS_ADJ[:20]:
        subj = rnd.choice(SUBJECTS)
        rows.append((f"{subj} was not {adj}.", "negative", f"notadj:{adj}"))
    for adj in NEG_ADJ[:20]:
        subj = rnd.choice(SUBJECTS)
        rows.append((f"{subj} was not {adj}.", "positive", f"notadj:{adj}"))
    for adj in NEG_OPEN:
        rows.append((f"I am not {adj} about this.", "negative", f"notfeel:{adj}"))
        rows.append((f"I feel {adj} today.", "positive", f"feel1:{adj}"))
    for adj in NEG_OPEN_NEG:
        rows.append((f"I am not {adj} about this.", "positive", f"notfeel:{adj}"))
        rows.append((f"I feel {adj} today.", "negative", f"feel1:{adj}"))
    for label, items in SHORT.items():
        for s in items:
            rows.append((s, label, f"short:{s}"))
    return rows


def _assign_groups(df: pd.DataFrame) -> dict[str, str]:
    """Stratified-by-label group split: groups ranked by md5 hash, 70/15/15 per label."""
    mapping: dict[str, str] = {}
    for label, sub in df.groupby("label"):
        groups = sorted(sub.group.unique(), key=lambda g: hashlib.md5(g.encode()).hexdigest())
        n = len(groups)
        for i, g in enumerate(groups):
            mapping[g] = "train" if i < round(n * 0.7) else ("val" if i < round(n * 0.85) else "test")
    return mapping


def build() -> dict[str, pd.DataFrame]:
    df = pd.DataFrame(_rows(), columns=["text", "label", "group"]).drop_duplicates("text")
    df["split"] = df["group"].map(_assign_groups(df))
    out = {s: df[df.split == s][["text", "label", "group"]].reset_index(drop=True) for s in ("train", "val", "test")}
    for a in out:
        for b in out:
            if a < b:
                assert not set(out[a].text) & set(out[b].text), f"leakage between {a} and {b}"
                assert not set(out[a].group) & set(out[b].group), f"group leakage {a}/{b}"
    hold = pd.read_csv(DATA_DIR / "handwritten_holdout.csv")
    fit_text = set(out["train"].text) | set(out["val"].text) | set(out["test"].text)
    assert not set(hold.text) & fit_text, "holdout overlaps generated data"
    return out


def write() -> dict[str, pd.DataFrame]:
    splits = build()
    DATA_DIR.mkdir(exist_ok=True)
    for name, d in splits.items():
        d.to_csv(DATA_DIR / f"{name}.csv", index=False)
    return splits


def load_splits() -> dict[str, pd.DataFrame]:
    if not all((DATA_DIR / f"{n}.csv").exists() for n in ("train", "val", "test")):
        write()
    s = {n: pd.read_csv(DATA_DIR / f"{n}.csv") for n in ("train", "val", "test")}
    s["holdout"] = pd.read_csv(DATA_DIR / "handwritten_holdout.csv")
    return s


if __name__ == "__main__":
    for n, d in write().items():
        print(n, len(d), d.label.value_counts().to_dict())
