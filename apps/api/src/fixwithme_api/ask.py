"""Free-form questions (follow-ups after a diagnosis, and items outside the curated products)."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import knowledge, safety
from .answer import answer
from .diagnose import ConfirmOut, StopOut
from .knowledge import Lang
from .web import general_answer

router = APIRouter(prefix="/v1")


class AskRequest(BaseModel):
    question: Annotated[str, Field(min_length=2, max_length=500)]
    item: str | None = None
    lang: Lang = "en"
    safety_checked: bool = False
    confirm_hazard: str | None = None
    # "Ask anyway" for an item outside the curated products: if the corpus can't answer, fall back
    # to a web-grounded suggestion (Tier C, unverified).
    web: bool = False


class SourceOut(BaseModel):
    id: str
    title: str
    url: str | None
    license: str
    source_type: str


class ClaimOut(BaseModel):
    text: str
    sources: list[str]


class GuideOut(BaseModel):
    item: str
    procedure_id: str
    safety_level: int


class AskResponse(BaseModel):
    state: Literal["answer", "abstain", "stop", "confirm"]
    say: str
    claims: list[ClaimOut] = []
    sources: list[SourceOut] = []
    tier: Literal["curated", "sourced", "web", "general"] | None = None
    guides: list[GuideOut] = []  # full step-by-step guides behind the cited curated passages
    caution: str | None = None
    verified: bool = False
    dropped_unsupported: int = 0
    dropped_unsafe: int = 0
    stop: StopOut | None = None
    confirm: ConfirmOut | None = None
    search_html: str | None = None  # Google's search suggestions; must be shown with web answers


_ABSTAIN = {
    "en": "I'm not sure about that from what I know. A local technician can check it for you.",
    "hi": "मेरी जानकारी से इसका पक्का जवाब नहीं है। कोई लोकल मिस्त्री इसे जांच सकता है।",
}


_CAUTION = {
    "en": "This involves electrical work. Follow the full guide, including every safety step.",
    "hi": "इसमें बिजली का काम है। पूरी गाइड देखें और हर सुरक्षा कदम का पालन करें।",
}


_WEB_CAUTION = {
    "en": "General tips from a web search, not checked by us. If it uses power, unplug it first.",
    "hi": "वेब सर्च से सामान्य सुझाव, हमने जांचे नहीं हैं। बिजली से चलता है तो पहले प्लग निकालें।",
}


_GENERAL_CAUTION = {
    "en": "General tips from AI, not checked by us. If it uses power, unplug it first.",
    "hi": "AI के सामान्य सुझाव, हमने जांचे नहीं हैं। बिजली से चलता है तो पहले प्लग निकालें।",
}


def _guides(passages) -> list[GuideOut]:
    """kb:<item>:procedure:<id>:<lang> passages → their guides, so a summary never replaces one."""
    out: dict[tuple[str, str], GuideOut] = {}
    for p in passages:
        parts = p.id.split(":")
        if p.source_type == "kb" and len(parts) >= 4 and parts[2] == "procedure":
            out.setdefault(
                (parts[1], parts[3]),
                GuideOut(item=parts[1], procedure_id=parts[3], safety_level=p.safety_level or 0),
            )
    return list(out.values())


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request) -> AskResponse:
    if req.item is not None and req.item not in knowledge.available():
        raise HTTPException(status_code=422, detail=f"Unknown item {req.item!r}")
    if req.confirm_hazard:
        if req.confirm_hazard not in safety.HAZARDS:
            raise HTTPException(status_code=422, detail="Unknown hazard")
        payload = safety.stop_payload(req.confirm_hazard, req.lang)
        return AskResponse(state="stop", say=payload["title"], stop=StopOut(**payload))

    hazard, source = safety.screen(req.question, use_model=not req.safety_checked)
    if source == "rules" and not req.safety_checked and safety.informational(req.question):
        source = "model"  # a general question, not a report: ask "Just checking" once
    elif source == "rules" and req.safety_checked and safety.informational(req.question):
        source = None  # the user said it isn't happening to them
    if source == "rules":
        payload = safety.stop_payload(hazard, req.lang)
        return AskResponse(state="stop", say=payload["title"], stop=StopOut(**payload))
    if source == "model":
        text = safety.CONFIRM[hazard].get(req.lang)
        return AskResponse(state="confirm", say=text, confirm=ConfirmOut(hazard=hazard, text=text))

    state = request.app.state
    result = await answer(
        req.question, state.retriever, state.llm, state.verifier, req.item, req.lang
    )
    if result.state == "abstain" and req.web and req.item is None:
        web = await state.web.answer(req.question, req.lang) if state.web else None
        if web and web.claims:
            return AskResponse(
                state="answer",
                say=" ".join(t for t, _ in web.claims),
                claims=[
                    ClaimOut(text=t, sources=[f"web:{i}" for i in idx]) for t, idx in web.claims
                ],
                sources=[
                    SourceOut(
                        id=f"web:{i}", title=s.title, url=s.url, license="web", source_type="web"
                    )
                    for i, s in enumerate(web.sources)
                ],
                tier="web",
                caution=_WEB_CAUTION[req.lang],
                dropped_unsafe=web.dropped_unsafe,
                search_html=web.search_html,
            )
        steps = await general_answer(state.llm, req.question, req.lang) if state.llm else []
        if steps:
            return AskResponse(
                state="answer",
                say=" ".join(steps),
                claims=[ClaimOut(text=t, sources=[]) for t in steps],
                tier="general",
                caution=_GENERAL_CAUTION[req.lang],
            )
    if result.state == "abstain":
        return AskResponse(
            state="abstain",
            say=_ABSTAIN[req.lang],
            verified=result.verified,
            dropped_unsupported=result.dropped_unsupported,
            dropped_unsafe=result.dropped_unsafe,
        )
    tier = "curated" if all(p.source_type == "kb" for p in result.passages) else "sourced"
    guides = _guides(result.passages)
    risky = any(g.safety_level >= 2 for g in guides) or any(
        (p.safety_level or 0) >= 2 for p in result.passages
    )
    return AskResponse(
        state="answer",
        say=" ".join(c.text for c in result.claims),
        claims=[ClaimOut(text=c.text, sources=c.sources) for c in result.claims],
        sources=[
            SourceOut(
                id=p.id, title=p.title, url=p.url, license=p.license, source_type=p.source_type
            )
            for p in result.passages
        ],
        tier=tier,
        guides=guides,
        caution=_CAUTION[req.lang] if risky else None,
        verified=result.verified,
        dropped_unsupported=result.dropped_unsupported,
        dropped_unsafe=result.dropped_unsafe,
    )
