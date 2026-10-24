"""Bayesian diagnostic engine.

Causes are treated as mutually exclusive, and answers as conditionally independent given the
cause (naive Bayes). The next question is the one with the highest expected information gain.
No LLM is involved, so diagnosis keeps working when every LLM provider is down.
"""

import math
from dataclasses import dataclass
from typing import Literal

from .knowledge import ProductKB, Question

Answer = Literal["yes", "no", "unknown"]

CONFIDENT = 0.75  # stop asking once the top cause reaches this posterior
MAX_QUESTIONS = 5  # informative (yes/no) answers to non-safety questions
MAX_ASKED = 8  # hard cap on non-safety questions, including "not sure" answers
MIN_GAIN_BITS = 0.02


@dataclass(frozen=True)
class Ranked:
    cause_id: str
    p: float


def posterior(kb: ProductKB, answers: dict[str, Answer]) -> list[Ranked]:
    log_p = {c.id: math.log(c.prior) for c in kb.causes}
    for qid, ans in answers.items():
        q = kb.question(qid)
        if q is None or ans == "unknown":
            continue
        for cid in log_p:
            p_yes = q.p_yes[cid]
            log_p[cid] += math.log(p_yes if ans == "yes" else 1 - p_yes)
    top = max(log_p.values())
    weights = {cid: math.exp(lp - top) for cid, lp in log_p.items()}
    total = sum(weights.values())
    ranked = [Ranked(cid, w / total) for cid, w in weights.items()]
    return sorted(ranked, key=lambda r: r.p, reverse=True)


def entropy(probs: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probs if p > 0)


def expected_gain(kb: ProductKB, current: list[Ranked], q: Question) -> float:
    dist = {r.cause_id: r.p for r in current}
    p_yes = sum(dist[c] * q.p_yes[c] for c in dist)
    after = 0.0
    for p_branch, like in ((p_yes, q.p_yes), (1 - p_yes, {c: 1 - v for c, v in q.p_yes.items()})):
        if p_branch <= 0:
            continue
        branch = [dist[c] * like[c] / p_branch for c in dist]
        after += p_branch * entropy(branch)
    return entropy(list(dist.values())) - after


def next_question(
    kb: ProductKB, answers: dict[str, Answer], current: list[Ranked]
) -> Question | None:
    """Safety questions first, then the most informative question, until confident or done."""
    for q in kb.questions:
        if q.safety and q.id not in answers:
            return q
    # "Not sure" answers don't use up the budget (FixBench-IN v1 showed that unanswerable
    # questions were starving the useful ones), but MAX_ASKED still bounds the session.
    asked = [q for q in kb.questions if not q.safety and q.id in answers]
    informative = [q for q in asked if answers[q.id] != "unknown"]
    if len(informative) >= MAX_QUESTIONS or len(asked) >= MAX_ASKED or current[0].p >= CONFIDENT:
        return None
    candidates = [q for q in kb.questions if q.id not in answers]
    if not candidates:
        return None
    best = max(candidates, key=lambda q: expected_gain(kb, current, q))
    return best if expected_gain(kb, current, best) >= MIN_GAIN_BITS else None


def confidence_label(p: float) -> Literal["likely", "possible", "uncertain"]:
    if p >= CONFIDENT:
        return "likely"
    return "possible" if p >= 0.45 else "uncertain"
