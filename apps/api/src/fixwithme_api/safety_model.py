"""FT-1 safety classifier runtime: character n-gram TF-IDF + multinomial logistic regression.

A dependency-free re-implementation of the scikit-learn pipeline trained in
ml/safety_classifier/train.py, so the API needs no ML runtime on its 512 MB instance. The
exported model carries self-test cases (scikit-learn's own outputs); tests check that this
runtime reproduces them.
"""

import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "models" / "safety_ft1.json"
_MULTI_SPACE = re.compile(r"\s\s+")


@dataclass(frozen=True)
class Prediction:
    label: str  # most likely class, possibly "none"
    hazard: str  # most likely hazard class, ignoring "none"
    p_hazard: float  # 1 - P(none)
    flagged: bool  # p_hazard >= threshold


class SafetyModel:
    def __init__(self, data: dict) -> None:
        self.version: str = data["version"]
        self.classes: list[str] = data["classes"]
        self.threshold: float = data["threshold"]
        self.min_n, self.max_n = data["ngram_range"]
        self.index = {term: i for i, term in enumerate(data["terms"])}
        self.idf: list[float] = data["idf"]
        self.coef: list[list[float]] = data["coef"]
        self.intercept: list[float] = data["intercept"]
        self.selftest: list[dict] = data.get("selftest", [])
        self._none = self.classes.index("none")

    def _ngrams(self, text: str):
        # Mirrors sklearn's "char_wb" analyzer after lowercasing.
        text = _MULTI_SPACE.sub(" ", text.lower())
        for word in text.split():
            w = f" {word} "
            for n in range(self.min_n, self.max_n + 1):
                offset = 0
                yield w[offset : offset + n]
                while offset + n < len(w):
                    offset += 1
                    yield w[offset : offset + n]
                if offset == 0:  # a short word is counted only once
                    break

    def probabilities(self, text: str) -> list[float]:
        counts = Counter(self.index[g] for g in self._ngrams(text) if g in self.index)
        weights = {i: (1.0 + math.log(c)) * self.idf[i] for i, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in weights.values())) or 1.0
        scores = [
            b + sum(row[i] * v / norm for i, v in weights.items())
            for row, b in zip(self.coef, self.intercept, strict=True)
        ]
        top = max(scores)
        exps = [math.exp(s - top) for s in scores]
        total = sum(exps)
        return [e / total for e in exps]

    def predict(self, text: str) -> Prediction:
        probs = self.probabilities(text)
        p_hazard = 1.0 - probs[self._none]
        hazard_idx = max((i for i in range(len(probs)) if i != self._none), key=probs.__getitem__)
        label_idx = max(range(len(probs)), key=probs.__getitem__)
        return Prediction(
            label=self.classes[label_idx],
            hazard=self.classes[hazard_idx],
            p_hazard=p_hazard,
            flagged=p_hazard >= self.threshold,
        )


@lru_cache
def load() -> SafetyModel | None:
    if not MODEL_PATH.exists():
        log.warning("FT-1 model not found at %s; safety gate runs on rules only", MODEL_PATH)
        return None
    with MODEL_PATH.open(encoding="utf-8") as f:
        return SafetyModel(json.load(f))
