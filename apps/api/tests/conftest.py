import pytest

from fixwithme_api.config import Settings


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    """Tests never read apps/api/.env: it holds live keys (Gemini, Supabase), and a test must not
    write to the production database or spend free-tier quota."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in ("FWM_SUPABASE_URL", "FWM_SUPABASE_KEY", "FWM_GEMINI_API_KEY", "FWM_INGEST_TOKEN"):
        monkeypatch.delenv(name, raising=False)
