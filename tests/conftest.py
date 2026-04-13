import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def test_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SITE_EVENTS_BACKEND", "memory")
    monkeypatch.setenv("RUNTIME_API_KEY", "dev-runtime-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    return TestClient(app)
