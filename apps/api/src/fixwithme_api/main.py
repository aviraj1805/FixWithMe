import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__, ask, diagnose, identify, knowledge, safety
from .config import Settings, get_settings
from .llm import build_llm, build_verifier
from .outcomes import OutcomeStore
from .ratelimit import RateLimit
from .retrieval import build_retriever
from .web import WebAnswerer

log = logging.getLogger(__name__)


class Health(BaseModel):
    status: str
    version: str
    llm_provider: str
    retrieval: bool
    verifier: bool
    products: list[str]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Fix with Me API", version=__version__)

    try:
        app.state.llm = build_llm(settings)
    except ValueError:
        log.warning("no LLM provider configured; running in engine-only mode")
        app.state.llm = None
    app.state.verifier = build_verifier(settings)
    app.state.retriever = build_retriever(settings)
    app.state.web = (
        WebAnswerer(settings.gemini_api_key, settings.web_models)
        if settings.gemini_api_key and settings.web_models and "gemini" in settings.llm_chain
        else None
    )
    app.state.outcomes = OutcomeStore(settings)
    for product in knowledge.available():  # fail fast on an invalid knowledge file
        for q in knowledge.load(product).questions:
            if q.hazard and q.hazard not in safety.HAZARDS:
                raise ValueError(f"{product}/{q.id}: unknown hazard {q.hazard}")

    if settings.env != "test" and settings.rate_per_minute > 0:
        app.add_middleware(
            RateLimit, per_minute=settings.rate_per_minute, per_day=settings.rate_per_day
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", response_model=Health)
    async def health() -> Health:
        provider = app.state.llm.providers[0].name if app.state.llm else "none"
        return Health(
            status="ok",
            version=__version__,
            llm_provider=provider,
            retrieval=app.state.retriever.enabled,
            verifier=app.state.verifier is not None,
            products=knowledge.available(),
        )

    app.include_router(diagnose.router)
    app.include_router(ask.router)
    app.include_router(identify.router)
    return app


app = create_app()
