from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.dependencies import actor_context_dependency
from app.main import create_app

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_runtime_security_headers_are_set(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_runtime_docs_are_disabled_by_default(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_runtime_docs_can_be_explicitly_enabled_but_require_auth(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_DOCS_ENABLED", "true")
    get_settings.cache_clear()
    app = create_app()

    try:
        with TestClient(app) as docs_client:
            assert docs_client.get("/docs").status_code == 401
            assert docs_client.get("/openapi.json").status_code == 401
            assert docs_client.get("/docs", headers=AUTH_HEADERS).status_code == 200
            assert docs_client.get("/openapi.json", headers=AUTH_HEADERS).status_code == 200
    finally:
        get_settings.cache_clear()


def test_protected_routes_fail_closed_when_runtime_api_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("RUNTIME_API_KEY", raising=False)
    get_settings.cache_clear()
    app = create_app()

    try:
        with TestClient(app) as local_client:
            response = local_client.get("/skills")
            assert response.status_code == 503
            assert response.json()["detail"] == "Runtime API key is not configured"
    finally:
        get_settings.cache_clear()


def test_actor_context_ignores_caller_headers_by_default(monkeypatch) -> None:
    monkeypatch.delenv("RUNTIME_ACTOR_HEADER_OVERRIDES_ENABLED", raising=False)
    get_settings.cache_clear()

    try:
        actor = actor_context_dependency(
            x_ares_org_id="org_attacker",
            x_ares_actor_id="user_attacker",
            x_ares_actor_type="user",
        )
        assert actor.org_id == "org_internal"
        assert actor.actor_id == "ares-runtime"
        assert actor.actor_type == "service"
    finally:
        get_settings.cache_clear()


def test_actor_context_header_overrides_require_explicit_enable(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_ACTOR_HEADER_OVERRIDES_ENABLED", "true")
    get_settings.cache_clear()

    try:
        actor = actor_context_dependency(
            x_ares_org_id="org_operator",
            x_ares_actor_id="user_operator",
            x_ares_actor_type="user",
        )
        assert actor.org_id == "org_operator"
        assert actor.actor_id == "user_operator"
        assert actor.actor_type == "user"
    finally:
        get_settings.cache_clear()


def test_validation_errors_do_not_echo_secret_values(client: TestClient) -> None:
    response = client.post(
        "/secrets",
        headers=AUTH_HEADERS,
        json={"name": "bad_secret", "secret_value": {"raw": "super-secret-token"}},
    )

    assert response.status_code == 422
    assert "super-secret-token" not in response.text
