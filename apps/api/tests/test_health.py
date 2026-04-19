from fastapi.testclient import TestClient

def test_health_endpoint(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "artifacts" / "test.sqlite3"))
    monkeypatch.setenv("SKILL_ASSETS_ROOT", str(tmp_path / "skill_assets"))
    monkeypatch.setenv("FAKE_PROVIDER_ENABLED", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from app.core.config import get_settings
    from app.dependencies import get_repository
    from app.main import create_app

    get_settings.cache_clear()
    get_repository.cache_clear()
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "fake" in payload["configured_providers"]
