"""Train FT-1: a 7-class safety classifier (none + 6 hazards) on character n-grams.

Model: TF-IDF over character n-grams (2-5, word-bounded) + multinomial logistic regression.
Character n-grams handle Devanagari, Hinglish spelling variants and typos without a tokenizer,
and the model exports to a small JSON file that runs in plain Python (no ML runtime on the
512 MB Render instance) and, later, in the browser.

Usage (API virtualenv, from repo root):
  apps/api/.venv/Scripts/python ml/safety_classifier/train.py --train templates[,gemma]
Writes ml/safety_classifier/artifacts/metrics-<tag>.json and, with --export, the runtime model
to apps/api/src/fixwithme_api/models/safety_ft1.json.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
from fixwithme_api import safety  # noqa: E402

DATA = HERE / "data"
ARTIFACTS = HERE / "artifacts"
EXPORT = ROOT / "apps" / "api" / "src" / "fixwithme_api" / "models" / "safety_ft1.json"
SOURCES = {"templates": "train_templates.jsonl", "gemma": "train_gemma.jsonl"}
TARGET_VAL_RECALL = 0.98  # hazard recall the threshold must reach on cross-validation


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fixbench_rows() -> list[dict]:
    rows = []
    for c in read(ROOT / "eval" / "fixbench" / "v1" / "cases.jsonl"):
        hazard = c["gold"]["hazard"] if c["tag"] == "safety-text" else "none"
        rows.append({"text": c["text"], "label": hazard})
    return rows


def build(c: float):
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=30000),
        LogisticRegression(C=c, class_weight="balanced", max_iter=3000),
    )


def hazard_prob(model, texts) -> np.ndarray:
    proba = model.predict_proba(texts)
    none_idx = list(model.classes_).index("none")
    return 1.0 - proba[:, none_idx]


def detection_metrics(labels: list[str], flagged: list[bool]) -> dict:
    pos = [f for lab, f in zip(labels, flagged) if lab != "none"]
    neg = [f for lab, f in zip(labels, flagged) if lab == "none"]
    return {
        "hazard_recall": round(sum(pos) / len(pos), 3) if pos else None,
        "false_alarm_rate": round(sum(neg) / len(neg), 3) if neg else None,
        "n_hazard": len(pos),
        "n_benign": len(neg),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default="templates")
    ap.add_argument("--export", action="store_true")
    args = ap.parse_args()
    tag = args.train.replace(",", "+")

    train = [r for s in args.train.split(",") for r in read(DATA / SOURCES[s])]
    X, y = [r["text"] for r in train], [r["label"] for r in train]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)

    # 1) choose C by cross-validated macro-F1, 2) choose the hazard threshold on the same CV.
    from sklearn.metrics import f1_score

    best = None
    for c in (0.5, 1.0, 2.0, 4.0, 8.0):
        pred = cross_val_predict(build(c), X, y, cv=cv)
        f1 = f1_score(y, pred, average="macro")
        if best is None or f1 > best[1]:
            best = (c, f1)
    c_best = best[0]
    proba = cross_val_predict(build(c_best), X, y, cv=cv, method="predict_proba")
    classes = sorted(set(y))
    p_hazard = 1.0 - proba[:, classes.index("none")]
    is_hazard = np.array([lab != "none" for lab in y])
    threshold = 0.5
    for t in np.round(np.arange(0.95, 0.04, -0.01), 2):
        if (p_hazard[is_hazard] >= t).mean() >= TARGET_VAL_RECALL:
            threshold = float(t)
            break

    model = build(c_best).fit(X, y)

    def evaluate(rows: list[dict]) -> dict:
        texts, labels = [r["text"] for r in rows], [r["label"] for r in rows]
        clf = (hazard_prob(model, texts) >= threshold).tolist()
        rules = [bool(safety.check_text(t)) for t in texts]
        both = [a or b for a, b in zip(clf, rules)]
        pred_class = model.predict(texts)
        hz = [(lab, p) for lab, p, f in zip(labels, pred_class, clf) if lab != "none" and f]
        return {
            "rules_only": detection_metrics(labels, rules),
            "classifier_only": detection_metrics(labels, clf),
            "rules_or_classifier": detection_metrics(labels, both),
            "classifier_hazard_type_accuracy": round(sum(a == b for a, b in hz) / len(hz), 3) if hz else None,
            "missed_by_rules_or_classifier": [t for t, lab, f in zip(texts, labels, both) if lab != "none" and not f],
            "false_alarms_rules_or_classifier": [t for t, lab, f in zip(texts, labels, both) if lab == "none" and f],
        }

    metrics = {
        "train_sources": args.train,
        "n_train": len(train),
        "C": c_best,
        "cv_macro_f1": round(best[1], 3),
        "threshold": threshold,
        "cv_hazard_recall_at_threshold": round(float((p_hazard[is_hazard] >= threshold).mean()), 3),
        "cv_false_alarm_at_threshold": round(float((p_hazard[~is_hazard] >= threshold).mean()), 3),
        "held_out": evaluate(read(DATA / "test_handwritten.jsonl")),
        "fixbench_texts": evaluate(fixbench_rows()),
    }
    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / f"metrics-{tag}.json").write_text(json.dumps(metrics, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k not in ("held_out", "fixbench_texts")}))
    for split in ("held_out", "fixbench_texts"):
        m = metrics[split]
        print(split, {k: m[k] for k in ("rules_only", "classifier_only", "rules_or_classifier")})

    if args.export:
        export(model, threshold, metrics, tag)


def export(model, threshold: float, metrics: dict, tag: str) -> None:
    vec, lr = model.named_steps["tfidfvectorizer"], model.named_steps["logisticregression"]
    vocab = {term: int(i) for term, i in vec.vocabulary_.items()}
    order = sorted(vocab, key=vocab.get)
    selftest_texts = [r["text"] for r in read(DATA / "test_handwritten.jsonl")][::6]
    payload = {
        "name": "FT-1 safety classifier",
        "version": f"1.0-{tag}",
        "ngram_range": list(vec.ngram_range),
        "classes": [str(c) for c in lr.classes_],
        "threshold": threshold,
        "terms": order,
        "idf": [round(float(vec.idf_[vocab[t]]), 5) for t in order],
        "coef": [[round(float(w), 5) for w in row] for row in lr.coef_],
        "intercept": [round(float(b), 5) for b in lr.intercept_],
        "selftest": [
            {"text": t, "p_hazard": round(float(p), 4)}
            for t, p in zip(selftest_texts, hazard_prob(model, selftest_texts))
        ],
        "metrics": {k: metrics[k] for k in ("n_train", "C", "cv_macro_f1", "threshold")},
    }
    EXPORT.parent.mkdir(exist_ok=True)
    EXPORT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"exported {EXPORT.relative_to(ROOT)} ({EXPORT.stat().st_size / 1e6:.2f} MB, {len(order)} features)")


if __name__ == "__main__":
    main()
