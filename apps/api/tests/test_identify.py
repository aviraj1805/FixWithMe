import base64
import json

from fastapi.testclient import TestClient

from fixwithme_api.config import Settings
from fixwithme_api.llm import FallbackRouter
from fixwithme_api.llm.fake import FakeProvider
from fixwithme_api.main import create_app

IMG = base64.b64encode(b"\xff\xd8\xff fake jpeg").decode()


def client(reply):
    app = create_app(Settings(env="test", llm_chain=["fake"], retrieval="off"))
    fake = FakeProvider(json.dumps(reply))
    app.state.llm = FallbackRouter([fake])
    return TestClient(app), fake


def test_photo_identifies_a_curated_item():
    c, fake = client(
        {"item": "battery_toy", "name": "TV remote", "problem": "white crust on the springs"}
    )
    out = c.post("/v1/identify", json={"image": IMG}).json()
    assert out == {
        "item": "battery_toy",
        "name": "TV remote",
        "problem": "white crust on the springs",
        "text": "TV remote: white crust on the springs",
    }
    assert fake.calls[0].images[0][1] == "image/jpeg"


def test_other_item_has_no_product_id():
    c, _ = client({"item": "other_item", "name": "Mixer grinder", "problem": ""})
    out = c.post("/v1/identify", json={"image": IMG}).json()
    assert out["item"] is None and out["problem"] is None and out["text"] == "Mixer grinder"


def test_bad_inputs_rejected():
    c, _ = client({})
    assert c.post("/v1/identify", json={"image": "%%%"}).status_code == 422
    assert c.post("/v1/identify", json={"image": IMG, "mime": "image/gif"}).status_code == 422


def test_model_failure_is_503():
    c, _ = client("not json")
    assert c.post("/v1/identify", json={"image": IMG}).status_code == 503
