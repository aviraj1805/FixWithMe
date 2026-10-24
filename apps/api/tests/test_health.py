from fastapi.testclient import TestClient

from fixwithme_api.config import Settings
from fixwithme_api.main import create_app


def test_health_reports_ok_and_version():
    client = TestClient(create_app(Settings(env="test", llm_chain=["fake"])))

    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["llm_provider"] == "fake"


def test_cors_allows_configured_origin_only():
    client = TestClient(
        create_app(
            Settings(env="test", llm_chain=["fake"], cors_origins=["https://fixwithme.example"])
        )
    )

    allowed = client.get("/health", headers={"Origin": "https://fixwithme.example"})
    denied = client.get("/health", headers={"Origin": "https://evil.example"})

    assert allowed.headers.get("access-control-allow-origin") == "https://fixwithme.example"
    assert "access-control-allow-origin" not in denied.headers
