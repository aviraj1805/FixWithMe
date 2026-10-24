"""Photo → item + visible problem (R4 lean). The browser downscales the photo and strips EXIF
(canvas re-encode) before upload; the image is never stored."""

import base64
import binascii
import json
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import knowledge
from .extract import OTHER
from .knowledge import Lang
from .llm import LLMRequest

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")

MAX_BYTES = 1_500_000


class IdentifyRequest(BaseModel):
    image: Annotated[str, Field(max_length=2_100_000)]  # base64 JPEG/PNG/WebP
    mime: str = "image/jpeg"
    lang: Lang = "en"


class IdentifyResponse(BaseModel):
    item: str | None  # a curated product id, or None when it isn't one
    name: str  # what the photo shows, e.g. "TV remote"
    problem: str | None  # visible damage, if any
    text: str  # a first message for the chat, in the user's language


_SYSTEM = (
    "You look at a photo of a household item that may be broken. Identify the item and any "
    "visible problem (burn marks, corrosion, cracks, a loose wire, swelling). Do not describe "
    "people. Answer in {lang_name}."
)


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "item": {"type": "string", "enum": [*knowledge.available(), OTHER]},
            "name": {"type": "string"},
            "problem": {"type": "string"},
        },
        "required": ["item", "name", "problem"],
    }


@router.post("/identify", response_model=IdentifyResponse)
async def identify(req: IdentifyRequest, request: Request) -> IdentifyResponse:
    if req.mime not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Unsupported image type")
    try:
        data = base64.b64decode(req.image, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid image") from exc
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large")
    llm = request.app.state.llm
    if llm is None:
        raise HTTPException(status_code=503, detail="Photo identification is unavailable")
    products = ", ".join(f"{p} = {knowledge.load(p).names.en}" for p in knowledge.available())
    prompt = (
        f"Products I support: {products}. Use '{OTHER}' for anything else.\n"
        "Return the product id, a short name for the item, and the visible problem "
        "(empty if none is visible)."
    )
    try:
        res = await llm.generate(
            LLMRequest(
                prompt=prompt,
                system=_SYSTEM.format(
                    lang_name="Hindi (Devanagari)" if req.lang == "hi" else "English"
                ),
                json_schema=_schema(),
                images=((data, req.mime),),
                max_output_tokens=300,
            )
        )
        out = json.loads(res.text)
        if not isinstance(out, dict):
            raise ValueError("expected a JSON object")
    except Exception as exc:
        log.warning("identify failed: %s", exc)
        raise HTTPException(status_code=503, detail="Photo identification failed") from exc
    item = out.get("item")
    name = str(out.get("name") or "").strip()[:80] or ("item" if req.lang == "en" else "चीज़")
    problem = str(out.get("problem") or "").strip()[:200] or None
    return IdentifyResponse(
        item=item if item in knowledge.available() else None,
        name=name,
        problem=problem,
        text=f"{name}: {problem}" if problem else name,
    )
