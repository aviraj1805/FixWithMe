import asyncio
import json

import pytest
import yaml
from pydantic import ValidationError

from fixwithme_api import knowledge, pii, safety
from fixwithme_api.extract import extract
from fixwithme_api.llm import FallbackRouter, LLMRequest, LLMResult, LLMUnavailable
from fixwithme_api.llm.fake import FakeProvider


@pytest.fixture(scope="module")
def kb():
    return knowledge.load("ceiling_fan")


def run(coro):
    return asyncio.run(coro)


# ---------- knowledge ----------


def test_ceiling_fan_kb_is_valid_and_draft(kb):
    assert kb.tier == "curated"  # not "verified" until a technician reviews it
    assert any(q.safety for q in kb.questions)


def _raw():
    with (knowledge.KNOWLEDGE_DIR / "ceiling_fan.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_kb_rejects_priors_that_do_not_sum_to_one():
    raw = _raw()
    raw["causes"][0]["prior"] = 0.9
    with pytest.raises(ValidationError, match="priors must sum to 1"):
        knowledge.ProductKB.model_validate(raw)


def test_kb_rejects_undefined_sources():
    raw = _raw()
    raw["causes"][0]["sources"] = ["made_up_source"]
    with pytest.raises(ValidationError, match="undefined sources"):
        knowledge.ProductKB.model_validate(raw)


def test_kb_rejects_diy_steps_on_professional_only_procedures():
    raw = _raw()
    raw["procedures"]["refer_winding"]["steps"] = [{"text": {"en": "open it", "hi": "खोलें"}}]
    with pytest.raises(ValidationError, match="must not contain DIY steps"):
        knowledge.ProductKB.model_validate(raw)


@pytest.mark.parametrize("product", knowledge.available())
def test_every_product_is_consistent(product):
    kb = knowledge.load(product)
    assert kb.tier == "curated"
    assert kb.questions[0].safety, "a safety question must come first"
    for q in kb.questions:
        if q.safety:
            assert q.hazard in safety.HAZARDS
    for c in kb.causes:
        assert c.component in knowledge.components().components
    for pid, proc in kb.procedures.items():
        if proc.safety_level >= 2:  # risky steps must cite a source
            assert all(step.sources for step in proc.steps), pid
        for step in proc.steps:
            assert len(step.text.en) <= 140, f"{pid}: keep steps short"


# ---------- PII ----------


def test_scrub_removes_contacts():
    text = "call me on +91 98765 43210 or 9876543210, mail a.b@example.co.in, see https://x.y/z"
    out = pii.scrub(text)
    assert "98765" not in out and "@" not in out and "https" not in out
    assert out.count("[phone]") == 2


def test_scrub_keeps_ratings():
    assert pii.scrub("capacitor 2.5 uF 440V, model 1200") == "capacitor 2.5 uF 440V, model 1200"


# ---------- extraction ----------


def test_rules_only_extraction(kb):
    out = run(extract("mera pankha hum karta hai par bahut dheere chalta hai", None))
    assert out.item == "ceiling_fan" and not out.llm_used
    assert out.answers == {"hums": "yes", "slow": "yes"}


def test_rules_mark_other_fans_as_unsupported(kb):
    assert run(extract("my table fan is not working", None)).item == "other_item"


class RecordingProvider(FakeProvider):
    pass


def test_llm_answers_merge_over_rules_and_prompt_is_scrubbed(kb):
    reply = json.dumps(
        {
            "item": "ceiling_fan",
            "answers": {
                "ceiling_fan.push_spins": "yes",
                "ceiling_fan.slow": "no",
                "ceiling_fan.bogus": "yes",
                "headphones.wiggle": "yes",
            },
        }
    )
    fake = RecordingProvider(reply=reply)
    out = run(extract("fan hums, slow. call 9876543210", FallbackRouter([fake])))
    assert out.llm_used
    assert out.answers == {
        "hums": "yes",
        "slow": "no",
        "push_spins": "yes",
    }  # bogus and other-product ids dropped
    assert "9876543210" not in fake.calls[0].prompt


class Broken:
    name = "broken"
    model = "x"

    async def generate(self, request: LLMRequest) -> LLMResult:
        raise LLMUnavailable("down")


def test_llm_failure_falls_back_to_rules(kb):
    out = run(extract("ceiling fan hums", FallbackRouter([Broken()])))
    assert out.item == "ceiling_fan" and out.answers == {"hums": "yes"} and not out.llm_used


def test_non_json_llm_reply_falls_back_to_rules(kb):
    out = run(extract("ceiling fan hums", FallbackRouter([FakeProvider(reply="not json")])))
    assert out.answers == {"hums": "yes"} and not out.llm_used


def test_push_then_starts_word_order(kb):
    out = run(extract("my fan hums, and if I push the blades it starts", None))
    assert out.answers["push_spins"] == "yes"


class Exploding:
    name = "exploding"
    model = "x"

    async def generate(self, request: LLMRequest) -> LLMResult:
        raise RuntimeError("event loop is closed")


def test_unexpected_llm_errors_fall_back_to_rules(kb):
    out = run(extract("ceiling fan hums", FallbackRouter([Exploding()])))
    assert out.answers == {"hums": "yes"} and not out.llm_used


def test_non_object_json_falls_back_to_rules(kb):
    out = run(extract("ceiling fan hums", FallbackRouter([FakeProvider(reply="[1, 2]")])))
    assert out.answers == {"hums": "yes"} and not out.llm_used


@pytest.mark.parametrize(
    "text",
    [
        "remote wali car nahi chal rahi",
        "my remote control car won't move",
        "remote ki gaadi band hai",
    ],
)
def test_remote_control_toys_are_not_tv_remotes(text):
    assert run(extract(text, None)).answers.get("is_remote") == "no"
