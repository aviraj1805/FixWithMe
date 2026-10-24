import json

import pytest
from fastapi.testclient import TestClient

from fixwithme_api import answer as answer_mod
from fixwithme_api.config import Settings
from fixwithme_api.llm import FallbackRouter
from fixwithme_api.llm.fake import FakeProvider
from fixwithme_api.main import create_app
from fixwithme_api.retrieval import Embedder, LocalBackend, Passage, Retriever, fuse

CORPUS = [
    {
        "id": "kb:ceiling_fan:cause:capacitor_weak:en",
        "source_type": "kb",
        "lang": "en",
        "title": "Ceiling fan — Weak capacitor",
        "url": None,
        "license": "Fix with Me curated",
        "product": "ceiling_fan",
        "safety_level": 2,
        "text": "A weak capacitor makes a ceiling fan hum without spinning, or run slowly. "
        "Replace it with one of the same microfarad and voltage rating.",
    },
    {
        "id": "wiki:en:Motor capacitor#0",
        "source_type": "wikipedia",
        "lang": "en",
        "title": "Motor capacitor",
        "url": "https://en.wikipedia.org/wiki/Motor_capacitor",
        "license": "CC BY-SA 4.0",
        "product": None,
        "safety_level": None,
        "text": "A motor capacitor is used with a single-phase induction motor to create a "
        "rotating magnetic field for starting.",
    },
    {
        "id": "kb:headphones:cause:pairing_glitch:en",
        "source_type": "kb",
        "lang": "en",
        "title": "Headphones — Pairing glitch",
        "url": None,
        "license": "Fix with Me curated",
        "product": "headphones",
        "safety_level": 0,
        "text": "Forget the earbuds in Bluetooth settings and pair them again.",
    },
]
CAP = CORPUS[0]["id"]
WIKI = CORPUS[1]["id"]


@pytest.fixture()
def retriever(tmp_path):
    path = tmp_path / "corpus.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in CORPUS), encoding="utf-8")
    return Retriever(LocalBackend(path, None), Embedder(None))


def router(reply: dict | str) -> FallbackRouter:
    return FallbackRouter([FakeProvider(reply if isinstance(reply, str) else json.dumps(reply))])


def make_client(retriever, draft, verdicts=None):
    app = create_app(Settings(env="test", llm_chain=["fake"], retrieval="off"))
    app.state.retriever = retriever
    app.state.llm = router(draft) if draft is not None else None
    app.state.verifier = router({"verdicts": verdicts}) if verdicts is not None else None
    return TestClient(app)


def ask(client, **body):
    resp = client.post("/v1/ask", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


DRAFT = {
    "can_answer": True,
    "claims": [
        {"text": "A weak capacitor makes the fan hum without spinning.", "sources": [CAP]},
        {"text": "The capacitor creates a rotating field for starting.", "sources": [WIKI]},
    ],
}


def test_supported_claims_are_answered_with_sources(retriever):
    client = make_client(retriever, DRAFT, ["supported", "supported"])
    out = ask(client, question="why does my fan capacitor hum", item="ceiling_fan")
    assert out["state"] == "answer" and out["verified"] is True
    assert [c["sources"] for c in out["claims"]] == [[CAP], [WIKI]]
    assert {s["id"] for s in out["sources"]} == {CAP, WIKI}
    assert out["tier"] == "sourced"  # mixes curated and Wikipedia passages


def test_risky_procedure_links_the_full_guide(tmp_path):
    row = {
        "id": "kb:ceiling_fan:procedure:replace_capacitor:en",
        "source_type": "kb",
        "lang": "en",
        "title": "Ceiling fan — Replace the capacitor",
        "url": None,
        "license": "Fix with Me curated",
        "product": "ceiling_fan",
        "safety_level": 2,
        "text": "Switch off the MCB, discharge the old capacitor, fit one with the same rating.",
    }
    path = tmp_path / "c.jsonl"
    path.write_text(json.dumps(row), encoding="utf-8")
    r = Retriever(LocalBackend(path, None), Embedder(None))
    draft = {
        "can_answer": True,
        "claims": [{"text": "Switch off the MCB first.", "sources": [row["id"]]}],
    }
    out = ask(
        make_client(r, draft, ["supported"]), question="replace capacitor", item="ceiling_fan"
    )
    assert out["guides"] == [
        {"item": "ceiling_fan", "procedure_id": "replace_capacitor", "safety_level": 2}
    ]
    assert out["caution"]


def test_unsupported_claim_is_dropped(retriever):
    client = make_client(retriever, DRAFT, ["supported", "unsupported"])
    out = ask(client, question="why does my fan capacitor hum", item="ceiling_fan")
    assert out["state"] == "answer" and out["dropped_unsupported"] == 1
    assert len(out["claims"]) == 1 and out["tier"] == "curated"


def test_every_claim_unsupported_abstains(retriever):
    client = make_client(retriever, DRAFT, ["unsupported", "unsupported"])
    out = ask(client, question="why does my fan capacitor hum", item="ceiling_fan")
    assert out["state"] == "abstain" and out["claims"] == [] and out["dropped_unsupported"] == 2


def test_unsafe_claim_is_removed_even_if_supported(retriever):
    draft = {
        "can_answer": True,
        "claims": [
            {"text": "Touch the live terminal to check it.", "sources": [CAP]},
            {"text": "A weak capacitor makes the fan hum.", "sources": [CAP]},
        ],
    }
    client = make_client(retriever, draft, ["supported"])
    out = ask(client, question="fan capacitor hum", item="ceiling_fan")
    assert out["state"] == "answer" and out["dropped_unsafe"] == 1
    assert [c["text"] for c in out["claims"]] == ["A weak capacitor makes the fan hum."]


def test_claims_citing_unknown_passages_are_never_shown(retriever):
    draft = {"can_answer": True, "claims": [{"text": "Made up.", "sources": ["nope"]}]}
    client = make_client(retriever, draft, [])
    out = ask(client, question="fan capacitor hum", item="ceiling_fan")
    assert out["state"] == "abstain"


def test_no_passages_abstains_without_calling_the_llm(retriever):
    client = make_client(retriever, DRAFT, ["supported", "supported"])
    out = ask(client, question="zzzz qqqq", item="ceiling_fan")
    assert out["state"] == "abstain"
    assert client.app.state.llm.providers[0].calls == []


def test_model_says_it_cannot_answer(retriever):
    client = make_client(retriever, {"can_answer": False, "claims": []}, [])
    out = ask(client, question="fan capacitor price", item="ceiling_fan")
    assert out["state"] == "abstain"


def test_without_llm_abstains(retriever):
    client = make_client(retriever, None)
    assert ask(client, question="fan capacitor hum")["state"] == "abstain"


def test_verifier_failure_keeps_claims_but_marks_unverified(retriever):
    client = make_client(retriever, DRAFT)
    client.app.state.verifier = router("not json")
    out = ask(client, question="why does my fan capacitor hum", item="ceiling_fan")
    assert out["state"] == "answer" and out["verified"] is False and len(out["claims"]) == 2


def test_malformed_draft_abstains(retriever):
    client = make_client(retriever, "not json", [])
    assert ask(client, question="fan capacitor hum")["state"] == "abstain"


def test_product_filter_excludes_other_products(retriever):
    hits = retriever.search("pair earbuds bluetooth", product="ceiling_fan", k=5)
    assert all(p.product in (None, "ceiling_fan") for p in hits)


def test_hazard_in_question_stops_before_retrieval(retriever):
    client = make_client(retriever, DRAFT, ["supported", "supported"])
    out = ask(client, question="fan capacitor is smoking, can I still use it?", item="ceiling_fan")
    assert out["state"] == "stop" and out["stop"]["hazard"] == "fire_smoke"
    assert client.app.state.llm.providers[0].calls == []


def test_confirm_hazard_returns_stop(retriever):
    client = make_client(retriever, DRAFT)
    out = ask(client, question="anything", confirm_hazard="shock", lang="hi")
    assert out["state"] == "stop" and out["stop"]["call"] == "112"


def test_unknown_item_rejected(retriever):
    client = make_client(retriever, DRAFT)
    assert (
        client.post("/v1/ask", json={"question": "hi there", "item": "rocket"}).status_code == 422
    )


def test_hindi_abstain_message(retriever):
    client = make_client(retriever, None)
    out = ask(client, question="कुछ भी", lang="hi")
    assert out["state"] == "abstain" and "मिस्त्री" in out["say"]


def test_fuse_rewards_agreement_between_rankings():
    def p(i, v, k):
        return Passage(i, i, None, "x", "kb", "en", None, None, "", vec_rank=v, kw_rank=k)

    out = fuse([p("a", 1, None), p("b", 2, 2), p("c", None, 1)], "hybrid", 3)
    assert out[0].id == "b"
    assert [x.id for x in fuse([p("a", 1, None), p("c", None, 1)], "keyword", 3)] == ["c"]


@pytest.mark.parametrize(
    "text",
    [
        "Open the switchboard and check the wires.",
        "You can bypass the MCB for now.",
        "Charge the swollen battery slowly.",
        "Test it while plugged in.",
        "Get the refrigerant gas refilled yourself.",
    ],
)
def test_unsafe_patterns(text):
    assert answer_mod.unsafe(text)


@pytest.mark.parametrize(
    "text",
    [
        "Switch off the MCB before you start.",
        "Unplug the board before cleaning it.",
        "Do not charge a swollen battery; take it to a recycler.",
    ],
)
def test_safe_advice_not_flagged(text):
    assert not answer_mod.unsafe(text)


# ---------------------------------------------------------------- Tier C (web-grounded)

from fixwithme_api.web import WebAnswer, WebSource, parse  # noqa: E402


def test_parse_keeps_only_grounded_safe_bullets():
    text = (
        "* **Check the gasket:** a worn rubber ring lets water through.\n"
        "* Open the motor base and rewire it.\n"
        "* Ask a technician if it still leaks.\n"
    )
    supports = [
        ("a worn rubber ring lets water through.", [0, 2]),
        ("Open the motor base and rewire it.", [1]),
    ]
    claims, ungrounded, dropped_unsafe = parse(text, supports)
    assert claims == [("Check the gasket: a worn rubber ring lets water through.", [0, 2])]
    assert ungrounded == 1  # the technician line had no web source
    assert dropped_unsafe == 1  # opening the motor base is level 2+, never allowed in Tier C


@pytest.mark.parametrize(
    "text",
    [
        "Unscrew the base cover and check the coupler.",
        "Replace the thermal fuse inside.",
        "Solder the loose wire back.",
        "Use a multimeter to test the cord.",
    ],
)
def test_tier_c_blocks_level_2_steps(text):
    from fixwithme_api.web import above_level_1

    assert above_level_1(text)


@pytest.mark.parametrize(
    "text",
    [
        "Check the jar gasket for cracks.",
        "Make sure the jar is locked onto the base.",
        "Unplug it and let it cool.",
    ],
)
def test_tier_c_allows_level_0_1_checks(text):
    from fixwithme_api.web import above_level_1

    assert not above_level_1(text)


def test_parse_drops_unsafe_grounded_bullet():
    claims, _, dropped = parse(
        "- Test it while plugged in.\n", [("Test it while plugged in.", [0])]
    )
    assert claims == [] and dropped == 1


class FakeWeb:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    async def answer(self, question, lang):
        self.calls += 1
        return self.result


WEB = WebAnswer(
    claims=[("Check the jar gasket for wear.", [0])],
    sources=[WebSource(title="vidiem.in", url="https://example.org/r")],
    search_html="<div>chips</div>",
)


def test_ask_anyway_falls_back_to_web_when_corpus_abstains(retriever):
    client = make_client(retriever, {"can_answer": False, "claims": []}, [])
    client.app.state.web = FakeWeb(WEB)
    out = ask(client, question="mixer grinder jar leaking from the bottom", web=True)
    assert out["state"] == "answer" and out["tier"] == "web" and out["verified"] is False
    assert out["claims"] == [{"text": "Check the jar gasket for wear.", "sources": ["web:0"]}]
    assert out["sources"][0]["source_type"] == "web" and out["search_html"] and out["caution"]


def test_web_is_not_used_without_the_flag_or_for_curated_items(retriever):
    client = make_client(retriever, {"can_answer": False, "claims": []}, [])
    client.app.state.web = web = FakeWeb(WEB)
    assert ask(client, question="mixer grinder jar leaking")["state"] == "abstain"
    assert (
        ask(client, question="fan capacitor hum", item="ceiling_fan", web=True)["state"]
        == "abstain"
    )
    assert web.calls == 0


def test_web_hazard_still_stops_first(retriever):
    client = make_client(retriever, None)
    client.app.state.web = web = FakeWeb(WEB)
    out = ask(client, question="mixer is giving electric shock", web=True)
    assert out["state"] == "stop" and web.calls == 0


def test_web_with_no_grounded_claims_abstains(retriever):
    client = make_client(retriever, None)
    client.app.state.web = FakeWeb(WebAnswer())
    assert ask(client, question="mixer grinder jar leaking", web=True)["state"] == "abstain"


# ---------------------------------------------------------------- general questions vs reports


@pytest.mark.parametrize(
    "text",
    [
        "Why do lithium-ion batteries swell or catch fire?",
        "What is the let-go threshold in an electric shock?",
        "Why can a capacitor still give a shock after the power is off?",
    ],
)
def test_general_hazard_question_asks_once_then_answers(retriever, text):
    client = make_client(retriever, DRAFT, ["supported", "supported"])
    assert ask(client, question=text)["state"] == "confirm"
    assert ask(client, question=text, safety_checked=True)["state"] in ("answer", "abstain")


@pytest.mark.parametrize(
    "text",
    [
        "My earbud battery has swollen up, can I keep charging it?",
        "How do I fix a leaking LPG pipe at home?",
        "Why is my fan smoking?",
        "What should I do, I got a shock from the switch",
    ],
)
def test_personal_or_active_hazard_still_stops(retriever, text):
    client = make_client(retriever, DRAFT, ["supported"])
    assert ask(client, question=text)["state"] == "stop"
    assert ask(client, question=text, safety_checked=True)["state"] == "stop"


def test_rate_limit_returns_429():
    app = create_app(Settings(env="prod", llm_chain=["fake"], retrieval="off", rate_per_minute=2))
    c = TestClient(app)
    codes = [c.post("/v1/ask", json={"question": "fan hum"}).status_code for _ in range(3)]
    assert codes[:2] == [200, 200] and codes[2] == 429
    assert c.get("/health").status_code == 200  # GETs are not limited
