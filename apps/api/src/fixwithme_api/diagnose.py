"""Diagnosis session API.

Sessions are stateless: the client sends back the answers collected so far, and the server
returns the next state. Nothing about the user is stored until they report an outcome.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import engine, knowledge, safety
from .engine import Answer
from .extract import OTHER, extract
from .knowledge import Lang

router = APIRouter(prefix="/v1")

State = Literal["question", "diagnosis", "stop", "confirm", "clarify", "unsupported"]


class StepRequest(BaseModel):
    text: Annotated[str, Field(max_length=1000)] | None = None
    answers: dict[str, Answer] = {}
    item: str | None = None  # a product id once known
    lang: Lang = "en"
    # Set after the user answers "no" to a classifier safety check, so it isn't asked again.
    safety_checked: bool = False
    # Set after the user answers "yes" to a classifier safety check.
    confirm_hazard: str | None = None


class Option(BaseModel):
    id: str
    name: str


class CauseOut(BaseModel):
    id: str
    name: str
    short: str
    p: float


class QuestionOut(BaseModel):
    id: str
    text: str
    safety: bool


class DiagnosisOut(BaseModel):
    cause_id: str
    cause: str
    confidence: float
    label: Literal["likely", "possible", "uncertain"]
    procedure_id: str
    procedure_title: str
    professional: bool


class StopOut(BaseModel):
    hazard: str
    title: str
    actions: list[str]
    call: str


class ConfirmOut(BaseModel):
    hazard: str
    text: str


class StepResponse(BaseModel):
    state: State
    say: str
    confirm: ConfirmOut | None = None
    item: str | None = None
    answers: dict[str, Answer] = {}
    options: list[Option] = []
    causes: list[CauseOut] = []
    question: QuestionOut | None = None
    diagnosis: DiagnosisOut | None = None
    stop: StopOut | None = None
    tier: Literal["verified", "curated"] | None = None
    llm_used: bool = False


_SAY = {
    "clarify": {"en": "Which one is it?", "hi": "यह कौन-सा है?"},
    "unsupported": {
        "en": "For now I can help with ceiling fans, extension boards, earphones, and toys or remotes. More soon!",
        "hi": "अभी मैं छत के पंखे, एक्सटेंशन बोर्ड, ईयरफ़ोन, और खिलौने या रिमोट में मदद कर सकता हूँ। जल्द और भी!",
    },
    "likely": {"en": "Most likely: {x}.", "hi": "सबसे ज़्यादा संभावना: {x}।"},
    "possible": {"en": "It might be: {x}.", "hi": "शायद: {x}।"},
    "uncertain": {
        "en": "I'm not sure yet. Best guess: {x}.",
        "hi": "अभी पक्का नहीं। मेरा अनुमान: {x}।",
    },
}


def _stop(
    hazard_id: str, req: StepRequest, answers: dict[str, Answer] | None = None
) -> StepResponse:
    payload = safety.stop_payload(hazard_id, req.lang)
    return StepResponse(
        state="stop", say=payload["title"], stop=StopOut(**payload), answers=answers or req.answers
    )


def _kb(item: str) -> knowledge.ProductKB:
    if item not in knowledge.available():
        raise HTTPException(status_code=422, detail=f"Unknown item {item!r}")
    return knowledge.load(item)


def _options(ids: list[str], lang: Lang) -> list[Option]:
    return [Option(id=i, name=knowledge.load(i).names.get(lang)) for i in ids]


@router.post("/sessions/step", response_model=StepResponse)
async def step(req: StepRequest, request: Request) -> StepResponse:
    item = req.item
    if item is not None:
        _kb(item)
    answers = dict(req.answers)
    llm_used = False

    if req.confirm_hazard:
        if req.confirm_hazard not in safety.HAZARDS:
            raise HTTPException(status_code=422, detail="Unknown hazard")
        return _stop(req.confirm_hazard, req)

    if req.text:
        hazard, source = safety.screen(req.text, use_model=not req.safety_checked)
        if source == "rules":
            return _stop(hazard, req)
        if source == "model":
            text = safety.CONFIRM[hazard].get(req.lang)
            return StepResponse(
                state="confirm",
                say=text,
                confirm=ConfirmOut(hazard=hazard, text=text),
                item=item,
                answers=req.answers,
            )
        found = await extract(req.text, request.app.state.llm, known_item=item)
        llm_used = found.llm_used
        if item is None:
            if found.item == OTHER:
                return StepResponse(
                    state="unsupported", say=_SAY["unsupported"][req.lang], llm_used=llm_used
                )
            if found.item in knowledge.available():
                item = found.item
            else:
                ids = found.candidates or knowledge.available()
                return StepResponse(
                    state="clarify",
                    say=_SAY["clarify"][req.lang],
                    options=_options(ids, req.lang),
                    llm_used=llm_used,
                )
        for qid, ans in found.answers.items():
            answers.setdefault(qid, ans)

    if item is None:
        return StepResponse(
            state="clarify",
            say=_SAY["clarify"][req.lang],
            options=_options(knowledge.available(), req.lang),
            answers=answers,
            llm_used=llm_used,
        )

    kb = knowledge.load(item)
    answers = {k: v for k, v in answers.items() if kb.question(k) is not None}
    for q in kb.questions:
        if q.safety and answers.get(q.id) == "yes":
            return _stop(q.hazard or "fire_smoke", req, answers)

    ranked = engine.posterior(kb, answers)
    causes = [
        CauseOut(
            id=r.cause_id,
            name=kb.cause(r.cause_id).name.get(req.lang),
            short=kb.cause(r.cause_id).short.get(req.lang),
            p=round(r.p, 3),
        )
        for r in ranked[:3]
    ]
    base = dict(item=item, answers=answers, causes=causes, tier=kb.tier, llm_used=llm_used)

    q = engine.next_question(kb, answers, ranked)
    if q is not None:
        return StepResponse(
            state="question",
            say=q.text.get(req.lang),
            question=QuestionOut(id=q.id, text=q.text.get(req.lang), safety=q.safety),
            **base,
        )

    top = kb.cause(ranked[0].cause_id)
    proc = kb.procedures[top.procedure]
    label = engine.confidence_label(ranked[0].p)
    return StepResponse(
        state="diagnosis",
        say=_SAY[label][req.lang].format(x=top.short.get(req.lang)),
        diagnosis=DiagnosisOut(
            cause_id=top.id,
            cause=top.name.get(req.lang),
            confidence=round(ranked[0].p, 3),
            label=label,
            procedure_id=top.procedure,
            procedure_title=proc.title.get(req.lang),
            professional=proc.safety_level >= 3,
        ),
        **base,
    )


@router.get("/procedures/{item}/{procedure_id}")
async def procedure(item: str, procedure_id: str, lang: Lang = "en") -> dict:
    kb = _kb(item)
    proc = kb.procedures.get(procedure_id)
    if proc is None:
        raise HTTPException(status_code=404, detail="Unknown procedure")

    def src(ids: list[str]) -> list[dict]:
        return [{"title": kb.sources[i].title, "url": kb.sources[i].url} for i in ids]

    return {
        "id": procedure_id,
        "item": kb.id,
        "tier": kb.tier,
        "title": proc.title.get(lang),
        "safety_level": proc.safety_level,
        "minutes": proc.minutes,
        "difficulty": proc.difficulty.get(lang) if proc.difficulty else None,
        "cost_inr": proc.cost_inr.model_dump() if proc.cost_inr else None,
        "tools": proc.tools.get(lang) if proc.tools else [],
        "part_spec": proc.part_spec.model_dump() if proc.part_spec else None,
        "steps": [
            {
                "text": s.text.get(lang),
                "caution": s.caution.get(lang) if s.caution else None,
                "sources": src(s.sources),
            }
            for s in proc.steps
        ],
        "verify": proc.verify.get(lang) if proc.verify else None,
        "prevent": proc.prevent.get(lang) if proc.prevent else None,
        "professional": proc.professional.get(lang) if proc.professional else None,
        "reason": proc.reason.get(lang) if proc.reason else None,
        "sources": src(sorted(proc.source_ids())),
    }


class OutcomeIn(BaseModel):
    item: str
    cause_id: str
    procedure_id: str
    resolved: bool
    answers: dict[str, Answer] = {}
    lang: Lang = "en"


@router.post("/outcomes")
async def outcome(body: OutcomeIn, request: Request) -> dict:
    kb = _kb(body.item)
    if body.procedure_id not in kb.procedures or body.cause_id not in {c.id for c in kb.causes}:
        raise HTTPException(status_code=422, detail="Unknown cause or procedure")
    valid = {q.id for q in kb.questions}
    row = {
        "item": kb.id,
        "kb_version": kb.version,
        "cause_id": body.cause_id,
        "procedure_id": body.procedure_id,
        "resolved": body.resolved,
        "answers": {k: v for k, v in body.answers.items() if k in valid},
        "lang": body.lang,
    }
    stored = await request.app.state.outcomes.save(row)
    return {"stored": stored}
