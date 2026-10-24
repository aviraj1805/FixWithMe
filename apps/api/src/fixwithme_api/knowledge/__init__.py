"""Curated product knowledge (Tier A), loaded from YAML and validated on startup."""

import math
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

Lang = Literal["en", "hi"]
KNOWLEDGE_DIR = Path(__file__).parent


class Text(BaseModel):
    en: str
    hi: str

    def get(self, lang: Lang) -> str:
        return getattr(self, lang)


class TextList(BaseModel):
    en: list[str]
    hi: list[str]

    def get(self, lang: Lang) -> list[str]:
        return getattr(self, lang)


class Source(BaseModel):
    title: str
    url: str
    accessed: date


class Cause(BaseModel):
    id: str
    name: Text
    short: Text
    prior: float = Field(gt=0, lt=1)
    procedure: str
    sources: list[str]


class Question(BaseModel):
    id: str
    text: Text
    p_yes: dict[str, float]
    safety: bool = False


class Step(BaseModel):
    text: Text
    caution: Text | None = None
    sources: list[str] = []


class Cost(BaseModel):
    min: int = Field(ge=0)
    max: int = Field(ge=0)
    basis: Literal["estimate"]


class PartSpec(BaseModel):
    kind: str
    match: str
    sources: list[str]


class Procedure(BaseModel):
    title: Text
    safety_level: int = Field(ge=0, le=3)
    minutes: int | None = None
    difficulty: Text | None = None
    cost_inr: Cost | None = None
    tools: TextList | None = None
    part_spec: PartSpec | None = None
    steps: list[Step] = []
    verify: Text | None = None
    prevent: Text | None = None
    prevent_sources: list[str] = []
    professional: Text | None = None
    reason: Text | None = None
    sources: list[str] = []

    @model_validator(mode="after")
    def _professional_only_has_no_steps(self) -> "Procedure":
        if self.safety_level == 3 and self.steps:
            raise ValueError("safety_level 3 procedures must not contain DIY steps")
        if self.safety_level < 3 and not self.steps:
            raise ValueError("DIY procedures need steps")
        return self

    def source_ids(self) -> set[str]:
        ids = set(self.sources) | set(self.prevent_sources)
        for step in self.steps:
            ids |= set(step.sources)
        if self.part_spec:
            ids |= set(self.part_spec.sources)
        return ids


class ProductKB(BaseModel):
    id: str
    version: str
    review_status: Literal["draft", "reviewed"]
    names: Text
    sources: dict[str, Source]
    causes: list[Cause]
    questions: list[Question]
    procedures: dict[str, Procedure]

    @model_validator(mode="after")
    def _consistent(self) -> "ProductKB":
        cause_ids = {c.id for c in self.causes}
        if not math.isclose(sum(c.prior for c in self.causes), 1.0, abs_tol=1e-6):
            raise ValueError(f"{self.id}: cause priors must sum to 1")
        for q in self.questions:
            if set(q.p_yes) != cause_ids:
                raise ValueError(f"{self.id}/{q.id}: p_yes must cover exactly the causes")
            if not all(0 < p < 1 for p in q.p_yes.values()):
                raise ValueError(f"{self.id}/{q.id}: likelihoods must be strictly between 0 and 1")
        for c in self.causes:
            if c.procedure not in self.procedures:
                raise ValueError(f"{self.id}/{c.id}: unknown procedure {c.procedure}")
        used = {s for c in self.causes for s in c.sources}
        for p in self.procedures.values():
            used |= p.source_ids()
        missing = used - set(self.sources)
        if missing:
            raise ValueError(f"{self.id}: undefined sources {sorted(missing)}")
        return self

    @property
    def tier(self) -> Literal["verified", "curated"]:
        return "verified" if self.review_status == "reviewed" else "curated"

    def cause(self, cause_id: str) -> Cause:
        return next(c for c in self.causes if c.id == cause_id)

    def question(self, question_id: str) -> Question | None:
        return next((q for q in self.questions if q.id == question_id), None)


@lru_cache
def load(product_id: str) -> ProductKB:
    path = KNOWLEDGE_DIR / f"{product_id}.yaml"
    with path.open(encoding="utf-8") as f:
        return ProductKB.model_validate(yaml.safe_load(f))


def available() -> list[str]:
    return sorted(p.stem for p in KNOWLEDGE_DIR.glob("*.yaml"))
