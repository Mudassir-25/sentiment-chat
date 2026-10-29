"""Sentiment engine = optional trained classifier + rule layer, reported separately.

Engines:
  tfidf-logreg+rules : w * classifier probabilities + (1-w) * rule probabilities (w chosen on validation split)
  rules-fallback     : rule layer only (used when no trained model file is available)
Scores are model confidence estimates; calibration is measured in evaluation, not assumed.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.nlp.preprocessing import Processed, preprocess
from app.nlp.rules import LABELS, analyze_rules
from app.schemas import (ClassifierResult, EngineInfo, FeatureContribution, RuleResult,
                         SentimentAnalysis)

log = logging.getLogger("sentiment_chat.sentiment")

DEFAULT_CLF_WEIGHT = 0.5  # overridden by the value chosen on the validation split at training time
LOW_CONFIDENCE = 0.55
SMALL_MARGIN = 0.12
MIN_SIDE_FOR_MIXED = 1.0


def _display_feature(f: str) -> str:
    return " ".join(f"not {w[4:]}" if w.startswith("neg_") else w for w in f.split())


class SentimentEngine:
    def __init__(self, pipeline: Any | None = None, meta: dict | None = None, load_error: str | None = None):
        self.pipeline = pipeline
        self.meta = meta or {}
        self.load_error = load_error

    # ---- loading -------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> "SentimentEngine":
        if not path.exists():
            return cls(load_error="model file not found")
        try:
            import joblib  # local import: only needed when a model exists

            bundle = joblib.load(path)  # NOTE: only load model files you trained yourself
            pipe = bundle["pipeline"]
            if list(pipe.classes_) != sorted(LABELS):
                raise ValueError("unexpected class labels")
            return cls(pipe, bundle.get("meta", {}))
        except Exception as exc:  # corrupt file, sklearn version mismatch, ...
            log.warning("could not load model (%s); using rules fallback", type(exc).__name__)
            return cls(load_error=f"model could not be loaded ({type(exc).__name__})")

    @property
    def info(self) -> EngineInfo:
        if self.pipeline is not None:
            return EngineInfo(id="tfidf-logreg+rules", name="TF-IDF + Logistic Regression + rules",
                              classifier_loaded=True,
                              note="Trained local classifier combined with a lexicon/rule layer.")
        why = self.load_error or "no model"
        return EngineInfo(id="rules-fallback", name="Rule-based fallback", classifier_loaded=False,
                          note=f"No trained classifier active ({why}). Run `python -m app.nlp.training` to train one.")

    # ---- classifier ----------------------------------------------------
    @property
    def _classes(self) -> list[str]:
        return list(self.pipeline.classes_)

    def _classify(self, p: Processed) -> ClassifierResult:
        pipe = self.pipeline
        proba = pipe.predict_proba([p.model_text])[0]
        probs = {c: float(v) for c, v in zip(self._classes, proba)}
        label = max(probs, key=probs.get)  # type: ignore[arg-type]
        vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
        x = vec.transform([p.model_text])
        idx = self._classes.index(label)
        names = vec.get_feature_names_out()
        contribs = []
        row = x.tocoo()
        for j, v in zip(row.col, row.data):
            contribs.append((names[j], float(v * clf.coef_[idx][j])))
        contribs.sort(key=lambda t: -t[1])
        top = [FeatureContribution(feature=_display_feature(n), contribution=round(c, 3))
               for n, c in contribs[:5] if c > 0]
        return ClassifierResult(label=label, probabilities={k: round(v, 4) for k, v in probs.items()},  # type: ignore[arg-type]
                                top_features=top)

    # ---- public API ----------------------------------------------------
    def analyze(self, text: object) -> SentimentAnalysis:
        p = preprocess(text)
        rules = analyze_rules(p)
        clf = self._classify(p) if (self.pipeline is not None and not p.empty) else None
        if clf is not None:
            w = float(self.meta.get("clf_weight", DEFAULT_CLF_WEIGHT))
            probs = {k: w * clf.probabilities.get(k, 0.0) + (1 - w) * rules.probabilities[k] for k in LABELS}
        else:
            probs = dict(rules.probabilities)
        label = max(probs, key=probs.get)  # type: ignore[arg-type]
        ordered = sorted(probs.values(), reverse=True)
        confidence = ordered[0]
        margin = ordered[0] - ordered[1]

        mixed = min(rules.positive_mass, rules.negative_mass) >= MIN_SIDE_FOR_MIXED
        reasons: list[str] = []
        if p.empty:
            reasons.append("no analysable words")
        if mixed:
            reasons.append("both positive and negative cues found")
        if confidence < LOW_CONFIDENCE:
            reasons.append("low confidence estimate")
        elif margin < SMALL_MARGIN:
            reasons.append("top two classes are close")
        if clf is not None and clf.label != rules.label and "neutral" not in (clf.label, rules.label):
            reasons.append("classifier and rule layer disagree")
        if p.truncated:
            reasons.append("message was truncated for analysis")
        uncertain = bool(reasons) and not (reasons == ["message was truncated for analysis"])

        return SentimentAnalysis(
            label=label,  # type: ignore[arg-type]
            confidence=round(confidence, 3),
            probabilities={k: round(v, 4) for k, v in probs.items()},
            mixed=mixed,
            uncertain=uncertain,
            uncertainty_reasons=reasons,
            explanation=self._explain(label, mixed, clf, rules),
            engine=self.info,
            classifier=clf,
            rules=rules,
            truncated=p.truncated,
        )

    @staticmethod
    def _explain(label: str, mixed: bool, clf: ClassifierResult | None, rules: RuleResult) -> str:
        parts = []
        if clf is not None:
            feats = ", ".join(f.feature for f in clf.top_features[:3])
            parts.append(f"Classifier says {clf.label}" + (f" (strongest features: {feats})" if feats else ""))
        parts.append(f"rule layer says {rules.label}")
        if rules.cues:
            parts[-1] += " (cues: " + ", ".join(f'"{c.text}"' for c in rules.cues[:3]) + ")"
        s = "; ".join(parts) + f". Overall: {label}."
        if mixed:
            s += " Both positive and negative cues were found, so a single label is a simplification."
        return s
