"""Help with one step of a repair guide: the user is stuck and asks by text, voice or photo.

Answers stay inside the guide: Fixy explains or rephrases the step, says what a photo shows, and
sends the user to a professional instead of adding riskier steps."""

import base64
import binascii
import json
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import knowledge, safety
from .answer import unsafe
from .diagnose import StopOut
from .knowledge import Lang
from .llm import LLMRequest
from .pii import scrub

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")


class StepHelpRequest(BaseModel):
    item: str
    procedure_id: str
    step: Annotated[int, Field(ge=0, le=50)]
    question: Annotated[str, Field(max_length=500)] = ""
    image: Annotated[str | None, Field(max_length=2_100_000)] = None  # base64 JPEG
    lang: Lang = "en"


class StepHelpResponse(BaseModel):
    state: Literal["reply", "stop"]
    say: str
    stop: StopOut | None = None


_SYSTEM = (
    "You are Fixy, a friendly repair helper. The user is on one step of a repair guide and is "
    "confused. Using ONLY the guide below, answer in 1 to 3 short, simple sentences. You may "
    "rephrase the step, explain where a part is or what it looks like, or say whether their "
    "photo looks right for this step. Never add steps that are riskier than the guide, such as "
    "touching wires with the power on or opening other casings. If their photo shows burning, "
    "melting, sparks, exposed live wires, swelling or water near power, set danger to true. If "
    "you are not sure, tell them to ask a technician. Reply in {lang_name}."
)

_FALLBACK = {
    "en": "I'm not sure about that. Follow the step as written, or ask a technician to check it.",
    "hi": "मुझे इसका पक्का पता नहीं है। स्टेप जैसा लिखा है वैसा करें, या मिस्त्री से जांच करवाएं।",
}


@router.post("/step-help", response_model=StepHelpResponse)
async def step_help(req: StepHelpRequest, request: Request) -> StepHelpResponse:
    if req.item not in knowledge.available():
        raise HTTPException(status_code=422, detail="Unknown item")
    kb = knowledge.load(req.item)
    proc = kb.procedures.get(req.procedure_id)
    if proc is None or req.step >= max(len(proc.steps), 1):
        raise HTTPException(status_code=404, detail="Unknown step")
    if not req.question.strip() and not req.image:
        raise HTTPException(status_code=422, detail="Ask a question or send a photo")

    hazard, source = safety.screen(req.question) if req.question.strip() else (None, None)
    if source == "rules":
        payload = safety.stop_payload(hazard, req.lang)
        return StepHelpResponse(state="stop", say=payload["title"], stop=StopOut(**payload))

    images: tuple[tuple[bytes, str], ...] = ()
    if req.image:
        try:
            data = base64.b64decode(req.image, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Invalid image") from exc
        if len(data) > 1_500_000:
            raise HTTPException(status_code=413, detail="Image too large")
        images = ((data, "image/jpeg"),)

    llm = request.app.state.llm
    if llm is None:
        return StepHelpResponse(state="reply", say=_FALLBACK[req.lang])
    lines = []
    for i, s in enumerate(proc.steps):
        mark = ">> CURRENT STEP" if i == req.step else ""
        caution = f" (Caution: {s.caution.get(req.lang)})" if s.caution else ""
        lines.append(f"Step {i + 1}: {s.text.get(req.lang)}{caution} {mark}")
    guide = f"Guide: {proc.title.get(req.lang)} ({kb.names.get(req.lang)})\n" + "\n".join(lines)
    question = scrub(req.question.strip()) or (
        "Is this right for the current step?" if req.lang == "en" else "क्या यह इस स्टेप के लिए सही है?"
    )
    schema = {
        "type": "object",
        "properties": {"reply": {"type": "string"}, "danger": {"type": "boolean"}},
        "required": ["reply", "danger"],
    }
    try:
        res = await llm.generate(
            LLMRequest(
                prompt=f"{guide}\n\nUser: {question}",
                system=_SYSTEM.format(
                    lang_name="Hindi (Devanagari)" if req.lang == "hi" else "English"
                ),
                json_schema=schema,
                images=images,
                max_output_tokens=300,
            )
        )
        out = json.loads(res.text)
        reply = str(out.get("reply") or "").strip()
        danger = bool(out.get("danger"))
    except Exception as exc:
        log.warning("step help failed: %s", exc)
        return StepHelpResponse(state="reply", say=_FALLBACK[req.lang])
    if danger:
        payload = safety.stop_payload("fire_smoke", req.lang)
        return StepHelpResponse(
            state="stop", say=reply or payload["title"], stop=StopOut(**payload)
        )
    if not reply or unsafe(reply):
        return StepHelpResponse(state="reply", say=_FALLBACK[req.lang])
    return StepHelpResponse(state="reply", say=reply)
