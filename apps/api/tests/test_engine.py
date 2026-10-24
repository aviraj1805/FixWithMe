import math

import pytest

from fixwithme_api import engine, knowledge


@pytest.fixture(scope="module")
def kb():
    return knowledge.load("ceiling_fan")


def top(kb, answers):
    return engine.posterior(kb, answers)[0]


def test_posterior_is_a_distribution(kb):
    ranked = engine.posterior(kb, {"hums": "yes", "slow": "no"})
    assert math.isclose(sum(r.p for r in ranked), 1.0)
    assert ranked == sorted(ranked, key=lambda r: r.p, reverse=True)


def test_no_answers_returns_priors(kb):
    ranked = {r.cause_id: r.p for r in engine.posterior(kb, {})}
    for c in kb.causes:
        assert math.isclose(ranked[c.id], c.prior)


def test_unknown_answers_do_not_move_the_posterior(kb):
    assert engine.posterior(kb, {"hums": "unknown"}) == engine.posterior(kb, {})


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ({"burning": "no", "hums": "yes", "push_spins": "yes"}, "capacitor_weak"),
        ({"burning": "no", "hums": "yes", "push_spins": "no", "noise": "yes"}, "bearing_stiff"),
        ({"burning": "no", "hums": "no", "other_power": "no"}, "no_power"),
        (
            {"burning": "no", "runs": "yes", "speed_change": "no", "hums": "no", "slow": "no"},
            "regulator_faulty",
        ),
    ],
)
def test_textbook_cases_rank_the_expected_cause_first(kb, answers, expected):
    assert top(kb, answers).cause_id == expected


def test_safety_question_is_always_asked_first(kb):
    q = engine.next_question(kb, {"hums": "yes"}, engine.posterior(kb, {"hums": "yes"}))
    assert q.id == "burning" and q.safety


def test_next_question_never_repeats_and_has_positive_gain(kb):
    answers = {"burning": "no", "hums": "yes"}
    ranked = engine.posterior(kb, answers)
    q = engine.next_question(kb, answers, ranked)
    assert q is not None and q.id not in answers
    assert engine.expected_gain(kb, ranked, q) > 0


def test_stops_asking_once_confident(kb):
    answers = {"burning": "no", "hums": "yes", "push_spins": "yes", "noise": "no"}
    ranked = engine.posterior(kb, answers)
    assert ranked[0].p >= engine.CONFIDENT
    assert engine.next_question(kb, answers, ranked) is None


def test_not_sure_answers_do_not_use_the_budget(kb):
    answers = {"burning": "no", "hums": "unknown", "push_spins": "unknown", "slow": "unknown"}
    assert engine.next_question(kb, answers, engine.posterior(kb, answers)) is not None


def test_informative_budget_is_respected(kb, monkeypatch):
    monkeypatch.setattr(engine, "CONFIDENT", 0.999)  # isolate the budget from the confidence stop
    answers = {
        "burning": "no",
        "runs": "yes",
        "hums": "no",
        "slow": "no",
        "noise": "no",
        "other_power": "yes",
    }
    assert engine.next_question(kb, answers, engine.posterior(kb, answers)) is None


def test_total_questions_are_capped(kb):
    answers = {"burning": "no", **{q.id: "unknown" for q in kb.questions if not q.safety}}
    assert engine.next_question(kb, answers, engine.posterior(kb, answers)) is None


def test_entropy():
    assert engine.entropy([0.5, 0.5]) == 1.0
    assert engine.entropy([1.0, 0.0]) == 0.0


def test_confidence_labels():
    assert engine.confidence_label(0.9) == "likely"
    assert engine.confidence_label(0.5) == "possible"
    assert engine.confidence_label(0.3) == "uncertain"
