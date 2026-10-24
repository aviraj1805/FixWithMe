"""FT-1 runtime: parity with the trained scikit-learn model and its place in the safety gate."""

import pytest

from fixwithme_api import safety, safety_model


@pytest.fixture(scope="module")
def model():
    m = safety_model.load()
    assert m is not None, "export the model with ml/safety_classifier/train.py --export"
    return m


def test_runtime_matches_scikit_learn(model):
    assert model.selftest, "the exported model must carry self-test cases"
    for case in model.selftest:
        assert model.predict(case["text"]).p_hazard == pytest.approx(case["p_hazard"], abs=1e-3)


def test_probabilities_are_a_distribution(model):
    probs = model.probabilities("fan hums but does not spin")
    assert sum(probs) == pytest.approx(1.0) and all(0 <= p <= 1 for p in probs)
    assert set(model.classes) == {"none", *safety.HAZARDS}


@pytest.mark.parametrize("text", ["", "   ", "1234", "🙂"])
def test_degenerate_inputs_do_not_crash(model, text):
    assert 0.0 <= model.predict(text).p_hazard <= 1.0


def test_rules_still_decide_first():
    # A rule hit always wins and names its own hazard, whatever the classifier says.
    assert safety.stop_hazard("my son swallowed a battery") == "button_cell"


def test_gate_returns_none_for_ordinary_problems():
    for text in (
        "my ceiling fan hums but won't spin",
        "earbuds one side not working",
        "TV remote not working",
    ):
        assert safety.stop_hazard(text) is None


def test_every_hazard_has_a_confirm_question():
    assert set(safety.CONFIRM) == set(safety.HAZARDS)


def _client():
    from fastapi.testclient import TestClient

    from fixwithme_api.config import Settings
    from fixwithme_api.main import create_app

    return TestClient(create_app(Settings(env="test", llm_chain=["fake"])))


def _model_only_hazard_text():
    """A message the classifier flags but the rules do not (taken from the model's self-test)."""
    model = safety_model.load()
    for case in model.selftest:
        if case["p_hazard"] >= model.threshold and not safety.check_text(case["text"]):
            return case["text"]
    pytest.skip("no classifier-only hazard among the self-test cases")


def test_classifier_only_hazard_asks_to_confirm_then_stops_or_continues():
    client, text = _client(), _model_only_hazard_text()
    out = client.post("/v1/sessions/step", json={"text": text}).json()
    assert out["state"] == "confirm" and out["confirm"]["hazard"] in safety.HAZARDS
    hazard = out["confirm"]["hazard"]

    yes = client.post("/v1/sessions/step", json={"text": text, "confirm_hazard": hazard}).json()
    assert yes["state"] == "stop" and yes["stop"]["hazard"] == hazard

    no = client.post("/v1/sessions/step", json={"text": text, "safety_checked": True}).json()
    assert no["state"] != "confirm"


def test_rule_hazards_still_stop_without_confirmation():
    out = _client().post("/v1/sessions/step", json={"text": "smoke from the fan motor"}).json()
    assert out["state"] == "stop"


def test_unknown_confirm_hazard_is_rejected():
    resp = _client().post("/v1/sessions/step", json={"confirm_hazard": "nope"})
    assert resp.status_code == 422
