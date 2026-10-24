import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__, diagnose, knowledge
from .config import Settings, get_settings
from .llm import build_llm
from .outcomes import OutcomeStore

log = logging.getLogger(__name__)


class Health(BaseModel):
    status: str
    version: str
    llm_provider: str
    products: list[str]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Fix with Me API", version=__version__)

    try:
        app.state.llm = build_llm(settings)
    except ValueError:
        log.warning("no LLM provider configured; running in engine-only mode")
        app.state.llm = None
    app.state.outcomes = OutcomeStore(settings)
    for product in knowledge.available():
        knowledge.load(product)  # fail fast on an invalid knowledge file

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
            status="ok", version=__version__, llm_provider=provider, products=knowledge.available()
        )

    app.include_router(diagnose.router)
    return app


app = create_app()
