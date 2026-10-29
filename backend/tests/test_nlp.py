import pytest

from app.nlp.dataset import build, load_splits
from app.nlp.intent import detect_intent
from app.nlp.preprocessing import MAX_CHARS_ANALYSED, preprocess
from app.nlp.sentiment import SentimentEngine
from app.nlp.topics import extract_topics


def analyse_intent(engine, text):
    return detect_intent(preprocess(text), engine.analyze(text)).intent


# ---- preprocessing --------------------------------------------------------
def test_preprocess_handles_empty_and_odd_input():
    for v in ["", "   \n\t", None, 123, "!!!???"]:
        p = preprocess(v)
        assert p.empty


def test_preprocess_contractions_and_negation_marking():
    p = preprocess("I can't say it wasn't good")
    assert "can not" in p.normalized and "was not" in p.normalized
    assert "neg_good" in p.model_text


def test_preprocess_emoji_and_elongation():
    p = preprocess("soooo good 😍 :(")
    assert "xxemopos" in p.tokens and "xxemoneg" in p.tokens
    assert "soo" in p.tokens


def test_preprocess_truncates_long_input():
    p = preprocess("good " * 5000)
    assert p.truncated and len(p.normalized) <= MAX_CHARS_ANALYSED


# ---- sentiment (both engines) ----------------------------------------------
ENGINES = ["fallback_engine", "trained_engine"]


@pytest.fixture(params=ENGINES)
def engine(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize("text,label", [
    ("I finally passed my exam!", "positive"),
    ("This was absolutely terrible and I hate it.", "negative"),
    ("The meeting is at 3pm in room 204.", "neutral"),
    ("The movie was not bad.", "positive"),
    ("The service was not good.", "negative"),
    ("loved it 😍", "positive"),
    ("so bad :(", "negative"),
])
def test_sentiment_labels(engine, text, label):
    assert engine.analyze(text).label == label


def test_negation_not_automatically_negative(engine):
    assert engine.analyze("The movie was not bad.").label != "negative"


def test_mixed_sentiment_flagged(engine):
    for t in ["The presentation was good, but the ending was disappointing.",
              "I'm happy about my result, but nervous about tomorrow."]:
        a = engine.analyze(t)
        assert a.mixed and a.uncertain
        assert "both positive and negative" in " ".join(a.uncertainty_reasons)
        assert any(c.polarity == "positive" for c in a.rules.cues)
        assert any(c.polarity == "negative" for c in a.rules.cues)


def test_empty_input_is_safe(engine):
    a = engine.analyze("   ")
    assert a.label == "neutral" and a.uncertain


def test_intensifier_increases_weight(fallback_engine):
    a = fallback_engine.analyze("good").rules.positive_mass
    b = fallback_engine.analyze("very good").rules.positive_mass
    assert b > a


def test_emoji_cue_reported_by_rules(fallback_engine):
    a = fallback_engine.analyze("😭")
    assert a.label == "negative" and a.rules.cues


def test_classifier_and_rules_reported_separately(trained_engine):
    a = trained_engine.analyze("The food was wonderful.")
    assert a.classifier is not None and a.rules is not None
    assert a.engine.id == "tfidf-logreg+rules" and a.engine.classifier_loaded
    assert a.classifier.top_features


def test_fallback_engine_identifies_itself(fallback_engine):
    a = fallback_engine.analyze("great")
    assert a.engine.id == "rules-fallback" and a.classifier is None
    assert "training" in a.engine.note


def test_missing_model_file_falls_back(tmp_path):
    e = SentimentEngine.load(tmp_path / "nope.joblib")
    assert e.pipeline is None and e.info.id == "rules-fallback"


def test_corrupt_model_file_falls_back(tmp_path):
    p = tmp_path / "bad.joblib"
    p.write_bytes(b"not a model")
    e = SentimentEngine.load(p)
    assert e.pipeline is None and "could not be loaded" in e.info.note


def test_probabilities_sum_to_one(engine):
    a = engine.analyze("I'm not sure how I feel")
    assert abs(sum(a.probabilities.values()) - 1) < 0.01


# ---- intent -----------------------------------------------------------------
@pytest.mark.parametrize("text,intent", [
    ("Hello there!", "greeting"), ("bye, see you tomorrow", "farewell"), ("Thanks a lot", "gratitude"),
    ("What time does it open?", "question"), ("I got promoted today!", "good_news"),
    ("I studied for weeks and still failed.", "frustration"), ("I feel so lonely and overwhelmed", "sadness_stress"),
    ("I'm so excited, can't wait!!", "excitement"), ("Can you cheer me up?", "encouragement"),
    ("The bus leaves at noon", "general"), ("???", "unknown"),
])
def test_intents(fallback_engine, text, intent):
    assert analyse_intent(fallback_engine, text) == intent


# ---- topics -----------------------------------------------------------------
def test_topics_noun_chunk_and_possessive():
    t = extract_topics(preprocess("I finally passed my math exam!"))
    assert t[0].phrase == "math exam" and t[0].ref == "your math exam"


def test_topics_names_and_keywords():
    t = extract_topics(preprocess("I had a fight with Priya about money"))
    phrases = {x.phrase for x in t}
    assert "Priya" in phrases and "money" in phrases


def test_topics_empty_for_no_content():
    assert extract_topics(preprocess("ok")) == []


# ---- dataset hygiene --------------------------------------------------------
def test_no_leakage_between_splits():
    sp = build()
    for a in sp:
        for b in sp:
            if a < b:
                assert not set(sp[a].text) & set(sp[b].text)
                assert not set(sp[a].group) & set(sp[b].group)


def test_holdout_not_in_training():
    sp = load_splits()
    fit = set(sp["train"].text) | set(sp["val"].text) | set(sp["test"].text)
    assert not set(sp["holdout"].text) & fit
    assert set(sp["holdout"].label) == {"positive", "negative", "neutral"}
