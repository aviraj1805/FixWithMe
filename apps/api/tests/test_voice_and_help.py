import base64
import json

from fastapi.testclient import TestClient

from fixwithme_api.config import Settings
from fixwithme_api.llm import FallbackRouter
from fixwithme_api.llm.fake import FakeProvider
from fixwithme_api.main import create_app
from fixwithme_api.speak import _pcm_to_wav, _rate


def client(reply=None):
    app = create_app(Settings(env="test", llm_chain=["fake"], retrieval="off"))
    fake = FakeProvider(json.dumps(reply) if reply is not None else "x")
    app.state.llm = FallbackRouter([fake])
    return TestClient(app), fake


HELP = {"item": "ceiling_fan", "procedure_id": "replace_capacitor", "step": 3}


def test_step_help_answers_inside_the_guide():
    c, fake = client({"reply": "The two metal tabs on top are the terminals.", "danger": False})
    out = c.post("/v1/step-help", json={**HELP, "question": "where are the terminals?"}).json()
    assert out == {
        "state": "reply",
        "say": "The two metal tabs on top are the terminals.",
        "stop": None,
    }
    assert ">> CURRENT STEP" in fake.calls[0].prompt and "Step 4:" in fake.calls[0].prompt


def test_step_help_photo_showing_danger_stops():
    c, fake = client({"reply": "That wire looks burnt.", "danger": True})
    img = base64.b64encode(b"\xff\xd8 jpeg").decode()
    out = c.post("/v1/step-help", json={**HELP, "image": img}).json()
    assert out["state"] == "stop" and out["stop"]["call"] == "112"
    assert fake.calls[0].images


def test_step_help_hazard_in_question_stops_without_llm():
    c, fake = client({"reply": "x", "danger": False})
    out = c.post("/v1/step-help", json={**HELP, "question": "it is sparking and smoking"}).json()
    assert out["state"] == "stop" and fake.calls == []


def test_step_help_unsafe_reply_is_replaced():
    c, _ = client({"reply": "Just test it while plugged in.", "danger": False})
    out = c.post("/v1/step-help", json={**HELP, "question": "how do I know it works?"}).json()
    assert out["state"] == "reply" and "plugged in" not in out["say"]


def test_step_help_validation():
    c, _ = client({"reply": "x", "danger": False})
    assert c.post("/v1/step-help", json={**HELP, "question": ""}).status_code == 422
    assert c.post("/v1/step-help", json={**HELP, "step": 40, "question": "hi"}).status_code == 404
    assert (
        c.post("/v1/step-help", json={**HELP, "item": "rocket", "question": "hi"}).status_code
        == 422
    )


def test_speak_without_tts_is_503():
    c, _ = client()
    assert c.post("/v1/speak", json={"text": "hello"}).status_code == 503


def test_pcm_wrapped_as_wav():
    wav = _pcm_to_wav(b"\x00\x00" * 10, _rate("audio/L16;codec=pcm;rate=24000"))
    assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE" and len(wav) == 44 + 20
