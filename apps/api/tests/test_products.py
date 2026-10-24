"""Multi-product behaviour (R2.1): new families, product detection and new hazards."""

import pytest
from fastapi.testclient import TestClient

from fixwithme_api import engine, knowledge, safety
from fixwithme_api.config import Settings
from fixwithme_api.main import create_app

NO_SAFETY = {
    "extension_board": {"burnt": "no", "hot": "no"},
    "headphones": {"swollen": "no"},
    "battery_toy": {"swallowed": "no", "swollen": "no"},
}

TEXTBOOK = [
    (
        "extension_board",
        {"wall_works": "yes", "reset_popped": "yes", "heavy_load": "yes"},
        "overload_tripped",
    ),
    ("extension_board", {"wall_works": "no"}, "wall_socket_dead"),
    (
        "extension_board",
        {"wall_works": "yes", "some_sockets": "yes", "light_on": "yes"},
        "socket_loose",
    ),
    ("extension_board", {"wiggle": "yes", "light_on": "no", "some_sockets": "no"}, "cord_damaged"),
    (
        "extension_board",
        {"wall_works": "yes", "switch_loose": "yes", "wiggle": "no"},
        "board_switch_faulty",
    ),
    ("headphones", {"wireless": "no", "lint": "yes", "other_device": "no"}, "jack_dirty"),
    ("headphones", {"wireless": "no", "wiggle": "yes", "other_device": "yes"}, "cable_break"),
    ("headphones", {"wireless": "yes", "one_side": "yes", "lights_up": "yes"}, "pairing_glitch"),
    ("headphones", {"wireless": "yes", "lights_up": "no"}, "not_charging"),
    ("headphones", {"wireless": "yes", "other_device": "no", "one_side": "no"}, "source_device"),
    (
        "headphones",
        {"wireless": "no", "other_device": "yes", "wiggle": "no", "lint": "no"},
        "driver_failed",
    ),
    ("battery_toy", {"fresh_tried": "no"}, "batteries_dead"),
    ("battery_toy", {"crust": "yes"}, "contacts_corroded"),
    (
        "battery_toy",
        {"is_remote": "yes", "fresh_tried": "yes", "camera_light": "no"},
        "remote_faulty",
    ),
    ("battery_toy", {"is_remote": "no", "lights_no_move": "yes"}, "drive_jammed"),
    ("battery_toy", {"tap_works": "yes", "fresh_tried": "yes", "crust": "no"}, "wire_loose"),
]


@pytest.mark.parametrize(("product", "answers", "expected"), TEXTBOOK)
def test_textbook_cases(product, answers, expected):
    kb = knowledge.load(product)
    assert engine.posterior(kb, {**NO_SAFETY[product], **answers})[0].cause_id == expected


def test_every_cause_is_reachable_as_top_cause():
    covered = {(p, c) for p, _, c in TEXTBOOK}
    for p in NO_SAFETY:
        for c in knowledge.load(p).causes:
            assert (p, c.id) in covered, f"no textbook case for {p}/{c.id}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("my ceiling fan hums", ["ceiling_fan"]),
        ("extension board stopped working", ["extension_board"]),
        ("spike guard light is off", ["extension_board"]),
        ("one earbud not connecting", ["headphones"]),
        ("मेरे ईयरफ़ोन में एक तरफ़ आवाज़ नहीं", ["headphones"]),
        ("TV remote not working", ["battery_toy"]),
        ("bachche ka khilona nahi chal raha", ["battery_toy"]),
        ("fan ka remote kaam nahi karta", ["battery_toy", "ceiling_fan"]),
        ("my table fan is broken", []),
    ],
)
def test_product_detection(text, expected):
    assert knowledge.detect(text)[0] == expected


HAZARD_PHRASES = {
    "button_cell": [
        "my son swallowed a battery",
        "baby may have swallowed a coin cell from the remote",
        "toddler swallowed a magnet from the toy",
        "bachche ne battery nigal li",
        "beti ne cell kha liya",
        "बच्चे ने बैटरी निगल ली",
    ],
    "battery_swollen": [
        "the earbud case battery is swollen",
        "phone battery is bulging",
        "swollen battery in the toy",
        "battery phool gayi hai",
        "बैटरी फूल गई है",
    ],
}


@pytest.mark.parametrize(
    ("hazard", "text"), [(h, t) for h, ts in HAZARD_PHRASES.items() for t in ts]
)
def test_new_hazards_stop(hazard, text):
    assert safety.check_text(text)[0] == hazard


@pytest.mark.parametrize(
    "text",
    [
        "battery is low",
        "battery khatam ho gayi",
        "my earbuds battery dies fast",
        "new batteries didn't help",
        "he swallowed his food too fast",
        "the remote needs AAA cells",
        "bacche ki remote wali car ki lights jalti hain par chalti nahi",
        "board ki light jal rahi hai par socket kaam nahi karta",
        "लाइट जलती है पर पंखा नहीं चलता",
    ],
)
def test_battery_talk_is_not_a_hazard(text):
    assert safety.check_text(text) == []


# ---------- API ----------


@pytest.fixture()
def client():
    return TestClient(create_app(Settings(env="test", llm_chain=["fake"])))


def step(client, **body):
    resp = client.post("/v1/sessions/step", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.parametrize(
    ("text", "item", "first_q"),
    [
        ("my extension board stopped working after the heater", "extension_board", "burnt"),
        ("one earbud is not working", "headphones", "swollen"),
        ("TV remote not working", "battery_toy", "swallowed"),
    ],
)
def test_new_products_start_with_their_safety_question(client, text, item, first_q):
    out = step(client, text=text)
    assert out["item"] == item and out["question"]["id"] == first_q and out["question"]["safety"]


def test_ambiguous_text_offers_matching_products(client):
    out = step(client, text="fan ka remote kaam nahi karta")
    assert out["state"] == "clarify"
    assert [o["id"] for o in out["options"]] == ["battery_toy", "ceiling_fan"]


@pytest.mark.parametrize(
    ("item", "answers", "hazard"),
    [
        ("battery_toy", {"swallowed": "yes"}, "button_cell"),
        ("headphones", {"swollen": "yes"}, "battery_swollen"),
        ("extension_board", {"burnt": "no", "hot": "yes"}, "fire_smoke"),
    ],
)
def test_safety_answers_route_to_their_hazard(client, item, answers, hazard):
    out = step(client, item=item, answers=answers)
    assert out["state"] == "stop" and out["stop"]["hazard"] == hazard


def test_swallowed_battery_text_beats_every_other_hazard(client):
    out = step(client, text="my son swallowed a battery and there is smoke from the remote")
    assert out["stop"]["hazard"] == "button_cell"


def test_answers_from_another_product_are_dropped(client):
    out = step(client, item="headphones", answers={"swollen": "no", "hums": "yes"})
    assert "hums" not in out["answers"]


def test_unknown_item_is_rejected(client):
    assert client.post("/v1/sessions/step", json={"item": "washing_machine"}).status_code == 422


@pytest.mark.parametrize(
    ("item", "procedure"),
    [(p, pid) for p in knowledge.available() for pid in knowledge.load(p).procedures],
)
def test_every_procedure_is_served(client, item, procedure):
    for lang in ("en", "hi"):
        resp = client.get(f"/v1/procedures/{item}/{procedure}?lang={lang}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] and (body["steps"] or body["professional"])


def test_burning_board_still_stops_even_with_a_light_word():
    assert "fire_smoke" in safety.check_text("light jal rahi hai aur board bhi jal gaya")
