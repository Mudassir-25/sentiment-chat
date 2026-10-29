"""Train the TF-IDF + Logistic Regression baseline. Run: python -m app.nlp.training

C is chosen on the validation split; the test split and hand-written holdout are never used for fitting.
The model file is a generated artifact (git-ignored). Only load model files you trained yourself (joblib = pickle).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline

from app.core.config import BACKEND_DIR
from app.nlp.dataset import load_splits
from app.nlp.preprocessing import preprocess

C_GRID = [0.5, 1.0, 3.0, 10.0]
SEED = 7


def prep(texts) -> list[str]:
    return [preprocess(t).model_text for t in texts]


def make_pipeline(c: float) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, token_pattern=r"(?u)\b\w+\b")),
        ("clf", LogisticRegression(C=c, max_iter=2000, class_weight="balanced", random_state=SEED)),
    ])


def train(out: Path) -> dict:
    sp = load_splits()
    xtr, ytr = prep(sp["train"].text), sp["train"].label
    xva, yva = prep(sp["val"].text), sp["val"].label
    best_c, best_f1 = None, -1.0
    for c in C_GRID:
        f1 = f1_score(yva, make_pipeline(c).fit(xtr, ytr).predict(xva), average="macro")
        print(f"C={c:<5} val macro-F1={f1:.4f}")
        if f1 > best_f1:
            best_c, best_f1 = c, f1
    pipe = make_pipeline(best_c).fit(xtr, ytr)  # type: ignore[arg-type]
    # choose the classifier/rules blend weight on the validation split only
    import numpy as np
    from app.nlp.rules import LABELS, analyze_rules
    rule_p = np.array([[analyze_rules(preprocess(t)).probabilities[k] for k in LABELS] for t in sp["val"].text])
    clf_p = pipe.predict_proba(xva)[:, [list(pipe.classes_).index(k) for k in LABELS]]
    best_w, best_blend = 0.5, -1.0
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):
        pred = [LABELS[i] for i in (w * clf_p + (1 - w) * rule_p).argmax(1)]
        f1 = f1_score(yva, pred, average="macro")
        print(f"clf_weight={w:<4} val macro-F1={f1:.4f}")
        if f1 > best_blend + 1e-9:
            best_w, best_blend = w, f1
    data_hash = hashlib.sha256("".join(sorted(sp["train"].text)).encode()).hexdigest()[:12]
    meta = {"C": best_c, "clf_weight": best_w, "val_blend_macro_f1": round(best_blend, 4), "val_macro_f1": round(best_f1, 4), "train_rows": len(sp["train"]),
            "sklearn": sklearn.__version__, "train_data_sha": data_hash}
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "meta": meta}, out)
    print("saved", out, json.dumps(meta))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(BACKEND_DIR / "models" / "sentiment.joblib"))
    train(Path(ap.parse_args().out))
