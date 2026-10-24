import pytest
from fastapi.testclient import TestClient

from fixwithme_api.config import Settings
from fixwithme_api.main import create_app


@pytest.fixture()
def client():
    # The fake provider replies with non-JSON, so extraction runs on keyword rules only.
    return TestClient(create_app(Settings(env="test", llm_chain=["fake"])))


def step(client, **body):
    resp = client.post("/v1/sessions/step", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_dangerous_text_stops_before_anything_else(client):
    out = step(client, text="ceiling fan has a burning smell", lang="en")
    assert out["state"] == "stop"
    assert out["stop"]["hazard"] == "fire_smoke" and out["stop"]["call"] == "112"


def test_hindi_stop_is_localised(client):
    out = step(client, text="पंखे से धुआं निकल रहा है", lang="hi")
    assert out["state"] == "stop" and out["say"] == "रुकें! बिजली बंद करें।"


def test_unclear_item_asks_to_clarify(client):
    assert step(client, text="it is not working")["state"] == "clarify"


def test_other_items_are_unsupported_for_now(client):
    assert step(client, text="my table fan is broken")["state"] == "unsupported"


def test_first_question_is_the_safety_question(client):
    out = step(client, text="my ceiling fan hums but won't spin")
    assert (
        out["state"] == "question"
        and out["question"]["id"] == "burning"
        and out["question"]["safety"]
    )
    assert out["answers"]["hums"] == "yes" and out["item"] == "ceiling_fan"
    assert out["tier"] == "curated"


def test_answering_yes_to_burning_stops(client):
    out = step(client, item="ceiling_fan", answers={"hums": "yes", "burning": "yes"})
    assert out["state"] == "stop"


def test_full_session_reaches_capacitor_diagnosis(client):
    answers = {"hums": "yes", "burning": "no"}
    for _ in range(6):
        out = step(client, item="ceiling_fan", answers=answers)
        if out["state"] != "question":
            break
        qid = out["question"]["id"]
        answers[qid] = {
            "push_spins": "yes",
            "noise": "no",
            "slow": "yes",
            "speed_change": "yes",
        }.get(qid, "unknown")
    assert out["state"] == "diagnosis"
    d = out["diagnosis"]
    assert (
        d["cause_id"] == "capacitor_weak"
        and d["procedure_id"] == "replace_capacitor"
        and not d["professional"]
    )
    assert out["causes"][0]["id"] == "capacitor_weak" and out["causes"][0]["p"] >= 0.75


def test_stiff_fan_is_referred_to_a_professional(client):
    answers = {"burning": "no", "hums": "yes", "push_spins": "no", "noise": "yes", "slow": "yes"}
    out = step(client, item="ceiling_fan", answers=answers)
    assert out["state"] == "diagnosis" and out["diagnosis"]["professional"]


def test_procedure_has_cited_steps(client):
    p = client.get("/v1/procedures/replace_capacitor?lang=hi").json()
    assert p["tier"] == "curated" and p["safety_level"] == 2 and len(p["steps"]) == 6
    assert all(s["sources"] for s in p["steps"])
    assert p["cost_inr"]["basis"] == "estimate"


def test_professional_procedure_has_no_steps(client):
    p = client.get("/v1/procedures/refer_winding").json()
    assert p["safety_level"] == 3 and p["steps"] == [] and p["professional"]


def test_unknown_procedure_404(client):
    assert client.get("/v1/procedures/nope").status_code == 404


def test_outcome_without_supabase_is_not_stored(client):
    body = {"cause_id": "capacitor_weak", "procedure_id": "replace_capacitor", "resolved": True}
    assert client.post("/v1/outcomes", json=body).json() == {"stored": False}


def test_outcome_rejects_unknown_ids(client):
    body = {"cause_id": "x", "procedure_id": "replace_capacitor", "resolved": True}
    assert client.post("/v1/outcomes", json=body).status_code == 422


def test_text_length_is_limited(client):
    assert client.post("/v1/sessions/step", json={"text": "a" * 1001}).status_code == 422
